import json,time,subprocess,sys,os,threading
from pathlib import Path
from dataclasses import dataclass,field,replace
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from app.tooling.contracts import REGISTRY,ToolEnvelope
from app.tooling.attestation import claim_key,evidence_key

@dataclass
class ToolContext:
    actor:str
    permissions:frozenset=field(default_factory=lambda:frozenset({'READ_ONLY'}))
    max_calls:int=32
    timeout:float=30
    deadline:float=field(default_factory=lambda:time.monotonic()+120)
    trace_id:str=field(default_factory=lambda:str(uuid4()))
    run_id:str|None=None
    audit:object=None
    database_url:str|None=None
    calls:int=0
    lock:object=field(default_factory=threading.Lock,repr=False)
    evidence_attested:set=field(default_factory=set,repr=False)
    claims_attested:set=field(default_factory=set,repr=False)

def process_executor(name,args,context):
    worker=Path(__file__).with_name('worker.py')
    env=os.environ.copy()
    if context.database_url:env['AEGIS_DATABASE_URL']=context.database_url
    env['PYTHONPATH']=str(worker.parents[2])
    # Fixed executable/script; no shell, arbitrary URL, supplied code or credentials in argv.
    p=subprocess.Popen([sys.executable,str(worker)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    try:
        out,err=p.communicate(json.dumps({'tool':name,'args':args,'actor':context.actor}).encode(),
            timeout=max(.01,min(context.timeout,context.deadline-time.monotonic())))
    except subprocess.TimeoutExpired:
        p.kill();p.communicate();return {'status':'failed','errors':[{'code':'TOOL_TIMEOUT','message':'Isolated tool exceeded its execution budget'}],'retryable':True}
    if p.returncode:return {'status':'failed','errors':[{'code':'WORKER_FAILED','message':'Tool worker failed; inspect restricted server diagnostics'}],'retryable':False}
    if len(out)>4_000_000:return {'status':'failed','errors':[{'code':'OUTPUT_LIMIT','message':'Tool output exceeded bounded size'}]}
    return json.loads(out)

class ToolGateway:
    def __init__(self,executor=None):self.executor=executor or process_executor
    def invoke(self,name,args,context,*,attempt=1,timeout=None):
        started=time.monotonic();sequence=None
        def failure(code,message,retryable=False):return {'status':'failed','errors':[{'code':code,'message':message}],'retryable':retryable}
        spec=REGISTRY.get(name)
        if spec is None:result=failure('UNKNOWN_TOOL','Tool is not allowlisted')
        else:
            try:parsed=spec.input.model_validate(args).model_dump(mode='json',exclude_none=True)
            except ValidationError:result=failure('INVALID_INPUT','Input does not match the tool schema')
            else:
                needed={spec.permission}
                if parsed.get('refresh'):needed.update({'EXTERNAL_NETWORK','WRITE'})
                if not needed<=context.permissions:result=failure('PERMISSION_DENIED','Server capability does not permit this operation')
                else:
                    with context.lock:
                        if context.calls>=context.max_calls:result=failure('CALL_BUDGET_EXCEEDED','Tool call budget exhausted')
                        elif time.monotonic()>=context.deadline:result=failure('RUN_TIMEOUT','Run deadline exceeded')
                        else:context.calls+=1;sequence=context.calls;result=None
                    if result is None:
                        try:
                            execution_context=replace(context,deadline=min(context.deadline,time.monotonic()+max(0,timeout))) if timeout is not None else context
                            result=self.executor(name,parsed,execution_context)
                        except LookupError:result=failure('NOT_FOUND','Requested record is unavailable')
                        except ValueError:result=failure('INVALID_STATE','Tool could not process the supplied state')
                        except Exception:result=failure('TOOL_FAILURE','Tool failed without disclosing internal details')
        result=ToolEnvelope(tool=name,trace_id=context.trace_id,duration_ms=max(0,int((time.monotonic()-started)*1000)),**jsonable_encoder(result))
        with context.lock:
            context.evidence_attested.update(evidence_key(ref) for ref in result.evidence_refs)
            claims=result.data.get('items',[]) if name=='get_claims' and isinstance(result.data,dict) else []
            if name in ('get_verification_result','verify_claim') and isinstance(result.data,dict) and result.data.get('claim'):
                claims=[{**result.data['claim'],'trusted':result.data.get('trusted',False)}]
            for claim in claims:
                if claim.get('trusted') and claim.get('verification_status')=='CONFIRMED' and any(
                    r.get('verified') and r.get('evidence_id') and r.get('stance')=='support' and r.get('claim_id')==str(claim.get('id'))
                    and r.get('claim_revision')==claim.get('revision') for r in result.evidence_refs):
                    context.claims_attested.add(claim_key(claim))
        if context.audit:context.audit(name,args,result,sequence,attempt)
        return result

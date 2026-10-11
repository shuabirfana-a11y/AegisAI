from uuid import uuid4
from app.runtime.contracts import ToolReceipt, ExecutionOutcome, TaskArtifact, TaskState, TaskContract
from app.tooling.contracts import ToolEnvelope
from app.runtime.executor import evidence, call_summaries
from app.utils.time import utcnow
from tests.agents.fixtures import task, context

CVE = 'CVE-2099-9999001'

def source(**overrides):
    return {'source_id':str(uuid4()),'raw_document_id':str(uuid4()),
        'url':'https://example.invalid/SYNTHETIC-advisory','locator':{'line':1},
        'retrieved_at':utcnow().isoformat(),'authority_level':'official','authority_scope':'SYNTHETIC',
        'is_current':True,'verified':False,'content_trust_level':'UNTRUSTED_EXTERNAL_CONTENT',**overrides}

def detail():
    return {'id':str(uuid4()),'canonical_id':CVE,'title':'SYNTHETIC vLLM issue',
        'description':'SYNTHETIC description','affected_versions':[{'id':str(uuid4()),
            'package_identifier_id':str(uuid4()),'raw_expression':'>=0.5,<0.7',
            'fixed':'0.7','is_current':True,'source_key':'SYNTHETIC'}],
        'cvss_assessments':[{'version':'3.1','base_score':9.0,'provider':'SYNTHETIC','is_current':True}],
        'cwe':[{'cwe_id':'CWE-94'}],
        'intelligence':{'pocs':[{'id':str(uuid4()),'canonical_url':'https://example.invalid/SYNTHETIC-poc',
                               'status':'confirmed','usability_status':'not_evaluated'}],
                        'patches':[{'patch_type':'fixed_version','release_version':'0.7','status':'candidate'}],
                        'claims':[],'conflicts':[]}}

def execution(data=None, refs=None, statuses=None, names=None):
    names=names or ['get_vulnerability']; statuses=statuses or ['success']*len(names)
    ctx=context(); inputs=[{'name':n,'arguments':{'target':CVE}} for n in names]
    item=TaskContract(task_id='lookup',description='SYNTHETIC investigation',allowed_tools=names,
                      max_tool_calls=len(names),input_data={'steps':inputs})
    receipts=[]
    for idx,(name,status) in enumerate(zip(names,statuses),1):
        now=utcnow()
        env=ToolEnvelope(tool=name,trace_id=str(ctx.trace_id),duration_ms=1,status=status,
            data=(data if data is not None else detail()),evidence_refs=refs if refs is not None else [source()],
            errors=[{'code':'SYNTHETIC_FAILURE','message':'SYNTHETIC'}] if status=='failed' else [])
        receipts.append(ToolReceipt(call_index=idx,name=name,arguments=inputs[idx-1]['arguments'],
            started_at=now,finished_at=now,envelope=env))
    state=TaskState.FAILED if 'failed' in statuses else TaskState.WAITING_REVIEW if 'no_result' in statuses else TaskState.SUCCESS
    art=TaskArtifact(run_id=ctx.run_id,task_id=item.task_id,status=state,start_time=utcnow(),end_time=utcnow(),
        result={'outputs':[{'tool':r.name,'status':r.envelope.status,'data':r.envelope.data} for r in receipts],
                'dependencies':{}},evidence=evidence(receipts),tool_calls=call_summaries(receipts))
    return item,ctx,ExecutionOutcome(artifact=art,receipts=receipts)

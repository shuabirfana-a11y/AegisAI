"""Run the published local Dify workflow against the real backend.

Uses only environment credentials. A blocked or failed run exits nonzero and is
never converted to an acceptance pass. Does not call a substitute workflow.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib import error, parse, request
import uuid

def safe_local_url(value: str) -> str:
    parsed = parse.urlsplit(value)
    if parsed.scheme not in ('http','https') or parsed.hostname not in ('127.0.0.1','localhost','::1'):
        raise ValueError('Dify API URL must be local loopback for this deployment.')
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip('/') != '/v1':
        raise ValueError('Dify API URL must have path /v1 without credentials/query/fragment.')
    return value.rstrip('/')

def safe_backend_url(value: str) -> str:
    parsed = parse.urlsplit(value)
    if (parsed.scheme not in ('http','https') or parsed.hostname not in ('127.0.0.1','localhost','::1')
        or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip('/') != '/api/v1'):
        raise ValueError('AegisAI API URL must be loopback with path /api/v1 and no credentials/query/fragment.')
    return value.rstrip('/')

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirects are disabled for authenticated local acceptance requests.')

def read_json(req, *, timeout):
    with request.build_opener(NoRedirect()).open(req,timeout=timeout) as response:
        body=response.read(2_000_001)
        if len(body)>2_000_000:
            raise ValueError('Acceptance response exceeds the bounded JSON budget.')
        result=json.loads(body)
        if not isinstance(result,dict):
            raise ValueError('Acceptance response must be a JSON object.')
        return result

def ticket_identity(ticket):
    if not isinstance(ticket,dict):
        raise ValueError('Assistant ticket must be a JSON object.')
    try:
        return str(uuid.UUID(ticket['run_id'])),str(uuid.UUID(ticket['trace_id']))
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        raise ValueError('Assistant ticket must contain backend run and trace UUIDs.') from exc

def evidence_key(ref):
    return json.dumps({key:ref.get(key) for key in ('raw_document_id','evidence_id','claim_id','claim_revision','url','locator')},sort_keys=True)

def validate_assistant_final(ticket,run,tasks,trace,*,expected_mode='auto'):
    """Validate final authenticated backend receipts, not a 202 submission.

    This checks transport and audit consistency. Current claim truth is enforced
    by the backend gate; it is not an independent benchmark or LLM certification.
    """
    run_id,trace_id=ticket_identity(ticket)
    if not all(isinstance(item,dict) for item in (run,tasks,trace)):
        raise ValueError('Final run/tasks/trace must be JSON objects.')
    if any(item.get('run_id')!=run_id or item.get('trace_id')!=trace_id for item in (run,trace)):
        raise ValueError('Final run or audit identifiers differ from the submitted ticket.')
    status=run.get('status')
    if status not in ('COMPLETED','WAITING_REVIEW') or not run.get('finished_at'):
        raise ValueError('Assistant has not reached a successful or review-required final state.')
    result=run.get('result')
    if not isinstance(result,dict) or not isinstance(result.get('gate'),dict):
        raise ValueError('Final assistant result has no integration gate.')
    gate=result['gate'].get('status')
    allowed={'COMPLETED':('PASS','PASS_WITH_WARNINGS'),'WAITING_REVIEW':('HUMAN_REVIEW_REQUIRED',)}
    if gate not in allowed[status]:
        raise ValueError('Assistant final status and integration gate are inconsistent.')
    if not isinstance(run.get('route'),dict) or (expected_mode=='deep' and run['route'].get('path')!='deep'):
        raise ValueError('Requested Deep execution has not been verified.')
    if not isinstance(result.get('answer'),str) or not result['answer'].strip():
        raise ValueError('Assistant final answer is missing.')
    plan=result.get('plan');artifacts=result.get('artifacts');task_rows=tasks.get('items');calls=trace.get('items')
    if not all(isinstance(rows,list) and rows and all(isinstance(row,dict) for row in rows) for rows in (plan,artifacts,task_rows,calls)):
        raise ValueError('Final plan, artifacts, tasks and tool audit must all be present.')
    planned=[row.get('task_id') for row in plan]
    if any(not isinstance(key,str) or not key for key in planned) or len(set(planned))!=len(planned):
        raise ValueError('Final plan contains invalid or duplicate task identifiers.')
    completed={row.get('task_id'):row for row in artifacts}
    reported={row.get('task_id'):row for row in task_rows}
    if set(planned)!=set(completed) or set(planned)!=set(reported) or len(completed)!=len(artifacts) or len(reported)!=len(task_rows):
        raise ValueError('Final task artifacts do not match the submitted execution plan.')
    for key,artifact in completed.items():
        if (artifact.get('trace_id')!=trace_id or artifact.get('status') not in ('success','partial','failed','blocked')
            or reported[key].get('status')!=artifact.get('status')):
            raise ValueError('Task trace or terminal task status is inconsistent.')
    audited=set()
    for call in calls:
        if not call.get('id') or not call.get('tool_name') or call.get('status') not in ('succeeded','partial','failed','timeout'):
            raise ValueError('Tool execution audit is incomplete.')
        refs=call.get('evidence_refs',[])
        if not isinstance(refs,list) or not all(isinstance(ref,dict) for ref in refs):
            raise ValueError('Tool evidence audit is malformed.')
        audited.update(evidence_key(ref) for ref in refs)
    refs=result.get('evidence_refs')
    if not isinstance(refs,list) or not refs:
        raise ValueError('Acceptance case has no final source evidence.')
    for ref in refs:
        if (not isinstance(ref,dict) or not ref.get('raw_document_id') or not ref.get('url') or not ref.get('locator')
            or evidence_key(ref) not in audited):
            raise ValueError('Final source evidence is absent from the tool audit.')
    facts=result.get('facts',[])
    if not isinstance(facts,list) or (status=='WAITING_REVIEW' and facts):
        raise ValueError('Review-required execution cannot publish confirmed facts.')
    for fact in facts:
        if not isinstance(fact,dict) or not any(ref.get('verified') is True and ref.get('claim_id')==fact.get('claim_id')
            and ref.get('claim_revision')==fact.get('claim_revision') for ref in refs):
            raise ValueError('Confirmed fact has no matching verified evidence receipt.')
    return {'backend_run_id':run_id,'backend_trace_id':trace_id,'backend_status':status,'gate_status':gate,
            'task_count':len(planned),'tool_call_count':len(calls),'evidence_count':len(refs),
            'backend_final_result_verified':True,'backend_run':run,'backend_tasks':tasks,'backend_trace':trace}

def await_assistant_final(ticket,fetch,*,expected_mode='auto',timeout=150,now=time.monotonic,pause=time.sleep):
    run_id,_=ticket_identity(ticket)
    path='/assistant/runs/'+run_id
    deadline=now()+timeout
    while now()<deadline:
        run=fetch(path)
        if not isinstance(run,dict):
            raise ValueError('Polled assistant run must be a JSON object.')
        if run.get('status') in ('COMPLETED','WAITING_REVIEW','FAILED','CANCELLED','TIMEOUT'):
            return validate_assistant_final(ticket,run,fetch(path+'/tasks'),fetch(path+'/trace'),expected_mode=expected_mode)
        pause(.5)
    raise TimeoutError('Assistant final result did not arrive within the acceptance deadline.')

def redact(value, secrets):
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret,'[REDACTED]')
        return value
    if isinstance(value, list):
        return [redact(item,secrets) for item in value]
    if isinstance(value, dict):
        return {key:('[REDACTED]' if any(part in key.lower() for part in ('authorization','api_key','token','password')) else redact(item,secrets)) for key,item in value.items()}
    return value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=['assistant','tool'], default='assistant')
    parser.add_argument('--question', default='CVE-2026-64849 的 CVSS 是多少？')
    parser.add_argument('--mode', choices=['auto','fast','deep'],default='fast')
    parser.add_argument('--target',default='CVE-2026-64849')
    parser.add_argument('--asset-id',default='')
    parser.add_argument('--realtime',action='store_true')
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'runtime'/'smoke.local.json')
    options=parser.parse_args()
    api_key_name='DIFY_APP_API_KEY' if options.kind=='assistant' else 'DIFY_TOOL_APP_API_KEY'
    api_key=os.environ.get(api_key_name,'')
    secrets=[api_key,os.environ.get('AEGIS_ASSET_TOKEN','')]
    record={'recorded_at':datetime.now(timezone.utc).isoformat(),'kind':options.kind,
            'status':'BLOCKED','dify_runtime_verified':False,'backend_workflow_call_verified':False,
            'backend_submission_verified':False,'backend_final_result_verified':False,
            'reason':None}
    exit_code=2
    try:
        base=safe_local_url(os.environ.get('DIFY_API_URL','http://127.0.0.1:8088/v1'))
        console=base.removesuffix('/v1')
        try:
            with request.build_opener(NoRedirect()).open(console+'/install',timeout=5) as response:
                record['dify_console_http_status']=response.status
        except (error.URLError,TimeoutError,OSError):
            record['reason']='Local Dify console unavailable. Check Bootstrap-Dify.ps1 runtime status and prerequisites.'
            raise RuntimeError(record['reason'])
        if not api_key:
            record['reason']=api_key_name+' is missing. Import/publish the workflow and configure its secret before smoke.'
            raise RuntimeError(record['reason'])
        inputs={'target':options.target}
        if options.kind=='assistant':
            inputs={'question':options.question,'mode':options.mode,'request_key':'dify-smoke-'+str(uuid.uuid4()),
                    'realtime':'true' if options.realtime else 'false','asset_id':options.asset_id,'target':options.target}
        data={'inputs':inputs,'response_mode':'blocking','user':os.environ.get('DIFY_END_USER','aegis-local-phase9')}
        req=request.Request(base+'/workflows/run',data=json.dumps(data,ensure_ascii=False).encode('utf-8'),
                            headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},method='POST')
        body=read_json(req,timeout=320)
        run=body.get('data',{})
        record['workflow_run_id']=body.get('workflow_run_id') or run.get('id')
        record['dify_status']=run.get('status') or body.get('status')
        if record['dify_status'] != 'succeeded':
            record['status']='FAILED'
            record['reason']='Dify workflow did not succeed.'
            record['dify_error']=run.get('error')
            raise RuntimeError(record['reason'])
        uuid.UUID(record['workflow_run_id'])
        record['dify_runtime_verified']=True
        outputs=run.get('outputs') or body.get('outputs') or {}
        if type(outputs.get('http_status')) is not int or not 200 <= outputs['http_status'] < 300:
            raise ValueError('Workflow did not return a successful backend HTTP status.')
        result=json.loads(outputs['result_json'])
        if not isinstance(result,dict):
            raise ValueError('Workflow backend result is not a JSON object.')
        if options.kind=='tool':
            required={'tool','status','data','evidence_refs','warnings','errors','retryable','trace_id','duration_ms'}
            if not required.issubset(result) or result['tool']!='get_vulnerability' or not result['trace_id']:
                raise ValueError('Workflow did not return the expected auditable ToolEnvelope.')
            if result['status']=='failed':
                raise ValueError('Backend tool failed; preserve the failure rather than claiming PASS.')
            record.update(status='PASS_REAL_DIFY_HTTP_BRIDGE',backend_workflow_call_verified=True)
            record['reason']='Actual local Dify tool workflow returned its auditable tool result; no LLM provider is certified.'
        else:
            if outputs['http_status']!=202:
                raise ValueError('Assistant bridge must return an accepted 202 backend ticket.')
            ticket_identity(result)
            record.update(backend_submission_verified=True,backend_ticket=result)
            backend=safe_backend_url(os.environ.get('AEGIS_API_URL','http://127.0.0.1:8000/api/v1'))
            backend_token=os.environ.get('AEGIS_ASSET_TOKEN','')
            if not backend_token:
                raise ValueError('AEGIS_ASSET_TOKEN is required to read the submitted owner-scoped final run.')
            def fetch(path):
                req=request.Request(backend+path,headers={'Authorization':'Bearer '+backend_token,'Accept':'application/json'})
                value=read_json(req,timeout=15)
                record['last_backend_run' if not path.endswith(('/tasks','/trace')) else 'backend_tasks' if path.endswith('/tasks') else 'backend_trace']=value
                return value
            record.update(await_assistant_final(result,fetch,expected_mode=options.mode))
            record.update(status='PASS_REAL_DIFY_ASSISTANT_FINAL',backend_workflow_call_verified=True)
            record['reason']='Actual Dify submission and final backend run/tasks/trace/evidence/gate verified; gate status is preserved. No LLM or benchmark certification.'
        record.update(backend_http_status=outputs['http_status'],backend_result=result)
        exit_code=0
    except error.HTTPError as exc:
        record.update(status='FAILED',reason='Acceptance API HTTP '+str(exc.code))
        exit_code=1
    except (ValueError,KeyError,TypeError,AttributeError) as exc:
        record.update(status='FAILED',reason=str(exc))
        exit_code=1
    except (error.URLError,TimeoutError,OSError,RuntimeError) as exc:
        if record['reason'] is None:
            record.update(status='FAILED',reason=str(exc))
            exit_code=1
    record=redact(record,secrets)
    options.output.parent.mkdir(parents=True,exist_ok=True)
    options.output.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:record[key] for key in ('status','reason','dify_runtime_verified','backend_workflow_call_verified')},ensure_ascii=False))
    return exit_code

if __name__=='__main__':
    raise SystemExit(main())

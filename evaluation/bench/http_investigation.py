"""Public HTTP investigation adapter; no annotation, database or model access."""
import math,time
from uuid import uuid4
import httpx
from .schema import Prediction,ClaimOutput,reject_labels
from .data import canonical
from .adapters import backend_imports


def api_models():
    backend_imports()
    from app.investigation_api import schemas
    return schemas


def build_request(question,binding=None):
    context=question.input_context
    reject_labels(context)
    binding=dict(binding or {});reject_labels(binding)
    if set(binding)-{'asset_id','component_id','snapshot_id','component','target'}:
        raise ValueError('UNSUPPORTED_BINDING_FIELDS')
    assets=context.get('assets',[])
    if not isinstance(assets,list) or len(assets)>1:raise ValueError('MULTI_ASSET_SCOPE_UNSUPPORTED')
    values={**context,**(assets[0] if assets else {})}
    targets=values.get('targets',[])
    if targets and (not isinstance(targets,list) or len(targets)!=1):raise ValueError('MULTI_TARGET_SCOPE_UNSUPPORTED')
    target=values.get('target') or (targets[0] if targets else None)
    if binding.get('target') and binding['target']!=target:raise ValueError('TARGET_BINDING_MISMATCH')
    scope={k:v for k,v in binding.items() if k in {'asset_id','component_id','snapshot_id'}}
    if target:scope['target']=target
    component=values.get('component')
    if isinstance(component,dict):
        allowed={'name','ecosystem','package_name','namespace','purl','version','package_identifier_id'}
        if set(component)-allowed:raise ValueError('UNSUPPORTED_COMPONENT_FIELDS')
        component=dict(component)
    elif component:
        component={'name':component,'package_name':component,'ecosystem':values.get('ecosystem')}
    else:component={}
    if 'version' in values:component['version']=values['version']
    supplied=binding.get('component') or {}
    if not isinstance(supplied,dict):raise ValueError('INVALID_COMPONENT_BINDING')
    for key,value in supplied.items():
        if key in component and component[key] is not None and component[key]!=value:
            raise ValueError('COMPONENT_BINDING_MISMATCH')
    if component or supplied:scope['component']={**component,**supplied}
    needs_asset=question.category in {'version','risk','multihop'} and bool(component or assets)
    if needs_asset and not (scope.get('asset_id') and scope.get('component_id')):
        raise ValueError('ASSET_BINDING_REQUIRED')
    raw={'user_query':question.question,'asset_scope':scope,
         'options':{'objective_profile':'asset_risk_v1' if needs_asset else 'vulnerability_overview_v1'},
         'idempotency_key':'bench-'+uuid4().hex}
    return api_models().InvestigationCreateRequest.model_validate(raw).model_dump(mode='json',exclude_none=True)


def project_answer(question,raw,*,trace=None,artifacts=None):
    # The original domain validator checks frozen fact/citation references.
    backend_imports()
    from app.orchestration.answer_contracts import AnswerEnvelope
    e=AnswerEnvelope.model_validate(raw)
    answer={'native_answer_status':e.answer_status,'native_gate_status':e.integration_status,
            'native_citations':[c.model_dump(mode='json') for c in e.citations]}
    if e.answer_status in {'FAILED','CANCELLED'}:
        return Prediction(question_id=question.id,baseline='aegisai',status='FAILED',answer=answer,
                          error_code='INVESTIGATION_'+e.answer_status)
    risk=e.risk_assessment
    if risk:
        if risk.conclusion_scope=='ACCEPTED' or risk.risk_level=='UNKNOWN':
            answer.update(affected=risk.version_match_status,risk_level=risk.risk_level,
                          priority=risk.priority,verification_status=risk.verification_status)
        else:answer['native_risk_observation']=risk.model_dump(mode='json')
    if artifacts and artifacts.get('verification'):
        v=artifacts['verification'];answer['verification_status']=v['verification_status']
        answer['version_observations']=v.get('version_observations',[])
        answer['impact_version_evidence']=v.get('impact_version_evidence',[])
    fixes=sorted({f.value['version'] for f in e.verified_claims if str(f.claim_type)=='FIXED_VERSION' and f.value.get('version')})
    if fixes:answer.update(fixed_versions=fixes,patch_status='CONFIRMED_FIX')
    # No absent PoC, risk or fact field is filled from question or reference gold.
    if any(str(f.claim_type) in {'POC_EXISTS','POC_ASSOCIATION'} for f in e.verified_claims):
        answer['poc_status']='POC_CANDIDATE'
    claims=[ClaimOutput(claim_id=f.claim_id,statement=f'{f.claim_type}: {canonical(f.value)}') for f in e.verified_claims]
    # Keep textual/derived conclusions available to independent outcome review.
    claims.append(ClaimOutput(claim_id='native-summary',statement=e.summary or canonical(answer)))
    claims.extend(ClaimOutput(claim_id='native-finding-'+str(i),statement=text) for i,text in enumerate(e.key_findings))
    if risk:claims.append(ClaimOutput(claim_id='native-risk',statement=canonical(risk.model_dump(mode='json'))))
    claims.extend(ClaimOutput(claim_id='native-action-'+str(i),statement=canonical(a.model_dump(mode='json')))
                  for i,a in enumerate(e.recommended_actions))
    tools=set()
    for run in (trace or {}).get('agent_runs',[]):
        tools.update(t['tool'] for t in run['tool_calls'] if t['status']=='success' and run['task_statuses'].get(t['task_id'])=='SUCCESS')
    hops=[name for name,names in {'vulnerability':{'get_vulnerability','investigate_vulnerability'},
        'version':{'inspect_component_version'},'asset':{'get_asset'},
        'risk':{'analyze_risk_snapshot','analyze_asset_impact_snapshot','prioritize_remediation_snapshot'}}.items() if tools&names]
    return Prediction(question_id=question.id,baseline='aegisai',status='SUCCEEDED',answer=answer,claims=claims,
        abstained=e.answer_status in {'INCOMPLETE','REVIEW_REQUIRED'} or bool(risk and risk.risk_level=='UNKNOWN'),
        completed_hops=hops)


class HTTPFailure(Exception):
    def __init__(self,code):self.code=code;super().__init__(code)


class InvestigationHTTPAdapter:
    name='aegisai'
    recorded=False

    def __init__(self,*,client,token,bindings=None,timeout=180,poll_interval=.25,expected_mode='REAL'):
        if not math.isfinite(timeout) or not 0<timeout<=600 or not math.isfinite(poll_interval) or not 0<=poll_interval<=10:
            raise ValueError('INVALID_HTTP_BUDGET')
        self.client=client;self.token=token;self.bindings=bindings or {};self.timeout=timeout
        self.poll_interval=poll_interval;self.expected_mode=expected_mode;self.records={}
        self.configuration={'model':{},'native_admission_status':'PUBLIC_HTTP_WITH_APPROVED_GOLD_GATE'}

    def _call(self,method,path,model,record,*,body=None,deadline=None):
        remaining=deadline-time.monotonic() if deadline else 10
        if remaining<=0:raise HTTPFailure('INVESTIGATION_TIMEOUT')
        response=self.client.request(method,path,json=body,headers={'Authorization':'Bearer '+self.token},
            timeout=min(10,remaining),follow_redirects=False)
        record['endpoints'].append({'method':method,'path':path,'http_status':response.status_code})
        if not 200<=response.status_code<300:raise HTTPFailure('HTTP_'+str(response.status_code))
        if len(response.content)>4*1024*1024:raise HTTPFailure('RESPONSE_SIZE_LIMIT')
        try:return model.model_validate(response.json()).model_dump(mode='json')
        except (ValueError,TypeError):raise HTTPFailure('INVALID_RESPONSE_SCHEMA') from None

    def run(self,question,sources):
        started=time.monotonic();deadline=started+self.timeout
        record={'question_id':question.id,'transport':'HTTP','endpoints':[],'completed':False}
        self.records[question.id]=record;identifier=None
        try:body=build_request(question,self.bindings.get(question.id))
        except ValueError:
            return Prediction(question_id=question.id,baseline=self.name,status='NOT_EVALUATED',error_code='REQUEST_BINDING_INVALID')
        if not self.token:
            return Prediction(question_id=question.id,baseline=self.name,status='NOT_EVALUATED',error_code='AUTHENTICATION_NOT_CONFIGURED')
        models=api_models()
        try:
            record['request']=body
            created=self._call('POST','/api/investigations',models.InvestigationCreateResponse,record,body=body,deadline=deadline)
            identifier=created['investigation_id'];record['investigation_id']=identifier
            while True:
                state=self._call('GET',f'/api/investigations/{identifier}/status',models.InvestigationStatusResponse,record,deadline=deadline)
                if state['investigation_id']!=identifier or state['logical_investigation_id']!=identifier:
                    raise HTTPFailure('INVESTIGATION_ID_MISMATCH')
                if state['current_stage'] in {'COMPLETED','WAITING_REVIEW','FAILED','CANCELLED'}:break
                time.sleep(min(self.poll_interval,max(0,deadline-time.monotonic())))
            trace=self._call('GET',f'/api/investigations/{identifier}/trace',models.TraceResponse,record,deadline=deadline)
            if trace['investigation_id']!=identifier or trace['logical_investigation_id']!=identifier:
                raise HTTPFailure('TRACE_ID_MISMATCH')
            mode=trace.get('model_execution')
            if not mode or mode['execution_mode']!=self.expected_mode or (self.expected_mode=='REAL' and mode['provider']=='mock'):
                raise HTTPFailure('MODEL_EXECUTION_MODE_MISMATCH')
            if not trace['planner'] or trace['planner']['validation_status']!='VALIDATED':raise HTTPFailure('PLANNING_FAILED')
            artifacts=self._call('GET',f'/api/investigations/{identifier}/artifacts',models.ArtifactResponse,record,deadline=deadline)
            gate=self._call('GET',f'/api/investigations/{identifier}/integration',models.IntegrationResponse,record,deadline=deadline)
            answer=self._call('GET',f'/api/investigations/{identifier}/answer',models.AnswerResponse,record,deadline=deadline)
            if (artifacts['investigation_id']!=identifier or answer['logical_investigation_id']!=identifier
                or answer['integration_result_id']!=gate['integration_id'] or trace['integration_result_id']!=gate['integration_id']
                or answer['integration_status']!=gate['status'] or trace['answer_id']!=answer['answer_id']
                or trace['planner']['planner_run_id']!=state['planner_run_id']):raise HTTPFailure('ANSWER_BINDING_MISMATCH')
            for name in ('investigation','verification','analysis'):
                artifact=artifacts[name]
                if artifact and artifact['run_id']!=state[name+'_run_id']:raise HTTPFailure('ARTIFACT_RUN_MISMATCH')
            if not artifacts['investigation'] or not artifacts['verification']:raise HTTPFailure('REQUIRED_AGENT_ARTIFACT_MISSING')
            for name in ('verification','analysis'):
                artifact=artifacts[name]
                if artifact and not any(r['run_id']==artifact['run_id'] and any(
                    ref['artifact_id']==artifact['artifact_id'] for ref in r['artifact_references']) for r in trace['agent_runs']):
                    raise HTTPFailure('ARTIFACT_TRACE_MISMATCH')
            for expected in ('environment','exposure','version'):
                desired=question.input_context.get(expected)
                observations=artifacts['verification'].get('version_observations',[])
                if desired is not None and body['asset_scope'].get('asset_id') and (
                    len(observations)!=1 or observations[0].get(expected)!=desired):raise HTTPFailure('OBSERVED_ASSET_INPUT_MISMATCH')
            record.update(status=state,trace=trace,artifacts=artifacts,integration=gate,answer=answer,completed=True)
            prediction=project_answer(question,answer,trace=trace,artifacts=artifacts)
            return prediction.model_copy(update={'latency_ms':(time.monotonic()-started)*1000,
                'metadata':{'provider':mode['provider'],'model':mode['model'],'is_mock':mode['execution_mode']=='MOCK',
                'prompt_version':trace['planner']['prompt_version'],'logical_investigation_id':identifier,
                'native_status':answer['answer_status'],'native_priority_taxonomy':True}})
        except (HTTPFailure,httpx.HTTPError,ValueError,TypeError) as error:
            code=error.code if isinstance(error,HTTPFailure) else 'HTTP_TIMEOUT' if isinstance(error,httpx.TimeoutException) else 'HTTP_ADAPTER_FAILED'
            record['error_code']=code
            if identifier and code in {'HTTP_TIMEOUT','INVESTIGATION_TIMEOUT'}:
                try:
                    response=self.client.post(f'/api/investigations/{identifier}/cancel',headers={'Authorization':'Bearer '+self.token},
                        json={'acknowledge':True},timeout=5,follow_redirects=False)
                    record['timeout_cancel']={'http_status':response.status_code,'acknowledged':200<=response.status_code<300}
                except httpx.HTTPError:record['timeout_cancel']={'error_code':'CANCEL_TRANSPORT_FAILED'}
            return Prediction(question_id=question.id,baseline=self.name,status='FAILED',error_code=code,
                error='Controlled HTTP failure; no answer fabricated',latency_ms=(time.monotonic()-started)*1000)

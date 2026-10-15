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


def input_values(question):
    context=question.input_context
    assets=context.get('assets',[])
    if not isinstance(assets,list) or len(assets)>1:raise ValueError('MULTI_ASSET_SCOPE_UNSUPPORTED')
    if assets and not isinstance(assets[0],dict):raise ValueError('INVALID_ASSET_INPUT')
    asset=context.get('asset')
    if asset is not None and not isinstance(asset,dict):raise ValueError('INVALID_ASSET_INPUT')
    if asset is not None and assets:raise ValueError('AMBIGUOUS_ASSET_INPUT')
    nested=asset if asset is not None else (assets[0] if assets else {})
    if any(key in context and context[key]!=value for key,value in nested.items()):
        raise ValueError('INPUT_CONTEXT_CONFLICT')
    return {**context,**nested}


def build_request(question,binding=None):
    context=question.input_context;reject_labels(context)
    binding=dict(binding or {});reject_labels(binding)
    if set(binding)-{'asset_id','component_id','snapshot_id','component','target'}:
        raise ValueError('UNSUPPORTED_BINDING_FIELDS')
    values=input_values(question);assets=context.get('assets',[])
    api_models() # reuse the existing backend import path, no network or model call
    from app.agents.investigation.normalization import normalize_question
    normalized=normalize_question(question.question,values,binding)
    if normalized.input_status=='AMBIGUOUS':raise ValueError('QUESTION_NORMALIZATION_AMBIGUOUS')
    if normalized.vulnerability_id is not None:values['target']=normalized.vulnerability_id
    if normalized.component is not None:values['component']=normalized.component
    if normalized.version is not None or 'version' in values or \
        normalized.component is not None and 'version' in normalized.component:values['version']=normalized.version
    from .question_contract import BenchmarkQuestionContract
    # Validate only original question input and real inventory bindings. This
    # local diagnostic contract is never sent as annotation metadata to the API.
    BenchmarkQuestionContract.from_input(question.category,question.question,values,binding)
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
        if key not in component or component[key]!=value:
            raise ValueError('COMPONENT_BINDING_MISMATCH')
    needs_asset=question.category in {'version','risk'} or (question.category=='multihop' and bool(component or assets or scope.get('asset_id')))
    # An exact-target overview needs no deployed component. Passing its hint as
    # AssetScope.component makes the existing Planner require version input.
    # Keep component-only search requests without a target unchanged.
    if (needs_asset or not target) and (component or supplied):scope['component']={**component,**supplied}
    if needs_asset and not (scope.get('asset_id') and scope.get('component_id')):
        raise ValueError('ASSET_BINDING_REQUIRED')
    raw={'user_query':question.question,'asset_scope':scope,
         'options':{'objective_profile':'asset_risk_v1' if needs_asset else 'overview_v1'},
         'idempotency_key':'bench-'+uuid4().hex}
    return api_models().InvestigationCreateRequest.model_validate(raw).model_dump(mode='json',exclude_none=True)


def project_answer(question,raw,*,trace=None,artifacts=None):
    # The original domain validator checks frozen fact/citation references.
    backend_imports()
    from app.orchestration.answer_contracts import AnswerEnvelope
    # Validate HTTP metadata separately; it is not part of the immutable domain
    # envelope and must not alter any fact, evidence or metric projection.
    public=api_models().AnswerResponse.model_validate(raw)
    e=AnswerEnvelope.model_validate(public.model_dump(mode='python',exclude={'result_version'}))
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


def validate_bindings(question,body,state,trace,artifacts,gate,answer):
    """Bind public projections together; never invent or independently judge facts."""
    identifier=state['investigation_id']
    if (trace['original_question']!=question.question or answer['original_question']!=question.question
        or answer['trace_reference']!=identifier):raise HTTPFailure('QUESTION_BINDING_MISMATCH')
    by_schema={a['schema_version']:a for name in ('investigation','verification','analysis')
               if (a:=artifacts[name]) is not None}
    traced={(r['run_id'],a['task_id'],a['artifact_id']) for r in trace['agent_runs'] for a in r['artifact_references']}
    def identity(ref):return ref['run_id'],ref['task_id'],ref['artifact_id']
    def check_ref(ref):
        artifact=by_schema.get(ref['schema_version'])
        if not artifact or identity(ref)!=identity(artifact):raise HTTPFailure('SOURCE_ARTIFACT_MISMATCH')
    for artifact in by_schema.values():
        if identity(artifact) not in traced:raise HTTPFailure('ARTIFACT_TRACE_MISMATCH')
    for ref in gate['artifact_references']+gate['final_result_references']+gate['partial_result_references']:check_ref(ref)
    collected={a['run_id'] for a in by_schema.values()}
    if (set(gate['source_run_ids'])!=collected or set(answer['agent_run_references'])!=collected
        or set(answer['accepted_source_run_references'])!=set(gate['source_run_ids'])
        or {identity(r) for r in gate['artifact_references']}!={identity(a) for a in by_schema.values()}):
        raise HTTPFailure('SOURCE_RUN_MISMATCH')
    # Gate logical identity is its own stable key, not the Orchestrator ID.
    if gate['run_id']!=artifacts['investigation']['run_id']:raise HTTPFailure('GATE_RUN_MISMATCH')
    for collection,field in (('verified_claims','source_artifact'),('disputed_claims','verification_artifact'),
        ('citations','verification_artifact'),('evidence_observations','verification_artifact'),
        ('affected_assets','source_artifact'),('recommended_actions','source_artifact')):
        for item in answer[collection]:check_ref(item[field])
    if answer['risk_assessment']:check_ref(answer['risk_assessment']['source_artifact'])
    verification=artifacts['verification']
    if (verification['source_run_id']!=artifacts['investigation']['run_id']
        or verification['source_artifact_id']!=artifacts['investigation']['artifact_id']):
        raise HTTPFailure('VERIFICATION_SOURCE_MISMATCH')
    assessments={x['claim']['claim_id']:x for x in verification['claims']}
    for fact in answer['verified_claims']:
        checked=assessments.get(fact['claim_id'])
        if (not checked or checked['status']!='CONFIRMED' or checked['claim']['value']!=fact['value']
            or checked['claim']['claim_type']!=fact['claim_type']):
            raise HTTPFailure('VERIFIED_FACT_MISMATCH')
    evidence={x['evidence_id']:x for x in verification['supporting_evidence']+verification['conflicting_evidence']}
    for citation in answer['citations']:
        stored=evidence.get(citation['evidence_id'])
        if not stored or any(stored[k]!=citation[k] for k in ('claim_id','source_id','raw_document_id','observation_id','hash','reference')):
            raise HTTPFailure('CITATION_EVIDENCE_MISMATCH')
    if answer['risk_assessment']:
        if not artifacts['analysis'] or any(answer['risk_assessment'][field]!=artifacts['analysis'][field]
            for field in ('risk_level','priority','affected','verification_status','asset_match_status','version_match_status')):
            raise HTTPFailure('RISK_VIEW_MISMATCH')
    scope=body['asset_scope'];values=input_values(question)
    if scope.get('target') and scope['target'] not in {
        artifacts['investigation']['canonical_id'],artifacts['investigation']['vulnerability_id']}:
        raise HTTPFailure('TARGET_BINDING_MISMATCH')
    if scope.get('asset_id'):
        observations=verification.get('version_observations',[])
        if len(observations)!=1:raise HTTPFailure('OBSERVED_ASSET_INPUT_MISMATCH')
        observation=observations[0]
        if any(observation[k]!=scope[k] for k in ('asset_id','component_id')):
            raise HTTPFailure('OBSERVED_ASSET_INPUT_MISMATCH')
        component=values.get('component')
        desired=dict(component) if isinstance(component,dict) else {'name':component} if component else {}
        if 'version' in values:desired['version']=values['version']
        for field,value in desired.items():
            # The existing request's name is a display hint; an explicit
            # package_name is the identity checked by the original resolver.
            if field=='name' and desired.get('package_name'):continue
            observed_field='component' if field=='name' else field
            if observation.get(observed_field)!=value:raise HTTPFailure('OBSERVED_ASSET_INPUT_MISMATCH')
        for field in ('environment','exposure','criticality'):
            if field in values and observation.get(field)!=values[field]:raise HTTPFailure('OBSERVED_ASSET_INPUT_MISMATCH')
        origin=observation['source_artifact']
        # Public Trace lists primary outputs; an asset subtask output need not be
        # among them. Require the original investigation run and successful task.
        if origin['run_id']!=artifacts['investigation']['run_id'] or not any(
            r['run_id']==origin['run_id'] and r['task_statuses'].get(origin['task_id'])=='SUCCESS'
            for r in trace['agent_runs']):raise HTTPFailure('OBSERVATION_SOURCE_MISMATCH')
        for asset in answer['affected_assets']:
            if (asset['asset_id']!=scope['asset_id'] or asset['component_id']!=scope['component_id']
                or asset['deployed_version']!=observation['version']):raise HTTPFailure('ANSWER_ASSET_MISMATCH')


class InvestigationHTTPAdapter:
    name='aegisai'
    recorded=False

    def __init__(self,*,client,token,bindings=None,timeout=180,poll_interval=.25,expected_mode='REAL'):
        if not math.isfinite(timeout) or not 0<timeout<=600 or not math.isfinite(poll_interval) or not 0<=poll_interval<=10:
            raise ValueError('INVALID_HTTP_BUDGET')
        self.client=client;self.token=token;self.bindings=bindings or {};self.timeout=timeout
        self.poll_interval=poll_interval;self.expected_mode=expected_mode;self.records={}
        if expected_mode not in {'REAL','MOCK'}:raise ValueError('INVALID_EXPECTED_MODEL_MODE')
        self.configuration={'model':{},'native_admission_status':'PUBLIC_HTTP_WITH_APPROVED_GOLD_GATE'}

    def _call(self,method,path,model,record,*,body=None,deadline=None):
        remaining=deadline-time.monotonic() if deadline else 10
        if remaining<=0:raise HTTPFailure('INVESTIGATION_TIMEOUT')
        record['http_attempted']=True
        response=self.client.request(method,path,json=body,headers={'Authorization':'Bearer '+self.token},
            timeout=min(10,remaining),follow_redirects=False)
        record['endpoints'].append({'method':method,'path':path,'http_status':response.status_code})
        if not 200<=response.status_code<300:raise HTTPFailure('HTTP_'+str(response.status_code))
        if len(response.content)>4*1024*1024:raise HTTPFailure('RESPONSE_SIZE_LIMIT')
        try:result=model.model_validate(response.json()).model_dump(mode='json')
        except (ValueError,TypeError):raise HTTPFailure('INVALID_RESPONSE_SCHEMA') from None
        record['created' if method=='POST' else path.rsplit('/',1)[-1].split('?',1)[0]]=result
        return result

    def run(self,question,sources):
        started=time.monotonic();deadline=started+self.timeout
        record={'question_id':question.id,'transport':'HTTP','endpoints':[],'completed':False,'http_attempted':False}
        self.records[question.id]=record;identifier=None
        try:body=build_request(question,self.bindings.get(question.id))
        except ValueError:
            record['error_code']='REQUEST_BINDING_INVALID'
            return Prediction(question_id=question.id,baseline=self.name,status='NOT_EVALUATED',error_code='REQUEST_BINDING_INVALID')
        if not self.token:
            record['error_code']='AUTHENTICATION_NOT_CONFIGURED'
            return Prediction(question_id=question.id,baseline=self.name,status='NOT_EVALUATED',error_code='AUTHENTICATION_NOT_CONFIGURED')
        models=api_models()
        try:
            record['request']=body
            created=self._call('POST','/api/investigations',models.InvestigationCreateResult,record,body=body,deadline=deadline)
            if created.get('status')=='NEED_CONTEXT':
                record.update(completed=True,context_required=True,investigation_created=False)
                return Prediction(question_id=question.id,baseline=self.name,status='NOT_EVALUATED',
                    answer={'native_context_status':created['status'],'missing_fields':created['missing_fields']},
                    abstained=True,latency_ms=(time.monotonic()-started)*1000,
                    metadata={'execution_mode':'NOT_STARTED','investigation_created':False})
            identifier=created['investigation_id'];record['investigation_id']=identifier
            while True:
                state=self._call('GET',f'/api/investigations/{identifier}/status',models.InvestigationStatusResponse,record,deadline=deadline)
                if state['investigation_id']!=identifier or state['logical_investigation_id']!=identifier:
                    raise HTTPFailure('INVESTIGATION_ID_MISMATCH')
                if (state['current_stage'] in {'COMPLETED','WAITING_REVIEW','FAILED','CANCELLED'}
                        and state.get('processing_complete',True)):break
                time.sleep(min(self.poll_interval,max(0,deadline-time.monotonic())))
            version_query='?version=2' if state.get('result_version',1)==2 else ''
            trace=self._call('GET',f'/api/investigations/{identifier}/trace{version_query}',models.TraceResponse,record,deadline=deadline)
            if trace['investigation_id']!=identifier or trace['logical_investigation_id']!=identifier:
                raise HTTPFailure('TRACE_ID_MISMATCH')
            mode=trace.get('model_execution')
            if not mode or mode['execution_mode']!=self.expected_mode or (self.expected_mode=='REAL' and mode['provider']=='mock'):
                raise HTTPFailure('MODEL_EXECUTION_MODE_MISMATCH')
            if not trace['planner'] or trace['planner']['validation_status']!='VALIDATED':raise HTTPFailure('PLANNING_FAILED')
            artifacts=self._call('GET',f'/api/investigations/{identifier}/artifacts{version_query}',models.ArtifactResponse,record,deadline=deadline)
            gate=self._call('GET',f'/api/investigations/{identifier}/integration{version_query}',models.IntegrationResponse,record,deadline=deadline)
            answer=self._call('GET',f'/api/investigations/{identifier}/answer{version_query}',models.AnswerResponse,record,deadline=deadline)
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
            validate_bindings(question,body,state,trace,artifacts,gate,answer)
            prediction=project_answer(question,answer,trace=trace,artifacts=artifacts)
            record['completed']=True
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
            observed=record.get('trace',{});mode=observed.get('model_execution') or {}
            metadata={k:mode[k] for k in ('provider','model') if k in mode}
            if mode:metadata['is_mock']=mode['execution_mode']=='MOCK'
            if observed.get('planner'):metadata['prompt_version']=observed['planner']['prompt_version']
            if identifier:metadata['logical_investigation_id']=identifier
            return Prediction(question_id=question.id,baseline=self.name,status='FAILED',error_code=code,
                error='Controlled HTTP failure; no answer fabricated',latency_ms=(time.monotonic()-started)*1000,metadata=metadata)

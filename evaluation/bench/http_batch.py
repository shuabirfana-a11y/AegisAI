"""Native bounded batch transport, not a new planner or scoring policy."""
import math,time
from uuid import UUID,uuid4
from .schema import Prediction,ClaimOutput,reject_labels

def models():
    from .adapters import backend_imports
    backend_imports()
    from app.investigation_api import multi_asset_schemas
    return multi_asset_schemas

def original_assets(question):
    context=question.input_context;reject_labels(context)
    assets=context.get('assets')
    if not isinstance(assets,list) or len(assets)<2:raise ValueError('MULTI_ASSET_INPUT_REQUIRED')
    if any(not isinstance(a,dict) or not isinstance(a.get('id'),str) or not a['id'] for a in assets):
        raise ValueError('ORIGINAL_ASSET_ID_REQUIRED')
    if len({a['id'] for a in assets})!=len(assets):raise ValueError('DUPLICATE_ORIGINAL_ASSET_ID')
    return assets

def binding_map(question,binding):
    assets=original_assets(question);binding=dict(binding or {});reject_labels(binding)
    if set(binding)!={'assets'} or not isinstance(binding['assets'],list):raise ValueError('BATCH_BINDING_REQUIRED')
    rows=binding['assets']
    if any(not isinstance(r,dict) or set(r)!={'input_id','asset_id','component_id'} for r in rows):
        raise ValueError('UNSUPPORTED_BATCH_BINDING_FIELDS')
    if len(rows)!=len(assets) or {r['input_id'] for r in rows}!={a['id'] for a in assets}:
        raise ValueError('BATCH_ORIGINAL_SCOPE_MISMATCH')
    if len({r['input_id'] for r in rows})!=len(rows):raise ValueError('BATCH_ORIGINAL_SCOPE_MISMATCH')
    for row in rows:
        UUID(row['asset_id']);UUID(row['component_id'])
    if len({r['asset_id'] for r in rows})!=len(rows):raise ValueError('BATCH_ASSET_SCOPE_MISMATCH')
    return {r['input_id']:r for r in rows}

def build_batch_request(question,binding=None,*,timeout=180):
    assets=original_assets(question);context=question.input_context
    targets=context.get('targets',[])
    if targets and (not isinstance(targets,list) or len(targets)!=1):raise ValueError('MULTI_TARGET_SCOPE_UNSUPPORTED')
    target=context.get('target') or (targets[0] if targets else None)
    from .adapters import backend_imports
    backend_imports()
    from app.agents.investigation.normalization import normalize_question
    normalized=normalize_question(question.question,{k:v for k,v in context.items() if k!='assets'}, {})
    if normalized.input_status=='AMBIGUOUS':raise ValueError('QUESTION_NORMALIZATION_AMBIGUOUS')
    target=normalized.vulnerability_id or target
    if not target:raise ValueError('BATCH_TARGET_REQUIRED')
    if not math.isfinite(timeout) or not 1<=timeout<=600:raise ValueError('INVALID_HTTP_BUDGET')
    rows=binding_map(question,binding)
    return models().BatchRequest(vulnerability_id=target,asset_ids=tuple(rows[a['id']]['asset_id'] for a in assets),
        timeout_seconds=int(timeout),child_timeout_seconds=min(300,int(timeout)),
        idempotency_key='bench-batch-'+uuid4().hex).model_dump(mode='json')

def run_batch(adapter,question):
    from .http_investigation import HTTPFailure
    started=time.monotonic();deadline=started+adapter.timeout;identifier=None
    record={'question_id':question.id,'transport':'HTTP_BATCH','endpoints':[],'children':[],
        'completed':False,'http_attempted':False};adapter.records[question.id]=record
    try:body=build_batch_request(question,adapter.bindings.get(question.id),timeout=adapter.timeout)
    except ValueError as error:
        code=str(error) if str(error) in {'BATCH_TARGET_REQUIRED','MULTI_TARGET_SCOPE_UNSUPPORTED'} else 'REQUEST_BINDING_INVALID'
        record['error_code']=code
        return Prediction(question_id=question.id,baseline=adapter.name,status='NOT_EVALUATED',error_code=code)
    if not adapter.token:
        record['error_code']='AUTHENTICATION_NOT_CONFIGURED'
        return Prediction(question_id=question.id,baseline=adapter.name,status='NOT_EVALUATED',error_code=record['error_code'])
    try:
        record['request']=body;schema=models().BatchResponse
        result=adapter._call('POST','/api/investigations/batches',schema,record,body=body,deadline=deadline)
        identifier=result['batch_id'];record['batch_id']=identifier
        rows=binding_map(question,adapter.bindings.get(question.id));assets=original_assets(question)
        native={r['asset_id']:a for a in assets if (r:=rows[a['id']])}
        while result['execution_status'] not in {'COMPLETED','FAILED','CANCELLED','TIMED_OUT'}:
            time.sleep(min(adapter.poll_interval,max(0,deadline-time.monotonic())))
            result=adapter._call('GET','/api/investigations/batches/'+identifier,schema,record,deadline=deadline)
            if result['batch_id']!=identifier:raise HTTPFailure('BATCH_ID_MISMATCH')
        record['batch_response']=result
        if result['execution_mode']!=adapter.expected_mode or (adapter.expected_mode=='REAL' and result['model_provider']=='mock'):
            raise HTTPFailure('MODEL_EXECUTION_MODE_MISMATCH')
        if {i['snapshot']['asset_id'] for i in result['items']}!=set(native):raise HTTPFailure('BATCH_ASSET_SCOPE_MISMATCH')
        if result['execution_status']!='COMPLETED':raise HTTPFailure('BATCH_'+result['execution_status'])
        claims=[];hops=set();modes=[]
        for item in result['items']:
            source=native[item['snapshot']['asset_id']];row=rows[source['id']]
            if item['snapshot']['selected_component_id']!=row['component_id']:raise HTTPFailure('BATCH_COMPONENT_BINDING_MISMATCH')
            context={k:v for k,v in question.input_context.items() if k not in {'assets','triage_policy'}}
            context.update({k:v for k,v in source.items() if k not in {'id','scenario'}})
            # A plain component name is an input display/name field, not a
            # separately supplied canonical package_name. Keep that distinction.
            comp=context.get('component');comp=dict(comp) if isinstance(comp,dict) else {
                'name':comp,'ecosystem':context.get('ecosystem')}
            if 'version' in context:comp['version']=context['version']
            selected=next((c for c in item['snapshot']['components'] if c['component_id']==row['component_id']),None)
            if selected is None or selected.get('version')!=comp.get('version'):
                raise HTTPFailure('BATCH_VERSION_BINDING_MISMATCH')
            context['component']=comp;context['target']=body['vulnerability_id']
            child=question.model_copy(update={'input_context':context})
            child_record={'endpoints':[],'investigation_id':item['investigation_id'],'transport':'HTTP_ADMITTED_BATCH_CHILD'}
            record['children'].append({'input_id':source['id'],'asset_id':row['asset_id'],'record':child_record})
            if item['investigation_id'] is None:
                if item['execution_status']!='NEED_CONTEXT':raise HTTPFailure('BATCH_CHILD_NOT_ADMITTED')
                child_record['context_required']=True;continue
            local={'asset_scope':{'asset_id':row['asset_id'],'component_id':row['component_id'],
                'target':body['vulnerability_id'],'component':comp}}
            p=adapter.read_existing(item['investigation_id'],child,local,child_record,deadline,
                expected_version=item['result_version'],use_trace_question=True)
            a=child_record['answer'];gate=child_record['integration']
            if a['answer_id']!=item['answer_id'] or gate['integration_id']!=item['integration_result_id']:
                raise HTTPFailure('BATCH_CHILD_REFERENCE_MISMATCH')
            modes.append(p.metadata)
            for c in p.claims:claims.append(c.model_copy(update={'claim_id':source['id']+':'+c.claim_id}))
            hops.update(p.completed_hops)
        id_map={r['asset_id']:r['input_id'] for r in rows.values()}
        summary=result['summary']
        if any(id not in id_map for id in (*summary['actionable_asset_ids'],*summary['unresolved_asset_ids'])):
            raise HTTPFailure('BATCH_SUMMARY_SCOPE_MISMATCH')
        answer={'priority_asset_ids':[id_map[id] for id in summary['actionable_asset_ids']],
            'unknown_asset_ids':[id_map[id] for id in summary['unresolved_asset_ids']],
            'native_batch_status':result['execution_status'],'native_batch_id':identifier,
            'native_asset_results':[{'input_id':id_map[i['snapshot']['asset_id']],
                'impact':i['impact'],'risk_level':i['risk_level'],'priority':i['priority'],
                'gate_status':i['gate_status'],'execution_status':i['execution_status']} for i in result['items']]}
        claims.append(ClaimOutput(claim_id='native-batch-summary',statement='Bounded native batch: '+str(answer)))
        record['completed']=True
        return Prediction(question_id=question.id,baseline=adapter.name,status='SUCCEEDED',answer=answer,
            claims=claims,abstained=bool(summary['unresolved_asset_ids']),completed_hops=sorted(hops),
            latency_ms=(time.monotonic()-started)*1000,metadata={'is_mock':result['execution_mode']=='MOCK',
                'provider':result['model_provider'],'model':result['model_name'],
                'prompt_version':next((m['prompt_version'] for m in modes if m and m.get('prompt_version')),None),
                'batch_id':identifier,'execution_mode':result['execution_mode']})
    except (HTTPFailure,ValueError,TypeError) as error:
        import re
        record['error_class']=type(error).__name__
        if isinstance(error,ValueError) and re.fullmatch(r'[A-Z][A-Z_]{3,64}',str(error)):
            record['adapter_error_code']=str(error)
        code=error.code if isinstance(error,HTTPFailure) else 'HTTP_ADAPTER_FAILED'
    except Exception as error:
        import httpx
        if not isinstance(error,httpx.HTTPError):raise
        code='HTTP_TIMEOUT' if isinstance(error,httpx.TimeoutException) else 'HTTP_ADAPTER_FAILED'
    record['error_code']=code
    if identifier and code in {'INVESTIGATION_TIMEOUT','HTTP_TIMEOUT'}:
        import httpx
        try:
            response=adapter.client.post('/api/investigations/batches/'+identifier+'/cancel',
                headers={'Authorization':'Bearer '+adapter.token},timeout=5,follow_redirects=False)
            record['timeout_cancel']={'http_status':response.status_code}
        except httpx.HTTPError:record['timeout_cancel']={'error_code':'CANCEL_TRANSPORT_FAILED'}
    return Prediction(question_id=question.id,baseline=adapter.name,status='FAILED',error_code=code,
        latency_ms=(time.monotonic()-started)*1000,error='Controlled batch HTTP failure; all observed children retained')

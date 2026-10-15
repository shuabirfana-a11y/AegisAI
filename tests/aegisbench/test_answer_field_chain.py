"""Synthetic contract regressions; never creates or changes approved answers."""
import importlib,json
from uuid import uuid4
import httpx
import pytest
from evaluation.bench.schema import Question
from tests.aegisbench.test_http_investigation import envelope

def module():return importlib.import_module('evaluation.bench.http_investigation')
def batch_question(target=True):
    context={'component':'vllm','ecosystem':'PyPI','assets':[
        {'id':'original-a','component':'vllm','version':'0.6.0'},
        {'id':'original-b','component':'vllm','version':'0.7.0'}]}
    if target:context['target']='CVE-2099-0001'
    return Question(id='synthetic-parent-label',category='multihop',question='Prioritize these owned assets',
        origin='TEST_FIXTURE',source_ids=['synthetic-source'],input_context=context)
def batch_binding():return {'assets':[{'input_id':id,'asset_id':str(uuid4()),'component_id':str(uuid4())}
    for id in ('original-a','original-b')]}
def builder():
    f=getattr(module(),'build_batch_request',None)
    assert callable(f),'Existing multi-asset API must have an input-only HTTP adapter'
    return f

def test_confirmed_vendor_identity_reaches_existing_fact_projection():
    q=batch_question();e=envelope()
    e['verified_claims'][0].update(claim_type='VENDOR_CONFIRMED',value={'cve':'CVE-2099-0001','repository':'vendor/project'})
    p=module().project_answer(q,e)
    assert p.answer.get('cve')=='CVE-2099-0001'

def test_question_identity_does_not_fill_missing_confirmed_fact():
    p=module().project_answer(batch_question(),envelope())
    assert 'cve' not in p.answer

def test_batch_request_uses_native_ids_without_original_label_names():
    q=batch_question();b=batch_binding();body=builder()(q,b,timeout=180)
    assert body['vulnerability_id']=='CVE-2099-0001'
    assert body['asset_ids']==[x['asset_id'] for x in b['assets']]
    assert q.id not in json.dumps(body) and 'original-a' not in json.dumps(body)
    assert body['timeout_seconds']==180 and body['child_timeout_seconds']==180

@pytest.mark.parametrize('change',['missing','duplicate','budget'])
def test_batch_binding_cannot_omit_duplicate_or_increase_scope(change):
    q=batch_question();b=batch_binding()
    if change=='missing':b['assets'].pop()
    if change=='duplicate':b['assets'][1]['asset_id']=b['assets'][0]['asset_id']
    if change=='budget':b['max_supplement_rounds']=8
    with pytest.raises(ValueError):builder()(q,b,timeout=180)

def test_multi_asset_discovery_without_target_preserves_unavailability():
    seen=[]
    def handler(request):seen.append(request);return httpx.Response(500)
    q=batch_question(False)
    with httpx.Client(base_url='http://127.0.0.1:9',transport=httpx.MockTransport(handler)) as client:
        a=module().InvestigationHTTPAdapter(client=client,token='SYNTHETIC',bindings={q.id:batch_binding()})
        p=a.run(q,{})
    assert not seen and p.status=='NOT_EVALUATED'
    assert p.error_code=='BATCH_TARGET_REQUIRED'

def test_explicit_question_cve_uses_existing_normalizer_for_batch_request():
    q=batch_question(False).model_copy(update={'question':'Compare these assets for CVE-2099-0001'})
    assert builder()(q,batch_binding())['vulnerability_id']=='CVE-2099-0001'

def test_conflicting_question_and_context_targets_are_not_selected_silently():
    q=batch_question().model_copy(update={'question':'Compare these assets for CVE-2099-0002'})
    with pytest.raises(ValueError):builder()(q,batch_binding())

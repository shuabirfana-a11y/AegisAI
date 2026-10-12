"""Synthetic protocol controls only; no approved dataset records are created."""
import importlib,json
from pathlib import Path
from uuid import uuid4
import httpx
import pytest
from evaluation.bench.schema import Question

ROOT=Path(__file__).resolve().parents[2]


def module():
    try:return importlib.import_module('evaluation.bench.http_investigation')
    except ModuleNotFoundError:pytest.fail('Full investigation HTTP adapter is missing')


def question(category='risk',**context):
    return Question(id='synthetic-question-affected-label',category=category,
        question='Investigate the supplied component and version',origin='TEST_FIXTURE',source_ids=['synthetic-source'],
        input_context={'target':'CVE-2099-0001','component':'vllm','ecosystem':'PyPI','version':'0.6.0',**context})


def binding(**changes):return {'asset_id':str(uuid4()),'component_id':str(uuid4()),**changes}


def envelope(scenario='PASS'):
    return json.loads((ROOT/'AegisAI_FRONTEND_HANDOFF_PACKAGE/mock/answer-demo.json').read_text(encoding='utf-8'))['scenarios'][scenario]


def test_only_original_question_and_matching_inventory_reach_request():
    b=binding();q=question()
    body=module().build_request(q,b)
    assert body['user_query']==q.question
    assert body['asset_scope']['asset_id']==b['asset_id']
    assert body['asset_scope']['component']['version']=='0.6.0'
    assert q.id not in json.dumps(body)
    assert body['idempotency_key']!=module().build_request(q,b)['idempotency_key']


def test_binding_cannot_override_version_or_include_nested_gold():
    with pytest.raises(ValueError):
        module().build_request(question(),binding(component={'name':'vllm','ecosystem':'PyPI','version':'9.9.9'}))
    with pytest.raises(ValueError):
        module().build_request(question(),binding(nested={'expected_answer':{'risk_level':'LOW'}}))


def test_missing_binding_and_multi_asset_scope_are_not_silently_filled():
    with pytest.raises(ValueError,match='ASSET_BINDING_REQUIRED'):module().build_request(question())
    with pytest.raises(ValueError,match='MULTI_ASSET'):
        module().build_request(question(assets=[{'component':'vllm'},{'component':'torch'}]),binding())


def test_native_confirmed_risk_is_projected_without_frozen_reference_answers():
    p=module().project_answer(question(),envelope())
    assert p.status=='SUCCEEDED' and p.answer['affected']=='AFFECTED'
    assert p.answer['risk_level']=='HIGH' and p.answer['priority']=='P2'
    assert p.claims and all(not c.evidence_refs for c in p.claims)


def test_explicit_native_unknown_remains_unknown_not_safe():
    e=envelope();e.update(answer_status='INCOMPLETE',integration_status='REPLAN_REQUIRED')
    e['risk_assessment'].update(risk_level='UNKNOWN',priority='REVIEW_REQUIRED',affected=None,
        version_match_status='UNKNOWN',conclusion_scope='OBSERVATION')
    for a in e['recommended_actions']:a['conclusion_scope']='OBSERVATION'
    p=module().project_answer(question(),e)
    assert p.status=='SUCCEEDED' and p.abstained is True
    assert p.answer['affected']=='UNKNOWN' and p.answer['risk_level']=='UNKNOWN'


def test_blocked_definite_observation_is_not_delivered_as_accepted_risk():
    e=envelope();e.update(answer_status='INCOMPLETE',integration_status='REPLAN_REQUIRED')
    e['risk_assessment']['conclusion_scope']='OBSERVATION'
    for a in e['recommended_actions']:a['conclusion_scope']='OBSERVATION'
    p=module().project_answer(question(),e)
    assert 'risk_level' not in p.answer and 'affected' not in p.answer
    assert p.answer['native_risk_observation']['risk_level']=='HIGH'


def test_failed_answer_does_not_earn_unknown_or_safe_prediction():
    p=module().project_answer(question(),envelope('ORCHESTRATION_FAILED'))
    assert p.status=='FAILED' and p.abstained is None
    assert 'risk_level' not in p.answer and 'affected' not in p.answer


def test_http_failure_keeps_stable_category_without_credential_text():
    token='SYNTHETIC-private-credential-marker'
    seen=[]
    def handler(request):
        seen.append(request)
        return httpx.Response(401,json={'error':token})
    with httpx.Client(base_url='http://127.0.0.1:9',transport=httpx.MockTransport(handler)) as client:
        adapter=module().InvestigationHTTPAdapter(client=client,token=token,bindings={question().id:binding()},timeout=2)
        p=adapter.run(question(),{})
    assert p.status=='FAILED' and p.error_code=='HTTP_401'
    assert seen and seen[0].headers['Authorization']=='Bearer '+token
    assert token not in json.dumps(adapter.records)


def test_redirect_is_not_followed_with_authorization():
    seen=[]
    def handler(request):
        seen.append(request)
        return httpx.Response(302,headers={'Location':'https://untrusted.invalid'})
    with httpx.Client(base_url='http://127.0.0.1:9',transport=httpx.MockTransport(handler),follow_redirects=False) as client:
        adapter=module().InvestigationHTTPAdapter(client=client,token='SYNTHETIC-marker',bindings={question().id:binding()},timeout=2)
        p=adapter.run(question(),{})
    assert len(seen)==1 and p.status=='FAILED' and p.error_code=='HTTP_302'

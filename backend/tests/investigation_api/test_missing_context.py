"""Missing inputs are public preflight states, never invented risk answers."""
from types import SimpleNamespace
from importlib import import_module
from uuid import uuid4
from threading import Lock
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.investigation_api.schemas import InvestigationCreateRequest
from app.investigation_api.service import InvestigationApiService


def request(*,version='0.6.0',asset=True,target=True,profile='asset_risk_v1'):
    scope={'component':{'name':'vllm','version':version}}
    if asset:scope['asset_id']=str(uuid4())
    if target:scope['target']='CVE-2099-9999001'
    return InvestigationCreateRequest(user_query='Analyze this supplied component.',asset_scope=scope,
        options={'objective_profile':profile},idempotency_key='synthetic-context').to_internal()


def checker():
    try:return import_module('app.investigation_api.context_check').check_context
    except ModuleNotFoundError:pytest.fail('Missing-context preflight has not been implemented')


@pytest.mark.parametrize('changes,field',[({'version':None},'version'),({'asset':False},'asset_context'),({'target':False},'vulnerability_id')])
def test_missing_required_input_produces_need_context_without_mutating_request(changes,field):
    raw=request(**changes);before=raw.model_dump_json()
    decision=checker()(raw,actor='SYNTHETIC-owner')
    assert decision.status=='NEED_CONTEXT' and field in decision.missing_fields
    assert raw.model_dump_json()==before


def test_complete_context_proceeds_without_any_missing_fields():
    decision=checker()(request(),actor='SYNTHETIC-owner')
    assert decision.status=='READY' and decision.missing_fields==()


def test_exact_fact_question_does_not_require_an_asset_or_version():
    raw=InvestigationCreateRequest(user_query='CVE-2099-9999001是什么？',
        asset_scope={'target':'CVE-2099-9999001'},options={'objective_profile':'overview_v1'},
        idempotency_key='synthetic-facts').to_internal()
    assert checker()(raw,actor='SYNTHETIC-owner').status=='READY'


def test_public_search_without_exact_target_is_limited_investigation():
    raw=InvestigationCreateRequest(user_query='最近7天AI漏洞有哪些？',
        options={'objective_profile':'overview_v1'},idempotency_key='synthetic-search').to_internal()
    decision=checker()(raw,actor='SYNTHETIC-owner')
    assert decision.status=='LIMITED_INVESTIGATION' and decision.missing_fields==()


@pytest.mark.parametrize('value',['unknown','UNKNOWN','未知','',' Unknown ',' 未知 ',' '])
def test_unknown_version_markers_are_not_a_real_deployed_version(value):
    assert 'version' in checker()(request(version=value),actor='SYNTHETIC-owner').missing_fields


def test_overview_does_not_hide_existing_validator_version_requirement():
    decision=checker()(request(version=None,asset=False,profile='overview_v1'),actor='SYNTHETIC-owner')
    assert decision.status=='NEED_CONTEXT' and decision.missing_fields==('version',)


def test_http_need_context_has_no_worker_model_or_investigation(monkeypatch):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN','SYNTHETIC-context-token')
    monkeypatch.setenv('AEGIS_ASSET_OWNER','SYNTHETIC-owner')
    # Real create method with an empty owned-key lookup; no engine or model exists.
    svc=object.__new__(InvestigationApiService)
    svc.repository=SimpleNamespace(by_key=lambda *a:None)
    svc.lock=Lock();svc.pending={};svc.closed=False
    app=create_app();app.state.investigations=svc
    body={'user_query':'torch版本未提供是否受CVE-2099-9999001影响？',
        'asset_scope':{'target':'CVE-2099-9999001','component':{'name':'torch'}},
        'options':{'objective_profile':'asset_risk_v1'},'idempotency_key':'synthetic-context'}
    response=TestClient(app).post('/api/investigations',json=body,
        headers={'Authorization':'Bearer SYNTHETIC-context-token'})
    assert response.status_code==200,response.text
    data=response.json();assert data['status']=='NEED_CONTEXT'
    assert 'version' in data['missing_fields']
    assert data['investigation_created'] is False and data['execution_mode']=='NOT_STARTED'
    assert 'investigation_id' not in data and 'integration_status' not in data
    assert 'Location' not in response.headers and 'Retry-After' not in response.headers
    assert 'SYNTHETIC-context-token' not in response.text


def test_context_check_rejects_conflicting_scope_instead_of_treating_it_as_missing():
    raw=InvestigationCreateRequest(user_query='CVE-2099-9999002是什么？',
        asset_scope={'target':'CVE-2099-9999001'},idempotency_key='synthetic-conflict').to_internal()
    with pytest.raises(ValueError,match='TARGET_SCOPE_CONFLICT'):
        checker()(raw,actor='SYNTHETIC-owner')


@pytest.mark.parametrize('question',['CVE-2099-9999001 的风险评估？','CVE-2099-9999001 是否影响我的服务？'])
def test_overview_profile_cannot_hide_question_required_context(question):
    raw=InvestigationCreateRequest(user_query=question,options={'objective_profile':'overview_v1'},
        idempotency_key='synthetic-risk-overview').to_internal()
    decision=checker()(raw,actor='SYNTHETIC-owner')
    assert decision.status=='NEED_CONTEXT' and 'version' in decision.missing_fields


@pytest.mark.parametrize('question',[
    '官方修复版本 vllm 0.6.1，CVE-2099-9999001 是否影响我？',
    '官方受影响版本 vllm 0.6.1 至 0.6.5，CVE-2099-9999001 是否影响我？'])
def test_legacy_advisory_inference_is_not_a_deployed_version(question):
    raw=InvestigationCreateRequest(user_query=question,
        options={'objective_profile':'asset_risk_v1'},asset_scope={'asset_id':str(uuid4())},
        idempotency_key='synthetic-advisory').to_internal()
    assert 'version' in checker()(raw,actor='SYNTHETIC-owner').missing_fields


def test_version_influence_with_three_fields_may_proceed_without_creating_asset():
    decision=checker()(request(asset=False,profile='asset_impact_v1'),actor='SYNTHETIC-owner')
    assert decision.status=='READY' and decision.missing_fields==()


def test_public_context_status_is_a_required_discriminator():
    from app.investigation_api.schemas import ContextRequiredResponse
    assert 'status' in ContextRequiredResponse.model_json_schema()['required']


def test_missing_context_cannot_reuse_an_inflight_key_for_different_content():
    from app.assistant.storage import IdempotencyConflict
    svc=object.__new__(InvestigationApiService)
    svc.repository=SimpleNamespace(by_key=lambda *a:None)
    svc.lock=Lock();svc.closed=False
    svc.pending={('SYNTHETIC-owner','synthetic-context'):SimpleNamespace(request_hash='different')}
    with pytest.raises(IdempotencyConflict):svc.create(request(version=None),actor='SYNTHETIC-owner')


def test_closed_service_does_not_return_a_new_preflight_response():
    from app.investigation_api.errors import ApiFailure
    svc=object.__new__(InvestigationApiService)
    svc.repository=SimpleNamespace(by_key=lambda *a:None)
    svc.lock=Lock();svc.closed=True;svc.pending={}
    with pytest.raises(ApiFailure) as caught:svc.create(request(version=None),actor='SYNTHETIC-owner')
    assert caught.value.code=='SERVICE_UNAVAILABLE'


def test_explicit_null_is_not_overwritten_by_legacy_question_inference():
    raw=InvestigationCreateRequest(user_query='My deployed vllm 0.6.0 is affected by CVE-2099-9999001?',
        asset_scope={'component':{'name':'vllm','version':None},'asset_id':str(uuid4())},
        options={'objective_profile':'asset_risk_v1'},idempotency_key='synthetic-null').to_internal()
    assert 'version' in checker()(raw,actor='SYNTHETIC-owner').missing_fields


def test_blank_component_identity_is_missing_context():
    raw=request();raw.planner_input.component.name='   '
    assert 'component' in checker()(raw,actor='SYNTHETIC-owner').missing_fields


@pytest.mark.parametrize('question',[
    'My deployed vllm v0.6.0 is affected by CVE-2099-9999001?',
    'My deployed langchain-core 0.2.3 is affected by CVE-2099-9999001?'])
def test_literals_outside_frozen_scope_request_structured_context(question):
    raw=InvestigationCreateRequest(user_query=question,asset_scope={'asset_id':str(uuid4())},
        options={'objective_profile':'asset_risk_v1'},idempotency_key='synthetic-uncaptured').to_internal()
    decision=checker()(raw,actor='SYNTHETIC-owner')
    assert decision.status=='NEED_CONTEXT' and {'component','version'}<=set(decision.missing_fields)


def test_bare_component_risk_question_requests_context():
    raw=InvestigationCreateRequest(user_query='分析vLLM风险。',idempotency_key='synthetic-bare').to_internal()
    assert checker()(raw,actor='SYNTHETIC-owner').status=='NEED_CONTEXT'

from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.assistant.contracts import QueryRequest
from app.planner.schemas import PlannerInput


def request(question='CVE-2099-90001是什么？', **kwargs):
    from app.orchestration.contracts import InvestigationRequest
    return InvestigationRequest(planner_input=PlannerInput(query=QueryRequest(
        question=question, request_key='D1-'+uuid4().hex)), **kwargs)


def test_original_query_and_extracted_component_are_frozen():
    from app.orchestration.scope import resolve_scope
    got = resolve_scope(request('我的 vLLM 0.6.0 是否受到 CVE-2099-90001影响？'), actor='alice')
    assert got.targets == ('CVE-2099-90001',)
    assert got.planner_input.query.question == '我的 vLLM 0.6.0 是否受到 CVE-2099-90001影响？'
    assert got.planner_input.component.version == '0.6.0'
    assert got.component_origin == 'QUESTION_EXTRACTED'
    assert 'ASSET_SCOPE_MISSING' in got.objective.scope_gaps


def test_question_and_typed_scope_conflict():
    from app.orchestration.contracts import InvestigationRequest
    from app.orchestration.scope import resolve_scope
    raw = PlannerInput(query=QueryRequest(question='CVE-2099-90001是什么？',
                                         target='CVE-2099-90002',request_key='conflict'))
    with pytest.raises(ValueError, match='TARGET_SCOPE_CONFLICT'):
        resolve_scope(InvestigationRequest(planner_input=raw),actor='alice')


def test_explicit_version_cannot_replace_question_version():
    from app.orchestration.contracts import InvestigationRequest
    from app.orchestration.scope import resolve_scope
    from app.tooling.contracts import ResolutionInput
    raw=PlannerInput(query=QueryRequest(question='vLLM 0.6.0 CVE-2099-90001',request_key='version'),
                     component=ResolutionInput(name='vLLM',version='0.7.0'))
    with pytest.raises(ValueError,match='COMPONENT_SCOPE_CONFLICT'):
        resolve_scope(InvestigationRequest(planner_input=raw),actor='alice')


@pytest.mark.parametrize('days',[0,366,99999])
def test_unsupported_text_window_is_not_clamped(days):
    from app.orchestration.scope import resolve_scope
    scope=resolve_scope(request(f'最近{days}天 CVE-2099-90001已有情报概览'),actor='alice')
    assert 'UNSUPPORTED_TIME_SCOPE' in scope.objective.scope_gaps
    assert scope.objective.window_days is None


def test_explicit_time_is_retained_without_rewriting_query():
    from app.orchestration.scope import resolve_scope
    raw=request(time_scope={'window_days':3,'requires_current':True})
    scope=resolve_scope(raw,actor='alice')
    assert scope.objective.window_days == 3 and scope.objective.requires_current
    assert scope.objective_source == 'new_structured_request'
    assert scope.planner_input.query.question == raw.planner_input.query.question


def test_typed_and_text_time_conflict():
    from app.orchestration.scope import resolve_scope
    with pytest.raises(ValueError,match='TIME_SCOPE_CONFLICT'):
        resolve_scope(request('最近7天 CVE-2099-90001情报概览',time_scope={'window_days':3}),actor='alice')


def test_poc_scope_does_not_masquerade_as_complete_overview():
    from app.orchestration.scope import resolve_scope
    scope=resolve_scope(request('CVE-2099-90001 有没有公开POC？'),actor='alice')
    assert 'POC_COMPLETENESS_NOT_SUPPORTED' in scope.objective.scope_gaps
    assert scope.objective_source == 'new_structured_request'


@pytest.mark.parametrize('extra',[{'allowed_tools':['shell']},{'authorized_context':{'permissions':['WRITE']}},
                                 {'time_scope':{'window_days':366}}, {'investigation_options':{'timeout_seconds':301}}])
def test_client_cannot_expand_permissions_or_budget(extra):
    with pytest.raises(ValidationError):request(**extra)


def test_request_id_is_not_semantic_idempotency_content():
    from app.orchestration.contracts import request_fingerprint
    raw=request()
    other=type(raw).model_validate({**raw.model_dump(mode='json'),'request_id':str(uuid4())})
    assert request_fingerprint(raw)==request_fingerprint(other)
    changed=type(raw).model_validate({**raw.model_dump(mode='json'),'time_scope':{'window_days':2}})
    assert request_fingerprint(raw)!=request_fingerprint(changed)


@pytest.mark.parametrize('actor',['', '   ', 'x'*151])
def test_authenticated_actor_required(actor):
    from app.orchestration.scope import resolve_scope
    with pytest.raises(ValueError):resolve_scope(request(),actor=actor)
@pytest.mark.parametrize('prefix',['仅依据2025年1月1日至2025年1月31日的资料，','最近两天，','过去2周，','截至2025-01-31，','上个月，'])
def test_unsupported_temporal_scope_is_not_silently_removed(prefix):
    from app.orchestration.scope import resolve_scope
    value=request();raw=value.model_dump(mode='json')
    raw['planner_input']['query']['question']=prefix+raw['planner_input']['query']['question']
    scope=resolve_scope(type(value).model_validate(raw),actor='alice')
    assert 'UNSUPPORTED_TIME_SCOPE' in scope.objective.scope_gaps
    assert scope.objective_source=='new_structured_request'

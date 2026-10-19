"""Field diagnostics are feedback, never a replacement for validation or execution."""
from copy import deepcopy
import json
import os
from pathlib import Path
import pytest
from app.agents.investigation.planner import InvestigationPlannerAdapter
from tests.planner.fixtures import cve_input, context_for, valid_plan, gateway_with_responses


def run_case(initial, corrected=None, request=None):
    request=request or cve_input()
    ctx=context_for(input=request)
    gw,calls,sink=gateway_with_responses([initial] if corrected is None else [initial,corrected])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(request,ctx)
        if os.getenv('AEGIS_C20_AUDIT'):
            out=Path(os.environ['AEGIS_C20_AUDIT']);out.mkdir(exist_ok=True,parents=True)
            (out/(str(ctx.trace_id)+'.json')).write_text(json.dumps({
                'initial_output':initial,'schema_errors':[i.model_dump() for i in result.attempts[0].issues],
                'retry_feedback':calls[1].messages[-1].content if len(calls)>1 else None,
                'retry_output':corrected if corrected is not None else initial,
                'attempts':[a.model_dump(mode='json') for a in result.attempts],
                'final_planning_status':result.status,'runtime_executed':False},indent=2),encoding='utf8')
        return result,calls,sink
    finally:gw.close()


@pytest.mark.parametrize('kind,path,code',[
    ('required','$.tasks[0].acceptance_criteria','SCHEMA_FIELD_REQUIRED'),
    ('type','$.tasks[0].max_tool_calls','SCHEMA_FIELD_TYPE'),
    ('enum','$.tasks[0].type','SCHEMA_FIELD_ENUM'),
    ('nested','$.tasks[0].input_data.steps[0].arguments.target','SCHEMA_FIELD_REQUIRED'),
    ('multiple','$.tasks[0].acceptance_criteria','SCHEMA_FIELD_REQUIRED'),
])
def test_exact_formal_schema_errors_reach_the_second_request(kind,path,code):
    good=valid_plan();bad=deepcopy(good)
    if kind in ('required','multiple'):bad['tasks'][0].pop('acceptance_criteria')
    if kind in ('type','multiple'):bad['tasks'][0]['max_tool_calls']='one'
    if kind=='enum':bad['tasks'][0]['type']='unknown_action'
    if kind=='nested':bad['tasks'][0]['input_data']['steps'][0]['arguments'].pop('target')
    original=deepcopy(bad)
    result,calls,sink=run_case(bad,good)
    assert result.status=='VALIDATED' and len(calls)==2
    assert result.attempts[0].model_call['status']=='failed'
    assert any(i.code==code and i.path==path for i in result.attempts[0].issues)
    assert path in calls[1].messages[-1].content and code in calls[1].messages[-1].content
    assert 'requirement' in calls[1].messages[-1].content
    assert bad==original and result.attempts[0].validation_status=='REJECTED'
    assert result.attempts[1].validation_status=='VALIDATED'
    if kind in ('type','multiple'):
        assert 'expected_type' in calls[1].messages[-1].content and 'actual_type' in calls[1].messages[-1].content
    if kind=='multiple':
        assert any(i.path=='$.tasks[0].max_tool_calls' and i.code=='SCHEMA_FIELD_TYPE' for i in result.attempts[0].issues)


def test_missing_dependency_is_server_rejection_not_a_schema_error():
    good=valid_plan();bad=deepcopy(good);bad['tasks'][0]['dependencies']=['not-present']
    result,calls,_=run_case(bad,good)
    assert result.status=='VALIDATED' and len(calls)==2
    assert result.attempts[0].model_call['status']=='success'
    assert result.attempts[0].validation_status=='REJECTED'
    assert not any(i.code.startswith('SCHEMA_FIELD_') for i in result.attempts[0].issues)


def test_persistent_invalid_output_exhausts_the_existing_two_attempts_fail_closed():
    bad=valid_plan();bad['tasks'][0].pop('acceptance_criteria')
    result,calls,sink=run_case(bad)
    assert result.status=='PLANNING_FAILED' and result.validated_plan is None
    assert len(calls)==len(sink.attempts)==2
    assert all(a.validation_status=='REJECTED' and a.model_call['status']=='failed' for a in result.attempts)
    assert all(any(i.path=='$.tasks[0].acceptance_criteria' for i in a.issues) for a in result.attempts)


def test_second_response_is_revalidated_not_assumed_correct():
    first=valid_plan();first['tasks'][0].pop('acceptance_criteria')
    second=valid_plan();second['tasks'][0]['max_tool_calls']='bad'
    result,calls,_=run_case(first,second)
    assert result.status=='PLANNING_FAILED' and result.validated_plan is None and len(calls)==2
    assert any(i.path=='$.tasks[0].max_tool_calls' for i in result.attempts[1].issues)


def test_feedback_does_not_echo_candidate_instructions_or_unknown_property_names():
    bad=valid_plan();bad['reasoning_summary']='UNTRUSTED_REPAIR_INSTRUCTION'
    bad['tasks'][0].pop('acceptance_criteria')
    bad['tasks'][0]['UNTRUSTED_SECRET_FIELD']='DO_NOT_ECHO'
    _,calls,_=run_case(bad)
    assert all(s not in calls[1].messages[-1].content for s in ('UNTRUSTED_REPAIR_INSTRUCTION','UNTRUSTED_SECRET_FIELD','DO_NOT_ECHO'))


def test_different_asset_investigation_scopes_never_share_retry_errors():
    from uuid import uuid4
    from app.planner.schemas import PlannerInput
    a=cve_input(asset_id=uuid4());b=cve_input(asset_id=uuid4())
    first=valid_plan();first['tasks'][0].pop('acceptance_criteria')
    second=valid_plan();second['tasks'][0]['max_tool_calls']='bad'
    ra,ca,_=run_case(first,request=PlannerInput(query=a.query))
    rb,cb,_=run_case(second,request=PlannerInput(query=b.query))
    assert ca[0].trace_id!=cb[0].trace_id
    assert json.loads(ca[1].messages[1].content)['input_scope']['asset_id']==str(a.query.asset_id)
    assert json.loads(cb[1].messages[1].content)['input_scope']['asset_id']==str(b.query.asset_id)
    assert 'SCHEMA_FIELD_REQUIRED' in ca[1].messages[-1].content
    assert 'SCHEMA_FIELD_TYPE' in cb[1].messages[-1].content
    assert '$.tasks[0].acceptance_criteria' not in cb[1].messages[-1].content


def test_valid_plan_does_not_gain_feedback_or_extra_attempts():
    result,calls,_=run_case(valid_plan())
    assert result.status=='VALIDATED' and len(calls)==1 and not result.attempts[0].issues


def test_diagnostics_exception_is_visible_and_never_accepts_invalid_output(monkeypatch):
    import app.agents.investigation.planner as module
    def broken(*args):raise RuntimeError('PRIVATE_DIAGNOSTIC_EXCEPTION')
    monkeypatch.setattr(module,'schema_feedback',broken)
    bad=valid_plan();bad['tasks'][0].pop('acceptance_criteria')
    result,calls,_=run_case(bad)
    assert result.status=='PLANNING_FAILED' and result.validated_plan is None
    assert 'SCHEMA_DIAGNOSTICS_UNAVAILABLE' in calls[1].messages[-1].content
    assert 'PRIVATE_DIAGNOSTIC_EXCEPTION' not in calls[1].messages[-1].content


def test_rejected_enum_value_is_not_reflected_into_feedback():
    bad=valid_plan();bad['tasks'][0]['type']='UNTRUSTED_ENUM_VALUE'
    result,calls,_=run_case(bad)
    assert result.status=='PLANNING_FAILED'
    assert 'SCHEMA_FIELD_ENUM' in calls[1].messages[-1].content
    assert 'UNTRUSTED_ENUM_VALUE' not in calls[1].messages[-1].content


def test_feedback_bound_is_explicit_and_does_not_mutate_oversize_invalid_plan():
    from app.agents.investigation.schema_feedback import schema_feedback
    from app.agents.investigation.planning import scoped_plan_model
    from app.llm.schemas import StructuredRequest
    bad=valid_plan();bad['tasks']=[deepcopy(bad['tasks'][0]) for _ in range(16)]
    for t in bad['tasks']:
        t.pop('acceptance_criteria');t['max_tool_calls']='wrong';t['description']=42
    frozen=deepcopy(bad)
    issues=schema_feedback(json.dumps(bad),StructuredRequest(messages=[{'role':'user','content':'synthetic'}]),
                           scoped_plan_model(context_for()))
    assert len(issues)==33 and issues[-1].code=='SCHEMA_FEEDBACK_LIMIT'
    assert bad==frozen

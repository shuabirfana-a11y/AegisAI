"""Scope-derived obligations are not optional when repairing field errors."""
from copy import deepcopy
import json
from uuid import uuid4
import pytest
from jsonschema import Draft202012Validator, ValidationError
from app.agents.investigation.planning import InvestigationPlan, scoped_plan_model
from app.agents.investigation.validation import validate_investigation_plan
from app.agents.investigation.planner import InvestigationPlannerAdapter
from app.planner.validator import PlanValidationError
from tests.planner.fixtures import valid_plan,task,cve_input,context_for,gateway_with_responses


def asset_case(asset_id=None):
    aid=asset_id or uuid4();inp=cve_input(asset_id=aid)
    p=valid_plan();p['tasks'].append(task('asset_lookup','asset','get_asset',{'asset_id':str(aid)}))
    return inp,context_for(input=inp),p


def test_generation_enforces_the_existing_server_asset_obligation():
    inp,ctx,p=asset_case();p['tasks'].pop()
    with pytest.raises(PlanValidationError,match='ASSET_LOOKUP_REQUIRED'):
        validate_investigation_plan(InvestigationPlan.model_validate(p),ctx)
    with pytest.raises(ValidationError):Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(p)


def test_first_field_repair_carries_scope_obligation_even_if_asset_task_was_present():
    inp,ctx,good=asset_case();bad=deepcopy(good)
    for t in bad['tasks']:t.pop('acceptance_criteria')
    gw,calls,sink=gateway_with_responses([bad,good])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(inp,ctx)
        payload=json.loads(calls[1].messages[1].content)
        assert payload['required_asset_observations']==[{'name':'get_asset','arguments':{'asset_id':str(inp.query.asset_id)}}]
        correction=next(json.loads(m.content) for m in calls[1].messages if m.role=='user' and 'rejected_candidate' in json.loads(m.content))
        assert correction['rejected_candidate']==bad
        assert result.status=='VALIDATED' and len(calls)==2
        assert 'SCHEMA_FIELD_REQUIRED' in str(result.attempts[0].issues)
        assert 'ASSET_LOOKUP_REQUIRED' not in str(result.attempts[0].issues)
    finally:gw.close()


def test_retry_dropping_asset_keeps_original_rejection_distinct_from_c24_validated_completion():
    inp,ctx,p=asset_case();first=deepcopy(p);first['tasks'][0].pop('acceptance_criteria');dropped=deepcopy(p);dropped['tasks'].pop()
    gw,calls,sink=gateway_with_responses([first,dropped])
    try:
        got=InvestigationPlannerAdapter(gw,sink).plan(inp,ctx)
        # C24 explicitly authorizes catalog-bound completion. The raw model
        # candidate remains rejected; only the independently revalidated plan runs.
        assert got.status=='VALIDATED' and got.validated_plan is not None and len(calls)==2
        assert any(i.code=='ASSET_LOOKUP_REQUIRED' for i in got.attempts[1].issues)
        assert any(i.code=='SCHEMA_FIELD_CONTAINS' for i in got.attempts[1].issues)
        audit=got.attempts[1].diagnostic['task_integrity']
        assert audit['original_candidate_status']=='REJECTED' and audit['status']=='REPAIRED'
        assert json.loads(got.attempts[1].diagnostic['raw_output'])==dropped
        assert audit['added_tasks'][0]['input_data']['steps']==[{'name':'get_asset','arguments':{'asset_id':str(inp.query.asset_id)}}]
        Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(audit['effective_candidate'])
        validate_investigation_plan(InvestigationPlan.model_validate(audit['effective_candidate']),ctx)
    finally:gw.close()


def test_plain_lookup_keeps_legal_simplification_and_never_adds_assets():
    inp=cve_input();ctx=context_for(input=inp);p=valid_plan()
    Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(p)
    out=validate_investigation_plan(InvestigationPlan.model_validate(p),ctx)
    assert len(json.loads(out.runtime_plan_json)['tasks'])==1


def test_missing_deployment_version_remains_input_required():
    from app.planner.schemas import PlannerInput
    inp,_,p=asset_case();inp=PlannerInput(query=inp.query,component={'name':'synthetic-lib'})
    p['tasks'].append(dict(type='vulnerability_lookup',task_id='ask-version',task_type='input_required',description='Ask version',input_data={'required_fields':['version']},allowed_tools=[],max_tool_calls=0))
    ctx=context_for(input=inp);Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(p)
    result=validate_investigation_plan(InvestigationPlan.model_validate(p),ctx)
    assert json.loads(result.runtime_plan_json)['tasks'][-1]['task_type']=='input_required'


def test_missing_asset_identity_is_not_guessed_from_product_name():
    from app.planner.schemas import PlannerInput
    inp=PlannerInput(query=cve_input().query,component={'name':'synthetic-lib'})
    p=valid_plan();p['tasks'].append(dict(type='vulnerability_lookup',task_id='ask-version',task_type='input_required',description='Ask version',input_data={'required_fields':['version']},allowed_tools=[],max_tool_calls=0))
    ctx=context_for(input=inp)
    out=validate_investigation_plan(InvestigationPlan.model_validate(p),ctx)
    assert not any(s['name']=='get_asset' for t in json.loads(out.runtime_plan_json)['tasks'] for s in t['input_data'].get('steps',[]))


def test_asset_feedback_is_bound_to_each_request_not_adapter_state():
    a,ca,pa=asset_case();b,cb,pb=asset_case();ba=deepcopy(pa);bb=deepcopy(pb)
    ba['tasks'][0].pop('acceptance_criteria');bb['tasks'][0].pop('acceptance_criteria')
    gw,calls,sink=gateway_with_responses([ba,pa,bb,pb]);adapter=InvestigationPlannerAdapter(gw,sink)
    try:
        assert adapter.plan(a,ca).status==adapter.plan(b,cb).status=='VALIDATED'
        for index,inp in [(1,a),(3,b)]:
            payload=json.loads(calls[index].messages[1].content)
            assert payload['required_asset_observations'][0]['arguments']=={'asset_id':str(inp.query.asset_id)}
        assert calls[1].trace_id!=calls[3].trace_id
    finally:gw.close()


def test_wrong_asset_never_satisfies_required_scope():
    inp,ctx,p=asset_case();p['tasks'][-1]['input_data']['steps'][0]['arguments']['asset_id']=str(uuid4())
    with pytest.raises(ValidationError):Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(p)
    with pytest.raises(PlanValidationError,match='ID_SCOPE_MISMATCH'):validate_investigation_plan(InvestigationPlan.model_validate(p),ctx)

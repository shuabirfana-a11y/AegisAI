"""Existing execution criteria must be explicit in generated executable plans."""
from copy import deepcopy
import json
import pytest
from jsonschema import Draft202012Validator, ValidationError
from app.agents.investigation.planning import InvestigationPlan, scoped_plan_model
from app.agents.investigation.validation import validate_investigation_plan
from app.agents.investigation.roles import ROLES
from app.planner.validator import PlanValidationError
from app.runtime.contracts import TaskContract, TaskState
from app.runtime.executor import acceptance
from tests.planner.fixtures import valid_plan, task, context_for, CVE


def evidence_plan():
    p=valid_plan();e=task('evidence_search','evidence','get_evidence')
    e['acceptance_criteria']=sorted(ROLES['evidence_search'].criteria)
    p['tasks'].append(e)
    return p


def schema():return Draft202012Validator(scoped_plan_model(context_for()).model_json_schema())


@pytest.mark.parametrize('explicit', [False,True])
def test_generation_rejects_the_existing_evidence_minimum_criteria_omission(explicit):
    p=evidence_plan()
    if explicit:p['tasks'][1]['acceptance_criteria']=['tools_succeeded','output_nonempty']
    else:p['tasks'][1].pop('acceptance_criteria')
    with pytest.raises(PlanValidationError,match='MINIMUM_CRITERIA_MISSING'):
        validate_investigation_plan(InvestigationPlan.model_validate(p),context_for())
    with pytest.raises(ValidationError):schema().validate(p)


@pytest.mark.parametrize('missing', ['tools_succeeded','output_nonempty','evidence_present'])
def test_generation_requires_every_registered_evidence_condition(missing):
    p=evidence_plan();p['tasks'][1]['acceptance_criteria'].remove(missing)
    with pytest.raises(ValidationError):schema().validate(p)


def test_lookup_omission_is_not_silently_supplied_to_the_generation_contract():
    p=valid_plan();p['tasks'][0].pop('acceptance_criteria')
    with pytest.raises(ValidationError):schema().validate(p)


def test_complete_criteria_pass_without_inventing_version_observation_or_fact():
    p=evidence_plan();before=deepcopy(p);schema().validate(p)
    result=validate_investigation_plan(InvestigationPlan.model_validate(p),context_for())
    runtime=json.loads(result.runtime_plan_json)
    assert set(runtime['tasks'][1]['acceptance_criteria'])==ROLES['evidence_search'].criteria
    assert p==before and all(s['name']!='inspect_component_version' for t in p['tasks'] for s in t['input_data']['steps'])


def test_original_general_task_default_is_unchanged_not_a_success_certificate():
    t=TaskContract(task_id='synthetic',description='Unchanged legacy contract',allowed_tools=['get_evidence'],
        input_data={'steps':[{'name':'get_evidence','arguments':{'target':CVE}}]})
    assert t.acceptance_criteria==('tools_succeeded','output_nonempty')
    assert acceptance(t,[])[0]==TaskState.WAITING_REVIEW


def test_explicit_evidence_condition_still_rejects_successful_output_without_evidence():
    from tests.agents.investigation.helpers import execution
    t,_,result=execution(data={'items':[{'candidate':True}]},refs=[],names=['get_evidence'])
    t=t.model_copy(update={'acceptance_criteria':tuple(sorted(ROLES['evidence_search'].criteria))})
    status,reasons=acceptance(t,result.receipts)
    assert status==TaskState.WAITING_REVIEW and 'Required evidence was not returned by a tool' in reasons


def test_failed_version_observation_is_never_promoted_to_success():
    from tests.agents.investigation.helpers import execution
    t,_,result=execution(data={},refs=[],statuses=['failed'],names=['inspect_component_version'])
    assert acceptance(t,result.receipts)[0]==TaskState.FAILED


def test_zero_tool_missing_context_remains_accepted_as_input_required():
    from app.planner.schemas import PlannerInput
    from tests.planner.fixtures import cve_input
    ctx=context_for(input=PlannerInput(query=cve_input().query,component={'name':'synthetic-lib'}))
    p=valid_plan();p['tasks'].append({'type':'vulnerability_lookup','task_id':'ask-version',
        'task_type':'input_required','description':'Ask only for missing version',
        'input_data':{'required_fields':['version']},'allowed_tools':[],'max_tool_calls':0})
    Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(p)
    runtime=json.loads(validate_investigation_plan(InvestigationPlan.model_validate(p),ctx).runtime_plan_json)
    assert runtime['tasks'][1]['task_type']=='input_required' and not runtime['tasks'][1]['allowed_tools']

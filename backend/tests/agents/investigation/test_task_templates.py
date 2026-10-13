"""Templates guide the model; they never replace the model or server validator."""
from copy import deepcopy
import importlib,json
import pytest
from jsonschema import ValidationError,Draft202012Validator
from tests.planner.fixtures import context_for,valid_plan,task,CVE,cve_input,gateway_with_responses
from app.agents.investigation.planning import scoped_plan_model


def test_wrong_role_tool_is_rejected_by_model_facing_schema():
    p=valid_plan();p['tasks'][0]=task(name='get_claims')
    with pytest.raises(ValidationError):Draft202012Validator(scoped_plan_model(context_for()).model_json_schema()).validate(p)


def test_duplicate_root_lookup_rejected_without_relaxing_runtime():
    p=valid_plan();p['tasks'].append(task(task_id='other-root'))
    with pytest.raises(ValidationError):Draft202012Validator(scoped_plan_model(context_for()).model_json_schema()).validate(p)


def test_four_intent_templates_only_describe_existing_investigation_roles():
    try:module=importlib.import_module('app.agents.investigation.templates')
    except ModuleNotFoundError:pytest.fail('Intent template guidance is missing')
    from app.agents.investigation.roles import ROLES
    assert {'vulnerability_fact','version_impact','asset_risk','evidence_conflict'}<=set(module.TASK_TEMPLATES)
    for value in module.TASK_TEMPLATES.values():
        assert set(value['roles'])<=set(ROLES)
        assert 'tasks' not in value # no generated Runtime plan


def test_gateway_receives_normalized_goal_and_template_with_no_answer_label():
    from app.agents.investigation.planner import InvestigationPlannerAdapter
    gateway,calls,sink=gateway_with_responses([valid_plan()])
    try:
        got=InvestigationPlannerAdapter(gateway,sink).plan(cve_input(),context_for())
        assert got.status=='VALIDATED'
        payload=json.loads(calls[0].messages[1].content)
        assert payload['normalized_goal']['vulnerability_id']==CVE
        assert payload['task_template']['template_id']=='vulnerability-fact-v1'
        assert 'expected_answer' not in json.dumps(payload)
    finally:gateway.close()


def test_backend_goal_never_invents_fields_outside_frozen_scope():
    from app.agents.investigation.planner import InvestigationPlannerAdapter
    inp=cve_input(question='My langchain-core 0.3.0 deployment is affected by '+CVE+'?')
    ctx=context_for(input=inp);assert ctx.scope['component'] is None
    gateway,calls,sink=gateway_with_responses([valid_plan()])
    try:
        assert InvestigationPlannerAdapter(gateway,sink).plan(inp,ctx).status=='VALIDATED'
        payload=json.loads(calls[0].messages[1].content)
        assert payload['normalized_goal']['component'] is None
        assert payload['normalized_goal']['version'] is None
        assert payload['exact_tool_arguments']['inspect_component_version']==[]
    finally:gateway.close()


def test_fact_template_does_not_offer_missing_deployment_version_task():
    p=valid_plan();p['tasks'].append({'type':'vulnerability_lookup','task_id':'ask-unneeded-version',
        'task_type':'input_required','description':'Unneeded version',
        'input_data':{'required_fields':['version']},'allowed_tools':[],'max_tool_calls':0})
    with pytest.raises(ValidationError):Draft202012Validator(scoped_plan_model(context_for()).model_json_schema()).validate(p)

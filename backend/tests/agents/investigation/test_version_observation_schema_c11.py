"""Model schema must describe the server's existing mandatory version observation."""
from copy import deepcopy
import pytest
from jsonschema import Draft202012Validator,ValidationError
from app.planner.schemas import PlannerInput
from app.agents.investigation.planning import scoped_plan_model
from app.agents.investigation.validation import validate_investigation_plan
from app.planner.validator import PlanValidationError
from tests.planner.fixtures import context_for,cve_input,valid_plan,CVE

def context():
    return context_for(input=PlannerInput(query=cve_input().query,
        component={'name':'synthetic-lib','package_name':'synthetic-lib','ecosystem':'PyPI','version':'4.1'}))

def test_generation_schema_rejects_plan_missing_existing_server_requirement():
    ctx=context(); plan=valid_plan()
    from app.agents.investigation.planning import InvestigationPlan
    with pytest.raises(PlanValidationError):validate_investigation_plan(InvestigationPlan.model_validate(plan),ctx)
    with pytest.raises(ValidationError):Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(plan)

def test_valid_observation_is_not_rejected_and_missing_version_not_invented():
    ctx=context();plan=valid_plan()
    plan['tasks'][0]['allowed_tools'].append('inspect_component_version')
    plan['tasks'][0]['max_tool_calls']=2
    plan['tasks'][0]['input_data']['steps'].append({'name':'inspect_component_version','arguments':{'target':CVE,**ctx.scope['component']}})
    Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(plan)
    plain=context_for();Draft202012Validator(scoped_plan_model(plain).model_json_schema()).validate(valid_plan())

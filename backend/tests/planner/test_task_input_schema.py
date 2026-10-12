"""The model-facing schema must reject the structural input already rejected by Runtime."""
import pytest
from jsonschema import Draft202012Validator, ValidationError
from app.planner.schemas import PlannerPlan
from tests.planner.fixtures import valid_plan


def test_model_schema_rejects_direct_tool_arguments_in_task_input():
    candidate = valid_plan()
    candidate['tasks'][0]['input_data'] = {'target': 'CVE-2099-9999001'}
    with pytest.raises(ValidationError):
        Draft202012Validator(PlannerPlan.model_json_schema()).validate(candidate)


def test_model_schema_accepts_existing_tool_steps_and_pydantic_contract():
    candidate = valid_plan()
    Draft202012Validator(PlannerPlan.model_json_schema()).validate(candidate)
    checked = PlannerPlan.model_validate(candidate)
    assert checked.tasks[0].input_data['steps'][0]['name'] == 'get_vulnerability'


def test_model_schema_rejects_unknown_step_field():
    candidate = valid_plan()
    candidate['tasks'][0]['input_data']['steps'][0]['unsafe_extra'] = 'SYNTHETIC'
    with pytest.raises(ValidationError):
        Draft202012Validator(PlannerPlan.model_json_schema()).validate(candidate)


def test_model_schema_requires_tool_allowlist_for_tool_sequence():
    candidate = valid_plan()
    candidate['tasks'][0].pop('allowed_tools')
    with pytest.raises(ValidationError):
        Draft202012Validator(PlannerPlan.model_json_schema()).validate(candidate)


def test_model_schema_rejects_empty_tool_sequence():
    candidate = valid_plan()
    candidate['tasks'][0]['input_data'] = {'steps': []}
    with pytest.raises(ValidationError):
        Draft202012Validator(PlannerPlan.model_json_schema()).validate(candidate)


def test_model_schema_accepts_existing_zero_tool_input_required():
    candidate = valid_plan()
    candidate['tasks'][0].update(task_type='input_required',
        input_data={'required_fields': ['component_id']}, allowed_tools=[], max_tool_calls=0)
    Draft202012Validator(PlannerPlan.model_json_schema()).validate(candidate)
    assert PlannerPlan.model_validate(candidate).tasks[0].task_type == 'input_required'

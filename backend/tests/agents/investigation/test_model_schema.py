"""The HTTP Planner's model-facing contract must match its existing Runtime input."""
import pytest
from jsonschema import Draft202012Validator, ValidationError

from app.agents.investigation.planning import InvestigationPlan
from tests.planner.fixtures import valid_plan


def check(value):
    Draft202012Validator(InvestigationPlan.model_json_schema()).validate(value)
    return InvestigationPlan.model_validate(value)


def test_schema_rejects_direct_arguments_without_steps():
    candidate = valid_plan()
    candidate['tasks'][0]['input_data'] = {'target': 'CVE-2099-9999001'}
    with pytest.raises(ValidationError):
        check(candidate)


def test_schema_accepts_existing_nested_tool_steps():
    assert check(valid_plan()).tasks[0].input_data['steps'][0]['name'] == 'get_vulnerability'


def test_schema_rejects_unknown_tool_step_field():
    candidate = valid_plan()
    candidate['tasks'][0]['input_data']['steps'][0]['made_up'] = True
    with pytest.raises(ValidationError):
        check(candidate)


@pytest.mark.parametrize('mutation', ['missing_allowlist', 'empty_steps'])
def test_schema_requires_executable_tool_contract(mutation):
    candidate = valid_plan()
    if mutation == 'missing_allowlist':
        candidate['tasks'][0].pop('allowed_tools')
    else:
        candidate['tasks'][0]['input_data'] = {'steps': []}
    with pytest.raises(ValidationError):
        check(candidate)


def test_schema_preserves_zero_tool_input_required():
    candidate = valid_plan()
    candidate['tasks'][0].update(
        type='asset_lookup', task_type='input_required',
        input_data={'required_fields': ['asset_id']}, allowed_tools=[], max_tool_calls=0,
    )
    assert check(candidate).tasks[0].task_type == 'input_required'


@pytest.mark.parametrize('role', ['unknown_action', 'risk_analysis', 'version_match'])
def test_schema_preserves_exact_three_task_roles(role):
    candidate = valid_plan()
    candidate['tasks'][0]['type'] = role
    with pytest.raises(ValidationError):
        check(candidate)


def test_prompt_payload_distinguishes_optional_inputs_and_fixes_sampling():
    import json
    from app.agents.investigation.planner import InvestigationPlannerAdapter
    from tests.planner.fixtures import cve_input, context_for, gateway_with_responses

    gateway, calls, sink = gateway_with_responses([valid_plan()])
    try:
        planner = InvestigationPlannerAdapter(gateway, sink)
        assert planner.plan(cve_input(), context_for()).status == 'VALIDATED'
        payload = json.loads(calls[0].messages[1].content)
        assert payload['missing_fields_by_role'] == {
            'vulnerability_lookup': ['version'], 'evidence_search': [], 'asset_lookup': ['asset_id'],
        }
        assert payload['input_scope']['targets']
        assert list(payload['tool_inputs']) == sorted(payload['tool_inputs'])
        assert calls[0].temperature == 0.0
        assert planner.prompt_version == 'investigation-plan-v4'
        prompt = calls[0].messages[0].content
        for field in ('input_data.steps', 'allowed_tools', 'task_type', 'input_required'):
            assert field in prompt
        assert 'Optional absent fields' in prompt
        assert 'JSON key "type"' in prompt
        assert 'Do not include required_fields in a tool_sequence' in prompt
        assert payload['exact_tool_arguments']['get_vulnerability'] == [{'target': 'CVE-2099-9999001'}]
        assert payload['exact_tool_arguments']['semantic_search'] == {'query': payload['input_scope']['question']}
        assert payload['exact_tool_arguments']['get_asset'] is None
    finally:
        gateway.close()


@pytest.mark.parametrize('invalid', ['unknown_task', 'unknown_tool', 'invented_missing'])
def test_no_task_repair_or_mock_fallback_after_two_rejected_candidates(invalid):
    from app.agents.investigation.planner import InvestigationPlannerAdapter
    from tests.planner.fixtures import cve_input, context_for, gateway_with_responses

    candidate = valid_plan()
    item = candidate['tasks'][0]
    if invalid == 'unknown_task':
        item['type'] = 'unknown_action'
    elif invalid == 'unknown_tool':
        item['allowed_tools'] = ['unregistered_scanner']
        item['input_data']['steps'][0]['name'] = 'unregistered_scanner'
    else:
        item.update(task_type='input_required', allowed_tools=[], max_tool_calls=0,
                    input_data={'required_fields': ['target']})
    gateway, calls, sink = gateway_with_responses([candidate])
    try:
        outcome = InvestigationPlannerAdapter(gateway, sink).plan(cve_input(), context_for())
        assert outcome.status == 'PLANNING_FAILED' and outcome.validated_plan is None
        assert len(calls) == len(sink.attempts) == 2
        assert all(a.validation_status == 'REJECTED' for a in outcome.attempts)
        assert all(a.diagnostic['raw_output'] for a in outcome.attempts)
    finally:
        gateway.close()

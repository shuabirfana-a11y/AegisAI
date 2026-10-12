"""Protocol-only tests of the real Gateway/Planner probe, never model quality."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import httpx
import pytest
from app.llm.config import ModelConfig
from app.llm.gateway import ModelGateway
from app.llm.providers.openai_compatible import OpenAICompatibleProvider
from tests.planner.fixtures import cve_input, valid_plan

ROOT = Path(__file__).resolve().parents[3]


def probe():
    assert importlib.util.find_spec('scripts.probe_model_provider'), 'Provider probe is not implemented'
    from scripts import probe_model_provider
    return probe_model_provider


def controlled_gateway(plan=None, *, malformed=False, failure=None):
    config = ModelConfig(provider='openai_compatible', model='SYNTHETIC-protocol-model',
        api_base='https://protocol.example.invalid/v1', api_key='SYNTHETIC-test-key',
        embedding_provider='mock', structured_mode='json_schema', max_output_tokens=4096)
    def handle(request):
        if request.method == 'GET':
            return httpx.Response(200, json={'data': [{'id': config.model}]})
        body = json.loads(request.content)
        fmt = body.get('response_format')
        if fmt and fmt['json_schema']['name'] == 'PlannerPlan':
            value = plan or valid_plan()
        else:
            value = {'cve': 'CVE-2099-9999001', 'risk': 'high', 'evidence': []}
        if fmt and failure:
            if failure == 'TIMEOUT':
                raise httpx.ReadTimeout('SYNTHETIC private error', request=request)
            if failure == 'EMPTY':
                return httpx.Response(200, json={'model': config.model, 'choices': [{
                    'message': {'role': 'assistant', 'content': ''}, 'finish_reason': 'stop'}]})
        content = '{illegal-json' if malformed and fmt else json.dumps(value) if fmt else 'SYNTHETIC text'
        return httpx.Response(200, json={'model': config.model, 'choices': [{
            'message': {'role': 'assistant', 'content': content},
            'finish_reason': 'length' if fmt and failure == 'TRUNCATED' else 'stop'}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}})
    return ModelGateway(config, text_provider=OpenAICompatibleProvider(
        config, capability='text', transport=httpx.MockTransport(handle)))


def test_probe_calls_gateway_not_model_sdk():
    p = probe()
    with controlled_gateway() as gateway:
        result = p.run_provider_probe(gateway, (cve_input(), cve_input()))
    assert result.ready and result.structured_passed == 5 and result.planner_validated == 2
    assert result.structured_attempted == 5 and result.planner_attempted == 2
    assert result.execution_mode == 'REAL' and not result.benchmark
    assert result.data_origin == 'UNVERIFIED_SERVICE'
    assert result.embedding_provider == 'mock' and not result.embedding_exercised
    assert len(result.call_records) == 9
    assert 'SYNTHETIC-test-key' not in result.model_dump_json()


def test_invalid_json_does_not_execute_plan():
    with controlled_gateway(malformed=True) as gateway:
        result = probe().run_provider_probe(gateway, (cve_input(),))
    assert not result.ready and result.structured_passed == 0 and result.planner_validated == 0
    assert result.planner_checks[0].status == 'PLANNING_FAILED'
    assert result.planner_checks[0].attempt_count == 2
    assert '{illegal-json' not in result.model_dump_json()


@pytest.mark.parametrize('invalid', ['unknown_task', 'forbidden_tool'])
def test_unknown_task_and_forbidden_tool_are_rejected(invalid):
    plan = valid_plan()
    if invalid == 'unknown_task':
        plan['tasks'][0]['type'] = 'unknown_task'
    else:
        plan['tasks'][0]['allowed_tools'] = ['unregistered_tool']
    with controlled_gateway(plan) as gateway:
        result = probe().run_provider_probe(gateway, (cve_input(),))
    assert result.planner_validated == 0 and not result.ready
    assert result.planner_checks[0].attempt_count <= 2
    assert result.planner_checks[0].error_codes


@pytest.mark.parametrize('failure', ['TIMEOUT', 'EMPTY', 'TRUNCATED'])
def test_timeout_empty_and_truncated_response_are_reported(failure):
    with controlled_gateway(failure=failure) as gateway:
        result = probe().run_provider_probe(gateway, (cve_input(),))
    assert not result.ready and result.planner_validated == 0
    assert result.planner_checks[0].attempt_count == 2
    assert 'SYNTHETIC private error' not in result.model_dump_json()


def test_failed_probe_overwrites_previous_success(tmp_path, monkeypatch, capsys):
    p = probe()
    path = tmp_path / 'old.json'
    path.write_text('{"ready":true}', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['probe', '--output', str(path), '--mode', 'INVALID'])
    assert p.main() == 2
    report = json.loads(path.read_text(encoding='utf-8'))
    assert not report['ready'] and report['error_code'] == 'PROVIDER_PROBE_FAILED'
    assert 'INVALID' not in capsys.readouterr().out


def test_probe_deadline_stops_only_owned_worker():
    p = probe()
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    try:
        with pytest.raises(TimeoutError, match='PROVIDER_PROBE_TIMEOUT'):
            p.run_bounded_worker([sys.executable, '-c', 'import time; time.sleep(30)'], timeout_seconds=.1)
        assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        unrelated.wait(5)

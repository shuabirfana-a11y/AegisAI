"""Actual TCP transport with real services; synthetic inputs are NOT Benchmark data."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from uuid import uuid4

import httpx
import uvicorn
from app.main import create_app
from app.investigation_api.schemas import (
    ApiError, InvestigationCreateRequest, InvestigationStatusResponse, AnswerResponse,
)
from app.llm.config import ModelConfig
from app.llm.gateway import ModelGateway
from scripts.probe_investigation_http import run_probe
from tests.orchestration.fixtures import scenario

ROOT = Path(__file__).resolve().parents[3]
ORIGIN = 'http://127.0.0.1:5173'
TOKEN = 'SYNTHETIC-phase12c-test-token'


@contextmanager
def tcp_client(app):
    # Keep the socket open from bind through server startup; avoid port races.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, loop='asyncio', http='h11', ws='none',
                                lifespan='on', access_log=False, log_level='warning'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                assert thread.is_alive(), 'TCP server failed during startup'
                assert time.monotonic() < deadline, 'TCP server startup timed out'
                time.sleep(.02)
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False,
                              follow_redirects=False, timeout=5,
                              headers={'Authorization': 'Bearer ' + TOKEN, 'Origin': ORIGIN}) as client:
                assert client.get('/health').status_code == 200
                yield client
        finally:
            server.should_exit = True
            thread.join(10)
            assert not thread.is_alive(), 'Owned TCP test server did not stop'


def bound_case(seed, request):
    return {'case_id': 'synthetic-vllm-0_6_0-chain', 'data_origin': 'SYNTHETIC_TEST',
            'requested_mode': 'MOCK',
            'request': InvestigationCreateRequest(user_query=request.user_query,
                idempotency_key=request.request_key, asset_scope={
                    'asset_id': str(seed.asset_id), 'component_id': str(seed.component_id),
                    'component': seed.component, 'target': seed.cve})}


def save_report(name, report):
    directory = ROOT / 'work/phase12c'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (name + '.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def terminal(client, id):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        response = client.get(f'/api/investigations/{id}/status')
        assert response.status_code == 200
        status = InvestigationStatusResponse.model_validate(response.json())
        if status.overall_status != 'RUNNING':
            return status
        time.sleep(.05)
    raise AssertionError('TCP investigation poll budget exhausted')


def test_tcp_full_chain_eight_operations_and_frozen_answer(engine, monkeypatch):
    seed, request, gateway, calls, _ = scenario(engine)
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', TOKEN)
    monkeypatch.setenv('AEGIS_ASSET_OWNER', seed.actor)
    try:
        with tcp_client(create_app(engine, investigation_gateway=gateway)) as client:
            case = bound_case(seed, request)
            report = run_probe(client, case)
            save_report('controlled-tcp-chain', report)
            assert report['ready'] and report['chain_verified'], report
            assert len(report['endpoints']) == 8
            assert report['planner_validation'] == 'VALIDATED'
            assert report['agent_run_count'] == 3 and report['tool_call_count'] >= 3
            assert report['artifact_count'] == 3 and report['integration_status'] == 'PASS'
            assert report['model_mode']['observed'] == 'MOCK'
            assert report['benchmark'] is False and report['data_origin'] == 'SYNTHETIC_TEST'
            id = report['investigation_id']
            before = len(calls)
            answer = client.get(f'/api/investigations/{id}/answer')
            checked = AnswerResponse.model_validate(answer.json())
            assert checked.fact_origin == 'FROZEN_GATE_CONTEXT'
            assert checked.answer_status == 'COMPLETE' and len(checked.citations) > 0
            assert answer.headers['access-control-allow-origin'] == ORIGIN
            assert client.get(f'/api/investigations/{id}/answer').json() == answer.json()
            assert len(calls) == before
            client_env = dict(os.environ, AEGIS_PROBE_BASE=str(client.base_url),
                              AEGIS_ASSET_TOKEN=TOKEN, AEGIS_PROBE_ID=id,
                              AEGIS_PROBE_BODY=case['request'].model_dump_json())
            frontend = subprocess.run(['node', '--experimental-transform-types',
                str(Path(__file__).with_name('client_probe.mjs'))], env=client_env,
                capture_output=True, text=True, timeout=15)
            assert frontend.returncode == 0, 'Existing TypeScript API client failed its TCP contract check'
            client_report = json.loads(frontend.stdout)
            assert client_report['operations'] == 8 and client_report['answer_status'] == 'COMPLETE'
            save_report('typescript-client-tcp', client_report)
            assert len(calls) == before
            mismatch = run_probe(client, case, requested_mode='REAL')
            assert mismatch['chain_verified'] and not mismatch['ready']
            assert mismatch['error_code'] == 'MODEL_MODE_MISMATCH'
            assert len(calls) == before  # Reuses root; does not silently call another model.
            assert 'Authorization' not in json.dumps(report) and TOKEN not in json.dumps(report)
            missing = client.get(f'/api/investigations/{uuid4()}/status')
            assert missing.status_code == 404
            ApiError.model_validate(missing.json())
            denied = client.get(f'/api/investigations/{id}/status', headers={'Authorization': 'Bearer invalid'})
            assert denied.status_code == 401
            ApiError.model_validate(denied.json())
            with httpx.Client(base_url=str(client.base_url), trust_env=False, timeout=5,
                              headers={'Authorization': 'Bearer invalid'}) as unauthorized:
                refused = run_probe(unauthorized, case)
                assert not refused['ready'] and len(refused['endpoints']) == 1
                assert refused['error_code'] == 'AUTHENTICATION_REQUIRED'
    finally:
        gateway.close()


def test_tcp_default_mock_planning_failure_is_not_a_fake_success(engine, monkeypatch):
    seed, request, unused_gateway, _, _ = scenario(engine)
    unused_gateway.close()
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', TOKEN)
    monkeypatch.setenv('AEGIS_ASSET_OWNER', seed.actor)
    gateway = ModelGateway(ModelConfig())
    try:
        with tcp_client(create_app(engine, investigation_gateway=gateway)) as client:
            report = run_probe(client, bound_case(seed, request))
            save_report('default-mock-failure', report)
            assert not report['ready'] and not report['chain_verified']
            assert report['overall_status'] == 'FAILED' and report['error_code'] == 'PLANNING_FAILED'
            assert report['planner_present'] and report['agent_run_count'] == 0
            assert report['artifact_count'] == 0 and report['answer_status'] == 'FAILED'
            assert report['endpoints']['integration']['http_status'] == 409
            assert report['endpoints']['integration']['error_code'] == 'RESULT_UNAVAILABLE'
            assert len(report['endpoints']) == 8
    finally:
        gateway.close()


def test_tcp_cancel_during_planning_stops_later_agents(engine, monkeypatch):
    seed, request, gateway, _, _ = scenario(engine)
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', TOKEN)
    monkeypatch.setenv('AEGIS_ASSET_OWNER', seed.actor)
    entered, release = threading.Event(), threading.Event()
    original = gateway.text_provider.generate_structured

    def blocked(req, schema):
        entered.set()
        assert release.wait(15)
        return original(req, schema)

    gateway.text_provider.generate_structured = blocked
    try:
        with tcp_client(create_app(engine, investigation_gateway=gateway)) as client:
            body = bound_case(seed, request)['request'].model_dump(mode='json')
            created = client.post('/api/investigations', json=body)
            assert created.status_code == 202 and entered.wait(10)
            id = created.json()['investigation_id']
            timed_out = run_probe(client, bound_case(seed, request), timeout_seconds=.03)
            assert timed_out['error_code'] == 'PROBE_POLL_TIMEOUT'
            assert not timed_out['ready']
            assert 'cancel' not in timed_out['endpoints'] and 'answer' not in timed_out['endpoints']
            assert client.get(f'/api/investigations/{id}/status').json()['cancel_requested'] is False
            premature = client.get(f'/api/investigations/{id}/answer')
            assert premature.status_code == 409
            assert ApiError.model_validate(premature.json()).retryable is True
            cancelled = client.post(f'/api/investigations/{id}/cancel', json={})
            assert cancelled.status_code == 200
            assert InvestigationStatusResponse.model_validate(cancelled.json()).cancel_requested is True
            release.set()
            stopped = terminal(client, id)
            assert stopped.overall_status == 'CANCELLED'
            assert stopped.verification_run_id is None and stopped.analysis_run_id is None
            assert client.get(f'/api/investigations/{id}/trace').json()['agent_runs'] == []
    finally:
        release.set()
        gateway.close()

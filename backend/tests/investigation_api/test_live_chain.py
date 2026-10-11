import time
import threading
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import create_app
from tests.orchestration.fixtures import scenario


HEADERS = {'Authorization': 'Bearer SYNTHETIC-test-token'}


def terminal(client, id):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        response = client.get(f'/api/investigations/{id}/status', headers=HEADERS)
        assert response.status_code == 200, response.text
        if response.json()['overall_status'] != 'RUNNING':
            return response.json()
        time.sleep(.05)
    raise AssertionError('Real Orchestrator did not finish in test budget')


def test_http_runs_actual_chain_and_gets_frozen_outputs(engine, monkeypatch):
    seed, request, gateway, calls, sink = scenario(engine)
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', 'SYNTHETIC-test-token')
    monkeypatch.setenv('AEGIS_ASSET_OWNER', seed.actor)
    try:
        app = create_app(engine, investigation_gateway=gateway)
        with TestClient(app) as client:
            body = {'user_query': request.user_query,
                    'idempotency_key': request.request_key,
                    'asset_scope': {'asset_id': str(seed.asset_id), 'component_id': str(seed.component_id),
                                    'component': seed.component, 'target': seed.cve},
                    'options': {}}
            created = client.post('/api/investigations', json=body, headers=HEADERS)
            assert created.status_code == 202, created.text
            id = created.json()['investigation_id']
            result = terminal(client, id)
            assert result['overall_status'] == 'SUCCEEDED', result
            repeated = client.post('/api/investigations', json=body, headers=HEADERS)
            assert repeated.status_code == 202
            assert repeated.json()['investigation_id'] == id
            changed = client.post('/api/investigations', json={**body, 'user_query': 'changed question'}, headers=HEADERS)
            assert changed.status_code == 409
            trace = client.get(f'/api/investigations/{id}/trace', headers=HEADERS).json()
            assert {x['stage'] for x in trace['stages']} >= {'PLANNING', 'INVESTIGATING', 'VERIFYING', 'ANALYZING', 'INTEGRATING'}
            assert len(trace['agent_runs']) == 3
            artifacts = client.get(f'/api/investigations/{id}/artifacts', headers=HEADERS)
            assert artifacts.status_code == 200, artifacts.text
            assert all(artifacts.json()[key] for key in ('investigation', 'verification', 'analysis'))
            assert 'tool_calls' not in artifacts.text and 'model_calls' not in artifacts.text
            gate = client.get(f'/api/investigations/{id}/integration', headers=HEADERS)
            assert gate.status_code == 200 and gate.json()['status'] == 'PASS', gate.text
            call_count = len(calls)
            answer = client.get(f'/api/investigations/{id}/answer', headers=HEADERS)
            assert answer.status_code == 200, answer.text
            assert answer.json()['fact_origin'] == 'FROZEN_GATE_CONTEXT'
            assert client.get(f'/api/investigations/{id}/answer', headers=HEADERS).json() == answer.json()
            assert len(calls) == call_count
            history = client.get('/api/investigations/history?limit=1&status=SUCCEEDED', headers=HEADERS)
            assert history.status_code == 200 and history.json()['items'][0]['investigation_id'] == id
            assert client.post(f'/api/investigations/{id}/cancel', headers=HEADERS).json()['cancel_requested'] is False
            assert client.get(f'/api/investigations/{uuid4()}/status', headers=HEADERS).status_code == 404
            monkeypatch.setenv('AEGIS_ASSET_OWNER', 'SYNTHETIC-other-owner')
            assert client.get(f'/api/investigations/{id}/answer', headers=HEADERS).status_code == 404
            assert client.get('/api/investigations/history', headers=HEADERS).json()['total'] == 0
            monkeypatch.setenv('AEGIS_ASSET_OWNER', seed.actor)
            from copy import deepcopy
            from app.db import models as m
            from app.db.session import transaction
            from app.agents.contracts import fingerprint
            from app.orchestration.contracts import NAMESPACE
            with transaction(engine) as db:
                row = db.get(m.AgentRun, id)
                before = deepcopy(row.details)
                forged = deepcopy(before)
                forged[NAMESPACE]['context']['artifact_references'][0]['run_id'] = str(uuid4())
                forged[NAMESPACE]['context_hash'] = fingerprint(forged[NAMESPACE]['context'])
                row.details = forged
            try:
                rejected = client.get(f'/api/investigations/{id}/artifacts', headers=HEADERS)
                assert rejected.status_code == 500 and rejected.json()['error_code'] == 'INTERNAL_ERROR'
                assert 'BINDING' not in rejected.text
            finally:
                with transaction(engine) as db:
                    db.get(m.AgentRun, id).details = before
    finally:
        gateway.close()


def test_cancel_during_real_planning_prevents_later_agents_and_reuses_root(engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    seed, request, gateway, calls, sink = scenario(engine)
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', 'SYNTHETIC-test-token')
    monkeypatch.setenv('AEGIS_ASSET_OWNER', seed.actor)
    import app.main as main_module
    from app.investigation_api.service import InvestigationApiService
    monkeypatch.setattr(main_module, 'InvestigationApiService', lambda engine, gateway: InvestigationApiService(engine, gateway, max_workers=1))
    entered, release = threading.Event(), threading.Event()
    original = gateway.text_provider.generate_structured
    def wait(req, schema):
        entered.set()
        assert release.wait(15)
        return original(req, schema)
    gateway.text_provider.generate_structured = wait
    try:
        with TestClient(create_app(engine, investigation_gateway=gateway)) as client:
            body = request.model_dump(mode='json')
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = [pool.submit(client.post, '/api/investigations', json=body, headers=HEADERS) for _ in range(3)]
                results = [future.result(timeout=10) for future in futures]
            assert all(result.status_code == 202 for result in results), [x.text for x in results]
            ids = {result.json()['investigation_id'] for result in results}
            assert len(ids) == 1
            id = ids.pop()
            assert entered.wait(10)
            busy_body = request.model_copy(update={'planner_input': request.planner_input.model_copy(update={
                'query': request.planner_input.query.model_copy(update={'request_key': 'SYNTHETIC-busy-' + uuid4().hex})})}).model_dump(mode='json')
            busy = client.post('/api/investigations', json=busy_body, headers=HEADERS)
            assert busy.status_code == 429 and busy.json()['error_code'] == 'INVESTIGATION_BUSY'
            assert client.get('/api/investigations/history', headers=HEADERS).json()['total'] == 1
            running = client.get(f'/api/investigations/{id}/status', headers=HEADERS).json()
            assert running['overall_status'] == 'RUNNING'
            not_ready = client.get(f'/api/investigations/{id}/answer', headers=HEADERS)
            assert not_ready.status_code == 409 and not_ready.json()['retryable'] is True
            cancelling = client.post(f'/api/investigations/{id}/cancel', headers=HEADERS)
            assert cancelling.status_code == 200 and cancelling.json()['cancel_requested'] is True
            release.set()
            stopped = terminal(client, id)
            assert stopped['overall_status'] == 'CANCELLED'
            assert stopped['verification_run_id'] is None and stopped['analysis_run_id'] is None
            assert client.get('/api/investigations/history', headers=HEADERS).json()['total'] == 1
    finally:
        release.set()
        gateway.close()

from fastapi.testclient import TestClient
from app.main import create_app
from uuid import uuid4
import pytest


def test_openapi_has_eight_typed_investigation_operations_and_no_empty_legacy_success():
    schema = create_app().openapi()
    operations = [(path, method, op) for path, item in schema['paths'].items()
                  for method, op in item.items() if method in ('get', 'post', 'patch', 'delete', 'put')]
    added = [op for path, method, op in operations if path.startswith('/api/investigations')]
    assert len(added) == 8
    # New monitoring endpoints are independently typed; retain the original
    # 42-operation investigation/legacy contract as the compatibility boundary.
    monitoring = [op for path, method, op in operations if path.startswith('/api/v1/intelligence')]
    assert len(monitoring) == 6
    assert len(operations) - len(monitoring) == 42
    for path, method, op in operations:
        code = next(code for code in op['responses'] if code.startswith('2'))
        assert op['responses'][code]['content']['application/json']['schema'], (path, method)
    for op in added:
        assert op['security']
        assert op['responses']['401']['content']['application/json']['schema']


def test_investigation_auth_errors_use_safe_public_protocol(monkeypatch):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', 'SYNTHETIC-test-token')
    # No lifespan: unauthenticated requests must not touch a database or worker.
    client = TestClient(create_app())
    response = client.get('/api/investigations/history')
    assert response.status_code == 401
    assert response.json()['error_code'] == 'AUTHENTICATION_REQUIRED'
    assert 'SYNTHETIC-test-token' not in response.text


def test_cors_is_explicit_and_does_not_replace_auth(monkeypatch):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', 'SYNTHETIC-test-token')
    client = TestClient(create_app())
    response = client.options('/api/investigations', headers={
        'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,idempotency-key,content-type'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert client.options('/api/investigations', headers={
        'Origin': 'https://attacker.invalid', 'Access-Control-Request-Method': 'POST'}).status_code == 400
    assert client.get('/api/investigations/history', headers={'Origin': 'http://localhost:5173'}).status_code == 401
    monkeypatch.setenv('AEGIS_CORS_ORIGINS', '*')
    with pytest.raises(ValueError):
        create_app()


def test_validation_and_internal_errors_never_echo_inputs_or_exceptions(monkeypatch):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', 'SYNTHETIC-test-token')
    app = create_app()
    class BrokenService:
        def history(self, **kwargs):
            raise RuntimeError('database password=secret; C:\\Users\\X\\private')
    app.state.investigations = BrokenService()
    client = TestClient(app)
    headers = {'Authorization': 'Bearer SYNTHETIC-test-token'}
    invalid = client.get('/api/investigations/private-path/status', headers=headers)
    assert invalid.status_code == 422 and invalid.json()['error_code'] == 'INVALID_REQUEST'
    assert 'private-path' not in invalid.text
    response = client.get('/api/investigations/history', headers=headers)
    assert response.status_code == 500 and response.json()['error_code'] == 'INTERNAL_ERROR'
    assert 'secret' not in response.text and 'private' not in response.text
    assert response.json()['request_id'] == response.headers['x-request-id']


@pytest.mark.parametrize('body,header,code', [
    ({'user_query': '查漏洞'}, None, 'IDEMPOTENCY_KEY_REQUIRED'),
    ({'user_query': '查漏洞', 'idempotency_key': ' '}, None, 'INVALID_IDEMPOTENCY_KEY'),
    ({'user_query': '查漏洞', 'idempotency_key': 'one'}, 'two', 'IDEMPOTENCY_KEY_MISMATCH'),
])
def test_create_rejects_invalid_key_before_business(body, header, code, monkeypatch):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', 'SYNTHETIC-test-token')
    app = create_app()
    app.state.investigations = object()
    headers = {'Authorization': 'Bearer SYNTHETIC-test-token'}
    if header:
        headers['Idempotency-Key'] = header
    response = TestClient(app).post('/api/investigations', json=body, headers=headers)
    assert response.status_code == 422
    assert response.json()['error_code'] == code


def test_nested_public_projection_strips_credentials_and_preserves_verdict(monkeypatch):
    from app.investigation_api.projection import public_copy
    monkeypatch.setenv('MODEL_API_KEY', 'SYNTHETIC-real-secret')
    original = {'status': 'CONFLICT', 'value': {'version': '0.6.0', 'api_key': 'do-not-export'},
        'evidence': [{'reference': {'url': 'https://user:password@example.invalid/advisory?token=private#fragment'},
                      'content': 'MODEL_API_KEY=SYNTHETIC-real-secret C:\\Users\\X\\private Bearer secret',
                      'details': {'internal_configuration': 'private'}}],
        'tool_calls': [{'arguments': {'password': 'private'}}]}
    cleaned = public_copy(original)
    assert cleaned['status'] == 'CONFLICT' and cleaned['value']['version'] == '0.6.0'
    assert cleaned['evidence'][0]['reference']['url'] == 'https://example.invalid/advisory'
    assert 'SYNTHETIC-real-secret' not in str(cleaned)
    assert 'private' not in str(cleaned) and 'tool_calls' not in cleaned
    assert original['value']['api_key'] == 'do-not-export'


@pytest.mark.parametrize('state', ['PASS','PASS_WITH_WARNINGS','REPLAN_REQUIRED','HUMAN_REVIEW_REQUIRED','FAILED'])
def test_http_preserves_five_gate_states_without_reclassification(state, monkeypatch):
    from app.investigation_api.schemas import IntegrationResponse
    from app.utils.time import utcnow
    gate = IntegrationResponse(integration_id=uuid4(),logical_investigation_id=uuid4(),trace_id=uuid4(),
        status=state,checks=(),input_hash='0'*64,objective_hash='1'*64,created_at=utcnow(),evaluation_time=utcnow())
    class Service:
        def integration(self, id, *, actor):
            return gate
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', 'SYNTHETIC-test-token')
    app = create_app()
    app.state.investigations = Service()
    response = TestClient(app).get(f'/api/investigations/{uuid4()}/integration',
        headers={'Authorization': 'Bearer SYNTHETIC-test-token'})
    assert response.status_code == 200 and response.json()['status'] == state

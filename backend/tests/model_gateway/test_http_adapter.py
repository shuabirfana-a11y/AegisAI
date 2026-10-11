"""Real adapter tests against controlled protocol responses and a loopback server."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import httpx
import pytest
from app.llm import ModelConfig, ModelGateway
from app.llm.config import ConfigError
from .test_contracts import MemorySink, VulnerabilityAnalysis, module, request


def config(**kwargs):
    return ModelConfig.from_env({'MODEL_PROVIDER': 'openai_compatible',
        'MODEL_NAME': 'text-test', 'MODEL_EMBEDDING_NAME': 'embed-test',
        'MODEL_EMBEDDING_DIMENSION': '3', 'MODEL_API_BASE': 'https://model.example.invalid/prefix/v1/',
        'MODEL_API_KEY': 'secret-contract-key', **kwargs})


def chat(content='Hello from protocol service.', **updates):
    payload = {'model': 'text-test', 'choices': [{'index': 0,
        'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 7, 'completion_tokens': 5, 'total_tokens': 12}}
    payload.update(updates)
    return payload


def adapter_gateway(handler, *, settings=None, sink=None):
    settings = settings or config()
    adapter = module('providers.openai_compatible').OpenAICompatibleProvider
    transport = httpx.MockTransport(handler)
    return ModelGateway(settings, record_sink=sink if sink is not None else MemorySink(),
        text_provider=adapter(settings, capability='text', transport=transport),
        embedding_provider=adapter(settings, capability='embedding', transport=transport))


def test_compatible_text_request_respects_base_prefix_auth_and_usage():
    seen = []
    def handler(req):
        seen.append(req)
        return httpx.Response(200, json=chat())
    sink = MemorySink()
    with adapter_gateway(handler, sink=sink) as model:
        result = model.generate_text(request())
    assert result.status == 'success' and not result.is_mock
    assert result.data.text == 'Hello from protocol service.'
    assert (result.usage.input_tokens, result.usage.output_tokens, result.usage.total_tokens) == (7, 5, 12)
    assert len(seen) == 1 and str(seen[0].url) == 'https://model.example.invalid/prefix/v1/chat/completions'
    assert seen[0].headers['authorization'] == 'Bearer secret-contract-key'
    body = json.loads(seen[0].content)
    assert body['model'] == 'text-test' and body['max_tokens'] == 1024
    assert body['stream'] is False and body['n'] == 1
    assert 'temperature' not in body
    assert 'secret-contract-key' not in sink.records[0].model_dump_json()
    assert 'https://' not in sink.records[0].model_dump_json()


@pytest.mark.parametrize('mode', ['prompt_json', 'json_object', 'json_schema'])
def test_compatible_structured_modes_are_explicit_and_locally_validated(mode):
    seen = []
    fixture = {'cve': 'CVE-2099-9999001', 'risk': 'high', 'evidence': []}
    def handler(req):
        seen.append(json.loads(req.content))
        return httpx.Response(200, json=chat(json.dumps(fixture)))
    with adapter_gateway(handler, settings=config(MODEL_STRUCTURED_MODE=mode,
        MODEL_TOKEN_PARAMETER='max_completion_tokens')) as model:
        result = model.generate_structured(request(), output_model=VulnerabilityAnalysis)
    assert result.status == 'success' and result.data.data == fixture
    assert seen[0]['max_completion_tokens'] == 1024 and 'max_tokens' not in seen[0]
    assert any('JSON' in message['content'] for message in seen[0]['messages'])
    if mode == 'prompt_json':
        assert 'response_format' not in seen[0]
    else:
        assert seen[0]['response_format']['type'] == mode


def test_compatible_invalid_structured_output_preserves_actual_token_usage():
    sink = MemorySink()
    with adapter_gateway(lambda _: httpx.Response(200, json=chat('private-output-not-json')), sink=sink) as model:
        result = model.generate_structured(request(), output_model=VulnerabilityAnalysis)
    assert result.error.code == 'INVALID_JSON' and result.usage.total_tokens == 12
    assert sink.records[0].usage.total_tokens == 12
    assert 'private-output-not-json' not in sink.records[0].model_dump_json()


def test_embedding_response_indices_restore_input_order():
    seen = []
    def handler(req):
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={'model': 'embed-test', 'data': [
            {'index': 1, 'embedding': [0, 1, 0]}, {'index': 0, 'embedding': [1, 0, 0]}],
            'usage': {'prompt_tokens': 8, 'total_tokens': 8}})
    with adapter_gateway(handler) as model:
        result = model.embed({'texts': ['first', 'second']})
    assert result.status == 'success'
    assert result.data.vectors == [[1, 0, 0], [0, 1, 0]]
    assert result.model == 'embed-test' and result.usage.input_tokens == 8
    assert seen[0]['model'] == 'embed-test' and seen[0]['input'] == ['first', 'second']


@pytest.mark.parametrize('data', [
    [{'index': 0, 'embedding': [1, 0]}],
    [{'index': 0, 'embedding': [0, 0, 0]}],
    [{'index': 0, 'embedding': ['bad', 1, 0]}],
    [{'index': 1, 'embedding': [1, 0, 0]}],
    [{'index': 0, 'embedding': [1, 0, 0]}, {'index': 0, 'embedding': [0, 1, 0]}],
])
def test_invalid_embedding_shapes_or_indices_never_succeed(data):
    with adapter_gateway(lambda _: httpx.Response(200, json={'model': 'embed-test', 'data': data})) as model:
        result = model.embed({'texts': ['one']})
    assert result.status == 'failed' and result.error.code == 'INVALID_EMBEDDING'


@pytest.mark.parametrize('status,code,retryable', [
    (401, 'AUTHENTICATION_FAILED', False), (403, 'AUTHENTICATION_FAILED', False),
    (429, 'RATE_LIMITED', True), (500, 'PROVIDER_ERROR', True),
    (400, 'PROVIDER_REQUEST_REJECTED', False), (302, 'INVALID_RESPONSE', False),
])
def test_http_failures_are_safe_and_never_auto_retry_or_redirect(status, code, retryable):
    calls = []
    def handler(req):
        calls.append(req)
        return httpx.Response(status, headers={'Location': 'https://other.invalid/private'},
                              json={'error': 'secret-contract-key and private server traceback'})
    sink = MemorySink()
    with adapter_gateway(handler, sink=sink) as model:
        result = model.generate_text(request())
    assert result.error.code == code and result.error.retryable == retryable
    assert len(calls) == 1 and result.attempt_count == 1
    assert 'secret-contract-key' not in result.model_dump_json() + sink.records[0].model_dump_json()
    assert 'traceback' not in result.error.message


@pytest.mark.parametrize('exception,code', [(httpx.ReadTimeout, 'TIMEOUT'),
                                          (httpx.ConnectError, 'NETWORK_ERROR')])
def test_transport_errors_map_without_exposing_exception_text(exception, code):
    def handler(req):
        raise exception('secret-contract-key private endpoint', request=req)
    with adapter_gateway(handler) as model:
        result = model.generate_text(request())
    assert result.error.code == code and result.error.retryable
    assert 'secret-contract-key' not in result.model_dump_json()


@pytest.mark.parametrize('payload,code', [
    ({}, 'INVALID_RESPONSE'),
    (chat(choices=[]), 'INVALID_RESPONSE'),
    (chat(choices=[{'message': {'role': 'assistant', 'content': None, 'refusal': 'policy'},
                    'finish_reason': 'stop'}]), 'MODEL_REFUSED'),
    (chat(choices=[{'message': {'role': 'assistant', 'content': 'cut'},
                    'finish_reason': 'length'}]), 'OUTPUT_TRUNCATED'),
    (chat(usage={'prompt_tokens': -1}), 'INVALID_RESPONSE'),
])
def test_malformed_refused_and_truncated_responses_are_explicit(payload, code):
    with adapter_gateway(lambda _: httpx.Response(200, json=payload)) as model:
        result = model.generate_text(request())
    assert result.error.code == code and result.data is None


def test_health_probe_only_lists_models_and_unsupported_probe_does_not_generate():
    calls = []
    def handler(req):
        calls.append(req)
        return httpx.Response(200, json={'data': [{'id': 'text-test'}, {'id': 'embed-test'}]})
    with adapter_gateway(handler) as model:
        result = model.health_check(capability='embedding')
    assert result.data.probe_kind == 'http_models' and result.data.model_seen
    assert len(calls) == 1 and calls[0].method == 'GET' and calls[0].url.path.endswith('/models')
    with adapter_gateway(lambda _: httpx.Response(404)) as model:
        result = model.health_check()
    assert result.error.code == 'HEALTH_UNSUPPORTED'


def test_missing_usage_remains_unknown_and_missing_model_has_a_warning():
    payload = chat()
    del payload['usage'], payload['model']
    with adapter_gateway(lambda _: httpx.Response(200, json=payload)) as model:
        result = model.generate_text(request())
    assert result.status == 'success' and result.usage.total_tokens is None
    assert result.model == 'text-test' and result.warnings


@pytest.mark.parametrize('body', [b'not-json', b' ' * (4 * 1024 * 1024 + 1)], ids=['invalid-json', 'oversize'])
def test_non_json_and_oversize_http_responses_are_bounded_failures(body):
    with adapter_gateway(lambda _: httpx.Response(200, content=body)) as model:
        result = model.generate_text(request())
    assert result.error.code == 'INVALID_RESPONSE'


@pytest.mark.parametrize('address', ['http://public.example.invalid/v1',
    'https://user:password@model.example.invalid/v1', 'https://model.example.invalid/v1?key=x',
    'https://model.example.invalid/v1#fragment'])
def test_unsafe_model_addresses_are_rejected_by_configuration(address):
    with pytest.raises(ConfigError):
        config(MODEL_API_BASE=address)


@contextmanager
def loopback_server():
    captured = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            captured.append((self.path, body, self.headers.get('Authorization')))
            encoded = json.dumps(chat()).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:' + str(server.server_port) + '/v1', captured
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_provider_switch_uses_same_gateway_call_and_real_loopback_http():
    sink = MemorySink()
    with ModelGateway(ModelConfig(), record_sink=sink) as model:
        mock_result = model.generate_text(request())
    with loopback_server() as (address, seen):
        settings = config(MODEL_API_BASE=address, MODEL_API_KEY='', MODEL_ALLOW_KEYLESS_LOCAL='true')
        with ModelGateway(settings, record_sink=sink) as model:
            http_result = model.generate_text(request())
    assert mock_result.is_mock and not http_result.is_mock
    assert http_result.status == 'success' and http_result.data.text == 'Hello from protocol service.'
    assert seen[0][0] == '/v1/chat/completions' and seen[0][2] is None
    assert [r.provider for r in sink.records] == ['mock', 'openai_compatible']


def test_refusal_preserves_usage_when_only_output_tokens_are_known():
    payload = chat(usage={'completion_tokens': 5}, choices=[{
        'message': {'role': 'assistant', 'content': None, 'refusal': 'policy'}, 'finish_reason': 'stop'}])
    sink = MemorySink()
    with adapter_gateway(lambda _: httpx.Response(200, json=payload), sink=sink) as model:
        result = model.generate_text(request())
    assert result.error.code == 'MODEL_REFUSED'
    assert result.usage.output_tokens == sink.records[0].usage.output_tokens == 5
    assert result.usage.input_tokens is None and result.usage.total_tokens is None


def test_constructor_identity_failure_closes_both_created_http_clients():
    settings = config()
    adapter = module('providers.openai_compatible').OpenAICompatibleProvider
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=chat()))
    text = adapter(settings, capability='text', transport=transport)
    embedding = adapter(settings, capability='embedding', transport=transport)
    embedding.model = 'unexpected-model'
    with pytest.raises(ConfigError):
        ModelGateway(settings, text_provider=text, embedding_provider=embedding, record_sink=MemorySink())
    assert text.client.is_closed and embedding.client.is_closed

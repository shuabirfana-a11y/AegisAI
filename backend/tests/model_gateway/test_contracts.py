"""Consumer contracts; no database fixture or external model service required."""
from importlib import import_module
import pytest
from pydantic import ValidationError
from pydantic import BaseModel, ConfigDict, model_validator
from typing import Literal
import json
from concurrent.futures import ThreadPoolExecutor


def module(name):
    return import_module('app.llm.' + name)


def test_config_defaults_are_explicit_mock_and_embeddings_are_separate():
    config = module('config').ModelConfig.from_env({})
    assert (config.provider, config.model) == ('mock', 'mock-text-v1')
    assert (config.embedding_provider, config.embedding_model) == ('mock', 'mock-embedding-v1')
    assert config.embedding_dimension == 384


@pytest.mark.parametrize('env', [
    {'MODEL_PROVIDER': 'unknown'},
    {'MODEL_PROVIDER': 'local_embedding'},
    {'MODEL_PROVIDER': 'openai_compatible'},
    {'MODEL_TIMEOUT_SECONDS': '0'},
    {'MODEL_MAX_OUTPUT_TOKENS': '4097'},
])
def test_invalid_model_configuration_fails_before_provider_construction(env):
    config = module('config')
    with pytest.raises(config.ConfigError):
        config.ModelConfig.from_env(env)


def test_credentials_are_not_exposed_by_configuration_or_errors():
    config = module('config')
    values = {'MODEL_PROVIDER': 'openai_compatible', 'MODEL_NAME': 'text-test',
              'MODEL_EMBEDDING_NAME': 'embed-test', 'MODEL_EMBEDDING_DIMENSION': '3',
              'MODEL_API_BASE': 'https://model.example.invalid/v1',
              'MODEL_API_KEY': 'secret-test-key'}
    settings = config.ModelConfig.from_env(values)
    assert 'secret-test-key' not in repr(settings) + settings.model_dump_json()
    with pytest.raises(config.ConfigError) as error:
        config.ModelConfig.from_env({**values, 'MODEL_TIMEOUT_SECONDS': 'secret-test-key'})
    assert 'secret-test-key' not in str(error.value)


@pytest.mark.parametrize('payload', [
    {'messages': []},
    {'messages': [{'role': 'tool', 'content': 'x'}]},
    {'messages': [{'role': 'user', 'content': 'x'}], 'api_key': 'should-not-be-accepted'},
    {'messages': [{'role': 'user', 'content': '中' * 22000}]},
])
def test_text_contract_rejects_unbounded_or_unapproved_inputs(payload):
    with pytest.raises(ValidationError):
        module('schemas').TextRequest.model_validate(payload)


def test_embedding_query_rejects_more_than_one_text():
    with pytest.raises(ValidationError):
        module('schemas').EmbeddingRequest(texts=['a', 'b'], purpose='query')


class MemorySink:
    def __init__(self):
        self.records = []

    def write(self, record):
        self.records.append(record)


class VulnerabilityAnalysis(BaseModel):
    model_config = ConfigDict(extra='forbid')
    cve: str
    risk: Literal['high', 'medium', 'low']
    evidence: list[dict]

    @model_validator(mode='after')
    def synthetic_only(self):
        if self.cve != 'CVE-2099-9999001':
            raise ValueError('Synthetic fixture only')
        return self


def gateway(**kwargs):
    return module('gateway').ModelGateway(module('config').ModelConfig(), **kwargs)


def request():
    return {'messages': [{'role': 'user', 'content': 'Analyze synthetic vulnerability.'}]}


def test_text_generation_records_metadata_and_explicit_mock_identity():
    sink = MemorySink()
    with gateway(record_sink=sink) as model:
        result = model.generate_text({**request(), 'trace_id': 'trace-text'})
    assert result.status == 'success' and result.is_mock
    assert 'MOCK' in result.data.text
    assert result.provider == 'mock' and result.model == 'mock-text-v1'
    assert result.usage.total_tokens == 0
    assert len(sink.records) == 1
    assert sink.records[0].request_id == result.request_id
    assert sink.records[0].function == 'generate_text'
    assert sink.records[0].trace_id == 'trace-text'
    assert result.finished_at >= result.started_at and result.started_at.tzinfo
    assert result.attempt_count == 1


def test_structured_generation_runs_pydantic_validation_and_preserves_schema_identity():
    sink = MemorySink()
    with gateway(record_sink=sink) as model:
        result = model.generate_structured(request(), output_model=VulnerabilityAnalysis)
    assert result.status == 'success'
    assert result.data.data == {'cve': 'CVE-2099-9999001', 'risk': 'high', 'evidence': []}
    assert result.data.schema_name == 'VulnerabilityAnalysis'
    assert len(result.data.schema_hash) == 64
    assert sink.records[0].function == 'generate_structured'


def test_raw_json_schema_is_validated_and_can_reject_extra_fields():
    provider = module('providers.mock').MockProvider(module('config').ModelConfig(),
        structured_fixtures={'OnlyRisk': {'risk': 'high', 'unapproved': True}})
    with gateway(text_provider=provider, record_sink=MemorySink()) as model:
        result = model.generate_structured({**request(), 'schema_name': 'OnlyRisk',
            'json_schema': {'type': 'object', 'properties': {'risk': {'enum': ['high']}},
                            'required': ['risk'], 'additionalProperties': False}})
    assert result.status == 'failed' and result.error.code == 'SCHEMA_VALIDATION_FAILED'
    assert result.data is None


@pytest.mark.parametrize('raw', ['not JSON', '```json\n{}\n```',
    '{"cve":"CVE-2099-9999001","risk":"high","evidence":[]} trailing',
    '{"risk":"high","risk":"low"}', '{"risk":NaN}', '{"risk":Infinity}'])
def test_invalid_json_is_never_repaired_or_reported_success(raw):
    sink = MemorySink()
    provider = module('providers.mock').MockProvider(module('config').ModelConfig(),
        structured_fixtures={'VulnerabilityAnalysis': raw})
    with gateway(text_provider=provider, record_sink=sink) as model:
        result = model.generate_structured(request(), output_model=VulnerabilityAnalysis)
    assert result.status == 'failed' and result.error.code == 'INVALID_JSON'
    assert result.data is None and result.usage.total_tokens == 0
    assert sink.records[0].error.code == 'INVALID_JSON'


@pytest.mark.parametrize('fixture', [
    {'cve': 'CVE-2099-9999001', 'risk': 'extreme', 'evidence': []},
    {'cve': 'CVE-2025-12345', 'risk': 'high', 'evidence': []},
    {'cve': 'CVE-2099-9999001', 'risk': 'high'},
])
def test_json_schema_and_custom_pydantic_validators_are_both_enforced(fixture):
    provider = module('providers.mock').MockProvider(module('config').ModelConfig(),
        structured_fixtures={'VulnerabilityAnalysis': fixture})
    with gateway(text_provider=provider, record_sink=MemorySink()) as model:
        result = model.generate_structured(request(), output_model=VulnerabilityAnalysis)
    assert result.error.code == 'SCHEMA_VALIDATION_FAILED'


@pytest.mark.parametrize('schema', [
    {'$ref': 'https://example.invalid/schema'},
    {'$defs': {'remote': {'$ref': 'file:///private'}}, 'type': 'object'},
    {'type': 'unrecognized'},
    {'description': 'x' * 65537},
])
def test_invalid_or_external_schemas_fail_before_provider_call(schema):
    sink = MemorySink()
    with gateway(record_sink=sink) as model:
        result = model.generate_structured({**request(), 'json_schema': schema})
    assert result.error.code == 'INVALID_SCHEMA'
    assert result.attempt_count == 0 and sink.records[0].attempt_count == 0


def test_structured_generation_requires_exactly_one_schema_source():
    with gateway(record_sink=MemorySink()) as model:
        missing = model.generate_structured(request())
        both = model.generate_structured({**request(), 'json_schema': {'type': 'object'}},
                                        output_model=VulnerabilityAnalysis)
    assert missing.error.code == both.error.code == 'INVALID_SCHEMA'
    assert missing.attempt_count == both.attempt_count == 0


def test_invalid_input_has_safe_error_zero_calls_and_an_audit_record():
    sink = MemorySink()
    with gateway(record_sink=sink) as model:
        result = model.generate_text({'messages': [], 'api_key': 'private-input'})
    assert result.error.code == 'INVALID_INPUT' and result.attempt_count == 0
    assert 'private-input' not in sink.records[0].model_dump_json()


def test_config_output_limit_is_enforced_before_call():
    with gateway(record_sink=MemorySink()) as model:
        result = model.generate_text({**request(), 'max_output_tokens': 1025})
    assert result.error.code == 'INVALID_INPUT' and result.attempt_count == 0


def test_embeddings_are_ordered_finite_nonzero_and_explicitly_simulated():
    with gateway(record_sink=MemorySink()) as model:
        result = model.embed({'texts': ['first document', 'second document']})
    assert result.status == 'success' and result.is_mock
    assert result.model == 'mock-embedding-v1' and result.data.dimension == 384
    assert len(result.data.vectors) == 2 and any(result.data.vectors[0])
    assert result.data.vectors[0] != result.data.vectors[1]


def test_health_check_and_closed_gateway_are_audited_without_generation():
    sink = MemorySink()
    model = gateway(record_sink=sink)
    health = model.health_check(capability='embedding')
    assert health.data.probe_kind == 'mock' and health.data.model_seen
    model.close()
    result = model.generate_text(request())
    assert result.error.code == 'GATEWAY_CLOSED' and result.attempt_count == 0
    assert [r.function for r in sink.records] == ['health_check', 'generate_text']


def test_audit_write_failure_is_explicit_and_does_not_repeat_the_model_call():
    class BrokenSink:
        def write(self, record):
            raise OSError('private-disk-path')
    with gateway(record_sink=BrokenSink()) as model:
        result = model.generate_text(request())
    assert result.error.code == 'AUDIT_WRITE_FAILED'
    assert result.attempt_count == 1 and result.usage.total_tokens == 0
    assert 'private-disk-path' not in result.model_dump_json()


def test_jsonl_records_are_safe_and_complete_under_threaded_calls(tmp_path):
    path = tmp_path / 'calls.jsonl'
    sink = module('records').JsonlRecordSink(path)
    with gateway(record_sink=sink) as model:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: model.generate_text({'messages': [
                {'role': 'user', 'content': 'private-user-question'}]}), range(12)))
    records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    assert len(records) == 12 and len({r['request_id'] for r in records}) == 12
    assert all(r['status'] == 'success' for r in records)
    assert all(r.status == 'success' for r in results)
    assert 'private-user-question' not in path.read_text(encoding='utf-8')
    assert all('data' not in r for r in records)


@pytest.mark.parametrize('raw', ['{"metric":1e400}', '{"description":"\\ud800"}'])
def test_structured_json_rejects_float_overflow_and_invalid_unicode(raw):
    provider = module('providers.mock').MockProvider(module('config').ModelConfig(),
        structured_fixtures={'Numeric': raw})
    with gateway(text_provider=provider, record_sink=MemorySink()) as model:
        result = model.generate_structured({**request(), 'schema_name': 'Numeric',
                                           'json_schema': {'type': 'object'}})
    assert result.status == 'failed' and result.error.code == 'INVALID_JSON'


@pytest.mark.parametrize('field', ['MODEL_NAME', 'MODEL_EMBEDDING_NAME'])
def test_config_rejects_api_key_reflected_in_loggable_model_metadata(field):
    config = module('config')
    with pytest.raises(config.ConfigError):
        config.ModelConfig.from_env({'MODEL_PROVIDER': 'openai_compatible',
            'MODEL_NAME': 'text-test', 'MODEL_EMBEDDING_NAME': 'embed-test',
            'MODEL_EMBEDDING_DIMENSION': '3', 'MODEL_API_BASE': 'https://example.invalid/v1',
            'MODEL_API_KEY': 'secret-contract-key', field: 'alias-secret-contract-key'})


def test_audit_failure_preserves_original_model_error_and_known_usage():
    class BrokenSink:
        def write(self, record):
            raise OSError('private path')
    provider = module('providers.mock').MockProvider(module('config').ModelConfig(),
        structured_fixtures={'VulnerabilityAnalysis': 'invalid JSON'})
    with gateway(text_provider=provider, record_sink=BrokenSink()) as model:
        result = model.generate_structured(request(), output_model=VulnerabilityAnalysis)
    assert result.error.code == 'AUDIT_WRITE_FAILED'
    assert result.original_error.code == 'INVALID_JSON'
    assert result.usage.total_tokens == 0 and result.attempt_count == 1


@pytest.mark.parametrize('trace', ['https://private.invalid/path?token=private',
                                 '//private.invalid/path?token=private', '\ud800'])
def test_trace_ids_cannot_put_urls_or_invalid_unicode_in_call_records(trace):
    sink = MemorySink()
    with gateway(record_sink=sink) as model:
        result = model.generate_text({**request(), 'trace_id': trace})
    assert result.error.code == 'INVALID_INPUT' and result.attempt_count == 0
    assert sink.records[0].trace_id is None and result.trace_id is None


@pytest.mark.parametrize('schema', [{'$ref': '#/$defs/missing'}, {'$ref': '#missing-anchor'}])
def test_unresolved_local_schema_references_fail_before_model_call(schema):
    with gateway(record_sink=MemorySink()) as model:
        result = model.generate_structured({**request(), 'json_schema': schema})
    assert result.error.code == 'INVALID_SCHEMA' and result.attempt_count == 0


def test_valid_local_schema_reference_remains_supported():
    provider = module('providers.mock').MockProvider(module('config').ModelConfig(),
        structured_fixtures={'RiskSummary': {'risk': 'high'}})
    schema = {'type': 'object', '$defs': {'Risk': {'type': 'string', 'enum': ['high']}},
              'properties': {'risk': {'$ref': '#/$defs/Risk'}}, 'required': ['risk']}
    with gateway(text_provider=provider, record_sink=MemorySink()) as model:
        result = model.generate_structured({**request(), 'schema_name': 'RiskSummary', 'json_schema': schema})
    assert result.status == 'success' and result.data.data == {'risk': 'high'}


def test_local_reference_target_must_itself_be_a_schema():
    schema = {'description': 'plain text, not a schema', '$ref': '#/description'}
    with gateway(record_sink=MemorySink()) as model:
        result = model.generate_structured({**request(), 'json_schema': schema})
    assert result.error.code == 'INVALID_SCHEMA' and result.attempt_count == 0


def test_audit_failure_still_returns_safe_result_when_fallback_logger_also_fails(monkeypatch):
    class BrokenSink:
        def write(self, record):
            raise OSError('private storage path')
    def broken_logger(*args, **kwargs):
        raise OSError('private console path')
    monkeypatch.setattr(module('records').logger, 'error', broken_logger)
    with gateway(record_sink=BrokenSink()) as model:
        result = model.generate_text(request())
    assert result.error.code == 'AUDIT_WRITE_FAILED' and result.attempt_count == 1
    assert result.usage.total_tokens == 0
    assert 'private' not in result.model_dump_json()

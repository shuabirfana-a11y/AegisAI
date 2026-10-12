"""Local demo configurations remain usable without keys or embedding downloads."""
import json
from pathlib import Path
from app.llm.config import ModelConfig, ConfigError
from app.llm.gateway import ModelGateway
from app.llm.schemas import EmbeddingRequest
import pytest
import httpx
from app.llm.providers.openai_compatible import OpenAICompatibleProvider

ROOT = Path(__file__).resolve().parents[3]


def profile(name):
    path = ROOT / 'demo/phase12d' / (name + '-profile.json')
    assert path.is_file(), 'Phase12D model profile is not implemented'
    return json.loads(path.read_text(encoding='utf-8'))


def test_local_profiles_are_valid_and_embedding_stays_mock():
    real = ModelConfig.from_env(profile('local-real'))
    mock = ModelConfig.from_env(profile('mock'))
    assert real.provider == 'openai_compatible' and real.allow_keyless_local
    assert real.api_base == 'http://127.0.0.1:11434/v1'
    assert real.api_key is None or not real.api_key.get_secret_value()
    assert mock.provider == 'mock' and mock.api_base is None
    for config in (real, mock):
        with ModelGateway(config) as gateway:
            result = gateway.embed(EmbeddingRequest(texts=['local configuration check'], purpose='query'))
        assert result.status == 'success' and result.is_mock
        assert result.provider == 'mock' and result.data.dimension == 384


def test_keyless_local_profile_cannot_be_repointed_to_remote():
    settings = {**profile('local-real'), 'MODEL_API_BASE': 'https://model.example.invalid/v1'}
    with pytest.raises(ConfigError):
        ModelConfig.from_env(settings)


def test_model_profile_has_bounded_timeout_and_output():
    settings = ModelConfig.from_env(profile('local-real'))
    assert settings.timeout_seconds == 60 and settings.max_output_tokens == 4096
    assert settings.structured_mode == 'json_schema'
    assert settings.token_parameter == 'max_tokens'


def test_local_profile_health_accepts_canonical_ollama_alias():
    config = ModelConfig.from_env(profile('local-real'))
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={
        'data': [{'id': 'aegisai-qwen25-planner:latest'}]}))
    provider = OpenAICompatibleProvider(config, capability='text', transport=transport)
    with ModelGateway(config, text_provider=provider) as gateway:
        result = gateway.health_check()
    assert result.status == 'success'


def test_optional_thinking_control_is_configured_only_at_gateway():
    from app.llm.schemas import TextRequest, Message
    settings = {**profile('local-real'), 'MODEL_REASONING_EFFORT': 'none'}
    config = ModelConfig.from_env(settings)
    requests = []
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={'model': config.model, 'choices': [{
            'message': {'role': 'assistant', 'content': 'SYNTHETIC text'}, 'finish_reason': 'stop'}]})
    with ModelGateway(config, text_provider=OpenAICompatibleProvider(
            config, transport=httpx.MockTransport(respond))) as gateway:
        result = gateway.generate_text(TextRequest(messages=[Message(role='user', content='SYNTHETIC')]))
    assert result.status == 'success' and requests[0]['reasoning_effort'] == 'none'
    assert ModelConfig().reasoning_effort is None


def test_unrecognized_reasoning_effort_fails_configuration():
    with pytest.raises(ConfigError):
        ModelConfig.from_env({**profile('local-real'), 'MODEL_REASONING_EFFORT': 'SYNTHETIC-invalid'})

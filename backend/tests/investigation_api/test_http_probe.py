"""Readiness checks must not relabel synthetic models as real investigations."""
import importlib.util
import json
from pathlib import Path
import sys
import pytest
from app.llm.config import ModelConfig

ROOT = Path(__file__).resolve().parents[3]


def get_probe():
    spec = importlib.util.find_spec('scripts.probe_investigation_http')
    assert spec is not None, 'Phase12-C HTTP probe has not been implemented'
    from scripts import probe_investigation_http
    return probe_investigation_http


def test_real_request_rejects_mock_metadata():
    probe = get_probe()
    mode = probe.check_mode('REAL', 'mock', True)
    assert mode['observed'] == 'MOCK'
    assert mode['matched'] is False
    assert mode['error_code'] == 'MODEL_MODE_MISMATCH'


def test_non_mock_metadata_is_not_a_model_quality_evaluation():
    probe = get_probe()
    mode = probe.check_mode('REAL', 'openai_compatible', False)
    assert mode['observed'] == 'NON_MOCK'
    assert mode['matched'] is True
    assert mode['model_quality_evaluated'] is False


@pytest.mark.parametrize('provider,is_mock', [('mock', False), ('openai_compatible', True)])
def test_inconsistent_provider_flags_are_rejected(provider, is_mock):
    probe = get_probe()
    with pytest.raises(ValueError, match='MODEL_METADATA_INCONSISTENT'):
        probe.check_mode('REAL', provider, is_mock)


@pytest.mark.parametrize('url', [
    'https://example.invalid', 'http://127.0.0.1.evil.invalid:8769',
    'http://user:secret@localhost:8000', 'http://localhost:8000/api',
    'http://localhost:8000?key=secret', 'http://localhost:8000/#fragment',
])
def test_probe_refuses_external_or_ambiguous_origins(url):
    probe = get_probe()
    with pytest.raises(ValueError, match='LOOPBACK_ORIGIN_REQUIRED'):
        probe.checked_origin(url)


def test_fixed_case_has_no_generated_answer_or_asset():
    probe = get_probe()
    case = probe.load_case(ROOT / 'demo/phase12c/real-source-case.json')
    assert case['data_origin'] == 'REAL_SOURCE'
    request = case['request']
    assert request.asset_scope.target == 'CVE-2025-32434'
    assert request.asset_scope.component.package_name == 'torch'
    assert request.asset_scope.component.version == '2.5.1'
    assert request.asset_scope.asset_id is None
    assert 'expected_answer' not in json.loads((ROOT / 'demo/phase12c/real-source-case.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('profile', ['MOCK', 'REMOTE_COMPATIBLE', 'LOCAL_COMPATIBLE'])
def test_documented_model_profiles_validate_offline(profile):
    configs = json.loads((ROOT / 'demo/phase12c/model-profiles.json').read_text(encoding='utf-8'))
    env = configs[profile]
    assert 'MODEL_API_KEY' not in env
    if profile == 'REMOTE_COMPATIBLE':
        env = {**env, 'MODEL_API_KEY': 'SYNTHETIC-CONFIG-TEST-ONLY'}
    config = ModelConfig.from_env(env)
    assert config.provider == ('mock' if profile == 'MOCK' else 'openai_compatible')
    assert config.embedding_provider == 'mock'
    assert config.structured_mode == 'prompt_json'


def test_failed_cli_overwrites_stale_success_without_exposing_secrets(tmp_path, monkeypatch, capsys):
    probe = get_probe()
    destination = tmp_path / 'probe.json'
    destination.write_text('{"ready": true}', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['probe', '--base-url', 'http://user:secret@example.invalid',
                                     '--output', str(destination)])
    assert probe.main() == 2
    report = json.loads(destination.read_text(encoding='utf-8'))
    assert report['ready'] is False and report['error_code'] == 'HTTP_PROBE_FAILED'
    assert 'secret' not in capsys.readouterr().out

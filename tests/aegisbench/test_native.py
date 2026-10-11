"""Native boundary tests use fixtures; they do not measure real Agent quality."""
from types import SimpleNamespace
import json
import pytest

from evaluation.bench.adapters import AegisAIAdapter, corpus_fingerprint
from evaluation.bench.data import load_benchmark
from evaluation.bench.native import configured_gateway
from evaluation.bench.runner import DEFAULT_MANIFEST, write_report, evaluate_dataset


def test_live_factory_with_unconfigured_model_never_builds_gateway(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    assert configured_gateway() is None


def test_real_configuration_can_build_without_connecting_or_loading_embeddings(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "openai_compatible")
    monkeypatch.setenv("MODEL_NAME", "fixture-only-model")
    monkeypatch.setenv("MODEL_API_BASE", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("MODEL_ALLOW_KEYLESS_LOCAL", "true")
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    gateway = configured_gateway()
    try:
        assert gateway.config.provider == "openai_compatible"
        assert gateway.config.embedding_provider == "mock"
    finally:
        gateway.close()


def test_native_refuses_mismatched_source_corpus_and_multiple_asset_scope():
    data = load_benchmark(DEFAULT_MANIFEST)
    gateway = SimpleNamespace(config=SimpleNamespace(provider="openai_compatible"))
    adapter = AegisAIAdapter(service=object(), gateway=gateway, actor="fixture")
    assert adapter.run(data["questions"][0], data["sources"]).error_code == "NATIVE_CORPUS_NOT_IDENTICAL"
    adapter.runtime_corpus = corpus_fingerprint(data["sources"])
    multi = next(q for q in data["questions"] if len(q.input_context.get("assets", [])) > 1)
    assert adapter.run(multi, data["sources"]).error_code == "NATIVE_SINGLE_ASSET_SCOPE_LIMIT"


def test_native_request_version_cannot_silently_change_case_input():
    data = load_benchmark(DEFAULT_MANIFEST)
    q = next(q for q in data["questions"] if q.id == "GHSA-53q9-r3pm-6pq6-affected")
    raw = {"planner_input": {"query": {"question": q.question, "target": q.input_context["target"],
                                     "request_key": "fixture-key"},
                             "component": {"name": "torch", "ecosystem": "PyPI", "version": "2.6.0"}}}
    class NeverCalled:
        def investigate(self, *args, **kwargs):
            raise AssertionError("Mismatched native input must be rejected before execution")
    adapter = AegisAIAdapter(NeverCalled(), SimpleNamespace(config=SimpleNamespace(provider="openai_compatible")),
                            "fixture", {q.id: raw}, corpus_fingerprint(data["sources"]))
    assert adapter.run(q, data["sources"]).error_code == "NATIVE_REQUEST_COMPONENT_MISMATCH"


def test_report_does_not_leak_password_embedded_in_database_configuration(monkeypatch, tmp_path):
    from evaluation.bench.adapters import KeywordAdapter
    from evaluation.bench.schema import Prediction
    secret = "fixture-dsn-sensitive-marker"
    monkeypatch.setenv("AEGIS_BENCH_DATABASE_URL", f"postgresql://fixture:{secret}@localhost/aegis_bench_test")
    class FixtureAdapter(KeywordAdapter):
        name = "fixture"
        def run(self, question, sources):
            return Prediction(question_id=question.id, baseline=self.name, status="SUCCEEDED", answer={"detail": secret})
    write_report(evaluate_dataset(load_benchmark(DEFAULT_MANIFEST), adapters=[FixtureAdapter()]), tmp_path)
    assert secret not in (tmp_path / "report.json").read_text(encoding="utf-8")


def test_native_uses_fresh_request_key_and_does_not_invent_completed_steps():
    from uuid import uuid4
    from evaluation.bench.schema import Question
    data = load_benchmark(DEFAULT_MANIFEST)
    q = next(q for q in data["questions"] if q.id == "GHSA-53q9-r3pm-6pq6-affected")
    q = Question.model_validate({**q.model_dump(), "origin": "TEST_FIXTURE"})
    captured = []
    run_id = uuid4()
    context = SimpleNamespace(logical_investigation_id=run_id, investigation_run_id=run_id, analysis_run_id=None)
    envelope = SimpleNamespace(answer_status="REVIEW_REQUIRED", integration_status="HUMAN_REVIEW_REQUIRED",
                                risk_assessment=None, verified_claims=[], citations=[])
    class FixtureService:
        def investigate(self, request, **kwargs):
            captured.append(request)
            return SimpleNamespace(context=context, answer=envelope)
        def get_trace(self, *args, **kwargs):
            return SimpleNamespace(planner=None, agent_runs=[SimpleNamespace(run_id=run_id, status="failed",
                task_statuses={"investigation": "FAILED"}, tool_calls=[])])
    raw = {"planner_input": {"query": {"question": q.question, "target": q.input_context["target"], "request_key": "reused-key"},
                             "component": {"name": "torch", "ecosystem": "PyPI", "version": "2.5.1"}}}
    gateway = SimpleNamespace(config=SimpleNamespace(provider="openai_compatible", model="fixture-only"))
    adapter = AegisAIAdapter(FixtureService(), gateway, "fixture-actor", {q.id: raw}, corpus_fingerprint(data["sources"]))
    result = adapter.run(q, data["sources"])
    assert captured[0].request_key != "reused-key"
    assert raw["planner_input"]["query"]["request_key"] == "reused-key"
    assert result.completed_hops == []
    assert result.abstained is True and result.answer["native_answer_status"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize("query", ["host=remote.invalid", "hostaddr=192.0.2.1", "dbname=other_database",
                                   "service=untrusted", "port=6543"])
def test_native_database_query_overrides_are_refused_before_engine_creation(monkeypatch, tmp_path, query):
    from evaluation.bench.native import native_adapter
    def prohibited(*args, **kwargs):
        raise AssertionError("Unvalidated connection must never create an engine")
    monkeypatch.setattr("sqlalchemy.create_engine", prohibited)
    monkeypatch.setenv("AEGIS_BENCH_DATABASE_URL", f"postgresql+psycopg://fixture@localhost/aegis_bench_test?{query}")
    with pytest.raises(ValueError, match="NATIVE_DEDICATED_LOCAL_BENCH_DATABASE_REQUIRED"):
        native_adapter(object(), load_benchmark(DEFAULT_MANIFEST), tmp_path / "requests.json", "fixture")


def test_native_factory_stays_unavailable_until_effective_data_and_inventory_parity_exist(monkeypatch, tmp_path):
    import evaluation.bench.native as native
    from evaluation.bench.data import sha256
    monkeypatch.setattr(native, "__file__", str(tmp_path / "evaluation/bench/native.py"))
    path = tmp_path / "evaluation/experiments/requests.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("AEGIS_BENCH_DATABASE_URL", "postgresql+psycopg://fixture@localhost/aegis_bench_test")
    monkeypatch.setenv("AEGIS_BENCH_ACTOR", "fixture-actor")
    def prohibited(*args, **kwargs):
        raise AssertionError("Raw source parity alone cannot authorize native execution")
    monkeypatch.setattr("sqlalchemy.create_engine", prohibited)
    gateway = SimpleNamespace(config=SimpleNamespace(provider="openai_compatible"))
    data = load_benchmark(DEFAULT_MANIFEST)
    adapter = native.native_adapter(gateway, data, path, "fixture")
    assert adapter.run(data["questions"][0], data["sources"]).error_code == "NATIVE_EFFECTIVE_DATA_PARITY_NOT_IMPLEMENTED"
    assert adapter.configuration["native_request_map_sha256"] == sha256(path)


def test_real_case_cannot_bypass_parity_gate_with_injected_native_service():
    data = load_benchmark(DEFAULT_MANIFEST)
    q = next(q for q in data["questions"] if q.id == "GHSA-53q9-r3pm-6pq6-affected")
    raw = {"planner_input": {"query": {"question": q.question, "target": q.input_context["target"], "request_key": "fixture-key"},
                             "component": {"name": "torch", "ecosystem": "PyPI", "version": "2.5.1"}}}
    class NeverCalled:
        def investigate(self, *args, **kwargs):
            raise AssertionError("Real cases require effective normalized data and inventory parity")
    adapter = AegisAIAdapter(NeverCalled(), SimpleNamespace(config=SimpleNamespace(provider="openai_compatible")),
                            "fixture", {q.id: raw}, corpus_fingerprint(data["sources"]))
    assert adapter.run(q, data["sources"]).error_code == "NATIVE_EFFECTIVE_DATA_PARITY_NOT_IMPLEMENTED"

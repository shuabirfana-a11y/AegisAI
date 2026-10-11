"""Default evaluation is offline; fixture model outputs are not benchmark scores."""
import json
from pathlib import Path
from types import SimpleNamespace

from evaluation.bench.adapters import KeywordAdapter, FixedWorkflowAdapter, RagOnlyAdapter, AegisAIAdapter
from evaluation.bench.data import load_benchmark
from evaluation.bench.runner import evaluate_dataset, write_report
from evaluation.bench.schema import Question, Prediction


MANIFEST = Path(__file__).resolve().parents[2] / "evaluation/datasets/AegisBench-v0.2-pilot/manifest.json"


def data():
    return load_benchmark(MANIFEST)


def test_default_run_never_calls_network_and_reports_missing_real_model(monkeypatch, tmp_path):
    def prohibited(*args, **kwargs):
        raise AssertionError("Default evaluation must not connect to external services")
    monkeypatch.setattr("socket.socket.connect", prohibited)
    report = evaluate_dataset(data())
    assert report["sample_count"] == 49
    assert report["eligible_gold_count"] == 0
    assert report["quality_status"] == "NOT_EVALUATED"
    for name in ["rag_only", "aegisai"]:
        assert report["variants"][name]["metrics"]["execution"] == {"NOT_EVALUATED": 49}
        assert report["variants"][name]["metrics"]["accuracy"] is None
    assert report["variants"]["fixed_workflow"]["metrics"]["execution"] == {"SUCCEEDED": 49}
    write_report(report, tmp_path)
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["quality_status"] == "NOT_EVALUATED"


def test_fixed_workflow_uses_real_boundaries_union_and_abstention():
    dataset = data()
    adapter = FixedWorkflowAdapter()
    qs = {q.id: q for q in dataset["questions"]}
    for suffix, expected in [("affected", "AFFECTED"), ("fixed", "NOT_AFFECTED"),
                             ("unknown", "UNKNOWN"), ("gap", "NOT_AFFECTED"), ("older-fix", "NOT_AFFECTED")]:
        result = adapter.run(qs[f"GHSA-c67j-w6g6-q2cm-{suffix}"], dataset["sources"])
        assert result.answer["affected"] == expected
    assert adapter.run(qs["cross-advisory-missing-version"], dataset["sources"]).abstained is True


def test_mock_gateway_is_refused_before_generation():
    mock = SimpleNamespace(config=SimpleNamespace(provider="mock"))
    q = data()["questions"][0]
    assert RagOnlyAdapter(mock).run(q, data()["sources"]).status == "NOT_EVALUATED"
    assert AegisAIAdapter(gateway=mock).run(q, data()["sources"]).status == "NOT_EVALUATED"


def test_rag_prompt_has_only_question_and_retrieved_source_not_labels():
    captured = []
    class FixtureGateway:
        config = SimpleNamespace(provider="openai_compatible", model="fixture-only")
        def generate_structured(self, request, **kwargs):
            captured.append(request.model_dump())
            return SimpleNamespace(is_mock=False, status="success", provider="openai_compatible", model="fixture-only",
                usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}),
                request_id="fixture", data=SimpleNamespace(data={"answer": {"affected": "UNKNOWN"}, "claims": [], "abstained": True}))
    q = Question(id="fixture-q", category="version", question="Is this affected?",
                 input_context={"target": "CVE-2025-32434", "component": "torch", "version": "2.5.1"},
                 source_ids=["GHSA-53q9-r3pm-6pq6"], origin="TEST_FIXTURE")
    result = RagOnlyAdapter(FixtureGateway()).run(q, data()["sources"])
    assert result.status == "SUCCEEDED"
    raw = json.dumps(captured)
    assert "expected_answer" not in raw and "review_status" not in raw and "should_abstain" not in raw
    assert '"model": "fixture-only"' not in raw


def test_adapter_exception_is_preserved_without_leaking_exception_message(tmp_path, monkeypatch):
    secret = "fixture-sensitive-marker"
    class Broken(KeywordAdapter):
        name = "broken"
        def run(self, question, sources):
            raise RuntimeError(secret)
    monkeypatch.setenv("MODEL_API_KEY", secret)
    report = evaluate_dataset(data(), adapters=[Broken()])
    assert report["variants"]["broken"]["metrics"]["execution"] == {"FAILED": 49}
    write_report(report, tmp_path)
    assert secret not in (tmp_path / "report.json").read_text(encoding="utf-8")


def test_report_redacts_credentials_even_if_adapter_returns_them(tmp_path, monkeypatch):
    secret = "fixture-report-sensitive-marker"
    monkeypatch.setenv("MODEL_API_KEY", secret)
    class Unsafe(KeywordAdapter):
        name = "unsafe"
        def run(self, question, sources):
            return Prediction(question_id=question.id, baseline=self.name, status="SUCCEEDED",
                              answer={"summary": secret}, metadata={"api_key": secret})
    report = evaluate_dataset(data(), adapters=[Unsafe()])
    write_report(report, tmp_path)
    raw = (tmp_path / "report.json").read_text(encoding="utf-8")
    assert secret not in raw and "api_key" not in raw


def test_keyword_does_not_claim_version_inference_or_verified_exploit():
    dataset = data()
    q = next(q for q in dataset["questions"] if q.category == "version")
    result = KeywordAdapter().run(q, dataset["sources"])
    assert result.answer["affected"] == "UNKNOWN" and result.abstained is True


def test_recorded_answers_can_be_rescored_without_new_model_calls(tmp_path, monkeypatch):
    from evaluation.bench.runner import main
    original, rescored = tmp_path / "original", tmp_path / "rescored"
    assert main(["--output", str(original)]) == 0
    def prohibited(*args, **kwargs):
        raise AssertionError("Rescoring must not call a model or connect to a database")
    monkeypatch.setattr("socket.socket.connect", prohibited)
    assert main(["--rescore-report", str(original / "report.json"), "--outcome-audit",
                 str(original / "outcome-audit-pending.jsonl"), "--output", str(rescored)]) == 0
    before = json.loads((original / "report.json").read_text(encoding="utf-8"))
    after = json.loads((rescored / "report.json").read_text(encoding="utf-8"))
    assert after["parameters"]["execution_mode"] == "RESCORE_RECORDED_OUTPUTS"
    assert before["variants"]["fixed_workflow"]["predictions"] == after["variants"]["fixed_workflow"]["predictions"]


def test_effective_generation_settings_are_allowlisted_in_reports(tmp_path):
    gateway = SimpleNamespace(config=SimpleNamespace(provider="openai_compatible", model="fixture-only",
        timeout_seconds=17.0, max_output_tokens=321, structured_mode="json_schema", token_parameter="max_completion_tokens",
        api_key="fixture-never-export", api_base="https://private.invalid/v1"))
    adapter = RagOnlyAdapter(gateway)
    dataset = data()
    dataset["questions"], dataset["annotations"] = [], []
    report = evaluate_dataset(dataset, adapters=[adapter])
    settings = report["variants"]["rag_only"]["configuration"]
    assert settings["model"]["max_output_tokens"] == 321
    assert settings["model"]["timeout_seconds"] == 17.0
    assert settings["model"]["structured_mode"] == "json_schema"
    write_report(report, tmp_path)
    text = (tmp_path / "report.json").read_text(encoding="utf-8")
    assert "fixture-never-export" not in text and "private.invalid" not in text

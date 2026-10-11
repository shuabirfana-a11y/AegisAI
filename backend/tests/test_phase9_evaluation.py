"""Evaluation contracts; all local labels are TEST_FIXTURE, never benchmark gold."""
import importlib
import importlib.util
import json
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def module(name):
    assert importlib.util.find_spec("evaluation") is not None, "AegisBench package missing"
    assert importlib.util.find_spec(name) is not None, f"Missing evaluation behavior: {name}"
    return importlib.import_module(name)


def test_classification_counts_failed_predictions_and_false_safe():
    metrics = module("evaluation.metrics").classification_metrics(
        [
            {"expected": "affected", "predicted": "not_affected"},
            {"expected": "affected", "predicted": "affected"},
            {"expected": "unknown", "predicted": "unknown"},
            {"expected": "not_affected", "predicted": "affected"},
            {"expected": "not_affected", "predicted": None},
        ],
        labels=["affected", "not_affected", "unknown"],
    )
    assert metrics["accuracy"] == 0.4
    assert metrics["false_safe_count"] == 1
    assert metrics["false_safe_rate"] == 0.5
    assert metrics["per_class"]["affected"] == {
        "tp": 1, "fp": 1, "fn": 1, "support": 2,
        "precision": 0.5, "recall": 0.5, "f1": 0.5,
    }
    assert metrics["confusion_matrix"]["not_affected"]["NO_PREDICTION"] == 1


def test_empty_metrics_are_null_instead_of_a_perfect_score():
    metrics = module("evaluation.metrics").classification_metrics([], labels=["relevant", "irrelevant", "uncertain"])
    assert metrics["accuracy"] is None
    assert metrics["macro_f1"] is None
    assert metrics["per_class"]["relevant"]["precision"] is None


def test_unrecognized_prediction_is_rejected_instead_of_becoming_a_negative():
    with pytest.raises(ValueError, match="label"):
        module("evaluation.metrics").classification_metrics(
            [{"expected": "affected", "predicted": "invented"}], labels=["affected", "not_affected"]
        )


def test_retrieval_preserves_rank_and_counts_empty_result_as_zero():
    value = module("evaluation.metrics").retrieval_metrics([
        {"relevant_ids": ["a", "b"], "retrieved_ids": ["x", "a", "a", "b"]},
        {"relevant_ids": ["c"], "retrieved_ids": []},
        {"relevant_ids": [], "retrieved_ids": ["x"]},
    ], k=2)
    assert value["recall_at_k"] == 0.25
    assert value["mrr"] == 0.25
    assert value["scored_queries"] == 2
    assert value["unlabeled_queries"] == 1


def test_abstention_separates_unknown_and_answerable_denominators():
    value = module("evaluation.metrics").abstention_metrics([
        {"should_abstain": True, "abstained": True},
        {"should_abstain": True, "abstained": False},
        {"should_abstain": False, "abstained": True},
    ])
    assert value["correct_abstention_rate"] == 0.5
    assert value["incorrect_abstention_rate"] == 1.0
    assert value["false_confident_answer_count"] == 1


def test_unsupported_claim_rate_requires_reviewed_claim_counts():
    metrics = module("evaluation.metrics")
    assert metrics.unsupported_claim_metrics([])["unsupported_claim_rate"] is None
    value = metrics.unsupported_claim_metrics([
        {"claim_count": 3, "unsupported_claim_count": 1},
        {"claim_count": 1, "unsupported_claim_count": 1},
    ])
    assert value["unsupported_claim_rate"] == 0.5
    with pytest.raises(ValueError):
        metrics.unsupported_claim_metrics([{"claim_count": 1, "unsupported_claim_count": 2}])


def test_latency_percentiles_are_computed_from_observations():
    value = module("evaluation.metrics").latency_metrics([1.0, 2.0, 3.0, 4.0])
    assert value["p50_ms"] == 2.5
    assert value["p95_ms"] == pytest.approx(3.85)
    assert value["mean_ms"] == 2.5
    assert module("evaluation.metrics").latency_metrics([])["p95_ms"] is None


def approved_gold(**changes):
    return {
        "case_id": "fixture-case", "origin": "REAL_SOURCE_CANDIDATE",
        "expected": {"label": "affected"}, "annotator": "reviewer-001",
        "annotator_type": "HUMAN", "reviewer": "reviewer-002", "reviewer_type": "HUMAN",
        "review_status": "APPROVED", "annotation_note": "Reviewed source scope and boundary",
        "supporting_evidence": [{"source_url": "https://example.org/advisory", "locator": {"section": "affected"}, "excerpt": "reviewed evidence"}],
        **changes,
    }


@pytest.mark.parametrize("changes", [
    {"review_status": "PENDING_HUMAN_REVIEW"},
    {"annotator_type": "LLM"},
    {"reviewer_type": "AGENT"},
    {"reviewer": ""},
    {"annotation_note": ""},
    {"supporting_evidence": []},
    {"supporting_evidence": [{"source_url": "https://example.org/advisory"}]},
    {"origin": "TEST_FIXTURE"},
])
def test_machine_drafts_unreviewed_and_fixture_gold_never_enter_formal_metrics(changes):
    reason = module("evaluation.dataset").gold_exclusion_reason(approved_gold(**changes))
    assert reason is not None


def test_complete_human_review_is_eligible_but_never_transmitted_to_runtime():
    dataset = module("evaluation.dataset")
    assert dataset.gold_exclusion_reason(approved_gold()) is None
    payload = dataset.assistant_payload({
        "case_id": "fixture-case", "question": "Which versions are affected?", "target": "CVE-2025-32434",
        "expected": {"secret_gold": "must not transmit"}, "annotation_note": "private label", "mode": "fast",
    }, request_key="test-run")
    assert payload == {"question": "Which versions are affected?", "target": "CVE-2025-32434", "mode": "fast", "request_key": "test-run", "realtime": False}


@contextmanager
def runtime_server():
    observations = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def response(self, status, value):
            data = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            observations.append({"path": self.path, "body": data, "authorization": self.headers.get("Authorization")})
            if self.path == "/api/v1/assistant/query":
                self.response(202, {"id": "run-1", "status": "running"})
            elif self.path == "/api/v1/tools/get_vulnerability":
                self.response(200, {"tool": "get_vulnerability", "status": "failed", "data": {}, "evidence_refs": [], "errors": [{"code": "DB_ERROR"}], "warnings": [], "duration_ms": 1, "retryable": False, "trace_id": "trace-1"})
            else:
                self.response(404, {"detail": "not found"})
        def do_GET(self):
            if self.path == "/api/v1/assistant/runs/run-1":
                self.response(200, {"id": "run-1", "status": "succeeded", "result": {"answer": "Source-supported answer", "gate": {"status": "PASS"}, "evidence_refs": [{"evidence_id": "e1"}]}})
            elif self.path == "/api/v1/assistant/runs/run-1/trace":
                self.response(200, {"items": [], "events": []})
            else:
                self.response(404, {"detail": "not found"})
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", observations
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_async_runtime_adapter_polls_real_http_and_keeps_gold_out_of_payload():
    with runtime_server() as (url, observations):
        adapter = module("evaluation.runners.runtime").RuntimeAdapter(url, token="test-token", timeout=1, poll_interval=0)
        result = adapter.assistant({"case_id": "fixture-case", "question": "Real question", "expected": {"label": "gold"}}, mode="deep")
    assert result["status"] == "COMPLETED"
    assert result["actual"]["answer"] == "Source-supported answer"
    assert result["latency_ms"] >= 0
    assert observations[0]["authorization"] == "Bearer test-token"
    assert "expected" not in observations[0]["body"]
    assert observations[0]["body"]["mode"] == "deep"


def test_http_200_tool_failure_is_not_counted_as_success():
    with runtime_server() as (url, _):
        value = module("evaluation.runners.runtime").RuntimeAdapter(url, token="test-token", timeout=1).tool("get_vulnerability", {"target": "CVE-2025-32434"})
    assert value["status"] == "FAILED"
    assert value["error_type"] == "TOOL_ERROR"
    assert value["actual"]["errors"][0]["code"] == "DB_ERROR"


def test_runtime_rejects_write_tools_and_arbitrary_url():
    runtime = module("evaluation.runners.runtime")
    adapter = runtime.RuntimeAdapter("http://127.0.0.1:8000", token="test-token")
    with pytest.raises(ValueError, match="read-only"):
        adapter.tool("verify_claim", {"claim_id": "unused"})
    with pytest.raises(ValueError, match="loopback"):
        runtime.RuntimeAdapter("https://example.org", token="test-token")


def test_rag_without_real_llm_is_blocked_instead_of_fabricating_baseline():
    value = module("evaluation.baselines").baseline_readiness("rag_only", {})
    assert value["status"] == "BLOCKED"
    assert "LLM" in value["reason"]


def test_error_analysis_includes_failures_and_excludes_unreviewed_labels():
    scoring = module("evaluation.scoring")
    value = scoring.summarize(
        [{"case_id": "fixture-case", "group": "B", "origin": "REAL_SOURCE_CANDIDATE"}],
        [approved_gold()],
        [{"case_id": "fixture-case", "variant": "full_agent", "status": "FAILED", "actual": {}, "error_type": "TOOL_ERROR", "error": "Runtime failed", "latency_ms": 12}],
    )
    assert value["status"] == "PARTIAL"
    assert value["formal_scored_cases"] == 1
    assert value["classification"]["B"]["accuracy"] == 0.0
    assert value["errors"][0]["expected"] == {"label": "affected"}
    assert value["errors"][0]["error_type"] == "TOOL_ERROR"


def test_default_dataset_has_no_invented_human_review():
    dataset = module("evaluation.dataset").load_dataset(ROOT / "evaluation/datasets/AegisBench-v0.1/manifest.json")
    assert set(dataset["manifest"]["groups"]) == set("ABCDEFGHIJK")
    assert dataset["manifest"]["time_split"]["status"] == "NOT_ESTABLISHED"
    assert dataset["eligible_gold"] == []
    assert len(dataset["questions"]) > 0
    assert all("expected" not in q for q in dataset["questions"])


def test_suite_executes_available_adapters_but_keeps_missing_gold_partial():
    run = module("evaluation.run")
    with runtime_server() as (url, _):
        adapter = module("evaluation.runners.runtime").RuntimeAdapter(url, token="test-token", timeout=1, poll_interval=0)
        dataset = {"manifest": {"dataset_version": "TEST_FIXTURE", "sample_count": 1},
                   "questions": [{"case_id": "fixture-case", "group": "F", "origin": "TEST_FIXTURE", "question": "Which fact is supported?", "target": "CVE-2025-32434", "mode": "fast"}],
                   "gold": [], "eligible_gold": [], "excluded_gold": []}
        result = run.execute_suite(dataset, adapter, variants=["rag_only", "hybrid_fixed", "full_agent", "no_verification"])
    rows = {r["variant"]: r for r in result["results"]}
    assert rows["rag_only"]["status"] == "BLOCKED"
    assert rows["no_verification"]["status"] == "BLOCKED"
    assert rows["hybrid_fixed"]["status"] == "FAILED"
    assert rows["full_agent"]["status"] == "COMPLETED"
    assert result["status"] == "PARTIAL"
    assert result["formal_scored_cases"] == 0
    assert result["summaries"]["full_agent"]["qa"]["accuracy"] is None
    assert any(e["error_type"] == "TOOL_ERROR" for e in result["runtime_errors"])


def test_missing_token_records_blocked_cases_without_talking_to_runtime():
    run = module("evaluation.run")
    dataset = {"manifest": {"dataset_version": "TEST_FIXTURE", "sample_count": 1},
               "questions": [{"case_id": "fixture-case", "group": "F", "origin": "TEST_FIXTURE", "question": "Question"}],
               "gold": [], "eligible_gold": [], "excluded_gold": []}
    adapter = module("evaluation.runners.runtime").RuntimeAdapter("http://127.0.0.1:1", token=None, timeout=0.01)
    result = run.execute_suite(dataset, adapter, variants=["full_agent"])
    assert result["status"] == "PARTIAL"
    assert result["results"][0]["status"] == "BLOCKED"
    assert result["results"][0]["latency_ms"] is None


def test_runner_exit_code_and_report_preserve_partial_result(tmp_path, monkeypatch):
    run = module("evaluation.run")
    monkeypatch.delenv("AEGIS_ASSET_TOKEN", raising=False)
    output = tmp_path / "benchmark.json"
    code = run.main(["--suite", "full", "--limit", "1", "--output", str(output)])
    result = json.loads(output.read_text(encoding="utf-8"))
    assert code == 2
    assert result["status"] == "PARTIAL"
    assert result["formal_scored_cases"] == 0
    assert result["environment"]["credentials_recorded"] is False

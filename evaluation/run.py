"""Reusable Phase 9 benchmark preparation runner; completion is not correctness."""
import argparse
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from evaluation.baselines import baseline_readiness
from evaluation.dataset import load_dataset
from evaluation.runners.runtime import RuntimeAdapter
from evaluation.scoring import summarize

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "evaluation/datasets/AegisBench-v0.1/manifest.json"
VARIANTS = ["rag_only", "hybrid_fixed", "full_agent", "no_verification"]


def _blocked(reason):
    return {"status": "BLOCKED", "actual": {}, "error": reason, "error_type": "INTEGRATION_ERROR", "latency_ms": None}


def _hybrid_fixed(question, adapter):
    """Fixed read-only tool workflow, explicitly without an LLM answer generator."""
    started = time.perf_counter()
    if question.get("asset_id"):
        calls = [("get_asset_risks", {"asset_id": question["asset_id"]})]
    elif question.get("target"):
        calls = [("get_vulnerability", {"target": question["target"]}),
                 ("get_claims", {"target": question["target"], "limit": 100}),
                 ("relation_query", {"target": question["target"], "limit": 100}),
                 ("semantic_search", {"query": question["question"], "limit": 5})]
    else:
        calls = [("semantic_search", {"query": question["question"], "limit": 5})]
    steps = []
    for name, arguments in calls:
        step = adapter.tool(name, arguments)
        steps.append({"tool": name, **step})
    failures = [step for step in steps if step["status"] == "FAILED"]
    partial = any(step["status"] == "PARTIAL" for step in steps)
    result = {"status": "FAILED" if failures else "PARTIAL" if partial else "COMPLETED",
              "actual": {"tool_results": [step["actual"] for step in steps],
                         "capability": "FIXED_READ_ONLY_TOOL_WORKFLOW; NO_GENERATION_MODEL"},
              "steps": steps, "tool_calls": len(steps), "llm_calls": None,
              "input_tokens": None, "output_tokens": None,
              "latency_ms": (time.perf_counter() - started) * 1000}
    if failures:
        result.update(error_type="TOOL_ERROR", error="One or more actual tool calls failed")
    return result


def execute_suite(dataset, adapter, *, variants=None, metadata=None, limit=None):
    """Run actual available adapters and retain every failed or blocked case."""
    variants = list(variants if variants is not None else VARIANTS)
    metadata = metadata or {}
    questions = dataset["questions"][:limit] if limit is not None else dataset["questions"]
    results = []
    readiness = {variant: baseline_readiness(variant, metadata) for variant in variants}
    for question in questions:
        for variant in variants:
            if readiness[variant]["status"] == "BLOCKED":
                outcome = _blocked(readiness[variant]["reason"])
            elif not adapter.token:
                outcome = _blocked("AEGIS_ASSET_TOKEN absent; authenticated runtime execution not attempted")
            elif question.get("requires_asset") and not question.get("asset_id"):
                outcome = _blocked("Safe authorized asset ID missing; no actor or asset changes permitted")
            elif question.get("requires_source_fixture"):
                outcome = _blocked("External source TEST_FIXTURE requires isolated injection harness; production ingestion forbidden")
            elif question.get("requires_adapter"):
                outcome = _blocked("Requested typed adapter is not exposed by the current read-only runtime: " + question["requires_adapter"])
            elif variant == "hybrid_fixed":
                outcome = _hybrid_fixed(question, adapter)
            elif variant == "vector_retrieval":
                outcome = adapter.tool("semantic_search", {"query": question["question"], "limit": 5})
            else:
                outcome = adapter.assistant(question, mode=question.get("mode", "auto"))
            results.append({"case_id": question["case_id"], "group": question["group"],
                            "origin": question.get("origin"), "variant": variant, **outcome})
    summaries = {variant: summarize(questions, dataset["gold"], results, variant=variant) for variant in variants}
    runtime_errors = [{"case_id": row["case_id"], "group": row["group"], "variant": row["variant"],
                       "status": row["status"], "actual": row.get("actual"), "expected": None,
                       "evidence": [], "error_type": row.get("error_type", "INTEGRATION_ERROR"),
                       "possible_cause": row.get("error", "Unavailable runtime result")}
                      for row in results if row["status"] in {"FAILED", "BLOCKED"}]
    statuses = {status: sum(row["status"] == status for row in results)
                for status in ("COMPLETED", "PARTIAL", "FAILED", "BLOCKED")}
    reviewed_count = max((summary["formal_scored_cases"] for summary in summaries.values()), default=0)
    return {"schema_version": "aegisbench-run/0.1", "scope": "PHASE9_BENCHMARK_PREPARATION",
            "dataset_version": dataset["manifest"]["dataset_version"], "dataset_manifest": dataset["manifest"],
            "status": "PARTIAL", "candidate_cases": len(questions), "formal_scored_cases": reviewed_count,
            "execution_status": "FAIL" if statuses["FAILED"] else "PARTIAL" if statuses["BLOCKED"] or statuses["PARTIAL"] else "PASS" if results else "BLOCKED",
            "outcome_counts": statuses, "baseline_readiness": readiness, "results": results,
            "summaries": summaries, "runtime_errors": runtime_errors, "excluded_gold": dataset.get("excluded_gold", []),
            "limitations": ["Prepared benchmark is not a completed formal evaluation.",
                            "No quality score is inferred from successful HTTP requests or tool completion.",
                            "Missing human-reviewed gold and outcome-specific citation audits remain explicit blockers.",
                            "RAG-only and no-verification controls are unavailable; no fair three-way ablation claim is made."]}


def _environment(metadata):
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                                  capture_output=True, text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = None
    allowed = {key: metadata.get(key) for key in ("model", "model_config", "backend_version", "dify_version", "database_snapshot", "data_mode")}
    return {"date_utc": datetime.now(timezone.utc).isoformat(), "git_commit": revision,
            "machine": platform.platform(), "python": platform.python_version(),
            "credentials_recorded": False, **allowed}


def main(argv=None):
    parser = argparse.ArgumentParser(description="AegisBench preparation runner; human gold required for formal scores")
    parser.add_argument("--suite", choices=["full"], default="full")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--variants", nargs="+", choices=VARIANTS + ["vector_retrieval"], default=VARIANTS)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--prepare-only", action="store_true", help="Validate dataset and record blocked executions without runtime calls")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/reports/latest-preparation.json")
    arguments = parser.parse_args(argv)
    if arguments.limit is not None and arguments.limit < 1:
        parser.error("--limit must be positive")
    metadata = json.loads(arguments.metadata.read_text(encoding="utf-8-sig")) if arguments.metadata else {}
    dataset = load_dataset(arguments.dataset)
    adapter = RuntimeAdapter(arguments.base_url, token=None if arguments.prepare_only else os.environ.get("AEGIS_ASSET_TOKEN"), timeout=arguments.timeout)
    report = execute_suite(dataset, adapter, variants=arguments.variants, metadata=metadata, limit=arguments.limit)
    report["environment"] = _environment(metadata)
    report["command_config"] = {"suite": arguments.suite, "runtime_url": arguments.base_url,
                                "timeout_seconds": arguments.timeout, "variants": arguments.variants,
                                "limit": arguments.limit, "prepare_only": arguments.prepare_only}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "execution_status": report["execution_status"],
                      "candidate_cases": report["candidate_cases"], "formal_scored_cases": report["formal_scored_cases"],
                      "output": str(arguments.output)}, ensure_ascii=False))
    return 1 if report["execution_status"] == "FAIL" else 2 if report["status"] == "PARTIAL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

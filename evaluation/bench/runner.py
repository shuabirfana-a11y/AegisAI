"""Reproducible runner with unavailable baselines and draft agreement clearly labelled."""
import argparse
import json
import os
import platform
import re
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, unquote
from uuid import uuid4

from .adapters import (AegisAIAdapter, FixedWorkflowAdapter, KeywordAdapter, RagOnlyAdapter,
                       corpus_fingerprint)
from .data import canonical, load_benchmark, prediction_fingerprint, read_jsonl, sha256
from .quality import same, score_variant
from .schema import Annotation, OutcomeAudit, Prediction, Question


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "evaluation/datasets/AegisBench-v0.2-pilot/manifest.json"
PUBLIC_METADATA = {"provider", "model", "prompt_version", "is_mock", "request_id", "usage",
                   "retrieved_source_ids", "capability", "policy", "logical_investigation_id",
                   "native_status", "native_priority_taxonomy"}
SECRET_KEYS = re.compile(r"(?i)(?:api[_-]?key|password|secret|authorization|access[_-]?token|database[_-]?url)")


def clean(value):
    secrets = [v for k, v in os.environ.items() if SECRET_KEYS.search(k) and v]
    for key, item in os.environ.items():
        if key.upper().endswith(("_URL", "_URI", "_DSN")):
            try:
                password = urlsplit(item).password
                if password:
                    secrets.extend([password, unquote(password)])
            except ValueError:
                pass
    def visit(item):
        if isinstance(item, dict):
            return {key: visit(v) for key, v in item.items() if not SECRET_KEYS.search(key)}
        if isinstance(item, list):
            return [visit(v) for v in item]
        if isinstance(item, str):
            for secret in secrets:
                item = item.replace(secret, "[REDACTED]")
            item = re.sub(r"(?i)\b(?:Bearer\s+|(?:api[_-]?key|password|access[_-]?token)\s*[:=]\s*)[^\s,;]+", "[REDACTED]", item)
            item = re.sub(r"(?i)(postgres(?:ql)?(?:\+\w+)?://)[^\s/]+@", r"\1[REDACTED]@", item)
        return item
    return visit(value)


def git_identity():
    def read(*args):
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=8)
        return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"
    return {"commit": read("rev-parse", "HEAD"), "working_tree_dirty": bool(read("status", "--porcelain"))}


def evaluator_hashes():
    paths = [ROOT / "evaluate.py", ROOT / "evaluation/dataset.py", ROOT / "evaluation/metrics/__init__.py",
             ROOT / "backend/app/services/versions.py", ROOT / "backend/app/assets/versions.py",
             ROOT / "backend/app/enrichment/versions.py", *sorted((ROOT / "evaluation/bench").glob("*.py"))]
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in paths}


def reference_diagnostics(annotations, predictions):
    """Machine reference agreement is diagnostic only; never promote drafts to gold."""
    by_id = {p.question_id: p for p in predictions}
    comparisons = []
    for annotation in annotations:
        if annotation.origin != "SOURCE_REFERENCE":
            continue
        prediction = by_id.get(annotation.id)
        matched = {field: bool(prediction and prediction.status == "SUCCEEDED" and field in prediction.answer
                               and same(expected, prediction.answer[field]))
                   for field, expected in annotation.expected_answer.items()}
        comparisons.append({"question_id": annotation.id, "field_matches": matched,
                            "all_reference_fields_match": bool(matched) and all(matched.values())})
    return {"label": "MACHINE_REFERENCE_AGREEMENT_NOT_FORMAL_ACCURACY",
            "independent_ground_truth": False, "review_status": "PENDING_HUMAN_REVIEW",
            "case_count": len(comparisons),
            "matching_cases": sum(row["all_reference_fields_match"] for row in comparisons),
            "cases": comparisons}


def evaluate_dataset(data, *, adapters=None, audits=None, run_id=None):
    adapters = adapters or [KeywordAdapter(), RagOnlyAdapter(), FixedWorkflowAdapter(), AegisAIAdapter()]
    names = [adapter.name for adapter in adapters]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate baseline names")
    audits = audits or []
    known_cases = {q.id for q in data["questions"]}
    if any(a.baseline not in names or a.question_id not in known_cases for a in audits):
        raise ValueError("Outcome audit references an unknown baseline or question")
    variants = {}
    for adapter in adapters:
        predictions = []
        for question in data["questions"]:
            started = time.perf_counter()
            try:
                # Copy validated inputs so an adapter cannot modify later baselines.
                q = Question.model_validate_json(question.model_dump_json())
                sources = json.loads(canonical(data["sources"]))
                prediction = adapter.run(q, sources)
                prediction = Prediction.model_validate_json(prediction.model_dump_json())
                if prediction.question_id != question.id or prediction.baseline != adapter.name:
                    raise ValueError("Prediction identity mismatch")
                metadata = {k: v for k, v in prediction.metadata.items() if k in PUBLIC_METADATA}
                prediction = prediction.model_copy(update={"metadata": metadata})
            except Exception as exc:
                # Exceptions can contain DSNs or provider secrets. Preserve a stable
                # category and the failure row, not third-party exception text.
                prediction = Prediction(question_id=question.id, baseline=adapter.name, status="FAILED",
                    error_code="ADAPTER_TIMEOUT" if isinstance(exc, TimeoutError) else "ADAPTER_FAILED",
                    error="Controlled adapter failure; no prediction fabricated.")
            if not getattr(adapter, "recorded", False):
                prediction = prediction.model_copy(update={"latency_ms": (time.perf_counter() - started) * 1000})
            predictions.append(prediction)
        scores = score_variant(data["questions"], data["annotations"], predictions,
                               [a for a in audits if a.baseline == adapter.name], data["sources"])
        groups = {}
        for category in sorted({q.category for q in data["questions"]}):
            qs = [q for q in data["questions"] if q.category == category]
            ids = {q.id for q in qs}
            groups[category] = score_variant(qs, [a for a in data["annotations"] if a.id in ids],
                [p for p in predictions if p.question_id in ids],
                [a for a in audits if a.baseline == adapter.name and a.question_id in ids], data["sources"])
        variants[adapter.name] = {"metrics": scores, "categories": groups,
            "reference_diagnostics": reference_diagnostics(data["annotations"], predictions),
            "predictions": [p.model_dump(mode="json") for p in predictions]}
    complete_variants = all(v["metrics"]["execution"].get("SUCCEEDED", 0) == len(data["questions"])
                            for v in variants.values())
    quality_ready = bool(data["eligible_gold"]) and len(data["eligible_gold"]) == len(data["questions"])
    return clean({"schema_version": "aegisbench-report-v0.2", "run_id": run_id or str(uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(), "dataset_version": data["manifest"]["dataset_version"],
        "dataset_manifest": data["manifest"], "dataset_fingerprint": corpus_fingerprint(data["sources"]),
        "sample_count": len(data["questions"]), "eligible_gold_count": len(data["eligible_gold"]),
        "source_count": len(data["sources"]), "git": git_identity(), "python_version": platform.python_version(),
        "evaluator_file_hashes": evaluator_hashes(),
        "quality_status": "EVALUATED" if quality_ready and complete_variants else "NOT_EVALUATED",
        "execution_status": "COMPLETED" if complete_variants else "PARTIAL",
        "comparison_status": "READY_FOR_REVIEW" if quality_ready and complete_variants else "NOT_COMPARABLE",
        "parameters": {"retrieval_k": 5, "default_mode": "OFFLINE_NO_MODEL_NO_DATABASE",
                       "failure_policy": "KEEP_ALL_CASES", "scoring_version": "aegisbench-metrics-v0.2"},
        "variants": variants, "limitations": data["manifest"].get("limitations", []) + [
            "Draft reference agreement cannot establish model or agent accuracy.",
            "No relative uplift, ranking or confidence interval from this pilot.",
            "Evidence coverage and hallucination require complete independent human outcome audits.",
            "Native AegisAI has one-asset scope; its risk priority semantics differ from the reference triage policy.",
            "Unavailable variants and absent classes are not reported as successful zero-error experiments."]})


def write_report(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    report = clean(report)
    (directory / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    def pct(value):
        return "NOT_EVALUATED" if value is None else f"{value * 100:.2f}%"
    lines = ["# AegisBench Report", "", f"Run: `{report['run_id']}`", "",
        f"Dataset: {report['dataset_version']}; samples={report['sample_count']}; eligible human gold={report['eligible_gold_count']}.",
        f"Execution: {report['execution_status']}; formal quality: {report['quality_status']}; comparison: {report['comparison_status']}.", "",
        "| Baseline | Success / Failed / Not evaluated | Accuracy | Evidence Coverage | Hallucination |", "|---|---|---|---|---|"]
    for name, variant in report["variants"].items():
        m = variant["metrics"]
        counts = m["execution"]
        lines.append(f"| {name} | {counts.get('SUCCEEDED', 0)} / {counts.get('FAILED', 0)} / {counts.get('NOT_EVALUATED', 0)} | "
                     f"{pct(m['accuracy'])} | {pct(m['evidence_coverage'])} | {pct(m['hallucination_rate'])} |")
    lines += ["", "## Reference diagnostics (not formal accuracy)", "",
              "Machine draft agreement checks data extraction and evaluator wiring. It is not independent ground truth and must not be used as an accuracy or superiority claim.", ""]
    for name, variant in report["variants"].items():
        d = variant["reference_diagnostics"]
        if variant["metrics"]["execution"].get("SUCCEEDED", 0):
            lines.append(f"- {name}: {d['matching_cases']} of {d['case_count']} draft reference cases match; review pending.")
        else:
            reasons = Counter(p["error_code"] for p in variant["predictions"] if p["error_code"])
            lines.append(f"- {name}: NOT_EVALUATED; {dict(reasons)}")
    lines += ["", "## Limitations", "", *[f"- {line}" for line in report["limitations"]], ""]
    (directory / "report.md").write_text(clean("\n".join(lines)), encoding="utf-8")
    (directory / "predictions.jsonl").write_text("".join(canonical(p) + "\n" for variant in report["variants"].values()
                                                       for p in variant["predictions"]), encoding="utf-8")
    # Explicit packets: reviewing output support is separate from gold annotation.
    packets = [{"question_id": p["question_id"], "baseline": name, "reviewer": "",
                "reviewer_type": "MACHINE", "review_status": "PENDING",
                "prediction_sha256": prediction_fingerprint(Prediction.model_validate(p)),
                "claims": [{"claim_id": c["claim_id"], "verdict": "UNRESOLVED", "evidence_refs": [],
                            "review_note": "Pending independent human semantic review"} for c in p["claims"]]}
               for name, variant in report["variants"].items() for p in variant["predictions"] if p["status"] == "SUCCEEDED"]
    (directory / "outcome-audit-pending.jsonl").write_text("".join(canonical(p) + "\n" for p in packets), encoding="utf-8")


def export_schemas(path):
    from .schema import EvidenceReference
    schemas = {model.__name__: model.model_json_schema() for model in
               (Question, Annotation, Prediction, OutcomeAudit, EvidenceReference)}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(schemas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class RecordedAdapter:
    recorded = True

    def __init__(self, name, predictions):
        self.name = name
        self.predictions = {p.question_id: p for p in predictions}
        if len(self.predictions) != len(predictions):
            raise ValueError("Duplicate recorded predictions")

    def run(self, question, sources):
        if question.id not in self.predictions:
            return Prediction(question_id=question.id, baseline=self.name, status="FAILED", error_code="MISSING_RECORDED_PREDICTION")
        return self.predictions[question.id]


def recorded_adapters(path, data):
    previous = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    receipt = json.loads((Path(path).parent / "experiment.json").read_text(encoding="utf-8-sig"))
    if receipt["report_sha256"] != sha256(path):
        raise ValueError("Recorded experiment report hash mismatch")
    if (previous["dataset_fingerprint"] != corpus_fingerprint(data["sources"])
            or previous["dataset_manifest"]["questions_sha256"] != data["manifest"]["questions_sha256"]):
        raise ValueError("Recorded experiment source/question scope mismatch")
    adapters = [RecordedAdapter(name, [Prediction.model_validate(p) for p in variant["predictions"]])
                for name, variant in previous["variants"].items()]
    if not adapters:
        raise ValueError("Recorded experiment has no baselines")
    return adapters, {"run_id": previous["run_id"], "report_sha256": sha256(path),
                      "original_evaluator_file_hashes": previous["evaluator_file_hashes"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="AegisBench: offline pilot by default; no mock quality claims")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--outcome-audit", type=Path)
    parser.add_argument("--rescore-report", type=Path, help="Score frozen observed answers without rerunning models; requires experiment receipt")
    parser.add_argument("--live-model", action="store_true", help="Explicitly enable a configured real model; may incur provider charges")
    parser.add_argument("--live-aegisai-requests", type=Path, help="Explicit native Orchestrator run using existing dedicated bench data; requires --live-model")
    parser.add_argument("--export-schemas", type=Path)
    args = parser.parse_args(argv)
    if args.live_aegisai_requests and not args.live_model:
        parser.error("Native evaluation requires explicit --live-model")
    if args.rescore_report and args.live_model:
        parser.error("Recorded scoring and live execution are separate modes")
    data = load_benchmark(args.manifest)
    run_id = str(uuid4())
    output = args.output or ROOT / "evaluation/reports" / run_id
    if output.exists() and any(output.iterdir()):
        parser.error("Experiment output already exists; choose a new directory")
    gateway, native = None, AegisAIAdapter()
    try:
        if args.live_model:
            from .native import configured_gateway, native_adapter
            try:
                gateway = configured_gateway()
            except Exception:
                print("MODEL_CONFIGURATION_UNAVAILABLE; live variants are NOT_EVALUATED.")
            if args.live_aegisai_requests:
                try:
                    native = native_adapter(gateway, data, args.live_aegisai_requests, run_id)
                except Exception:
                    print("NATIVE_EVALUATION_NOT_READY; no database changes or predictions fabricated.")
                    native = AegisAIAdapter(gateway=gateway)
        audits = [OutcomeAudit.model_validate(row) for row in read_jsonl(args.outcome_audit)] if args.outcome_audit else []
        adapters, rescore_of = ([KeywordAdapter(), RagOnlyAdapter(gateway), FixedWorkflowAdapter(), native], None)
        if args.rescore_report:
            adapters, rescore_of = recorded_adapters(args.rescore_report, data)
        report = evaluate_dataset(data, adapters=adapters,
                                  audits=audits, run_id=run_id)
        report["parameters"]["default_mode"] = "EXPLICIT_LIVE_MODEL" if args.live_model else "OFFLINE_NO_MODEL_NO_DATABASE"
        report["parameters"]["live_model_enabled"] = args.live_model
        report["parameters"]["native_enabled"] = args.live_aegisai_requests is not None
        report["parameters"]["execution_mode"] = "RESCORE_RECORDED_OUTPUTS" if args.rescore_report else "NEW_OBSERVATIONS"
        if rescore_of:
            report["rescore_of"] = rescore_of
        write_report(report, output)
        # Minimal, credential-free metadata receipt for reproducibility.
        receipt = {key: report[key] for key in ("run_id", "generated_at", "dataset_version", "dataset_fingerprint",
                                               "git", "python_version", "evaluator_file_hashes", "parameters", "quality_status", "execution_status")}
        receipt["source_hashes"] = {s["id"]: s["sha256"] for s in data["manifest"]["sources"]}
        receipt["question_hash"] = data["manifest"]["questions_sha256"]
        receipt["annotation_hash"] = data["manifest"]["annotations_sha256"]
        receipt["model_identities"] = {name: sorted({(p["metadata"].get("provider", "NONE"), p["metadata"].get("model", "NONE"),
                                                      p["metadata"].get("prompt_version", "NONE"))
                                                    for p in value["predictions"]}) for name, value in report["variants"].items()}
        receipt["report_sha256"] = sha256(output / "report.json")
        (output / "experiment.json").write_text(json.dumps(clean(receipt), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.export_schemas:
            export_schemas(args.export_schemas)
        print(f"AegisBench Report: {output / 'report.md'}")
        print(f"Accuracy: {'NOT_EVALUATED (0 human gold)' if not data['eligible_gold'] else 'see per-baseline report'}")
        coverage = any(v["metrics"]["evidence_coverage"] is not None for v in report["variants"].values())
        hallucination = any(v["metrics"]["hallucination_rate"] is not None for v in report["variants"].values())
        print(f"Evidence Coverage: {'see reviewed report' if coverage else 'NOT_EVALUATED'}")
        print(f"Hallucination: {'see reviewed report' if hallucination else 'NOT_EVALUATED'}")
        return 0  # The runner completed; quality availability is explicit in the report.
    finally:
        if getattr(native, "engine", None) is not None:
            native.engine.dispose()
        if gateway is not None:
            gateway.close()


if __name__ == "__main__":
    raise SystemExit(main())

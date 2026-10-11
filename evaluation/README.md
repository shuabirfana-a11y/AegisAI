# AegisBench preparation (Phase 9)

## Phase 13-B / v0.2.1 pilot entry point

Phase 13-B adds a separate `bench/` package and a frozen **49-question, five-advisory pilot**; all draft annotations await human review. It does not change the legacy Phase 9 runner described below. Formal human gold currently remains **0**.

```powershell
& backend/.venv/Scripts/python.exe evaluate.py
& backend/.venv/Scripts/python.exe -m pytest tests/aegisbench -q
```

`python evaluate.py` also works when the active Python has the existing backend dependencies. Default execution is offline: no models, model downloads, service startup, database writes or paid calls. It actually executes keyword retrieval and a fixed workflow using the existing version parser/comparator. RAG-only requires an explicitly enabled real model. Native Phase 11-D evaluation stays `NOT_EVALUATED` until effective normalized-intelligence and actual-inventory parity checks exist, even with otherwise valid configuration. A completed framework run exits 0 even when quality is unavailable; failures/unavailability are counted explicitly in the report. Invalid data/configuration arguments exit nonzero. This exit convention belongs to **v0.2**, not the older runner.

Outputs in a fresh `evaluation/reports/<run-id>/` include `report.json`, `report.md`, 196 per-case prediction rows, an experiment receipt and pending human outcome-audit packets. No percentage is emitted for Accuracy without human gold, or Evidence Coverage/Hallucination without complete human result audits. A draft reference match is a wiring diagnostic and cannot be advertised as accuracy or an Agent advantage.

- [Annotation rules](ground_truth/schema.md)
- [Metric definitions and denominators](METRICS.md)
- [Baselines and native prerequisites](BASELINES.md)
- [Experiment procedure](experiments/README.md)
- [Actual first pilot report](reports/phase13b-pilot-20261011/report.md)
- [Final corrected pilot report](reports/phase13b-final-20261011/report.md)
- [Pydantic-derived JSON Schemas](contracts/aegisbench-v0.2.schema.json)
- [Pilot source attribution and demo scenarios](datasets/AegisBench-v0.2-pilot/README.md)
- [Pending annotation erratum](datasets/AegisBench-v0.2.1-pilot/README.md)

The pilot is not a held-out accuracy experiment. It has five correlated advisory clusters, controlled assets, no verified exploit positives and a declared reference risk rubric. Native AegisAI has a one-asset scope and a different priority taxonomy; future human labels must align tasks and semantics before a fair comparison. No current report claims all four baselines have been evaluated, proves cross-document reasoning correctness or states a relative improvement.

## Preserved Phase 9 framework

This directory contains a reusable benchmark framework and candidate questions. It does **not** establish completed Phase 10 evaluation or measured quality results. Existing `seed_set/` and `source_contracts/` are preserved.

`datasets/AegisBench-v0.1/manifest.json` freezes 24 A–K candidate questions with a SHA-256 hash, source snapshot cutoff and explicit development overlap. There is no independent time split. Real negatives and complete POC/patch annotations are still needed. `ground_truth/AegisBench-v0.1.jsonl` is intentionally empty: **zero human-reviewed gold cases**.

Gold requires an expected result, named human annotator and human reviewer, accepted `APPROVED` or `REVIEWED` status, an annotation note and supporting sources with URL, locator and excerpt. Agent, LLM and machine drafts cannot enter formal metrics. `TEST_FIXTURE` questions and labels are excluded from formal metrics and cannot be ingested into production through this runner.

Questions and gold are separate files. Runtime request payloads only include question, target/authorized asset ID, mode, a fresh request key and `realtime=false`. No expected answer or annotation is sent to the runtime. The backend URL is restricted to plain HTTP loopback; redirects and arbitrary URL/tool calls are rejected. The fixed workflow uses read-only tools and does not change actors, owned assets or review state.

Preparation only, with no backend calls:

```powershell
& backend/.venv/Scripts/python.exe -m evaluation.run --suite full --prepare-only
```

Future authorized runtime execution uses the real asynchronous assistant API and tools on port 8000. Set `AEGIS_ASSET_TOKEN` in the process environment without printing it. After formal evaluation is authorized:

```powershell
& backend/.venv/Scripts/python.exe -m evaluation.run --suite full --base-url http://127.0.0.1:8000 --output evaluation/reports/runtime.json
```

Options include `--dataset`, `--limit`, `--timeout`, `--variants` and an optional safe environment `--metadata` JSON. No database service is started or stopped. Existing runtime endpoints can record their normal run/tool audit records. Authentication is never written to reports.

Available adapters execute actual fixed Hybrid tool calls, full deterministic assistant runs, or vector retrieval. A configured generation LLM adapter is absent, so RAG-only is `BLOCKED`. A controlled no-verification switch is absent, so that variant is also `BLOCKED`. Fixed tool results are explicitly disclosed as having no generation model; they are not substituted for LLM answers. Version matching, asset and external source fixture cases remain blocked when their necessary adapter or authorized context is absent.

Metrics implement multiclass precision/recall/F1, confusion matrices, accuracy, False Safe, abstention, reviewed unsupported claims, retrieval Recall@K/MRR and observed latency percentiles. Failed predictions remain in denominators. Zero denominators produce JSON `null`. Semantic QA, citation correctness and unsupported claim counting require additional outcome-specific human review; no automated gold is invented. Runtime errors include actual failed/blocked cases even when gold is unavailable.

Exit codes: `0` verified completed run, `1` actual adapter execution failure, `2` incomplete/blocked preparation. Current preparation always remains `PARTIAL`; a successful request does not prove correctness or satisfy the formal evaluation gate.

Local framework verification:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_phase9_evaluation.py -q
```

The loopback test server uses explicit `TEST_FIXTURE` responses and does not touch PostgreSQL. Those test successes are framework verification, not real system benchmark scores.

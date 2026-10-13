# AegisBench Phase 13-E readiness implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Validate formal admission and deliver an honest blocked preparation record at 0 human gold.
**Architecture:** New offline preflight helper delegates data admission to the unchanged loader. Existing HTTP/replay/scoring remain unchanged. No network or automatic human approval.
**Tech Stack:** Existing Python/Pydantic/pytest, no dependencies.
**Spec:** docs/superpowers/specs/2026-10-13-aegisbench-formal-readiness.md

## Global Constraints

- Minimum 10 eligible human-gold records; no lower threshold.
- No Agent/Runtime/Gate/Runner/metric/data edits; no formal evaluation with insufficient gold.
- Model/prompt/dataset template is not a frozen experiment.
- Keep unavailable baselines and independent OutcomeAudit requirements explicit.

## Review Focus

- Task DRAFT or machine reference confused with human completion: separate counts.
- Labels leaked into runtime: preflight never creates a client or invokes evaluator.
- Invalid evidence/hash/human identity: original loader rejects, controlled blocked output.
- Threshold bypass or empty cohort: exit3 before any experiment.
- Overwrite of dataset/old experiment or metadata with invented quality: safe fresh output, no quality numbers.

### Task 1: Preflight and experimental handoff

Files: new evaluation/bench/readiness.py; scripts/check_bench_readiness.py; tests/aegisbench/test_readiness.py; evaluation/experiments/phase13e; docs/phase13e; PHASE_13E_RESULT.md; CURRENT_STATUS.md.
Interfaces: consumes load_benchmark(manifest), annotation_exclusion, checked_output; produces readiness report only, no Prediction or HTTP result.

- [ ] Write failing controls for valid approved dataset, invalid hash/reviewer, 0/9/10 threshold, exact unknown preservation, no runtime labels/client construction, report output protection and no metrics.
- [ ] Run new tests RED, implement helper, run GREEN.
- [ ] Actual candidate preflight: expect49 questions,0 eligible, exit3, no network/model/metrics.
- [ ] Run complete AegisBench and current contract/repository checks; protect original business/evaluation/data bytes.
- [ ] Prepare model/prompt/dataset/config freeze template, baseline plan and operation manual; actual results only.
- [ ] Commit; one fresh read-only final review; resolve important findings with negative tests; publish own draft PR stacked on PR13, never merge it implicitly.

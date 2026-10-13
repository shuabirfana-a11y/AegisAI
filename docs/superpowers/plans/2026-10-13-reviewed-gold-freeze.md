# Reviewed gold and experiment config preparation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. No production or evaluator changes.

**Goal:** Freeze the supplied39approved records, preserve10rejections, prepare exact experiment metadata without running experiments.
**Architecture:** Existing Schema, loader, HTTP request builder and preflight are reused. New files are data/config/docs/tests only; one-off import helper stays ignored.
**Spec:** docs/superpowers/specs/2026-10-13-reviewed-gold-freeze.md

## Global Constraints

- No model/investigation calls or formal quality metrics, even at39approved.
- No original question/source/oldmanifest, evaluator or business edits.
- Keep original bytes and approval hashes; export status separately.
- Freeze immutable model bytes on disk, not running-service attestations.

## Review Focus

- Duplicate or inconsistent/manualapproved counts: original loader must actually admit39.
- Evidence/field conversion changing human answers: exact scored-field projection, original evidence locators validated.
- Unsupported policy or step labels: preserve original and report limits; no artificial metric uplift.
- Configuration contradictions: current request forbids execution;10threshold isn't authorization.
- Secrets / overwrite / stale source and model hashes: safe new files, scoped local metadata and full scans.

### Task 1: Frozen records/config and handoff

Files: evaluation/ground_truth/samples/{approved,rejected}; evaluation/datasets/AegisBench-v0.3-human39-20261013; experiments/config; docs/phase13e2; EXPERIMENT_PLAN.md; PHASE_13E2_PREP_RESULT.md; current/progress docs; tests/aegisbench/test_frozen_experiment_prep.py.
Consumes: approved zip, original MANUAL_RECORD_SCHEMA projection, Annotation/load_benchmark/inspect_readiness/build_request. Produces: frozen39human dataset and config/report templates, zero predictions.

- [ ] New test controls RED: exact39admission, original hashes/evidence, config/Pprompt/model pins, GT isolation, emptyGold refusal, report template.
- [ ] Import raw approved/rejected, whitelist projection and immutable model/source receipts; testGREEN.
- [ ] Actual preflight newmanifest:39eligible/data gate pass, noHTTP/scorer. Oldmanifest remains0.
- [ ] Update progress/config/experiment plan; fullAegisBench, contracts, safety; core/old frozen bytes unchanged.
- [ ] Commit, one fresh final read-only review; fiximportant withnegative controls; own draftPR stacked onPR14, no merge; folder delivery; stop.

# AegisBench Report

Run: `aegisbench13f-neutral-human39-offline-score-20261013`

Dataset: AegisBench-v0.3-human39-20261013; samples=49; eligible human gold=39.
Execution: PARTIAL; formal quality: NOT_EVALUATED; comparison: NOT_COMPARABLE.

| Baseline | Success / Failed / Not evaluated | Accuracy | Evidence Coverage | Hallucination |
|---|---|---|---|---|
| rag_only | 0 / 0 / 49 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |
| agent_without_verification | 0 / 0 / 49 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |
| aegisai | 2 / 37 / 10 | 0.00% | NOT_EVALUATED | NOT_EVALUATED |

## Reference diagnostics (not formal accuracy)

Machine draft agreement checks data extraction and evaluator wiring. It is not independent ground truth and must not be used as an accuracy or superiority claim.

- rag_only: NOT_EVALUATED; {'INDEPENDENT_RAG_CONTROL_NOT_IMPLEMENTED': 39, 'GROUND_TRUTH_NOT_APPROVED': 10}
- agent_without_verification: NOT_EVALUATED; {'INDEPENDENT_ABLATION_NOT_IMPLEMENTED': 39, 'GROUND_TRUTH_NOT_APPROVED': 10}
- aegisai: 0 of 0 draft reference cases match; review pending.

## Limitations

- Five selected advisory clusters; questions are correlated.
- Not an independent holdout; some vulnerabilities appeared in development fixtures.
- No verified exploit execution evidence; positive PoC classes lack coverage.
- Patch release confirmation is separate from commit correctness or exploit validation.
- Human-approved asset risk labels measure benchmark-reference-triage-v1 policy conformance, not production risk ground truth.
- Draft reference agreement cannot establish model or agent accuracy.
- No relative uplift, ranking or confidence interval from this pilot.
- Evidence coverage and hallucination require complete independent human outcome audits.
- Native AegisAI has one-asset scope; its risk priority semantics differ from the reference triage policy.
- Unavailable variants and absent classes are not reported as successful zero-error experiments.
- Online uses public Investigation API; no internal Orchestrator/Agent/model calls.
- Raw database source UUIDs and citation hashes are retained, not relabelled as frozen corpus evidence.
- Normalized source/inventory equivalence across baselines is not independently attested; no fair ablation claim.
- Missing native fact fields remain missing; human expected answers are not adjusted to system output.
- No-verification is an independent experimental control, never a production bypass switch.

## Risk and abstention (reviewed gold required)

| Baseline | Risk Accuracy | Priority Accuracy | Abstention Quality |
|---|---|---|---|
| rag_only | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |
| agent_without_verification | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |
| aegisai | 0.00% | 0.00% | 0.00% |

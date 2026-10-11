# AegisBench Report

Run: `42bd69aa-db11-40ac-bd3f-7188bdfbd6e8`

Dataset: AegisBench-v0.2-pilot; samples=49; eligible human gold=0.
Execution: PARTIAL; formal quality: NOT_EVALUATED; comparison: NOT_COMPARABLE.

| Baseline | Success / Failed / Not evaluated | Accuracy | Evidence Coverage | Hallucination |
|---|---|---|---|---|
| keyword_search | 49 / 0 / 0 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |
| rag_only | 0 / 0 / 49 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |
| fixed_workflow | 49 / 0 / 0 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |
| aegisai | 0 / 0 / 49 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

## Reference diagnostics (not formal accuracy)

Machine draft agreement checks data extraction and evaluator wiring. It is not independent ground truth and must not be used as an accuracy or superiority claim.

- keyword_search: 10 of 49 draft reference cases match; review pending.
- rag_only: NOT_EVALUATED; {'REAL_GENERATION_MODEL_NOT_CONFIGURED': 49}
- fixed_workflow: 49 of 49 draft reference cases match; review pending.
- aegisai: NOT_EVALUATED; {'REAL_PLANNER_MODEL_NOT_CONFIGURED': 49}

## Limitations

- Five selected advisory clusters; questions are correlated.
- Not an independent holdout; some vulnerabilities appeared in development fixtures.
- No verified exploit execution evidence; positive PoC classes lack coverage.
- Patch release confirmation is separate from commit correctness or exploit validation.
- Asset risk labels are policy-conformance drafts, not production risk ground truth.
- Draft reference agreement cannot establish model or agent accuracy.
- No relative uplift, ranking or confidence interval from this pilot.
- Evidence coverage and hallucination require complete independent human outcome audits.
- Native AegisAI has one-asset scope; its risk priority semantics differ from the reference triage policy.
- Unavailable variants and absent classes are not reported as successful zero-error experiments.

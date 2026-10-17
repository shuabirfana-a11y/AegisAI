# Phase 14-B1 PoC enrichment implementation plan

> **For agentic workers:** Use superpowers:executing-plans for the authorized inline implementation.

**Goal:** Complete the user-authorized PoC Artifact, Evidence/Verification projection, read-only HTTP API and frontend contract.

**Architecture:** Reuse PocEnricher, EvidenceService, VerificationService, the professional Verification Agent and the existing verified-exploit predicate. Add a bounded DTO/projection, persist snapshots after existing enrichment verification, and expose a paginated public GET. No exploit execution, new Agent, migration or altered verdict rules.

**Tech Stack:** Existing FastAPI, Pydantic v2, SQLAlchemy/PostgreSQL and TypeScript.

**Spec:** User's Phase 14-B1 instruction in this chat.

## Global constraints

- No Planner, Runtime, Gate or security Agent business changes.
- Three public states: NO_EVIDENCE, POC_CANDIDATE, VERIFIED_EXPLOIT.
- Association confirmation is distinct from exploit usability.
- Missing metadata remains null; missing/invalid provenance is reported, not invented.
- No changes to Ground Truth, scoring or historical experiment records.
- Work on codex/phase14b1-poc-enrichment, stacked on Phase 14-A; do not merge main.

## Review focus

- A confirmed association without validated exploitation remains a candidate.
- Historical, conflicted or incomplete verification never establishes current exploit usability.
- Missing Evidence or invalid public URLs are omitted with explicit warnings.
- Empty/paginated results retain a separate bounded search status; absence is not proof of safety.
- Public output cannot expose asset-scoped Evidence or credentials.

## Task 1 — DTO and projection

Files: backend/app/enrichment/poc_schemas.py, poc_artifacts.py; tests/test_phase14b1_poc.py.

- [x] Add failing tests for provenance, states, stale verification, invalid URLs and pagination.
- [x] Run tests and retain the failure record.
- [x] Implement strict frozen DTOs and existing-model read projection, with linked current verification records.
- [x] Validate successful tests against the dedicated synthetic PostgreSQL cluster.

## Task 2 — Enrichment and HTTP integration

Files: enrichment/service.py, enrichers/poc.py, api/intelligence.py.

- [x] Add a failing API test and an enrichment-snapshot test.
- [x] Capture actual repository language; emit snapshot after original verification/adoption.
- [x] Add GET /api/v1/intelligence/vulnerabilities/{id}/poc, without write/scan endpoints.
- [x] Verify the original professional Verification Agent consumes unchanged Claim/Evidence via Tool Gateway.

## Task 3 — Contracts and delivery

Files: frontend/contracts/intelligence.ts, export scripts/generated contracts, CI/test counts, Phase result.

- [x] Regenerate actual OpenAPI/TypeScript contracts and synchronize the handoff package.
- [x] Run portable backend baseline, related integration tests, frontend/types and export consistency checks.
- [x] Review the whole diff, scan secrets, preserve protected source hashes.
- [x] Save the report with actual limitations, create a draft PR, and stop before Phase 14-B2.

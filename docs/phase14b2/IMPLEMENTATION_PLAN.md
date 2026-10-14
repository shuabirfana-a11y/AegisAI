# Phase 14-B2 bounded automation implementation plan

> Use superpowers:executing-plans for the already-authorized inline implementation.

## Intent and constraints

Reuse the existing 11 adapters, SyncService, FeedSyncService, EnrichmentService and asset risk worker.
Complete bounded automatic collection → normalization → enrichment → original verification → queryable knowledge.
No new Agent, normalizer/retrieval rewrite, distributed scheduler, migration, Gate or scoring changes.
LIVE never silently falls back to Mock; Mock work is limited to the dedicated synthetic test database.

## Design

- A typed collector registry describes current source capabilities and executes existing fetch/normalize/save paths.
- A pipeline coordinator processes only targets linked to the selected source runs, including their due backlog.
- Record stage receipts on existing SyncRun metadata and original job rows; no pretend source or new domain table.
- Keep candidate Evidence and original verification decisions. AVAILABLE means queryable, not blanket verified.
- Use one local scheduling loop with due times, bounded budgets, graceful stop and a PostgreSQL session advisory guard.
- Perform optional existing inventory risk recomputation only for an explicitly configured owner; public progress omits asset details.
- Add typed read-only record lifecycle and pipeline run APIs; export actual OpenAPI/TypeScript.

## Execution

1. [x] Write failing config/registry/pipeline/state/scheduler/HTTP tests using synthetic source transports.
2. [x] Implement registry and batch-scoped queue processing; reuse normalizers and original evidence/verification.
3. [x] Implement durable source receipts, state projection and optional bounded original asset jobs.
4. [x] Implement scheduler and opt-in --pipeline on the existing CLI; preserve legacy CLI mode.
5. [x] Add read-only endpoints and frontend client/types; regenerate contracts and run related regressions.
6. [x] Run a small real-source scheduled pipeline in isolated demo storage; retain outages and partial outcomes.
7. [ ] Perform independent read-only review, secret/source checks, draft PR and folder delivery; stop.

## Review focus

- Source failure/disable does not suppress another source; no false LIVE success or invented normalization.
- Defer/backlog limits do not globally drain unrelated enrichment or private asset jobs.
- Multi-process scheduling cannot duplicate a cycle; cancellation prevents starting additional work.
- Pending/conflicted/absent Evidence never becomes VERIFIED merely because the pipeline finished.
- Public lifecycle/run DTOs contain bounded progress, actual timestamps and controlled errors, not owner identities or secrets.

## Rulings

- The user supplied purpose, pipeline and explicit implementation authorization; no repeated authorization gate is needed.
- Reuse existing paths rather than adding no-op fetch/normalize/save functions over an identical second collector.
- Source timestamps and job IDs are the authoritative execution record; lifecycle reads do not launch work.
- Existing source scopes remain bounded and non-independent where upstream publishers overlap.
- An operator must opt into the long-lived worker. This request authorizes code plus bounded validation, not an unattended OS service.

PostgreSQL guard behavior follows the official advisory-lock documentation:
https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS

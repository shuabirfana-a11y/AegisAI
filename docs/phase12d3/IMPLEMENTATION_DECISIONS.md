# SDD ledger — plan: PHASE_12D3_PLAN.md

Base 1537ffdc36a52e6d5aaec876534d70cec5d62d43; isolated attached worktree; codex/phase12d3-asset-risk-loop; AegisAI remote verified. User explicitly authorized implementation, so no repeat approval gate.

Pre-flight: exact Artifact references, inventory receipts and frozen context hashes are shared interfaces; no Runtime/Planner/rule file mutations. Reuse existing package/version parsers and Gate.

Task 1: implemented. test_later_version_and_independent_asset_are_handed_to_verifier RED (empty supplementary set) → GREEN. Snapshot integration RED (no VersionObservation) → GREEN. Original root Artifact retained; complete owner/run/target-bound supplementary receipts admitted.

Task 2: implemented. Parsed-range projection RED (missing adapter) → GREEN; unknown ranges remain unknown. Non-match output RED (FALSE impact / UNKNOWN version mismatch) → GREEN at compatibility adapter. Observation handoff RED → GREEN. Invalid Evidence inheriting CONFIRMED Claim RED → GREEN; evidence-level status needs its own support binding. Original inventory version remains sealed after live inventory change; unauthorized read produces original INVALID_INPUT_ARTIFACT protocol.

Task 3: live HTTP executed three times. First request REPLAN_REQUIRED (required semantic_search had no indexed knowledge); index same official advisory with existing cached embedding, retry PASS. After evidence-level projection hardening, final HTTP PASS. No model/prompt/risk/Gate changes. All backend tests running in NEW empty 55438 test cluster so migration tests do not touch existing databases.

Ruling: preserve exact selected Investigation Artifact and supplement its completed source receipts — avoids hash/identity migration; cost if wrong: missed supporting input blocks rather than creates a fact.

Ruling: demonstrate with a separately labelled official-source snapshot and is_demo inventory, retaining legacy invalid claims in the old database — no supplied/scanned enterprise inventory exists; cost if wrong: cannot generalize this acceptance to enterprise readiness or benchmark accuracy.

Ruling: map existing R1 false exact-distribution decision to a consistent scoped NOT_AFFECTED version DTO only when a sealed observation exists — does not change risk level or rules; cost if wrong: must never imply whole-asset safety, so text and tests bound it to the selected vulnerability/component.

Verification so far: portable 530 passed / 1 explicitly deselected; TypeScript semantic compilation PASS; frontend 23 passed; 42 HTTP operations and 5 Python schema groups aligned. Full regression and final independent review pending.

Final review: one fresh read-only whole-branch reviewer, 0 Critical / 3 Important / 0 Minor. No re-review. All three entered one fix pass.
Final fix controls: legacy null identity, qualified/subpath identity (registered/unregistered), expired transaction export — 6 RED failures; final 6 GREEN in 65.40s. The intermediate 4 failures were incorrect new-test Gate expectations: actual original FATAL objective-package mismatch must remain FAILED, not REPLAN. Rules were not changed. Full final suite pending in new empty 55440.
Task 3: public prepare_demo.py actually executed successfully; same controlled source/inventory case repeated after review fixes: real HTTP PASS / 68.656s / eight endpoints / frozen answer; Planner native rejected-first-attempt plus valid retry retained.
Final: Ruling: reject the dual-UUID same-distribution qualified-PURL reproduction as production evidence — DB uniqueness forbids it; test the legal single-package boundary instead — cost if wrong: do not generalize the defensive check to demonstrated importer exploitability.
Final: Ruling: enterprise scans, real exploit conditions and Benchmark accuracy remain unassessed — no supplied scan inventory or approved GT; labelled demo only — cost if wrong: claiming production readiness or accuracy from this run would mislead the team.
Final: minor (deferred): none.

Final: fixed all 3 Important findings — six covering controls RED→GREEN; whole final suite 1426/1426 passed, 900.02s, no skip/deselection, 23 warnings.
Task 1: complete — original selected artifact plus exact supplementary receipts; frozen observations and evidence trace; historical serialization/hash guards PASS.
Task 2: complete — existing Verification/Risk/Gate rules retained; conservative identity boundaries restored; complete full regression PASS.
Task 3: complete — final real HTTP PASS and published repro script successfully exercised; contracts/TSC/frontend/engineering checks PASS.

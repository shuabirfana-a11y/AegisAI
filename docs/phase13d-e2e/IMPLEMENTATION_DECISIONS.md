# Implementation decisions and costs

- Ruling: treat the user's detailed implementation instruction as the binding design and proceed inline without another approval gate — scope, isolation and stopping conditions are explicit — cost if wrong: limited evaluation-only adapters remain isolated for PR review.

- Ruling: retain unavailable RAG/no-verification controls and comparison limitations — no production verification bypass or unverified performance uplift — cost if wrong: three-way causal comparison remains unproved until independent controls/data parity exist.

- Task 3: Ruling: final review and publication follow task implementation completion, while remaining mandatory before delivery — prevents self-review inside task loop — cost if wrong: reviewer findings may require one additional isolated fix commit.

- Final: Ruling: re-grade http_executed false claim from Minor to Important — experiment provenance is a user-facing truth requirement — fixed by actual network-attempt marker; cost if wrong: one extra small control test and metadata field.

- Final: Ruling: public Trace intentionally exports primary artifacts, not the original asset subtask Artifact — check original run/successful task and actual observation identity while retaining its UUID; do not invent a missing endpoint or query DB — cost if wrong: independent expansion of that private sub-artifact remains unproved.

- Final: Ruling: reviewer declined live-model quality, formal accuracy/human approvals, corpus parity/fair baselines/causal uplift, unavailable control implementations, original business/scoring policy, remote security/load/recovery, independent historical log certification, coordinated receipt/hash forgery and concurrent scan docs — those are out of authorized preparation scope and remain unproved; SHA256 findings separately verified — cost if wrong: those assurance gaps require separately authorized work before competition claims.

Deferred minors: none.

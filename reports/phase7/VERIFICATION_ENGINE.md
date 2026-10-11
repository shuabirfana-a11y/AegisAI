# 核验引擎

采用 deterministic-evidence-v1：明确匹配目标与同 scope 的支持证据、权威原出版、独立 lineage、当前来源修订、时间范围，再处理矛盾或弃判。官方权威不能自动覆盖显式矛盾。相关转载只算一个来源组，未知来源保守处理。

统一 CONFIRMED/PENDING/INSUFFICIENT_EVIDENCE/CONFLICT/REJECTED，不造 confidence 小数。VerificationResult 保存 evaluated_value、adopted_value、支持/矛盾 IDs、来源、method、reason 与 timestamp，并通过 VerificationEvidence 实体绑定考虑过的 Evidence。新结论追加 revision；相同输入幂等。人工结论保留，新证据产生复查而不静默覆盖。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

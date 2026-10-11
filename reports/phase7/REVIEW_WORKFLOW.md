# 人工复核

自动只推送冲突、PoC不确定、Patch不确定、版本解析/证据不足等需要判断的 Claim，避免全部逐条人工确认。GET reviews 支持状态/分页，GET reviews/{id} 返回 Claim/Evidence/Audit。

POST reviews/{id}/resolve 默认关闭；配置 AEGIS_REVIEW_TOKEN 后需 Bearer，actor 来自服务器 AEGIS_REVIEW_ACTOR，正文不允许伪造 actor。需要 reason、期望 task/claim revision、request_key 和 evidence_ids。同键重复返回同审计；不同载荷/旧修订为409，无支持或跨 scope 为422。原 Phase5事务复用并追加 VerificationResult、AuditLog、REVIEW_RESOLVED/VERIFICATION_CHANGED。

当前仅本机开发写保护，不是完整企业权限；未在真实案例中假冒人类分析员进行 resolution。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

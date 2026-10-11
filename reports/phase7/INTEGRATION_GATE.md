# 可信结果入库门禁

IntelligenceIntegrationService 在 adopted 前检查 Claim/Result ID与revision、一致状态、Evidence/新鲜度、未被 superseded、无未解决冲突、无同 scope 其他 adopted value。未通过保留事实与理由，必要时创建 ReviewTask，不静默替换。

关键结论没有证据不能成为 trusted。现有数据库唯一索引限制同 predicate/scope 的 adopted 值，Raw/Evidence/history受约束。人工已核验的结论不能被后续自动任务抹掉；新证据触发人工复查。本机并发和事件一致性通过独立事务/数据库锁处理，未宣称分布式队列部署。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

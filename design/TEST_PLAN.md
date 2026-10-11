# 测试与本轮验证

offline默认；联网测试显式real_api标记且有配额，不让日常测试依赖互联网。12条候选在evaluation/seed_set，24份字节响应在tests/fixtures；原始来源URL、source时间、sha256和缺失字段都在manifest/各seed记录。review_status=MACHINE_CHECKED_PENDING_HUMAN，人工检查表先留PENDING，不编造人工签名。

| 测试层 | 必须验证 |
|---|---|
| Unit | PEP440边界/post/rc/unknown/GIT；别名scope、torch/pytorch不自动同一；AI三态/普通关键词不能确认；规范化缺字段和metadata保留 |
| Fixture | schema映射12条真实记录；正确CVE/包/源/locator/hash；3条无fixed、2条CNA metrics空；CNA与OSV有相同上游不能两票 |
| Integration | PostgreSQL17事务/unique；claim多Evidence与support/refute；重复同步/并发；blob写成功DB失败恢复；迁移升级回滚；source修订/rejected传播 |
| API | 详情/分页/证据/状态；bad input/not found/unauthorized；raw不作为HTML render；source字段和as_of，不泄secret |
| HTTP fake transport | httpx MockTransport模拟timeout/429/500/bad JSON/404；预算/游标不前进，单记录失败其他继续 |
| Real API opt-in | 少量CVE/OSV可达/shape；不强制永久固定线上内容，快照测试保持离线可重现 |

本轮已完成临时schema probe：12/12 Pydantic验证、24源hash匹配、5个有语义的版本/名称边界、重复内容键模拟24→24。它不证明DB幂等/事务已实现，也不证明API/容器可运行。数据库/API集成测试尚未执行；本机没有Docker和正式服务。

人工验收看Product/生态/范围/版本/CVSS/CWE/refs/locator及独立来源；允许unknown。一个CVE的多个alias/task不能膨胀样本数。未按12条做模型效果评测，不公布虚假准确率。后续回归测试覆盖实际错误风险，不为每个字段getter堆测试。

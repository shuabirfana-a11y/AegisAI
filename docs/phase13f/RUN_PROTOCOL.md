# Phase 13-F 首轮正式实验协议

授权：2026-10-13用户明确要求执行39条Approved样本；原复核人员将在输出生成后独立复核证据支持与幻觉。

- 源码基线：bbb3a0fd40e098c52db3dd0499b77bd53aecef86。业务、模型Prompt、Gate、Evaluator和人工答案均不改。
- Dataset：AegisBench-v0.3-human39-20261013；49题仅39人工准入，其余10条留作未批准记录，不发送调查。
- 模型沿用已冻结openai_compatible / aegisai-qwen25-planner:latest，temperature=0，40秒Provider timeout，4096输出上限；HTTP单题180秒。确定性Answer Composer无独立LLM Prompt。
- 实验使用独立数据库，输入库存仅由Question.input_context登记为演示资产；未给环境、暴露、版本时保留unknown/null。库存、原始来源与模型身份在第一道调查前冻结。
- 情报只来自原官方来源快照及既有正常采集/归一化/富化链。官方资料和人工标签分离，禁止将Annotation.expected_answer、审核字段或Ground Truth文件送入模型、检索数据库、Context或Tool输入。
- 全部题目只通过Investigation HTTP API；不直接评分专业Agent。原Adapter和Evaluator复用不修改，每题即时存档；失败、超时、Gate阻断及原生字段缺失不丢弃、不转换为成功。
- 主结果复用原评分规则：39条为分母，整题Exact Match与字段准确率分别报告；Risk Accuracy和Abstention Quality保留原定义、原优先级体系，不为政策标签改规则。
- Evidence Coverage / Hallucination Rate须独立、完整、本次输出哈希绑定的Human OutcomeAudit。该审核尚未完成时保留null/PENDING_HUMAN_OUTCOME_AUDIT，不把引用存在或Verification CONFIRMED当语义支持。
- RAG-only和无Verification对照标记NOT_IMPLEMENTED；不声称比较公平、相对提升、生产效果、全漏洞泛化或多跳表现（批准多跳=0）。
- 完成39题采集、已有指标和原始报告后停止；不根据成绩优化、换模型、改答案或扩展Benchmark。

观察记录应区分：真实模型驱动、真实公开情报、受控演示库存、人工金标和输出待复核。保留首轮结果，不因后续失败重新挑选最佳输出。

## 受控偏差与记录

首个试次因临时资产名称含题号分类提示而停止封存，不准评分；用户批准在干净库存中性命名重跑39题。完成采集后评分器拒绝人工NO_EVIDENCE标签，经用户单独授权仅补该合法类别，离线评分原39输出；公式、业务、金标和分母不改。审批前‘Evaluator均不改’由这一明确授权的类别兼容例外覆盖，其他要求继续生效。

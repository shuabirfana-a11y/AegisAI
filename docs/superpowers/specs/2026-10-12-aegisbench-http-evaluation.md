# Phase 13-D：完整调查 HTTP 评测准备设计

用户本轮明确授权实施并先合并 PR #12；该 PR 已合入 main 的 59ea2a239556e70514ce19bba52141121a98d570。沿用已附加工作树，在 codex/phase13d-e2e-evaluation 增量开发。

## 目标与范围

将现有 AegisBench 与公开 Investigation API 接通。复用人工准入、固定来源校验、Prediction/Annotation/OutcomeAudit、Metrics、哈希回放与报告机制。业务代码、Planner/Agent/Runtime/Gate、数据库、题目、人工答案和标注进度均保持。

新入口 `python evaluate.py --mode online|offline`；没有 --mode 时保留原 CLI 行为。Online 通过创建、状态、Trace、Artifact、Integration、Answer 等真实 HTTP 接口采集完整链，绝不调用内部 Orchestrator。Offline 回放已有完整链记录，通过现有 experiment.json 哈希及问题/来源指纹验证。

## 输入与隔离

问题来自原 Question。对 input_context 和操作者资产绑定检查禁止标注字段，正向投影为 InvestigationCreateRequest。原问题不变；请求键采用随机标识，不传问题 ID 中的标签提示。版本/风险类需显式匹配的既有资产/组件绑定；不创建库存、不猜 UUID、不从标准答案补版本。多资产/多目标不受当前闭环支持时明确 NOT_EVALUATED。

只有经原 load_benchmark 的人工准入与来源检查通过的题目才能进入在线执行。准入只传题目 ID 集合，答案/证据/审核说明不进入 HTTP Adapter。0 approved 时不建立网络连接、不调用模型，质量指标为 null/NOT_EVALUATED。

## 输出与度量

验证响应 Schema，以及调查、Planner、Trace、Artifact、Gate、Answer 的身份与引用一致。冻结 AnswerEnvelope 是答案来源；新 VersionObservation/ImpactVersionEvidence 作为追溯观察保存，不能替代独立标准答案。风险字段只取原 RiskView，限定结论范围；无风险或失败不编造 UNKNOWN/安全。拒答依据显式原 UNKNOWN 或原待调查/复核状态，失败调用不获得拒答成功分。

复用 score_variant 的答案、风险/优先级、拒答等指标。Evidence Coverage/Hallucination 仍需完整独立 OutcomeAudit；有效引用或 Verification CONFIRMED 不能自动视为独立正确性证明。原候选字段与原生输出不一致时保留缺失，不能改人工答案或补造字段。

Baseline 为 rag_only、agent_without_verification、aegisai。Online 只执行完整 AegisAI；另两项属于独立实验控制，当前未实现则记录不可用。不向生产 API 加禁用 Verification/Gate 的开关。离线可接收通过记录协议的外部 baseline，但来源/输入/模型数据一致性未确认不能作公平对比结论。

记录数据集版本/文件指纹、模型与 Prompt 的实际 Trace 值、时间、配置、原生优先级规则、执行模式、完整响应摘要与 run IDs。保持失败样本；超时尝试取消已知的本次调查，取消失败独立记录。无明文凭据、第三方错误文本或原始模型思考。记录目录不能覆盖既有实验或写入标注/数据集目录。

## 验收与停止

测试单条映射、整个真实 HTTP 调查（仅合成输入+Mock模型的工程控制）、标签隔离、异常、UNKNOWN/冲突、响应错配、回放篡改和批准准入。执行全部 AegisBench 测试及必要 API 控制、现有便携/契约/前端检查；1426 为此前真实回归，不借作本轮执行数。

原人工 Schema 的 JsonValue 已支持新字段，补充原生字段与 evidence source/URL/quote/locator 的解释文档，不转换或填写49题。交付 PHASE_13D_RESULT.md、操作说明、Schema 与脱敏准备记录。一次最终独立整体审查。完成后停止，不运行正式准确率实验、PPT 或部署。

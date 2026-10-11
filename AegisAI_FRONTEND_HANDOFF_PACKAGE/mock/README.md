# Mock 与历史测试回执说明

全部 JSON 标注 MOCK_ONLY、DEMO/MOCK、production_data=false。不是真实安全情报，不是在线 API 录制，也不是比赛 Benchmark。顶层包装不属于 Pydantic DTO。

## 五个联动入口

| 文件 | 场景路径 | 结构 |
|---|---|---|
| investigation-demo.json | scenarios[name].request / status | InvestigationRequest + InvestigationStatus |
| agent-trace-demo.json | scenarios[name] | 完整 InvestigationTrace，含 AgentTrace 摘要 |
| evidence-demo.json | scenarios[name] | AnswerEnvelope 的证据/Claim 展示投影，不是完整 VerificationArtifact |
| risk-demo.json | scenarios[name] | AnswerEnvelope 的 RiskView/AssetView/ActionView 展示投影，不是完整 RiskAnalysisArtifact |
| answer-demo.json | scenarios[name] | 完整 AnswerEnvelope |

五个文件共享 10 个场景：PASS、ORCHESTRATION_FAILED、SYNTHETIC_STOP、CANCELLED、DEADLINE_EXCEEDED、FAILED、REPLAN_REQUIRED、PLANNING_FAILED、HUMAN_REVIEW_REQUIRED、PASS_WITH_WARNINGS。default_scenario=PASS。历史 request/status/answer/trace 字段原样提取，ID、时间和引用不得随意更改或跨场景拼接。

数据来源：[历史合成回执](../api/reference/examples/orchestration-test-receipts.json)。这是历史真实代码执行使用合成测试数据/测试 Planner 的回执，本次仅校验结构与一致性，未重新执行 Agent 或模型。外部链接 example.invalid 不应当作公告打开。

## 三个独立专业 Artifact

investigation-demo、evidence-demo、risk-demo 的 artifact_examples 分别提供 InvestigationArtifact、VerificationArtifact、RiskAnalysisArtifact 的证据不足弃权对象。schema_model 指明精确模型，payload 是 DTO。

这些对象来源于 [Schema Mock](../api/reference/examples/professional-artifacts-mock.json)，只做模型验证，未执行业务；hash 是合成占位，不是已验证的冻结快照。scenario_id=INDEPENDENT_ABSTENTION_SCHEMA_MOCK，不能把它们放入 PASS 回执的同一链。Unknown affected 为 null，风险为 UNKNOWN，priority 为 REVIEW_REQUIRED。

## 独立 Gate

[integration-result-independent.json](integration-result-independent.json) 提供完整 IntegrationResult 的另一条合成测试回执，join_with_five_demo_files=false。不得拿其 ID/checks 冒充 PASS 场景完整 Gate；PASS 仅有 answer/trace 中的 Gate 状态与引用。

## 推荐加载方式

由 fixture adapter 统一选 scenario，给页面传 request/status/trace/answer 或展示投影。在 UI 持续显示数据来源标签，并校验逻辑根 ID、answer_id 和 integration_result_id 同场景一致。切换场景同时切换五个数据源，清掉前一个场景缓存。

真实 API adapter 只在明确接口 AVAILABLE 时开启。API_NOT_EXPOSED 的全链不因 fixture 文件存在变得可调用。页面返回到真实模式时，所有Mock数据必须清除；不能在真实网络失败后静默回退为假成功。

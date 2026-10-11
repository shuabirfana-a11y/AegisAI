# 同一场景的数据联动示例

## PASS：历史合成回执

场景问题是“我的 vLLM 0.6.0 部署是否受到某个合成 CVE 影响，如何修复？”确切字符串、ID 和生成时间取各 JSON；不把合成 CVE/包名/example.invalid 当真实漏洞来源。

默认选择 `PASS`，在五个文件中使用同一键：

| 文件 | 读取位置 | 用于页面 |
|---|---|---|
| [investigation-demo.json](../mock/investigation-demo.json) | `scenarios.PASS.request` / `.status` | 问题范围、根 ID、阶段与总体结果 |
| [agent-trace-demo.json](../mock/agent-trace-demo.json) | `scenarios.PASS` | Planner 摘要、三个专业 run、task 状态、tool 调用与 Artifact 引用 |
| [evidence-demo.json](../mock/evidence-demo.json) | `scenarios.PASS` | 已核验/争议 Claim、引用、EvidenceObservation 和证据 ID |
| [risk-demo.json](../mock/risk-demo.json) | `scenarios.PASS` | Answer 的 RiskView、影响资产与处置建议 |
| [answer-demo.json](../mock/answer-demo.json) | `scenarios.PASS` | 完整 AnswerEnvelope |

五份文件同场景的根 ID、answer_id、integration_result_id 和引用取自同一历史回执；用它们联动，不能把另一场景的风险或证据拼进来。元数据只属于 fixture，不属于业务 DTO。

PASS 的阶段为 COMPLETED，总体为 SUCCEEDED，Gate 状态 PASS，答案 COMPLETE。风险摘要 HIGH/P2 是这个合成范围的规则输出，不是整个真实 vLLM 生态的结论。修复建议必须以对应 recommended_actions 为准，不另造产品版本要求。

完整 IntegrationResult 另在 [独立 Gate 回执](../mock/integration-result-independent.json)。它来自其他合成测试链，**不是 PASS 场景的 Gate 详情**；ID 不一致时不能在本场景里加载它。PASS 界面可显示 trace/answer 的真实 Gate 状态，完整 Gate 详情必须显示“本回执未提供”。

## 还必须检查的场景

- `REPLAN_REQUIRED`：current_stage 可为 COMPLETED，但 overall_status=INCOMPLETE、answer_status=INCOMPLETE，不能显示全部通过。
- `HUMAN_REVIEW_REQUIRED`：显示需要人工复核、争议和未解决事项，不能把历史答案当确定结论。
- `PASS_WITH_WARNINGS`：成功与警告同时显示。
- `CANCELLED`：实际终态；不表示浏览器 Abort 就产生同样状态。
- `DEADLINE_EXCEEDED` / `PLANNING_FAILED` / 其他失败：保留范围、失败摘要、已有历史证据和数据标签。

另外，`artifact_examples` 是独立的证据不足弃权场景，只按模型验证，未执行业务，不能替换 PASS 的 Investigation/Verification/Risk Artifact。

这套样例用于前端字段和状态演示，不包含运行中的后端、响应时间 Benchmark、真实模型额度或实际网站地址。

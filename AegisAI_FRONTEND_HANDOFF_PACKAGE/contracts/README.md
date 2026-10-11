# 类型入口与复制要求

先读 [快速入门](../docs/FRONTEND_QUICK_START.md) 与 [完整交接](../docs/FRONTEND_TEAM_HANDOFF.md)。

请整目录复制，九个指定文件依赖 generated/。index.ts 只导出类型，不是运行库或 API Client。

| 入口 | 对应当前后端协议 |
|---|---|
| InvestigationRequest.ts | 真正内部输入；问题位于 planner_input.query.question |
| InvestigationStatus.ts | logical_investigation_id、current_stage、overall_status |
| AgentTrace.ts | Phase 11-D run 摘要和调查 Trace；专业任务 Trace / 旧问答 Trace 分开 |
| EvidenceReference.ts | Answer Citation / EvidenceObservation；不是 HTTP EvidenceRow |
| Claim.ts | 专业 VerificationClaim；HttpClaim 另映射数据库 HTTP 行 |
| VerificationResult.ts | 专业 VerificationArtifact；旧 HttpVerificationResult 单独导出 |
| RiskAnalysis.ts | 完整 RiskAnalysisArtifact；不等于 Answer 的 RiskView |
| IntegrationResult.ts | Gate 完整协议与 status 枚举 |
| AnswerEnvelope.ts | 冻结可信答案；answer_status 与 integration_status 分开 |
| InvestigationArtifact.ts | 补充调查 Artifact 的便捷入口 |
| HttpContracts.ts | 当前 AVAILABLE HTTP 的请求/返回类型与旧问答类型 |

generated/ 包含 JSON Schema 类型映射和人工 HTTP 响应映射；不是新建后端模型。来源 JSON Schema 在 [api/reference](../api/reference/)，字段 required/null、枚举和原名保留，不增加便利别名。UUID/日期在 JSON 中是 string，tuple 是数组，未知 dict/Any 用 unknown/Record<string,unknown>，没有 any 类型。

Phase 11-D DTO 仍是 API_NOT_EXPOSED。生成文件中的 InvestigationContext 等内部审计模型不可直接作为浏览器响应；其中控制字段只作为内部定义参考，不属于公开接口。类型里出现某字段不能说明前端有读取权限。

既有前端没有 TypeScript 构建系统。当前验证包括 Node 原生 TypeScript 语法、导入/导出引用及 Schema 比对，未运行 tsc。团队复制后需按自己的工程进行 TypeScript 语义检查；仅用类型断言不会验证网络返回。

所有示例的外层标签不属于这些 DTO，见 [Mock 说明](../mock/README.md)。

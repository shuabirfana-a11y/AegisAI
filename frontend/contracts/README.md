# AegisAI frontend contracts

本目录只新增类型与说明，没有运行代码、API Client 或 HTTP 接口。

先读 [FRONTEND_HANDOFF.md](../../docs/FRONTEND_HANDOFF.md)。现有 HTTP、Python 内部能力、演示数据分别标为 AVAILABLE、API_NOT_EXPOSED、MOCK_ONLY；既有 HTTP 的前端代理限制另标 PROXY_BLOCKED。

## 入口

九个指定文件：InvestigationRequest.ts、InvestigationStatus.ts、AgentTrace.ts、EvidenceReference.ts、Claim.ts、VerificationResult.ts、RiskAnalysis.ts、IntegrationResult.ts、AnswerEnvelope.ts。它们导出当前 Pydantic 精确映射；不是新建后端 DTO 或业务框架。

HttpContracts.ts 导出现有 HTTP 类型；index.ts 只导出类型。generated/ 保存实际 JSON Schema 映射及手工 HTTP 响应映射。

## 边界

- InvestigationRequest 顶层是 planner_input/time_scope/user_context/investigation_options。没有 query/asset_scope/options 的便利别名。
- InvestigationStatus 是 logical_investigation_id/current_stage/overall_status。COMPLETED 不等于 PASS。
- AnswerEnvelope 的 answer_status 与 IntegrationResult.status 不是同一枚举。
- Claim / VerificationResult 是专业快照 DTO 的明确导出别名；HttpClaim / HttpVerificationResult 是原有数据库 HTTP 行。
- EvidenceReference 是 Answer Citation；source_id/raw_document_id/observation_id 表示来源。派生 evidence_id 不保证能调用 GET /api/v1/evidence/{uuid}。
- Phase 11-D 全部类型仍是 API_NOT_EXPOSED；不要仅因为类型存在就发请求到建议 URL。
- generated/internal-output.ts 包括部分内部审计模型；InvestigationContext 不可原样作为浏览器响应暴露。

## 严格性

没有 TypeScript any。后端未限定的 dict/Any 映射为 unknown 或 Record<string, unknown>，使用前需要收窄。UUID、日期及带时区时间在 JSON 中为 string；数值边界、引用完整性、哈希绑定及业务弃权仍由后端验证。

生成文件的可省略/可空、联合枚举和字段名称取自模型 JSON Schema。静态类型不代替运行时 JSON Schema/Pydantic 验证。

当前 frontend 是 JavaScript ESM，尚未增加 TypeScript 构建系统。交接采用 Node 24 原生 TypeScript 语法检查，并核对 Schema 字段、引用及类型导出；没有安装编译器、改变 package.json 或启用前端构建。团队纳入 TypeScript 工程后还需按自己的 tsconfig 执行完整语义检查。

## 示例

[JSON fixtures](../../docs/frontend-contracts/examples/) 均标注 DEMO/MOCK、MOCK_ONLY 及 production_data=false。真实代码执行的合成测试回执也不是生产安全情报或 Benchmark 结果。

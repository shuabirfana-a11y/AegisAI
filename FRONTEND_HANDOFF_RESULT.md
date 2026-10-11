# AegisAI Phase 12-A.5 前端交接契约补齐结果

审查日期：2026-10-10。当前后端基线：Phase 11-D。

本阶段完成接口审查、交接文档、离线 Schema、严格 TypeScript 契约和 API 缺口说明。未新增 HTTP 接口、未开发前端页面、未修改 Agent 或后端业务。Phase 12-B 尚未实施。

## 完成内容

- 已保存 [FRONTEND_HANDOFF.md](docs/FRONTEND_HANDOFF.md)，覆盖实际技术栈、七个页面、现有 API、请求/响应、核心模型、错误、幂等、取消、超时、刷新机制及接口变更管理。
- 已审查当前 FastAPI Router、Pydantic Schema、Investigation Orchestrator、三个专业 Artifact、IntegrationResult、AnswerEnvelope 与 Trace，实现与浏览器接口分别标注。
- 导出当前真实 OpenAPI、JSON Schema 与类型。34 个现有 HTTP 操作的成功响应 Schema 为空，另提供按返回代码整理的响应类型，没有修改 OpenAPI 或伪造 response_model。
- 区分 AVAILABLE、API_NOT_EXPOSED、MOCK_ONLY。PROXY_BLOCKED 仅表示当前前端代理限制，PROPOSED 仅表示建议接口。
- 所有 JSON fixtures 均标注 DEMO/MOCK、MOCK_ONLY 和 production_data=false。历史代码执行的合成测试回执与人工模拟对象明确分开。

## 新增文件

| 文件组 | 位置与作用 |
|---|---|
| 主交接文档 | docs/FRONTEND_HANDOFF.md |
| 前端类型入口 | frontend/contracts/README.md、index.ts、HttpContracts.ts 和九个指定契约 |
| 生成的类型依赖 | frontend/contracts/generated/ 下 7 个 .ts 文件 |
| HTTP 逐项参考 | docs/frontend-contracts/HTTP_API_REFERENCE.md、http-apis.json |
| 原始 OpenAPI | docs/frontend-contracts/openapi.json |
| Schema 与声明 | docs/frontend-contracts/ 下 http-input、tool-input、internal-input、internal-output、legacy-output、http-data-columns 的 .schemas.json 与 .d.ts，以及 http-responses.d.ts |
| 工具注册信息 | docs/frontend-contracts/tools.registry.json |
| 缺口说明 | docs/frontend-contracts/API_GAPS.md、api-gaps.json |
| 脱敏示例 | docs/frontend-contracts/examples/ 下 4 个 JSON 文件 |
| 验证与哈希 | docs/frontend-contracts/verification.json、type-verification.json、manifest.json |
| 本结果报告 | FRONTEND_HANDOFF_RESULT.md |

具体文件、大小及 SHA-256 以 [manifest.json](docs/frontend-contracts/manifest.json) 为准。manifest 本身不递归计算自身哈希。

## 已确认 API

当前后端共 **33 条路径、34 个 HTTP 操作**。源码已实现不代表本次确认服务在线；本轮没有启动服务或在线抓包。

可复用的现有 HTTP 能力：

- 漏洞列表、详情、富化结果、Claim、Evidence、POC/Patch 候选及时间线。
- 证据详情、待复核列表与详情。
- 资产列表、概览、详情、风险、历史风险和变化记录。
- 数据源、同步记录及数据库健康检查。
- 旧版 assistant 查询、run、tasks、trace；工具契约查询与只读工具调用。

当前真实前端代理允许其中 **27 个操作**；另有 **7 个既有写操作被代理阻止**，包括复核提交、资产写入和工具 POST。这些 API 已存在，但需要补齐代理及权限对接才可在当前浏览器页面提交，不能误写为后端 API 缺失。

完整参数、响应、鉴权、错误及每项浏览器可达性见 [HTTP API 参考](docs/frontend-contracts/HTTP_API_REFERENCE.md)。

## API_NOT_EXPOSED 列表

Phase 11-D 没有挂载 FastAPI Router，以下 9 项仍无浏览器可调用接口：

| 能力 | 当前内部实现或缺口 |
|---|---|
| 创建调查 | investigate() 是同步方法，尚无异步 HTTP 适配与入队 |
| 查询调查状态 | get_status() 存在，未暴露 HTTP |
| 读取调查结果 | get_result() 存在，公开响应需排除内部 context 字段 |
| 专业 Agent Trace | get_trace() 存在，不能套用旧版 assistant Trace |
| 专业 Artifact 读取 | 内部引用与 Reader 存在，仍需根调查/归属/哈希绑定 |
| Integration Gate 结果 | IntegrationService.read() 存在，需根调查到 Gate ID 的绑定 |
| AnswerEnvelope | 内部冻结交付存在，未暴露 HTTP |
| 取消调查 | cancel() 保存取消请求，未暴露 HTTP |
| 历史调查 | 已有持久化记录，历史列表服务、分页 DTO 与 HTTP 均待补齐 |

[API_GAPS.md](docs/frontend-contracts/API_GAPS.md) 中的所有建议 URL 均为 PROPOSED、http_implemented=false，不能直接调用。全局情报趋势、主机/模型遥测等额外页面需求也标为 BACKEND_REQUIRED。

## TypeScript 类型列表

| 指定文件 | 真实模型对应 |
|---|---|
| InvestigationRequest.ts | InvestigationRequest、PlannerInput 及内部选项 |
| InvestigationStatus.ts | InvestigationStatus、阶段与整体状态 |
| AgentTrace.ts | Phase 11-D AgentTrace / InvestigationTrace，另列专业及旧版 Trace |
| EvidenceReference.ts | Answer Citation 和 EvidenceObservation |
| Claim.ts | VerificationClaim 的明确导出别名；HttpClaim 单独导出 |
| VerificationResult.ts | VerificationArtifact 的明确导出别名；HttpVerificationResult 单独导出 |
| RiskAnalysis.ts | RiskAnalysisArtifact |
| IntegrationResult.ts | IntegrationResult 与 Gate 相关模型 |
| AnswerEnvelope.ts | AnswerEnvelope 与答案视图 |

类型来自实际 Schema；未定义的字典使用 unknown 或 Record<string, unknown>，没有 TypeScript any。可选、可空及枚举按后端区分。

提示词中的示意字段没有擅自加到后端：

- 调查输入实际为 planner_input / time_scope / user_context / investigation_options，没有顶层 query / asset_scope / options。
- 状态实际为 logical_investigation_id / current_stage / overall_status。
- AnswerEnvelope 使用 answer_status、key_findings、risk_assessment、citations、recommended_actions；PASS 等属于 Gate 状态，不能当答案状态。
- 原有数据库 HTTP Claim/Verification 行与专业快照对象分别导出，避免同名含义混用。

## 验证结果

已实际执行本阶段针对性检查，结果见 [verification.json](docs/frontend-contracts/verification.json)：

- 18 个 contracts TypeScript 文件通过 Node 24 原生语法检查；118 项命名类型引用检查通过，无 any。
- 5 组 Pydantic Schema/生成类型与当前 Python 模型一致；OpenAPI 与当前代码一致。
- 6 份 Schema 文档通过结构及引用检查。
- 45 个示例对象通过 Pydantic 校验；其中 40 个另通过选定根 JSON Schema 校验。
- 34 个实际 HTTP 操作与清单一致，9 个建议操作均未出现在真实路由中。
- 示例未包含敏感凭据字段或带凭据的 URL。
- 258 个已有后端/前端文件的 SHA-256 与本轮开始基线相同，修改、删除、新增业务文件均为 0。

当前前端是 JavaScript ESM，没有现成 TypeScript 编译环境。本轮未安装依赖或修改 package.json；执行的是语法、引用与 Schema 一致性检查，**未运行 tsc 完整语义检查**。队友纳入自己的 TypeScript 工程后应按 tsconfig 再检查。

历史 1261 项工程测试未重跑。真实代码执行示例取自历史合成测试回执，本轮未产生新的端到端 HTTP 回执。

## 前端开发注意事项

- 前端只调用已确认 HTTP，不访问数据库、模型、内部 Python 服务，不保存 API Key。
- 必须先判断业务状态；HTTP 200、COMPLETED、Gate PASS 和 Answer COMPLETE 含义不同。
- evidence_id 可能是派生快照标识，不保证可用于现有 UUID 证据详情 URL。
- 浏览器停止请求不会取消后端调查；cancel_requested 不等于 CANCELLED。
- 不把内部 InvestigationContext、owner、stage_keys 或审计私有数据直接投影到页面。
- 遇到 UNKNOWN/BACKEND_REQUIRED 字段先做缺失状态；不能用 Mock 数据冒充真实返回。
- Phase 11-D 类型可用于界面设计和类型准备，不能据此判断 API 已上线。

## 未解决接口缺口

本阶段只完成交接，以上 9 个 Phase 11-D HTTP 缺口仍存在。34 个操作的成功响应 Schema 仍为空；离线声明没有修复后端 OpenAPI。

当前前端代理、生产域名 Host、认证和多用户归属约束，也需在实际暴露接口时共同验收。全局趋势/遥测、历史分页 DTO 等没有现成响应，不在本轮补造。

## Phase 12 建议

下一阶段建议为 **Phase 12-B：最小 HTTP 适配与前端联调**：

1. 先确认公开 DTO、认证归属、错误码与 response_model，禁止原样返回内部 context。
2. 将同步调查服务适配为可靠异步提交；保留 request_key 幂等与原子领取，避免重复执行。
3. 暴露只读状态/结果/Trace/Artifact/Gate/Answer 及取消接口，验证根调查和用户归属。
4. 补历史列表与分页 DTO；同步完善代理路径、必要方法/Header 和部署域名。
5. 更新 OpenAPI 与类型，再联调刷新、取消、错误、空数据和超时状态。

以上为建议，本轮没有实施。Phase 12-A.5 到此停止，等待下一阶段指令。

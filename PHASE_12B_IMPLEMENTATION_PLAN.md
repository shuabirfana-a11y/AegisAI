# AegisAI Phase 12-B Investigation API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Phase 11-D 调查闭环通过 8 个受保护、具备明确响应 Schema 的 HTTP 操作交给前端。

**Architecture:** FastAPI Router → InvestigationApiService → 原有 InvestigationOrchestrator / 受保护 Reader。同步调查由有并发上限的后台适配执行；已有领取、阶段推进、工具调用、取消与冻结答案不重写。公共 DTO 只投影已验证记录。

**Tech Stack:** 现有 Python 3.12、FastAPI 0.142.2、Pydantic 2.13.5、SQLAlchemy 2.0.54、PostgreSQL、Model Gateway；Node 原生同源代理。

**Spec:** [本次 Phase 12-B 指令](C:/Users/X/.codex/attachments/5172b840-eb4c-4dcb-9d02-cb5bf506fb63/已粘贴的文本.txt)，以及 [FRONTEND_HANDOFF.md](docs/FRONTEND_HANDOFF.md)、[API_GAPS.md](docs/frontend-contracts/API_GAPS.md)。

**状态：PLAN_READY / WAITING_CONFIRMATION。** 审查日期：2026-10-10。本轮只有检查与本计划文件，未实施下列 API、未修改核心代码、未运行新增 API 或全量回归测试。确认后在当前会话按任务执行。

## Global Constraints

- 不修改 Planner、三个专业 Agent、Integration Gate、Risk Engine、Artifact 核心模型及 Runtime / Scheduler / Executor。
- 只增加 API 适配、公共 DTO、受保护的读取与必要入口配置；Router 不查询数据库、不调用 Agent。
- 请求复用真正的 InvestigationRequest；状态、ID、证据及答案取自后端，不能根据提示词示意自行补造。
- 复用当前认证和 owner/type 绑定；浏览器不得指定 actor、owner 或 worker_token。
- 不增加数据库表、Migration、Redis、Celery 或第三方 Agent 框架。
- 前端调整仅限 server.mjs 的传输代理、类型与交接资料；不修改 public/ 页面、UI 或页面业务。
- 所有新增成功/等待/错误响应必须声明 Pydantic 模型并写入 OpenAPI。
- 不把历史 1261 项通过当成本轮实测；实施时必须运行新增 API 测试和已有后端回归。
- 完成 Phase 12-B 后停止，不进入 Phase 12-C。

## Review Focus

| 最可能出错的条件 | 必须保障的行为 | 对应任务 |
|---|---|---|
| 同 key 重复提交、两个适配实例并发、相同 key 不同内容 | 根调查最多创建一次；同内容回读，异内容 409 | Task 2 |
| 根记录尚未提交、ACK 超时、进程退出 | 202 只携带已提交的真实 ID；不伪造可靠队列或自动恢复 | Task 2 |
| 已有取消与新阶段创建同时发生 | 调用原有取消/creation_guard；取消确认后不启动新阶段 | Task 4 |
| 外部用户、错误类型 run、跨调查 Artifact/Gate 引用或审计篡改 | 归属及绑定校验失败，不泄露对象或返回可信结果 | Tasks 1、3、4 |
| 并发读取、缺少后续 Agent、答案尚未就绪或历史模型配置变化 | 返回同一实际快照；不补齐未执行的 Agent，不重新调用模型/Gate | Tasks 3、4 |

---

## 1. 已完成的开发前检查

### 1.1 HTTP 入口与运行方式

- backend/app/main.py 当前只挂载 routes、enrichment、assets、assistant、tools 五组 Router。
- 已用 backend/.venv/Scripts/python.exe 导入当前 app 并读取 OpenAPI，确认 **34 个 HTTP 操作**，没有 investigations 路由，app.user_middleware 为空。
- 34 个原操作的成功响应 Schema 为空；本阶段为新增 8 个操作补全 response_model，不顺带重构旧接口。
- frontend/server.mjs 代理 /api/v1/ 和 /health，POST 只允许 /api/v1/assistant/query，超时 30 秒。
- 当前允许 27 个操作经代理调用，7 个既有写操作仍被阻止。本阶段只放行两个调查写入口，其他写权限保持当前范围。

### 1.2 可复用接口与证据位置

| 能力 | 当前真实接口 / 文件 |
|---|---|
| 同步调查 | InvestigationOrchestrator.investigate(request, *, actor)，backend/app/orchestration/service.py |
| 状态 | get_status(id, *, actor)；同源 store.read_audit / status_snapshot |
| 冻结结果 | get_result(id, *, actor)，内部 InvestigationReader 校验冻结答案及绑定 |
| 安全 Trace | get_trace(id, *, actor)，backend/app/orchestration/trace.py |
| 取消 | cancel(id, *, actor) → PostgresInvestigationStore.request_cancel |
| 幂等领取 | store.claim；actor/type/request_key 的 PostgreSQL 锁与 request_fingerprint |
| 专业 Artifact | InvestigationReader.read(run_id, actor)、VerificationReader.read(run_id, *, actor)、AnalysisReader.read(run_id, *, actor) |
| 已完成 Gate/Artifact 快照 | AnswerSourcesLoader.load(context, *, actor)，校验根调查、来源及 Gate 哈希绑定 |
| Gate 单条读取 | IntegrationService.read(id, *, actor)，不可调用 evaluate() |
| 模型统一入口 | backend/app/llm/gateway.py 的 ModelGateway |
| 认证 | backend/app/api/assets.py 的 ActorDep；底层 app.assets.auth.asset_principal |
| 已有持久化 | app.AgentRun，actor_principal / agent_type / details.orchestration_v1 |
| 真实链路测试 | backend/tests/orchestration/test_actual_chain.py、fixtures.py、conftest.py |

历史列表没有现成 Orchestrator 方法。增加 API 适配层只读 Repository，对现有根记录进行归属过滤与分页，不新增历史业务表。

### 1.3 认证、错误、CORS

当前认证是本地静态 Bearer Token：AEGIS_ASSET_TOKEN 校验，AEGIS_ASSET_OWNER 映射主体，默认 local-analyst。未配置返回 503，令牌错误返回 401。不是多用户登录系统，本阶段不扩展身份体系。

旧接口返回 HTTPException 的 detail；新增调查接口采用局部 ErrorResponse，不全局替换旧错误格式。当前没有 CORS。实际前端优先走同源代理，独立开发前端可配置精确 Origin 白名单。

本次只阅读配置名称及代码，没有读取或导出凭据值。

## 2. API 设计

全部地址为 **PLANNED / 当前 API_NOT_EXPOSED**。采用现有版本前缀 /api/v1/investigations，不同时建立 /api/investigations 别名。

| Method / 路径 | 请求 | 主要响应及 HTTP 状态 |
|---|---|---|
| POST /api/v1/investigations | 当前 InvestigationRequest | 新建/仍运行：202 InvestigationStatusResponse；已终态幂等回读：200 同模型 |
| GET /api/v1/investigations/history | offset、limit、overall_status、sort | 200 InvestigationHistoryResponse |
| GET /api/v1/investigations/{id}/status | 根 logical_investigation_id | 200 InvestigationStatusResponse |
| GET /api/v1/investigations/{id}/trace | 根 ID | 200 AgentTraceResponse |
| GET /api/v1/investigations/{id}/artifacts | 根 ID | 200 ArtifactResponse；还未产生任何 Artifact 且仍运行：202 同模型 |
| GET /api/v1/investigations/{id}/integration | 根 ID | 200 IntegrationResponse；仍运行且无 Gate：202 InvestigationStatusResponse |
| GET /api/v1/investigations/{id}/answer | 根 ID | 200 AnswerResponse；仍运行且无答案：202 InvestigationStatusResponse |
| POST /api/v1/investigations/{id}/cancel | 根 ID，无须 Body | 请求取消：202 InvestigationStatusResponse；已终态：200 同模型 |

history 静态路由在带 ID 的路由之前声明。UUID 解析失败是 422，其他用户/错误类型/不存在的根 ID 统一 404。

新增 **2 POST + 6 GET = 8 操作**；若无额外范围变化，完成后预计总计 42 个 HTTP 操作。上一阶段建议的通用 GET /investigations/{id} 不是本指令要求，不在本次新增清单中；交接缺口应据此更新，不能将未新增 URL 标 AVAILABLE。

202 的提交返回 Location 指向 status 路由，等待响应携带 Retry-After: 2。终态没有 Gate 返回 409 RESULT_UNAVAILABLE；终态缺少应已冻结的 Answer 是 500 SNAPSHOT_INVALID，不能重新生成补齐。

## 3. Schema 映射与字段选择

### 3.1 请求与状态

保持当前 InvestigationRequest 顶层：

schema_version、request_id、planner_input、time_scope、user_context、investigation_options。

- 问题是 planner_input.query.question；幂等键是 planner_input.query.request_key。
- asset_id 在 planner_input.query；component_id 等使用 PlannerInput 已有字段。
- user_query 是 Python property，不是 JSON 字段；asset_scope/options 不存在，本次不添加便利别名。
- scope、realtime、网络权限按现有服务器策略校验；AEGIS_ALLOW_REALTIME 未启用时拒绝请求实时外部工具。
- 客户端不能通过附加 actor / owner / provider 字段切换身份或模型供应商。

InvestigationStatusResponse 保留 InvestigationStatus 全部真实字段，另增加 progress: tuple[StageEvent, ...]。progress 来自该根调查保存的 events。读取使用原 store.read_audit 与原 status_snapshot 生成同一快照，避免将不同 revision 的状态与事件拼在一起。

真实字段包括 logical_investigation_id、current_stage、overall_status、四个子 run ID、cancel_requested、recovery_required、warnings、error_code、revision、updated_at。

current_stage：
CREATED / PLANNING / INVESTIGATING / VERIFYING / ANALYZING / INTEGRATING / COMPOSING / COMPLETED / WAITING_REVIEW / FAILED / CANCELLED。

overall_status：
RUNNING / SUCCEEDED / SUCCEEDED_WITH_WARNINGS / INCOMPLETE / REVIEW_REQUIRED / FAILED / CANCELLED。

不增加 CANCEL_REQUESTED 业务状态。取消受理用原 cancel_requested=true 表达；COMPLETED 不自动等于答案 COMPLETE 或 Gate PASS。

### 3.2 Trace

AgentTraceResponse 字段：

- logical_investigation_id: UUID
- trace: 当前 InvestigationTrace
- stages: tuple[TraceStageView, ...]

TraceStageView：stage、agent_id（可空）、run_id（可空）、status（真实子 run / Planner 状态，可空）、start_time/end_time（可空）、artifact_references、time_source（RUN_RECORD / STAGE_EVENT / UNAVAILABLE；只描述时间来源）。

trace 由 Orchestrator.get_trace 读取。时间仅来自对应已保存 run 的 started_at/finished_at 或明确阶段事件，来源写入 time_source；没有记录则 null。root deadline/响应时间不冒充 Agent 执行时间。

专业 Agent 名称取现有注册 ID：investigation_agent、verification_agent、security_analysis_agent。Planner/Gate 是阶段服务，agent_id 为空。只列实际出现的阶段，不能为失败链路填充“已执行”的完整五段。

读取额外时间字段的 Repository 必须验证子 run 属于根 context 引用、同 actor、正确 agent_type。Trace 中不返回原始 Prompt、模型原文、任意 input/output_summary 或异常堆栈。

### 3.3 Artifact

ArtifactResponse：logical_investigation_id、status（当前 InvestigationStatus）、items、warnings。items 最多 3 个，保持选中引用顺序，不返回所有同 run 的未选 Artifact。

ArtifactItem：artifact_id、artifact_type、source: ArtifactRef、references: tuple[ArtifactRef, ...]、public_schema_version、data（三个 Public Artifact DTO 的联合）。

Public Artifact 是公共投影，不替代核心 Artifact：

- 共同保留 artifact_id/task_id/agent_id/run_id、来源 Schema、业务状态、置信度、公开证据及不确定项。
- 调查保留漏洞标识、description、组件/资产的公开字段、affected_versions/fixed_versions、version_match、CVSS/CWE、POC 候选、补丁、evidence、conflicts、findings。
- 核验保留 claims、verification_status、supporting_evidence、conflicting_evidence、conflicts、warnings、unresolved_items、rules_version、source_run_id/source_artifact_id/source_snapshot_hash、evaluation_time、execution_status。
- 风险保留风险/优先级、受影响判断、资产与版本匹配结果、利用/补丁信号、因子、措施、证据、规则、解释、warnings/unresolved_items、输入绑定哈希与历史时间。
- 排除 tool_calls、failed_tools 原始错误、model_calls、model_hints、receipt_references、内部上下文、库存或工具返回的任意私有字典。
- 调查的未知字典子结构采用公开工具字段白名单投影：只保留已交接的漏洞/版本/证据/候选/资产摘要字段；未知键不透传。字段类型复用原模型定义，未确定的子字段保持 unknown，而不捏造结构。
- 公共投影有独立 public-*-artifact-v1 版本。source 保留原 ArtifactRef，哈希绑定先在原对象上验证；不能将删减后的 data 哈希声称为原 artifact_hash。

Gate 产生后从 AnswerSourcesLoader 的冻结 source 读取；此前通过三个现有 Reader 回读原始正式回执，再用 artifact_ref 校验根 context 的引用。校验前后根 revision 不一致时做至多 2 次只读重试，仍不能获得一致快照返回 409 SNAPSHOT_READ_CONFLICT。不运行新的调查、核验或风险算法。

### 3.4 Gate 和答案

IntegrationResponse 复用当前 IntegrationResult 字段与状态：
PASS / PASS_WITH_WARNINGS / REPLAN_REQUIRED / HUMAN_REVIEW_REQUIRED / FAILED。

真实字段为 evidence_references、artifact_references、blocking_issues；不建立 evidence_refs 等别名。必须用根 context 绑定的 integration_result_id 读取并通过 AnswerSourcesLoader 校验。Gate 的 logical_investigation_id 不等于根 ID，不能拿根 ID 直接当 Gate ID。

AnswerResponse 复用当前 AnswerEnvelope，直接交付已存对象：

answer_id、answer_status、integration_status、summary、key_findings、affected_assets、risk_assessment、recommended_actions、verified_claims、disputed_claims、citations、evidence_observations、evidence_references、warnings、unresolved_items、引用及时间。

answer_status：
COMPLETE / COMPLETE_WITH_WARNINGS / INCOMPLETE / REVIEW_REQUIRED / FAILED / CANCELLED。

get_result 的内部冻结绑定校验可以执行；HTTP GET 不调用模型、不 evaluate Gate、不生成新的 answer_id/generated_at，不将 findings/risk/recommendation 等示意名称加为 wire 别名。

Integration/Answer 的公开结构使用明确 DTO；既有字典型证据引用也按公开引用白名单输出，不透传审计配置。若因此产生公共视图差异，在 API Schema 中明确为投影，而不声称是内部模型的字节级原样快照；结论、状态、证据标识及冻结时间不得变化。

### 3.5 历史与错误

InvestigationHistoryResponse：items、total、offset、limit。

InvestigationHistoryItem：logical_investigation_id、original_question、current_stage、overall_status、cancel_requested、recovery_required、revision、created_at、updated_at、finished_at（可空）。

参数：offset>=0，limit 默认20且1..100，overall_status 为原 Overall 或空，sort 为 created_desc（默认）/created_asc。以 started_at 与 id 同向排序确保同时间记录顺序稳定，started_at 必须与已验证根 context.created_at 绑定。分页与总量查询均过滤 actor_principal + agent_type=investigation-orchestrator-v1；排除 planner/runtime/旧 assistant 记录。

ErrorResponse：error_code、message、request_id（本次 HTTP 关联 ID，不复用幂等键）、retryable。错误码是新增 HTTP 适配码，不是新增业务状态：

| HTTP | error_code | 语义 |
|---|---|---|
| 401 | AUTH_REQUIRED | 无效/缺失 Bearer；WWW-Authenticate: Bearer |
| 403 | OPERATION_FORBIDDEN | 实时网络等服务器策略不允许 |
| 404 | INVESTIGATION_NOT_FOUND | 不存在、非本人或错误类型，不区分详情 |
| 409 | IDEMPOTENCY_CONFLICT | 同主体同 key 内容不同 |
| 409 | SNAPSHOT_READ_CONFLICT | 只读期间无法得到一致 revision |
| 409 | RESULT_UNAVAILABLE | 已终态，未产生所请求 Gate |
| 413 | REQUEST_TOO_LARGE | 新入口请求超过2MiB |
| 422 | INVALID_REQUEST | UUID/参数/Body不合法；只返回安全字段路径，不回显 input/body |
| 429 | INVESTIGATION_BUSY | 两个活动槽位已满；Retry-After: 2 |
| 503 | AUTH_NOT_CONFIGURED / MODEL_UNAVAILABLE / SERVICE_UNAVAILABLE | 服务必要配置或依赖不可用 |
| 503 | SUBMISSION_UNCONFIRMED | ACK 截止前无法确认提交；可能已开始，必须以同 key 回查 |
| 500 | SNAPSHOT_INVALID / INTERNAL_ERROR | 绑定/Hash损坏或内部失败；不暴露原异常 |

新增错误由局部 APIRoute 处理，涵盖认证依赖、参数校验和响应校验；旧 Router 的错误协议不改变。

## 4. 异步提交设计与替代方案

### 方案比较

1. **推荐：有并发上限的 Worker + 原领取成功通知。** 复用同步 investigate 和数据库 claim，只在 API 边界观察已提交的根 ID。无新表，改动集中在适配层。
2. 同步 HTTP 调用：最长300秒与代理30秒冲突，提交不能及时返回并供前端查询，不满足本阶段。
3. 独立持久化队列：需要新状态/重启领取协议和额外存储或 Broker，超出仅 API 适配范围。

### 推荐方案的具体边界

- InvestigationApiService 在 lifespan 中管理最多2个工作线程、2个活动名额；不接受无界排队。
- 提交前 capture_request，使用 request_fingerprint；先查同 actor/type/key 的已存在真实根记录，校验 hash 后直接回读。幂等回读先于容量检查。
- 当前进程对 (actor, request_key) 维护带请求 hash 的短锁/Future 槽位，避免相同 key 重复入线程；不同内容立即409。
- 每个新 Worker 构造原 InvestigationOrchestrator；其 store 外包 CreationAckStore，只透明委托原方法。
- CreationAckStore.claim(request, *, actor) 原样调用 PostgresInvestigationStore.claim；事务提交成功后才通知提交者 ClaimReceipt.logical_id，不预先 claim、不修改 receipt/token/context，不改 stage 推进。
- 包装器不自行调用 Planner/Agent/Runtime，worker 的唯一业务启动是 orchestrator.investigate(request, actor=actor)。
- PostgreSQL 原 claim 锁解决跨适配实例的同 key 竞争；只有 fresh=True 的原服务会启动阶段。另一调用回读原结果。
- 原服务容量分支可能直接回读同 key 结果而不调用 claim；Worker 此时以已通过原 Reader 校验的返回状态通知真实根 ID，不能因没有 claim 回调而另建调查。
- 等待根创建 ACK 最多2秒。真实根出现后再读实际 StatusResponse，返回202；此刻可能已经 PLANNING，不能强改 CREATED。
- ACK 等待截止且 Future 未结束：503 SUBMISSION_UNCONFIRMED，清楚说明同 key 重试；不得声称没有执行或另造一个临时 investigation_id。Worker 继续受现有300秒deadline控制。
- 原服务容量错误、取消、数据库失败及 NOT_STORED 按实际持久化结果映射，不把未确认保存当成功。
- 同 key 已存在但 recovery_required=true：只返回原记录，不自动重跑。API线程池不是持久化队列；进程崩溃后继续依赖原 lease 失效标志，不宣称任务自动恢复。
- lifespan 关闭时先拒绝新提交，再等待已接纳 worker 完成受原deadline约束的清理，最后关闭本层持有的 Model Gateway 和 engine。不能在线程仍使用资源时提前释放 engine。
- Model Gateway 使用现有配置；构造失败仅使新增提交503，历史 Reader和旧API仍可用。读取历史不以当前模型健康为条件。借用测试注入的 Gateway 不由适配层擅自关闭。

观察包装器是本阶段最重要的边界测试：如果无法保持原 claim/cancel/control 行为，应停下报告适配失败，不复制调查流程或修改核心模块。

## 5. 修改文件与职责

以下均为实施后的拟议变更，当前不存在的文件不代表已创建：

| 文件 | 拟议变更 / 职责 |
|---|---|
| backend/app/api/investigations.py | 新 Router，8个操作、ActorDep、response_model / responses / operation_id |
| backend/app/investigation_api/__init__.py | 新适配包入口 |
| backend/app/investigation_api/contracts.py | 公共请求引用、响应 DTO、Artifact 公开投影模型 |
| backend/app/investigation_api/service.py | InvestigationApiService，读/提交/取消/历史的用例适配 |
| backend/app/investigation_api/submission.py | Worker 生命周期、容量、同 key Future、CreationAckStore |
| backend/app/investigation_api/repository.py | actor/type绑定的根查找、历史分页、只读阶段时间查询 |
| backend/app/investigation_api/projection.py | 原对象校验后的 DTO 白名单投影，不包含业务判断 |
| backend/app/investigation_api/errors.py | 局部 InvestigationRoute、安全 ErrorResponse 映射和限量请求读取 |
| backend/app/investigation_api/config.py | ACK、worker上限、明确CORS白名单及API配置验证 |
| backend/app/main.py | 挂载新Router、lifespan管理适配Service；可注入service factory供测试 |
| frontend/server.mjs | 仅代理调查提交/取消与认证，传递Location/Retry-After等必要响应头 |
| backend/tests/investigation_api/ 下测试 | 新API契约、并发、真实链路、取消、权限、历史和快照测试 |
| frontend/tests/server.test.mjs | 增加两条调查写入口的同源/鉴权/限制测试 |
| frontend/contracts/InvestigationApi.ts、index.ts | 新HTTP公共DTO导出，保留原内部契约 |
| frontend/contracts/generated/ 相关文件 | 按真实新增OpenAPI/公共Schema更新生成类型 |
| docs/FRONTEND_HANDOFF.md、docs/frontend-contracts/ | 更新实际接口清单、Schema、缺口、示例、校验和manifest |
| work/phase12b/run_tests.py及实测回执 | 单独保存收集/新增/全量与Node测试证据，不覆盖历史验收 |
| PHASE_12B_RESULT.md | 实施成功后才写结果，不在计划阶段预写完成 |

backend/app/orchestration/、planner/、runtime/、agents/、integration/、assets/risk*、tooling/、llm/、db/models 与 Migration 文件作为只读基线，验收必须确认哈希不变。

## 6. 权限、CORS 与代理策略

- Router 使用现有 ActorDep；API Service 再做 valid_actor。actor 不由请求 Body、Query、前端localStorage或自定义Header提供。
- 根读/取消/历史都验证 owner + TYPE。返回404隐藏跨用户对象；客户端传任意子 run / Artifact / Gate ID不能绕过根绑定。
- CORS 使用 AEGIS_DEV_CORS_ORIGINS 精确Origin列表，默认空列表保留同源方式；配置 localhost/127.0.0.1 具体端口以支持独立开发页。拒绝 *、带路径或 userinfo 的Origin。
- 配置时只允许 GET/POST/OPTIONS，明确 Authorization/Content-Type，allow_credentials=False；暴露 Location、Retry-After、X-Request-ID。CORS 不替代认证。
- Node 代理仅新增 POST /api/v1/investigations 和符合UUID路径的 /cancel；保留同源Origin、application/json、2MiB限制。
- localDemoToken 覆盖新增调查路径的 Authorization，令牌留在服务器；普通模式透传已有 Bearer，仍不透传Cookie/Set-Cookie。
- 保留localhost Host检查。本轮为本地开发联调；公网域名/云发布配置仍属于后续部署，不顺带放宽Host到任意域。
- 旧34个操作的响应Body、权限和路由不修改；原7个被阻止的写操作不顺带开放。

## 7. 任务与测试计划

### Task 1：公共契约、局部错误及认证边界

**Files:** contracts.py、errors.py、projection.py的基础公共类型；tests/investigation_api/test_contracts.py、test_auth_errors.py。

**Interfaces:** 产生 InvestigationStatusResponse、AgentTraceResponse、ArtifactResponse、IntegrationResponse、AnswerResponse、InvestigationHistoryResponse、ErrorResponse；复用当前 Request/Stage/Overall/Gate/Answer枚举。

- [ ] 写失败测试：test_status_progress_matches_one_revision、test_answer_gate_enums_not_mixed、test_request_rejects_actor_and_aliases、test_errors_do_not_echo_body。
- [ ] 写错误/认证用例：缺Token401、未配置503、错误owner404、invalid UUID422、大Body413、异常栈或敏感输入不回显。
- [ ] 执行对应测试并记录失败原因，确认测试失败来自缺失能力。
- [ ] 实现局部Route错误映射与公共投影；仅真实字段和独立 public schema 版本。
- [ ] 执行同组测试通过；确认旧HTTP错误协议不改变。

### Task 2：后台提交、ACK、幂等与生命周期

**Files:** submission.py、repository.py的根key查找、service.py提交部分、config.py；test_submission.py、test_idempotency.py、test_lifespan.py。

**Interfaces:**
- InvestigationApiService.submit(request: InvestigationRequest, *, actor: str) -> SubmissionOutcome
- SubmissionOutcome：http_status（200/202）与 response: InvestigationStatusResponse
- CreationAckStore.claim(request, *, actor) -> 原 ClaimReceipt
- ApiRootRepository.find_by_key(request_key, *, actor) -> 已校验根快照或None
- InvestigationApiService.close()；create_app(engine=None, *, investigation_service_factory=None)兼容旧入口

- [ ] 写 test_202_ack_after_real_commit：暂停Planner，让原claim真实提交；响应ID能立即被状态/取消读取，拒绝预生成ID。
- [ ] 写 test_claim_observer_preserves_receipt 和 test_claim_rollback_never_ack：原receipt/token及所有委托行为不变，事务失败没有202。
- [ ] 写 test_same_key_one_root、test_two_adapters_same_key_one_execution、test_same_key_changed_content_409；断言根记录与真正业务启动次数均为1。
- [ ] 写 test_ack_timeout_is_unconfirmed_same_key_recovers：503不是未执行；同 key 重试回到原ID，无第二调查。
- [ ] 写 test_capacity_full_429_but_existing_key_can_read、test_expired_lease_not_restarted、test_model_config_failure_does_not_break_reads。
- [ ] 写 test_shutdown_drains_before_gateway_engine_close，验证关闭顺序与无活跃线程泄漏。
- [ ] 执行上述失败测试；实现有界Worker、原claim观察、容量和lifespan注入；执行通过。

### Task 3：状态、Trace、Artifact、Gate 与答案读取

**Files:** service.py读取部分、projection.py、repository.py只读时间；test_readers.py、test_artifacts.py、test_trace.py、test_snapshot_security.py。

**Interfaces:**
- read_status(id: UUID, *, actor: str) -> InvestigationStatusResponse
- read_trace(id: UUID, *, actor: str) -> AgentTraceResponse
- read_artifacts(id: UUID, *, actor: str) -> ArtifactResponse
- read_integration(id: UUID, *, actor: str) -> 当前Gate或等待状态
- read_answer(id: UUID, *, actor: str) -> 当前冻结答案或等待状态

- [ ] 写 test_actual_completed_trace_contains_three_real_runs：用原scenario和Orchestrator，检查Planner→三专业run→Gate的真实ID与时间来源。
- [ ] 写 test_incomplete_trace_does_not_invent_agents、test_running_status_progress_real_events、test_missing_artifact_is_pending。
- [ ] 写 test_artifact_root_ref_and_hash_bound、test_cross_root_artifact_rejected、test_private_artifact_fields_removed。
- [ ] 对五种Gate状态参数化验证原样映射；测试 pending202 与终态无Gate409。
- [ ] 写 test_answer_equals_frozen_public_projection：结论/ID/时间/引用一致；在GET期间禁止Model Gateway与Gate.evaluate调用，重复读取不产生新数据。
- [ ] 写 test_snapshot_changed_retry_bounded、test_tampered_snapshot_fails_closed；错误不透传内部信息。
- [ ] 执行失败测试，复用现有Readers/AnswerSourcesLoader完成投影；执行通过。

### Task 4：取消与历史查询

**Files:** service.py取消/历史、repository.py历史分页；test_cancel.py、test_history.py。

**Interfaces:**
- cancel(id: UUID, *, actor: str) -> 当前 InvestigationStatusResponse
- history(*, actor: str, offset: int=0, limit: int=20, overall_status: Overall|None=None, sort='created_desc') -> InvestigationHistoryResponse

- [ ] 写 test_cancel_during_planning_creates_no_next_stage：原Planner通过可控制Provider暂停；取消持久化后放行Provider，确认原control没有创建下一个专业run。
- [ ] 写 test_cancel_creation_race_uses_original_guard、test_repeat_cancel_idempotent、test_terminal_cancel_returns_real_status。
- [ ] 写 test_completed_investigation_in_history、test_history_owner_type_filter、test_history_status_sort_pagination、test_history_corrupt_audit_not_silently_skipped。
- [ ] 并发取消用原Postgres creation_guard测试，不用伪造状态字典代替。
- [ ] 实现只读历史与原取消委托；重复执行不重跑调查，测试通过。

### Task 5：Router、CORS、代理与OpenAPI

**Files:** api/investigations.py、main.py、config.py、frontend/server.mjs；test_http.py、test_openapi.py、test_cors.py、frontend/tests/server.test.mjs。

**Interfaces:** 8个固定URL；每个response_model及200/202/错误responses明确；operation_id唯一稳定。

- [ ] 先写 HTTP 9类主场景：创建、状态、Trace、答案、五Gate状态、取消、历史、未授权、Schema一致性；另覆盖Artifact。
- [ ] test_submit_uses_actual_orchestrator_chain 用合成scenario、真实PostgreSQL和三个实际专业Agent执行；只有Model Provider是明确标注的测试替身，不mock整条Orchestrator作为端到端证明。
- [ ] 写 test_history_static_route_not_uuid、test_previous_34_paths_unchanged、test_new_8_success_schemas_nonempty、test_actual_json_matches_openapi。
- [ ] 写CORS允许指定Origin/预检与拒绝未知Origin/*；认证必须独立通过。
- [ ] 写Node提交/取消同源放行、跨Origin拒绝、Token服务器保留、Location/Retry-After透传、Body上限；原资产/assistant测试继续通过。
- [ ] 执行失败测试；挂载Router及必要代理适配；执行新增API和全部Node测试通过。

### Task 6：回归、交接更新与停止

**Files:** work/phase12b/run_tests.py / *.json/*.xml/*.log；docs与contracts；PHASE_12B_RESULT.md。

- [ ] 编码前以collect-only保存原nodeid清单及实际数量；历史1261仅作对照。
- [ ] 新增API测试独立执行并保存回执；保持专用 aegis_phase5_test 数据库校验，真实数据源/生产数据库不得用于测试。
- [ ] 全部后端 tests 真实执行，保留每个原测试；按原nodeid与新增nodeid分类统计 old/new/total、failed/errors/skipped，不把独立运行次数相加作为总量。
- [ ] 沿用旧测试已有收集顺序处理，保留基于收集时刻的未来证据fixture语义，不改其断言、不跳过慢测试。必要order证据放在work/phase12b，不覆盖历史full_suite_final。
- [ ] 执行全部frontend Node测试，后端与Node计数分别报告。
- [ ] 检查核心目录与旧业务基线hash、公共DTO秘密字段、OpenAPI与实际JSON、线程/进程清理；发现核心修改即阻止阶段验收。
- [ ] 重导出OpenAPI/公共Schema/TypeScript并更新接口状态。保留内部types与public types区别，示例全部DEMO/MOCK；测试替身不能包装为生产AI结果。
- [ ] 更新handoff/HTTP inventory/gaps/manifest；按实际8个操作关闭缺口，保留未实现通用结果URL与部署限制。
- [ ] 从实际回执生成PHASE_12B_RESULT.md，明确接口、文件、OpenAPI变化、测试数量与限制。
- [ ] 完成即停止，不修改页面或开始Phase12-C。

### 计划中的验证命令

以下只供确认后执行，本轮未运行。工作目录为项目根：

- backend/.venv/Scripts/python.exe work/phase12b/run_tests.py baseline_collect --collect-only -q tests
- backend/.venv/Scripts/python.exe work/phase12b/run_tests.py new_api -q tests/investigation_api
- backend/.venv/Scripts/python.exe work/phase12b/run_tests.py full_suite -q tests
- node --test frontend/tests/*.test.mjs

新runner以backend为pytest工作目录，先验证两个测试数据库变量均指向 aegis_phase5_test，必要时以相同测试地址配置Alembic。只记录命令、计数及安全错误摘要，不输出环境变量值。

通过标准：本轮所有新增API及现有后端回归 exit=0，failed=0，errors=0，skipped=0；Node测试全部通过。接口实际响应符合导出Schema、42操作目标与旧34兼容、核心哈希未变。若失败，报告真实失败，不挪用历史验收。

## 8. OpenAPI 与前端联调准备

新增公共DTO和8个操作应可由 /openapi.json 导出。使用 response_model 与额外 responses 同时说明200/202/错误，避免历史空Schema问题继续扩散。[官方响应模型说明](https://fastapi.tiangolo.com/tutorial/response-model/)、[额外响应说明](https://fastapi.tiangolo.com/advanced/additional-responses/)。

前端提交后使用真实logical_investigation_id；状态轮询建议2秒，遇429/503遵循Retry-After并保留原request_key。状态显示以current_stage/overall_status为准；Trace/Artifact/Gate/Answer按需拉取，不每轮全部重建。终态停止自动轮询；recovery_required显示恢复待处理，不触发新调查。

后台服务在lifespan创建和关闭；线程适配具有进程生命周期限制，不是可靠消息队列。[官方生命周期说明](https://fastapi.tiangolo.com/advanced/events/)、[后台任务边界说明](https://fastapi.tiangolo.com/tutorial/background-tasks/)。

开发环境跨源访问采用明确白名单；当前同源代理仍是默认接入方式。[官方CORS说明](https://fastapi.tiangolo.com/tutorial/cors/)。

## 9. 当前计划限制与验收边界

1. 当前仍只有原34个HTTP操作；本文件中的8个新操作都未实施。
2. 当前认证是单主体本地令牌；本阶段不会产生团队多用户账号系统。
3. Worker不具备进程重启后的持久化调度；原lease失效会真实显示recovery_required，恢复机制另行安排。
4. 未配置真实模型服务时不能将Mock Planner输出宣称为真实模型调查效果；API测试可用受控Provider替身，但需标明。
5. Core Reader可能依据旧回执重建和校验投影，这是只读历史验证；不得以此重新采集、运行Agent或重评Gate。
6. 旧34个空成功Schema和7个代理阻止操作不在本次修复范围；新增8个必须完整。
7. 通用调查结果URL与公网部署保留为后续缺口；本阶段准备本地前端接入，不承诺网站已发布。

本计划已覆盖指令要求的8项API、公共Schema、认证/安全错误、CORS、真实API测试和完整回归；实施报告只有完成并取得本轮证据后生成。

**下一动作：按本次指令“等待确认后实施”，等待用户确认本计划；当前停止在计划阶段。**

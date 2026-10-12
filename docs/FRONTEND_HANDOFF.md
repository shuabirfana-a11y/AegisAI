# AegisAI 前后端协作契约交接

更新：2026-10-12，Phase 12-D。基于 Phase 12-C 的审查提交；本轮增加本地真实Provider联调和可选公共模型执行身份，不增加调查路由。

**当前有 41 条路径、42 个 HTTP 操作；8 个智能调查操作已经开放。完整成功链通过专用测试库的 TCP 联调验证，当前本地默认 Mock 对普通调查仍会规划失败。** 接口已存在、内部链可执行、真实模型可用、队友工作台已完成，是四个不同状态。

## 1. 项目与接入入口

AegisAI 是 ICT 大赛命题九、奇安信的 AI 安全知识情报系统。后端使用 Python / FastAPI / Pydantic；数据库为 PostgreSQL + pgvector，SQLAlchemy / Alembic 管理；已有 SQL、向量、关系检索及统一 Tool / Model Gateway。现有前端是原生 JavaScript ESM、History Router 和 Node 同源代理；TypeScript 文件是协作契约与 Client，不能据此认为现有页面已改为 React / Vue。Dify 不在运行链路中。

本机：后端 `http://127.0.0.1:8000`，现有七页入口 `http://127.0.0.1:8769/dashboard`。`127.0.0.1` 指使用者自己的电脑；队友需要完整项目在本机启动或另外取得已授权的可访问环境。此轮没有公网部署。

- 当前公共调查类型：[investigation-http.d.ts](frontend-contracts/investigation-http.d.ts)。
- 当前公共 Client：[investigation-client.ts](frontend-contracts/investigation-client.ts)。两个文件放在同一目录即可接入队友项目；源文件为 `frontend/contracts/investigations.ts`。
- 当前完整 [OpenAPI](frontend-contracts/openapi.json)、[调查 OpenAPI](frontend-contracts/investigation-http.openapi.json)、[机器接口清单](frontend-contracts/http-apis.json)。
- 旧 34 个操作的响应映射：[http-responses.d.ts](frontend-contracts/http-responses.d.ts)，参数与分页详见 [逐项参考](frontend-contracts/HTTP_API_REFERENCE.md)。
- 调查详细约束见 [Phase 12-B API](PHASE12B_INVESTIGATION_API.md)，实际联调结论见 [Phase 12-C结果](../PHASE_12C_RESULT.md)。

调查操作使用严格 Pydantic 公共响应；原 34 个操作的 OpenAPI 已有描述，但运行时仍保持兼容序列化，标为 `LEGACY_DESCRIPTION_ONLY`。OpenAPI 非空不代表旧响应已全部经过严格校验。

## 2. 七个页面与当前数据来源

| 页面/现有路由 | 可调用能力 | 当前边界 |
|---|---|---|
| 情报总览 `/dashboard` | `/health`、资产 overview、漏洞及复核列表 total | 不是全局趋势统计；缺失的时序图不可随机补值 |
| 漏洞中心 `/vulnerabilities` | 漏洞列表、筛选、分页 | `q` 搜索 canonical_id；不要假定支持全文语义搜索 |
| 漏洞详情 `/vulnerabilities/{id}` | 聚合详情、Claim / Evidence / POC / Patch / Timeline 子资源 | 候选 POC 不等于有效利用；来源文字按不可信文本显示 |
| 资产风险 `/assets` | owner 范围内的资产、风险快照、变更 | 真实资产 UUID 必须来自已授权库存；专业 Risk Artifact 在调查 artifacts.analysis 中 |
| 证据复核 `/reviews` | 列表、详情、Evidence、Claim 关系 | resolve 后端已有；当前 8769 代理仍阻止该写操作 |
| 智能调查 `/assistant` | 新调查八操作与旧 assistant 的独立入口 | 现有页仍用旧问答；队友工作台需按新 Client 接线，不能把旧 answer 字符串当成 AnswerEnvelope |
| 系统状态 `/system` | health、sources、sync-runs | 不提供 CPU / 内存 / 实时模型遥测；planned 源不代表已接入 |

## 3. 真实 HTTP 清单

`AVAILABLE` 表示代码中已实现；实际调用还需服务在线、身份与正确 Origin。`PROXY_BLOCKED` 表示后端已有，当前 8769 不放行，不是 API_NOT_EXPOSED。现有代理可接 35 个操作，另 7 个旧写操作受限。

| 方法 | 真实路径 | 响应类型 | 8769代理 |
|---|---|---|---|
| GET | `/health` | `Health` | AVAILABLE |
| GET | `/api/v1/sources` | `SourcesResponse` | AVAILABLE |
| GET | `/api/v1/sync-runs` | `SyncRunsResponse` | AVAILABLE |
| GET | `/api/v1/vulnerabilities` | `VulnerabilityListResponse` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}` | `VulnerabilityDetail` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/enrichment` | `EnrichedPage<EnrichmentJob>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/claims` | `EnrichedPage<ClaimRow>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/evidence` | `EnrichedPage<EvidenceRow>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/pocs` | `EnrichedPage<PocCandidate>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/patches` | `EnrichedPage<PatchCandidate>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/timeline` | `EnrichedPage<IntelligenceEvent>` | AVAILABLE |
| GET | `/api/v1/evidence/{id}` | `EvidenceRow` | AVAILABLE |
| GET | `/api/v1/reviews` | `Page<ReviewRow>` | AVAILABLE |
| GET | `/api/v1/reviews/{id}` | `ReviewDetail` | AVAILABLE |
| POST | `/api/v1/reviews/{id}/resolve` | `AuditRow` | PROXY_BLOCKED |
| GET | `/api/v1/assets` | `Page<AssetRow>` | AVAILABLE |
| POST | `/api/v1/assets` | `AssetRow` | PROXY_BLOCKED |
| GET | `/api/v1/assets/overview` | `AssetOverview` | AVAILABLE |
| GET | `/api/v1/assets/{id}` | `AssetDetail` | AVAILABLE |
| POST | `/api/v1/assets/{id}/components` | `ComponentRow` | PROXY_BLOCKED |
| PATCH | `/api/v1/assets/{id}/components/{component_id}` | `ComponentRow` | PROXY_BLOCKED |
| POST | `/api/v1/assets/{id}/sbom` | `SbomImportResponse` | PROXY_BLOCKED |
| GET | `/api/v1/assets/{id}/risks` | `AssetRisksResponse` | AVAILABLE |
| GET | `/api/v1/assets/{id}/risks/{snapshot_id}` | `HistoricalAssetRisk` | AVAILABLE |
| POST | `/api/v1/assets/{id}/recompute` | `{items: LegacyAssetRiskPayload[]}` | PROXY_BLOCKED |
| GET | `/api/v1/assets/{id}/risk-changes` | `RiskChangeResponse` | AVAILABLE |
| GET | `/api/v1/assets/{id}/inventory-history` | `InventoryHistoryResponse` | AVAILABLE |
| GET | `/api/v1/assets/{id}/reviews` | `Page<ReviewDetail>` | AVAILABLE |
| POST | `/api/v1/assistant/query` | `LegacyAssistantRun` | AVAILABLE |
| GET | `/api/v1/assistant/runs/{id}` | `LegacyAssistantRun` | AVAILABLE |
| GET | `/api/v1/assistant/runs/{id}/tasks` | `{items: LegacyTaskRun[]}` | AVAILABLE |
| GET | `/api/v1/assistant/runs/{id}/trace` | `LegacyAssistantTrace` | AVAILABLE |
| GET | `/api/v1/tools/contracts` | `ToolContractsResponse` | AVAILABLE |
| POST | `/api/v1/tools/{name}` | `ToolEnvelope` | PROXY_BLOCKED |
| POST | `/api/investigations` | `InvestigationCreateResponse` | AVAILABLE |
| GET | `/api/investigations/history` | `HistoryResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/status` | `InvestigationStatusResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/trace` | `TraceResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/artifacts` | `ArtifactResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/integration` | `IntegrationResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/answer` | `AnswerResponse` | AVAILABLE |
| POST | `/api/investigations/{id}/cancel` | `InvestigationStatusResponse` | AVAILABLE |


新调查的八操作均使用服务端主体授权。旧资产/assistant/tools 使用资产令牌，复核写接口使用复核令牌；完整权限逐项见机器清单。`/client-config` 属于 Node 代理，不计入 FastAPI 操作。

## 4. 浏览器、鉴权与模型配置

8769 同源模式可用 `new InvestigationApiClient()`；启用本地演示时 Node 从服务器进程注入短期访问令牌，浏览器没有模型 Key。自建 5173 前端直接连 8000 时，使用 `new InvestigationApiClient('http://127.0.0.1:8000', tokenCallback)`，只从获授权的运行时会话取 Bearer。

`AEGIS_CORS_ORIGINS` 默认显式允许 localhost / 127.0.0.1 的 5173、8769；不能用 `*`，CORS 本身不提供身份。8769 的 CSP 限制同源连接，不能在这个已有页面直接跨端口绕过代理。代理创建/取消要求同源 Origin 和 JSON；转发必要的 Content-Type、Idempotency-Key、Authorization。代理响应超时为 30 秒，创建返回后后台调查继续执行，不让浏览器保持 300 秒长请求。

当前认证是本地服务端令牌及主体，尚无生产多用户登录。不要在前端源码、构建环境变量、localStorage、Mock、截图或交接 JSON 放服务器令牌、模型 API Key、数据库密码。`/docs`、`/redoc`、`/openapi.json` 在后端，当前代理没有相应文档入口，可用离线导出。

模型配置全部由后端 ModelConfig.from_env 读取，`.env.example` 不会自动加载。兼容远程/国产服务需明确 `MODEL_PROVIDER=openai_compatible`、实际 MODEL_NAME、HTTPS MODEL_API_BASE、服务器端 MODEL_API_KEY；本地兼容服务可显式使用 loopback HTTP 和 MODEL_ALLOW_KEYLESS_LOCAL。本机已安装 Ollama/Qwen 7B并通过原Gateway实际调用；其他远程供应商未实测。具体成功/失败范围以 docs/MODEL_PROVIDER_TEST.md 的当次记录为准，不把接口格式测试当安全准确率。

## 5. InvestigationRequest：公共提交协议

浏览器优先使用公共 `InvestigationCreateRequest`；Python 内部 `InvestigationRequest.planner_input` 仍接受用于兼容，但不可混合两种格式。

```json
{
  "user_query": "torch 2.5.1 是否受到 CVE-2025-32434 影响？请给出补丁与证据，保留未知。",
  "asset_scope": {
    "target": "CVE-2025-32434",
    "component": {"name":"torch","ecosystem":"PyPI","package_name":"torch","version":"2.5.1"}
  },
  "options": {"mode":"deep","realtime":false}
}
```

这是固定真实来源**请求**，不是标准答案或成功响应。2.5.1 是查询条件，不是预认定影响结论；没有假定库存 asset_id。没有任何自动填写 Ground Truth。

| 字段 | 类型/约束 |
|---|---|
| user_query | string，1–2000 字符 |
| asset_scope | object，可省略；target 为合法 CVE 或漏洞 UUID |
| asset_scope.asset_id / component_id / snapshot_id | UUID string 或 null；由后端核对主体和引用绑定 |
| asset_scope.component | ResolutionInput 或 null：name，ecosystem?，package_name?，version?，purl? |
| options | mode=auto/fast/deep；realtime=false；time_scope 可空；timeout_seconds=1–300，默认300；objective_profile 可空 |
| idempotency_key | 可空 string，1–150 字符；与请求头二选一；不能只传空白 |

提交时必须提供 `Idempotency-Key` 或 body.idempotency_key，两者同时存在必须相同。相同主体/键/语义内容复用同一根调查，返回 reused=true 和当前状态；同键不同内容返回409。网络失败或确认超时保留同键重试，用户主动发起新调查才换键。

HTTP202 表示根记录已存储，不表示调查已成功；CreateResponse 包含 investigation_id、status、current_stage、overall_status、revision、reused、model_provider、is_mock，完整字段见类型文件。当前默认 Mock 没有 PlannerPlan，普通提交实际到 PLANNING_FAILED；禁止靠前端或假数据补成成功。

## 6. InvestigationStatus 与刷新

- Stage / status / current_stage：CREATED、PLANNING、INVESTIGATING、VERIFYING、ANALYZING、INTEGRATING、COMPOSING、COMPLETED、WAITING_REVIEW、FAILED、CANCELLED。
- Overall：RUNNING、SUCCEEDED、SUCCEEDED_WITH_WARNINGS、INCOMPLETE、REVIEW_REQUIRED、FAILED、CANCELLED。
- 普通刷新每 1–2 秒读 status，隐藏标签页暂停；revision 改变时再读 trace / artifacts。终态停止常规轮询。
- `cancel_requested=true` 只表示协作取消已请求；等待 overall_status=CANCELLED。终态 cancel 返回现状，不逆转已完成任务。
- `recovery_required=true` 表示重启后的孤立任务需处理；前端不能宣称自动恢复。浏览器检查超时不等于调查终止，不应悄悄取消。
- 当前最多两个进程内调查工作线程，没有分布式持久队列、SSE、WebSocket 或实时百分比进度。

## 7. Agent Run / Task Run / Trace

新 TraceResponse.planner 是实际规划审计摘要，含 planner_run_id、validation_status、retry_count、prompt_version、task_ids；不是模型思考链。

agent_runs 至多三个专业 Runtime 摘要，含 run_id、status、artifact_references、task_statuses 与 tool_calls。工具摘要只有 record_id、task_id、tool、status、duration_ms、evidence_ids。阶段展示使用 stages 的 agent / stage / status / time / run_id / artifact_ids；事件没发生时不虚构时间或节点。

这里的 task_statuses 是 task_id→status 映射，没有另一个新的全量 Task Run HTTP 接口。旧 `/assistant/runs/{id}/tasks` 与旧 trace 只服务旧协议，不可拿新根 ID 调用。内部 Runtime Task Contract、Agent Contract、完整提示和工具参数不公开。

## 8. Investigation / Verification / Risk Artifact

ArtifactResponse.investigation / verification / analysis 均可为 null；缺失通常表示尚未产出、没有执行或阶段失败，不等于零风险。公共投影移除了私有模型/工具原始调用、receipt、上下文 hash 控制字段；历史 hash 指向原始快照，不是浏览器投影的新 hash。

Investigation Artifact 保存发现信息，包括范围、版本匹配、CVSS/CWE、候选 POC、补丁候选、证据与不确定。候选发现不等于确认；Verification Artifact 新增 Claim–Evidence 判断，不覆盖调查原始数据。Verification 状态：CONFIRMED、PENDING、CONFLICT、INSUFFICIENT_EVIDENCE、REJECTED。

Risk Artifact 包含 asset_match_status、version_match_status、affected、risk_level、priority、risk_factors、mitigating_factors、recommended_actions、evidence_refs 和不确定项；未知值必须保留。专业风险结果与旧资产风险快照是不同协议，禁止靠 CVSS 直接补资产影响。

## 9. IntegrationResult 与 AnswerEnvelope

IntegrationResponse 保留 Gate 原状态 PASS、PASS_WITH_WARNINGS、REPLAN_REQUIRED、HUMAN_REVIEW_REQUIRED、FAILED。blocking_issues、replan_reasons、human_review_reasons、coverage 和真实 Artifact 引用用于展示验收依据；前端不得把需要重规划或人审渲染成安全结论。

AnswerResponse 是已保存 AnswerEnvelope 的公共副本，读取不调用模型。使用真实字段 summary、key_findings、risk_assessment、recommended_actions、verified_claims、disputed_claims、citations、evidence_observations、warnings、unresolved_items。

| integration_status | answer_status |
|---|---|
| PASS | COMPLETE |
| PASS_WITH_WARNINGS | COMPLETE_WITH_WARNINGS |
| REPLAN_REQUIRED | INCOMPLETE |
| HUMAN_REVIEW_REQUIRED | REVIEW_REQUIRED |
| FAILED | FAILED |
| 尚未产生 Gate 的失败 / 取消 | FAILED / CANCELLED，integration_status 可空 |

fact_origin 固定 FROZEN_GATE_CONTEXT、explanation_provider 固定 DETERMINISTIC_TEMPLATE、historical_snapshot=true。Answer 不是实时重新检索；若用户要再次调查，需新幂等键。失败 Answer 不提供已确认风险/修复结论。

## 10. Evidence Reference 与 Claim

证据通过 evidence_id / claim_id / source_id / raw_document_id / observation_id、reference URL、hash、时间和 Artifact 引用追溯；不存在万能 source 字段。已确认事实引用 `verified_claims[].evidence_ids`，指向 citations；争议事实另看 disputed_claims 和 evidence_observations，不能混为确认事实。

外部公告、代码、论文、描述与摘录是 UNTRUSTED_EXTERNAL_CONTENT。前端按纯文本显示、核对链接协议、不执行 HTML，不把证据内容当成系统指令。秘密/URL 用户信息/敏感查询参数会经过后端公共投影过滤，但前端仍应处理未知子字段。

## 11. TypeScript 类型映射与 Client

UUID/date-time→string；Literal→字符串联合；tuple/list→数组；可空字段→`T | null`；动态 JSON→unknown 或 JsonValue，不随意断言业务结论。**HTTP 公共类型以 investigation-http.d.ts 为准，旧 internal-output.d.ts 只作为内部定义与历史 fixture 参考。**

```ts
import { InvestigationApiClient, InvestigationApiError } from './investigation-client.js';
const api = new InvestigationApiClient(); // 8769 同源；不同前端需 baseUrl 与获授权 token 回调
const created = await api.create(request, idempotencyKey);
const status = await api.status(created.investigation_id);
// 按 status/revision 刷新；到终态后调用 api.answer / api.integration
```

现有 Client 提供 create、status、trace、artifacts、integration、answer、cancel、history。HTTP 非2xx抛出 InvestigationApiError（status、failure:ApiError）；网络失败、非JSON响应可能是普通 Error。Client 没有自动重试，也没有浏览器运行时 JSON Schema 校验；TypeScript 静态类型不是网络数据验证。本轮用实际 TCP 响应进行了 Pydantic 校验，并用未改动的这个 Client 完成八操作联调。

## 12. 错误、幂等、取消与超时

新调查错误统一为 `{error_code,message,request_id,retryable}`；旧34操作保持各自 detail 格式。关注 X-Request-ID 和 Retry-After，不在页面显示堆栈或密钥。

| HTTP / error_code | 处理 |
|---|---|
| 401 AUTHENTICATION_REQUIRED / 503 AUTHENTICATION_UNAVAILABLE | 检查运行时授权或后端配置 |
| 403 ACCESS_DENIED / 404 INVESTIGATION_NOT_FOUND | 检查范围；404也可能是无权访问 |
| 409 IDEMPOTENCY_CONFLICT | 同键内容改变；修正请求，不自动制造新任务 |
| 409 RESULT_NOT_READY | 仍在执行，按 Retry-After 再查 |
| 409 RESULT_UNAVAILABLE | 终止后未产生此结果，不无限重试 Gate |
| 422 INVALID_REQUEST / 幂等键错误 | 改字段或键；不重试无效请求 |
| 429 INVESTIGATION_BUSY / 503 CREATION_ACK_TIMEOUT | 按退避保留同键；ACK超时不代表未存储 |
| 503 SNAPSHOT_BUSY | revision推进造成暂时读竞争；短暂退避重读 |
| 500 INTERNAL_ERROR | 展示失败并记录 request_id |

PLANNING_FAILED 是调查生命周期业务错误，不等于创建HTTP失败；通常仍202创建、200读FAILED状态、200读失败Answer、409读未产生的Gate。取消是协作式，不能保证中断正在进行的模型/工具调用。

## 13. Mock / 真实来源 / 非Mock模型的区分

| 模式 | 当前事实 | 可以证明什么 |
|---|---|---|
| UI离线 Mock | 交接包 mock/ 历史演示 fixture | 界面字段和状态展示，不能证明在线接口或安全准确率 |
| SYNTHETIC_TEST + 显式测试规划回执 | 专用数据库、实际 Planner/Agent/Tool/Gate、TCP八操作通过 | HTTP和工程业务连接正确；证据与模型回执仍是合成输入 |
| REAL_SOURCE + 当前默认Mock | 固定torch场景真实本机HTTP，PLANNING_FAILED | 服务真实接收问题、失败和契约可读取；不是完整成功演示 |
| 本地REAL Provider | Ollama/Qwen经Gateway实际调用，结果另见本阶段实跑记录 | 按保存的调用身份展示；通过Schema不等于安全准确 |

创建响应的 model_provider / is_mock 反映创建/重用请求时的服务配置，不能用于重新标记历史调查。历史身份以 TraceResponse.model_execution 中已持久化的Planner调用回执为准。该字段为null时显示“模型调用尚未确认”；MOCK/REAL不等于成功/失败。前端切真实模式时清除旧 Mock 数据，真实失败不静默回退为假成功。真实模型和数据来源标签必须分别显示。后续文本模型切换时，独立 Embedding 仍为 Mock 的配置要明确，不能称作所有模型已经真实化。

此轮固定输入不随机；专用测试场景只为数据库隔离生成唯一CVE/UUID绑定，语义条件保持 vLLM0.6.0。合成记录不进入开发库、不当标准答案或正式评测。当前人工 Ground Truth 仍0/49，不生成准确率。

## 14. 当前未开放的能力与接口变更

调查八操作已经可接，没有再标 API_NOT_EXPOSED。仍缺：新的完整 Task Run 明细HTTP、SSE/WebSocket、分布式队列和自动恢复、多用户登录、全局趋势与资源遥测、面向公网的部署适配。参考 [当前缺口](frontend-contracts/API_GAPS.md)。当前7个旧写操作属于 PROXY_BLOCKED，后端接口已经存在。

契约变更须先改真实路由/DTO并经过PR；运行 `python scripts/export_investigation_api.py` 同步两份 OpenAPI/类型/Client，`--check`验证一致。破坏性字段变更先与前端协商，禁止手改类型来掩盖不匹配。每次交接更新MANIFEST及ZIP，历史验证保留时间与范围，不能挪用历史1261项作为本次验收。

## 15. 公共模型真实字段索引

以下名单从当前Pydantic模型提取；嵌套字段类型、是否必填、枚举及限制以随包的OpenAPI和TypeScript文件为准，不新增方便别名。


### InvestigationCreateRequest

`user_query`, `asset_scope`, `options`, `idempotency_key`

### InvestigationCreateResponse

`logical_investigation_id`, `current_stage`, `overall_status`, `planner_run_id`, `investigation_run_id`, `verification_run_id`, `analysis_run_id`, `cancel_requested`, `recovery_required`, `warnings`, `error_code`, `revision`, `updated_at`, `investigation_id`, `status`, `created_at`, `finished_at`, `reused`, `persistence`, `execution_backend`, `model_provider`, `is_mock`

### InvestigationStatusResponse

`logical_investigation_id`, `current_stage`, `overall_status`, `planner_run_id`, `investigation_run_id`, `verification_run_id`, `analysis_run_id`, `cancel_requested`, `recovery_required`, `warnings`, `error_code`, `revision`, `updated_at`, `investigation_id`, `status`, `created_at`, `finished_at`

### TraceResponse

`schema_version`, `logical_investigation_id`, `original_question`, `planner`, `events`, `agent_runs`, `integration_result_id`, `integration_status`, `answer_id`, `warnings`, `unresolved_items`, `error_code`, `historical_snapshot`, `investigation_id`, `stages`, `revision`

### ArtifactResponse

`investigation_id`, `revision`, `investigation`, `verification`, `analysis`, `content_trust_level`, `projection_version`

### PublicInvestigationArtifact

`artifact_id`, `task_id`, `agent_id`, `run_id`, `schema_version`, `status`, `runtime_status`, `partial_result`, `information_status`, `vulnerability_id`, `canonical_id`, `description`, `component`, `asset`, `affected_versions`, `fixed_versions`, `version_match`, `cvss`, `cwe`, `poc_candidates`, `patch_information`, `evidence`, `uncertainties`, `conflicts`, `confidence`, `dependency_artifact_ids`, `evidence_storage`, `findings`

### PublicVerificationArtifact

`claims`, `verification_status`, `confidence`, `supporting_evidence`, `conflicting_evidence`, `conflicts`, `warnings`, `unresolved_items`, `partial_result`, `rules_version`, `artifact_id`, `task_id`, `run_id`, `agent_id`, `schema_version`, `source_run_id`, `source_artifact_id`, `evaluation_time`, `execution_status`

### PublicRiskAnalysisArtifact

`verification_status`, `asset_id`, `component`, `version`, `asset_match_status`, `version_match_status`, `asset_match_result`, `version_match_result`, `exploitation_signal`, `patch_availability`, `risk_level`, `priority`, `affected`, `risk_factors`, `mitigating_factors`, `recommended_actions`, `evidence_refs`, `reasoning_summary`, `claim_dispositions`, `confidence`, `confidence_kind`, `warnings`, `unresolved_items`, `rule_ids`, `rules_version`, `priority_details`, `partial_result`, `coverage_complete`, `model_assist_used`, `model_assist_status`, `artifact_id`, `task_id`, `agent_id`, `run_id`, `schema_version`, `input_artifact_ids`, `evaluation_time`, `source_verification_time`, `inventory_revision`, `execution_status`, `historical_snapshot`, `scope_notice`

### IntegrationResponse

`integration_id`, `logical_investigation_id`, `trace_id`, `run_id`, `source_run_ids`, `status`, `objective_coverage`, `task_completion_summary`, `checks`, `passed_checks`, `failed_checks`, `blocking_issues`, `warnings`, `unresolved_items`, `artifact_references`, `evidence_references`, `replan_reasons`, `human_review_reasons`, `final_result_references`, `partial_result_references`, `input_hash`, `objective_hash`, `policy_version`, `created_at`, `evaluation_time`, `historical_snapshot`, `persistence`

### AnswerResponse

`schema_version`, `answer_id`, `logical_investigation_id`, `original_question`, `answer_status`, `integration_status`, `summary`, `key_findings`, `affected_assets`, `risk_assessment`, `recommended_actions`, `verified_claims`, `disputed_claims`, `citations`, `evidence_observations`, `evidence_references`, `warnings`, `unresolved_items`, `integration_result_id`, `agent_run_references`, `accepted_source_run_references`, `trace_reference`, `generated_at`, `historical_snapshot`, `fact_origin`, `explanation_provider`

### HistoryResponse

`items`, `total`, `offset`, `limit`, `sort`, `status_filter`

### ApiError

`error_code`, `message`, `request_id`, `retryable`

## Phase 12-D 可选模型执行元数据

GET /api/investigations/{id}/trace 的 model_execution 是可选且可为null的公共字段；其对象包含 execution_mode（MOCK/REAL）、provider、model（保存回执中的实际返回模型名）、source=PERSISTED_PLANNER_CALL、attempt_count（1–2）。不含模型地址、Key、原始输出或Prompt。服务重启/切换模型不改变历史标签，未知旧值须显示未知，不回填。

AnswerEnvelope仍由确定性模板生成；重复读取不请求模型，Verification/Risk/Gate仍由既有规则决定。文本模型REAL与独立Embedding Mock必须分别标识；浏览器只访问AegisAI API，不访问模型端口11434。

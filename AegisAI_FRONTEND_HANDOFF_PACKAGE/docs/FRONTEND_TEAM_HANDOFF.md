# AegisAI 前端团队完整交接

**独立交接包，沿用已审查的 Phase 12-A.5 契约。Phase 12-B 仍待实施；本包未开发新 API。**

阅读入口：[README](../README.md) → [快速入门](FRONTEND_QUICK_START.md) → [UI 需求](UI_REQUIREMENTS.md)。原项目源码位置只用于定位，源码没有随包附带。最新 Phase 12-B 提案为 8 个操作，见第 6 节；早期 9 项草案不作为当前可调用协议。

审查日期：2026-10-10。基线：Phase 11-D。范围：现有接口、内部协议、前端对接与 Phase 12 最小适配建议。本次不新增接口、不修改业务代码、不启动数据库或服务。

**最重要的结论：后端现有 33 条路径、34 个 HTTP 操作；Phase 11-D 的 Investigation Orchestrator 没有 HTTP 路由。旧版 /assistant/query 不能替代 Phase 11-D。**

历史工程验收 1261 项通过来自 work/orchestration/full_suite_final.json，exit_code=0、failed=0、errors=0、skipped=0。本次未重跑该套测试，未进行在线 HTTP 抓包。源码中存在接口不代表服务此刻在线。

## 1. 契约状态与证据

| 标签 | 含义 |
|---|---|
| AVAILABLE | 现有 HTTP 已实现，在正确同源/鉴权条件下可调用；代理是否放行另列 |
| API_NOT_EXPOSED | 只有 Python 内部能力，或所需 HTTP 接口未实现 |
| MOCK_ONLY | 仅用于 DEMO/MOCK 演示或类型校验，不能作为生产业务数据 |
| REAL_CODE_EXECUTION_SYNTHETIC_SEED | 历史真实代码执行产生的测试回执，输入是合成测试数据 |
| MOCK_SCHEMA_VALIDATED | 仅按当前 Pydantic 约束验证的模拟对象，没有业务执行或 HTTP 返回 |

AVAILABLE / API_NOT_EXPOSED / MOCK_ONLY 为主状态。PROXY_BLOCKED 是独立的浏览器传输限制，PROPOSED 是尚未实现的建议标记；二者不是新增业务状态。**AVAILABLE 不表示已经完成页面接入或服务当前在线；7 个 PROXY_BLOCKED 的现有 HTTP 操作不能从当前8769页面直接提交。**

- [逐项 HTTP API 参考](../api/reference/HTTP_API_REFERENCE.md)：每项列 URL、Method、参数/Body、响应类型、状态码、错误、权限和 MOCK 请求示例。
- [机器可读 API 清单](../api/reference/http-apis.json)：只列当前真实34个操作，所有建议路由单独列在 API_NOT_EXPOSED.md。
- [Phase 11-D 缺口](../api/API_NOT_EXPOSED.md)。
- [TypeScript 契约入口](../contracts/README.md)。
- [OpenAPI](../api/reference/openapi.json)：当前后端原样导出。
- [接口与字段校验结果](../VALIDATION.json)：本次实际检查，不是历史1261全量测试重跑。

主要事实来源：

- backend/app/main.py：只挂载 routes、enrichment、assets、assistant、tools 五组 Router。
- backend/app/api/{routes,enrichment,assets,assistant,tools}.py：真实 HTTP 参数、错误、返回路径。
- backend/app/repositories/queries.py、enrichment/queries.py、assets/queries.py：列表、聚合、字段和状态转换。
- backend/app/assistant/{service,storage,contracts,orchestrator}.py：旧版问答、任务和 Trace。
- backend/app/orchestration/{service,contracts,answer_contracts,trace,store,reader,composer}.py：Phase 11-D 内部总控与交付。
- backend/app/integration/contracts.py：IntegrationResult。
- backend/app/agents/{investigation,verification,analysis}/schemas.py：三个专业 Artifact。
- backend/app/runtime/contracts.py、agents/contracts.py：Task / Agent Trace。
- frontend/public/modules/{router,services,state}.js、pages/*.js、frontend/server.mjs：真实页面与浏览器约束。

本包的 openapi.json 应直接来自 app.openapi()，不启动 lifespan、不连接数据库、不插入建议路由。所有 34 个操作均未声明 response_model，成功响应 Schema 为 `{}`。这意味着 OpenAPI 能准确说明路径与已声明请求参数，但不能自动提供准确的业务响应类型。手工响应映射独立放在 http-responses.d.ts，必须结合序列化函数审查。[FastAPI response_model 说明](https://fastapi.tiangolo.com/tutorial/response-model/)。

## 2. 项目简介与前端技术约束

AegisAI 已具备安全情报引擎、Tool/Model Gateway、混合检索、受约束 Planner、DAG Runtime、调查/核验/风险分析专业 Agent、Integration Gate 与冻结 AnswerEnvelope。能力实现与浏览器 HTTP 暴露分别交接，现有业务不在本轮重写。

前端只通过 HTTP API 读取和提交业务，不直接访问数据库、不直接调用模型或内部 Python 服务、不保存 API Key。任何新增字段适配、认证、后台领取或路由均留到 Phase 12-B。

### 提示词示意字段与真实协议的差异

以下名称仅来自任务提示中的概念示意，**不是当前 wire 字段**；本包不添加便利别名或静默转换。

| 概念/示意字段 | 当前真实字段或限制 |
|---|---|
| InvestigationRequest.query | planner_input.query |
| asset_scope | BACKEND_REQUIRED：没有该顶层对象；当前 query.asset_id、planner_input.component_id、time_scope 分别描述范围 |
| options | investigation_options |
| investigation_id / stage / status | logical_investigation_id / current_stage / overall_status |
| AgentTrace.agent / task / timestamp | 当前 AgentTrace 是 run_id / task_statuses / tool_calls；事件时间在 StageEvent.at，任务时间在 TaskTrace.start_time/end_time |
| EvidenceReference.source | source_id、raw_document_id、observation_id；没有单一 source 字段 |
| IntegrationResult.blockers | blocking_issues |
| AnswerEnvelope.findings / risk / evidence / recommendations | key_findings / risk_assessment / citations与evidence_observations / recommended_actions |
| AnswerEnvelope.status="PASS" | 错误协议：PASS 是 integration_status；answer_status 为 COMPLETE等 |

对后端 list[dict]/Any 未限定的子字段标为 UNKNOWN，并在 TypeScript 使用 unknown/Record<string,unknown>。新增公共错误 Envelope、统一资产范围、全局趋势指标等未实现部分标 BACKEND_REQUIRED；不靠前端补造字段。

### 技术栈与运行边界

| 层 | 实际实现 |
|---|---|
| Backend | Python 3.12；FastAPI 0.142.2；Pydantic 2.13.5；Uvicorn 0.54.0 |
| Database | PostgreSQL + pgvector；SQLAlchemy 2.0.54；psycopg 3.3.6；Alembic 1.20.0 |
| Retrieval / Model | SQL / Vector / Relation；fastembed 0.8.1；onnxruntime 1.30.0；统一 Model Gateway |
| Frontend | 原生 JavaScript ESM、浏览器 History Router、Node HTTP 代理；当前不是 React / Vue / TypeScript 项目 |
| 配置 | 当前本地 frontend 127.0.0.1:8769 → backend 127.0.0.1:8000 |
| Prototype | 8768 上的 prototype 是静态 Mock 设计稿；其 hash 路由不等同于真实 API 前端 |
| Dify | 不在当前运行入口中；本交接无 Dify 配置要求 |

真实前端仅代理 /health 和 /api/v1/。OpenAPI 默认在后端 /openapi.json，文档页面 /docs、/redoc；当前前端代理不代理这些地址。可离线使用本包的 openapi.json。

浏览器约束：

1. 代理仅接受本地 localhost / 127.0.0.1 Host，尚不支持云端域名访问。
2. 仅允许 GET、HEAD、POST；POST 只放行 /api/v1/assistant/query。其他 POST 和全部 PATCH 被 405 拒绝。
3. 问答 POST 要求同源 Origin 和 application/json。代理请求体上限 2 MiB，上游超时 30 秒。
4. 代理转发 Accept、Authorization，问答 POST 转发 Content-Type；不转发任意业务 Header。SBOM 的 x-request-key 也需 Phase 12 单独适配。
5. CSP 的 connect-src 为 'self'，后端没有 CORS middleware。前端不要默认跨端口直接 fetch 后端。
6. /client-config 是 Node 前端提供的 GET，返回 {localDemoAccess:boolean}，不是 FastAPI API。
7. AEGIS_LOCAL_DEMO=1 时，Node 从服务器环境注入资产令牌，仅覆盖 assets 与 assistant；浏览器不收到令牌。当前手输令牌仅在会话内存保存。此方案是本地演示权限，不是生产多用户登录系统。

不得把 API Key、数据库连接密码或服务器令牌写入代码、Mock、交接包或浏览器存储。文档只列环境变量名称，不列值。

## 3. 七个页面及数据来源

| 页面 | 真实前端路由 | 已有调用与用途 | API状态与接入边界 |
|---|---|---|---|
| 情报总览 | /dashboard | /health、assets/overview、vulnerabilities、reviews | AVAILABLE：资产概况与两个列表total；全局趋势为 BACKEND_REQUIRED |
| 漏洞中心 | /vulnerabilities | GET vulnerabilities | AVAILABLE：分页、来源及AI筛选；q只搜索canonical_id |
| 漏洞详情 | /vulnerabilities/{id} | 聚合详情及 Evidence 读取；六种分页子资源可复用 | AVAILABLE：来源断言、Claim、候选POC/Patch、冲突与证据 |
| 资产风险 | /assets | assets、overview、/{id}/risks | AVAILABLE：owner约束的风险快照；专业Risk Artifact为API_NOT_EXPOSED |
| 证据复核 | /reviews | GET reviews，详情 API 已有 | AVAILABLE：读取；resolve为现有HTTP但PROXY_BLOCKED |
| 智能调查（现有问答页） | /assistant | POST assistant/query；GET run/tasks/trace | 旧版问答AVAILABLE；Phase 11-D为API_NOT_EXPOSED |
| 系统状态 | /system | /health、/sources | AVAILABLE：数据源/同步状态；CPU/内存/模型遥测为BACKEND_REQUIRED |

无需重新开发七个页面才能开始数据接入。应先复用 services.js，单独增加 Phase 11-D 的 UI 数据适配，避免把旧版 result.answer 字符串当作 AnswerEnvelope。

## 4. 真实 HTTP API 清单

本节每条均为 AVAILABLE（现有HTTP），但标 PROXY_BLOCKED 的行不能从当前8769页面直接提交。完整逐项错误/示例参见 [HTTP_API_REFERENCE.md](../api/reference/HTTP_API_REFERENCE.md)。

下表路径统一以 /api/v1 为前缀，/health 除外。A=资产/问答/工具令牌；R=复核写令牌。写接口同时标明当前代理限制。所有未特别说明的成功码为 200。

| Method | 路径 | 输入 | 返回 | 鉴权/约束 |
|---|---|---|---|---|
| GET | /health | 无 | Health | 数据库不可用为 503，仍返回 Health 字段 |
| GET | /sources | 无 | SourcesResponse | 无；包含 planned/deferred 等状态，不表示所有源已接入 |
| GET | /sync-runs | source?、offset、limit | Page<SyncRun> | source 仅 CVE_LIST / OSV / CISA_KEV |
| GET | /vulnerabilities | q?、source?、ai_relevance?、offset、limit、sort | VulnerabilityListResponse | q≤150；sort 默认 modified_desc |
| GET | /vulnerabilities/{id} | CVE canonical_id 或 UUID 字符串 | VulnerabilityDetail | 找不到为 404 |
| GET | /vulnerabilities/{id}/enrichment | offset、limit | EnrichedPage<EnrichmentJob> | 未知漏洞 404 |
| GET | /vulnerabilities/{id}/claims | offset、limit | EnrichedPage<ClaimRow> | Claim 状态转为大写 API 状态 |
| GET | /vulnerabilities/{id}/evidence | offset、limit | EnrichedPage<EvidenceRow> | 带 claim_verification_status、source_key |
| GET | /vulnerabilities/{id}/pocs | offset、limit | EnrichedPage<PocCandidate> | 候选项状态为小写 |
| GET | /vulnerabilities/{id}/patches | offset、limit | EnrichedPage<PatchCandidate> | 候选项状态为小写 |
| GET | /vulnerabilities/{id}/timeline | offset、limit | EnrichedPage<IntelligenceEvent> | 外部内容按不可信数据处理 |
| GET | /evidence/{id} | UUID | EvidenceRow | 非 UUID 422；未知 404 |
| GET | /reviews | status?、offset、limit | Page<ReviewRow> | 排除 ASSET_MATCH_REVIEW |
| GET | /reviews/{id} | UUID | ReviewDetail | ASSET_MATCH_REVIEW 也返回 404 |
| POST | /reviews/{id}/resolve | Decision | AuditLog | R；PROXY_BLOCKED；409/422 |
| GET | /assets | offset、limit | Page<AssetRow> | A；只看当前服务器 principal 的未删除资产 |
| GET | /assets/overview | 无 | AssetOverview | A；聚合计数口径见下文 |
| POST | /assets | NewAsset | AssetRow，201 | A；PROXY_BLOCKED；request_key |
| GET | /assets/{id} | UUID | AssetDetail | A；未拥有或不存在 404 |
| POST | /assets/{id}/components | NewComponent | ComponentRow，201 | A；PROXY_BLOCKED |
| PATCH | /assets/{id}/components/{component_id} | UpdateVersion | ComponentRow | A；PROXY_BLOCKED；版本修订冲突 409 |
| POST | /assets/{id}/sbom | 原始 JSON 字节；x-request-key Header | SbomImportResponse | A；PROXY_BLOCKED；2 MiB；不是 multipart |
| GET | /assets/{id}/risks | offset、limit | AssetRisksResponse | A；GET 只读，不重算 |
| GET | /assets/{id}/risks/{snapshot_id} | 两个 UUID | HistoricalAssetRisk | A；historical=true |
| POST | /assets/{id}/recompute | 无 Body | {items:风险 payload[]} | A；PROXY_BLOCKED；无 HTTP request_key |
| GET | /assets/{id}/risk-changes | offset、limit | Page<AssetRiskChange> | A |
| GET | /assets/{id}/inventory-history | offset、limit | Page<InventoryHistoryItem> | A；去掉完整 SBOM document |
| GET | /assets/{id}/reviews | offset、limit | Page<ReviewDetail> | A；仅当前资产及 principal 的 ASSET_MATCH_REVIEW |
| POST | /assistant/query | QueryRequest | LegacyAssistantRun，202 | A；唯一当前代理可提交的业务 POST |
| GET | /assistant/runs/{id} | UUID | LegacyAssistantRun | A；不存在或不属于 actor 为 404 |
| GET | /assistant/runs/{id}/tasks | UUID | {items:LegacyTaskRun[]} | A；旧协议 |
| GET | /assistant/runs/{id}/trace | UUID | LegacyAssistantTrace | A；旧协议 |
| GET | /tools/contracts | 无 | ToolContractsResponse | A；37 个注册工具及真实 input_schema |
| POST | /tools/{name} | 该工具的 input_schema JSON | ToolEnvelope | A；PROXY_BLOCKED；仅 READ_ONLY 且 refresh 不为真 |

分页共同约束：offset 为整数≥0，默认 0；limit 为整数 1..100，默认 20。返回 {items,total,offset,limit}。/sources 的返回没有 offset/limit；不要强行套用分页协议。

鉴权实际实现：

- A 对应 AEGIS_ASSET_TOKEN；未配置 503、Bearer 无效或缺失 401。actor 由服务器 AEGIS_ASSET_OWNER 提供，默认 local-analyst，不能由 Body 伪造。
- R 对应 AEGIS_REVIEW_TOKEN；未配置 503、无效 401。AEGIS_REVIEW_ACTOR 提供操作者。
- OpenAPI 将 authorization 描述为可选 Header，没有标准 securitySchemes Bearer 定义；运行时鉴权要求以上表为准。
- /tools/contracts 列出 READ_ONLY、WRITE、REVIEW_ACTION 工具，并不代表外部入口有这些写权限。未知工具 404；WRITE / REVIEW_ACTION / refresh=true 被 403 拒绝。

不存在 /vulnerabilities/{id}/conflicts、/epss、/verification_results、/reviews 等独立分页 URL。这些数组只在现有漏洞详情聚合中。没有 GET /claims/{id}，可通过漏洞详情 Claim 数组或内部工具读取关联。

## 5. 现有 HTTP 请求与响应 Schema

### 5.1 QueryRequest：旧问答提交

~~~typescript
type QueryRequest = {
  question: string;           // 必填 1..2000
  request_key: string;        // 必填 1..150
  asset_id?: string | null;   // UUID
  target?: string | null;     // CVE-年份-≥4位编号 或 UUID；最大80
  mode?: "auto" | "fast" | "deep"; // 默认auto
  realtime?: boolean;         // 默认false，服务器策略仍可拒绝
};
~~~

禁止额外字段。target 不能填任意组件名称；当前 UI 的“目标组件”提示超出后端约束。组件信息应在问题中说明，或等待 Phase 11-D 的结构化 PlannerInput 接口适配。

POST /assistant/query 返回 202 的运行摘要：
run_id、trace_id、status、route|null、result|null、warnings[]、started_at、finished_at|null、duration_ms|null。这不是 InvestigationStatus。

旧 result 完整分支包含 route、plan、artifacts、gate{status,reason}、answer:string、facts、asset_candidates、narrative_candidates、related_vulnerabilities、related_assets、evidence_refs、warnings、unresolved、capability、coverage、human_reviews。失败分支只保证 answer、warnings、evidence_refs；客户端要按字段是否存在处理。

旧运行 UI 状态为 PLANNING / RUNNING / WAITING_TOOL / VERIFYING / REPLANNING / WAITING_REVIEW / COMPLETED / FAILED。旧 TaskRun 为 pending / running / success / partial / failed / blocked。旧 Trace 的 ToolCall 状态是 succeeded / partial / failed / timeout / cancelled。不可统一转换成 Phase 11-D 枚举。

### 5.2 资产写请求

| 模型 | 必填字段 | 默认及可选字段 |
|---|---|---|
| NewAsset | name(1..200)、request_key(1..150) | asset_type=service；environment/exposure=unknown；description|null≤2000；is_demo=false |
| NewComponent | name(1..300)、request_key(1..150) | package_name|null≤300；package_identifier_id UUID|null；ecosystem|null≤40；namespace=""≤200；purl|null≤2000；version|null≤200；source_ref|null≤1000 |
| UpdateVersion | expected_revision 整数≥1、request_key(1..150) | version|null≤200；默认 null，会清除版本，不等同于“保持原值” |

asset_type：service / training / application / project / server / container。
environment：production / staging / development / unknown。
exposure：internet / internal / development / unknown。

SBOM：只支持 CycloneDX 1.6 JSON 或 SPDX 2.3 JSON；最大 2 MiB，最多 1000 个解析组件；拒绝重复 JSON key、非有限数字及远程 Schema 引用。OpenAPI 当前没有 SBOM requestBody Schema，需要参考 backend/app/resources/sbom 中实际官方 Schema。x-request-key 必填。响应为 format、sha256、added/updated/removed 计数、added_ids/updated_ids/removed_ids、component_count、content_trust_level。

### 5.3 Decision：人工复核提交

必填：expected_revision≥1、expected_claim_revision≥1、request_key(1..150)、status、reason(1..2000)、evidence_ids:UUID[]（最多100，可为空）；value:object|null 可选。

status：CONFIRMED / CONFLICT / INSUFFICIENT_EVIDENCE / PENDING / REJECTED / DEFERRED。DEFERRED 将 ReviewTask 置为 deferred，不是新增第六个 VerificationStatus。提交返回 AuditLog，不返回整个 ReviewDetail；成功后重新读取详情。

### 5.4 查询 DTO 字段与口径

VulnerabilityListItem：
id、canonical_id、title、description|null、published_at|null、modified_at|null、status、primary_severity、revision、deleted_at|null、created_at、updated_at。列表不返回 metadata；新增相应列表展示字段不能靠前端猜测。

status：published / withdrawn / rejected / unknown。
primary_severity：critical / high / medium / low / info / unknown。
列表额外 data_status = "source assertions; not verified intelligence"，coverage 为限定覆盖说明。

VulnerabilityDetail 在完整 Vulnerability 行（含 metadata）上增加：
source_variants、source_documents、external_identifiers、affected_versions、cvss_assessments、products、cwe、references、ai_relevance、known_exploitation；再合并 enrichment、claims、evidence、pocs、patches、timeline、epss、conflicts、verification_results、reviews。

关键字段：

- affected_versions 含 introduced/fixed/last_affected/limit_version 可空，raw_expression、events/explicit_versions、parse_status、scope_key、branch、source_key、is_current 等；不能仅凭 raw_expression 字符串推断确定影响。
- cvss_assessments 含 version、vector|null、base_score:number、severity、provider、assessment_kind、scope_key、source_key、is_current。
- Claim 含 id、claim_type、predicate、value_json、scope_key、branch、verification_status、adopted、revision，以及各关联实体 UUID。
- Evidence 含 id、claim_id、source_id、raw_document_id、observation_id、scope_key、stance、excerpt、excerpt_hash、source_url、published_at|null、retrieved_at、locator、locator_key、observed_value|null、publisher、lineage_key、claim_verification_status、source_key。
- ReviewDetail 在 ReviewTask 行上增加 claim、evidence[]、audit[]。通用复核列表没有这些展开字段。
- source_documents 去掉 raw_payload、parsed_payload、metadata，保留哈希、来源、定位信息及 untrusted=true。禁止为前端补出原始字节。
- 详情顶层 verification_status 固定为小写 pending，是历史聚合字段；具体 Claim 与 VerificationResult 的 API 状态才映射为大写。
- 富化数组每项增加 content_trust_level=UNTRUSTED_EXTERNAL_CONTENT。POC / Patch 的 candidate/confirmed/rejected/unknown 保持小写；POC 的 usability_status 也不要与专业 Artifact 的 NOT_EVALUATED 混用。

AssetOverview：
assets、components、affected_components、critical_high、confirmed_poc、kev、patch_available、uncertain_matches、not_evaluated_components、is_demo_inventory_included、counts_unit。

affected_components 按组件去重；critical_high、confirmed_poc、kev、patch_available 按“漏洞-组件对”计数。它们不是相同分母，不应直接绘成同一饼图。

当前 AssetRisksResponse 的 item 是 Phase 8 风险 payload：
资产/组件/版本、vulnerability_id/canonical_id、severity、match_status、verification_status、priority、kev、poc、epss、remediation、match_explanation、evidence_refs、component_revision、dependency_state、rule_version、risk_factors、why_now 等；GET 另加 snapshot_id、evaluated_at、is_stale。

- match_status：AFFECTED / NOT_AFFECTED / UNCERTAIN；历史移除快照可能有 NOT_EVALUATED。
- priority：P0 / P1 / P2 / P3 / REVIEW / INFO。**不是专业 Agent 的 REVIEW_REQUIRED / DEFER。**
- 过期快照 is_stale=true 时，返回 historical_match_status，并把当前 match_status 改为 UNCERTAIN、priority 改为 REVIEW；GET 不重算。
- EPSS status 为 UNKNOWN / STALE / SOURCE_ASSERTED；过期值的 score=null，observed_score 仅是历史观察。
- poc.confirmed 只代表关联已确认；usability 固定 NOT_EVALUATED。
- 历史风险详情是保存时 payload + snapshot_id + evaluated_at + historical=true，没有保证 is_stale 字段。
- recompute 的 {items:payload[]} 不保证 snapshot_id/evaluated_at/is_stale，不能直接当 GET 风险列表响应。

SourceItem 是 Source 行去 metadata，再加 last_sync（最近 SyncRun UUID，不是时间）、latest_error|null、records{raw_documents,processed_observations}。
Source status：planned / deferred / running / succeeded / partial / failed / rate_limited / stale / need_review。
SyncRun status：queued / running / succeeded / partial / failed / rate_limited / cancelled / need_review。
last_success_at 是真正同步成功时间；调研探测日期不能替代它。get_system_status 工具只返回 sources 与最近10条 sync_runs，不提供 CPU/内存/模型在线证明。

## 6. Phase 11-D 的 HTTP 缺口及最小适配建议

Investigation Orchestrator、三个专业 Agent、Integration Gate、AnswerEnvelope 都有内部实现，但没有供浏览器调用的对应路由。旧 assistant/query 的任务链与结果结构不同，不能通过改前端类型代替新接口。

最新 Phase 12-B 待实施计划为 8 个操作：提交、历史、status、trace、artifacts、integration、answer、cancel。具体方法/建议 URL 与实现边界见 [API_NOT_EXPOSED](../api/API_NOT_EXPOSED.md) 和 [机器提案](../api/proposed-investigations.json)。全部 PROPOSED，http_implemented=false，不加入当前 OpenAPI 或 AVAILABLE 清单。

公开提交确认、历史列表、Artifact 聚合、HTTP 错误 DTO 尚需冻结。内部模型可用于准确设计 UI，不能据此声称新路由或异步后台适配已完成。通用详情能力已拆为这组读取操作，不再保留早期集合 GET/通用详情草案作为当前提案。

## 7. InvestigationRequest：真实内部输入

状态：API_NOT_EXPOSED。完整机器约束以 internal-input.schemas.json 及其 TypeScript 映射为准。

~~~typescript
type InvestigationRequest = {
  schema_version?: "investigation-request-v1";
  request_id?: string; // UUID，缺省后端生成；不是幂等键
  planner_input: {
    query: QueryRequest;
    component_id?: string | null;
    snapshot_id?: string | null;
    component?: {
      name: string; // 必填，最大200；不是 NewComponent 的300限制
      ecosystem?: string | null;    // ≤40
      package_name?: string | null; // ≤200
      version?: string | null;      // ≤200
      purl?: string | null;         // ≤500
    } | null;
  };
  time_scope?: { window_days?: number | null; requires_current?: boolean } | null;
  user_context?: { display_language?: "zh-CN"; notes?: string };
  investigation_options?: {
    objective_profile?: "overview_v1" | "asset_impact_v1" | "asset_risk_v1" | null;
    timeout_seconds?: number;
  };
};
~~~

window_days 是 StrictInt 1..365；timeout_seconds 是 StrictInt 1..300，默认300；不接受浮点/布尔型伪整数。notes 默认空字符串、最多1000。request_key 位于 planner_input.query，必须非空白；没有顶层 idempotency_key 或 user_query 字段。时间窗口、多个目标、快照范围有现有覆盖限制，UNSUPPORTED_TIME_SCOPE 等缺口会保留为 REPLAN_REQUIRED，不能由前端擅自消除。

## 8. InvestigationStatus 与状态显示

字段：
logical_investigation_id:UUID；
current_stage:Stage；
overall_status:Overall；
planner_run_id/investigation_run_id/verification_run_id/analysis_run_id:UUID|null；
cancel_requested:boolean；
recovery_required:boolean；
warnings:string[]；
error_code:string|null；
revision:number；
updated_at:带时区时间字符串。

Stage：
CREATED / PLANNING / INVESTIGATING / VERIFYING / ANALYZING / INTEGRATING / COMPOSING / COMPLETED / WAITING_REVIEW / FAILED / CANCELLED。

Overall：
RUNNING / SUCCEEDED / SUCCEEDED_WITH_WARNINGS / INCOMPLETE / REVIEW_REQUIRED / FAILED / CANCELLED。

| Gate status | Answer status | Overall | 通常的 Stage |
|---|---|---|---|
| PASS | COMPLETE | SUCCEEDED | COMPLETED |
| PASS_WITH_WARNINGS | COMPLETE_WITH_WARNINGS | SUCCEEDED_WITH_WARNINGS | COMPLETED |
| REPLAN_REQUIRED | INCOMPLETE | INCOMPLETE | COMPLETED |
| HUMAN_REVIEW_REQUIRED | REVIEW_REQUIRED | REVIEW_REQUIRED | WAITING_REVIEW |
| FAILED | FAILED | FAILED | FAILED |
| 尚未产生 Gate 的失败/取消 | FAILED / CANCELLED | FAILED / CANCELLED | FAILED / CANCELLED |

**COMPLETED 只表示流程终态，不一定代表可信结果通过。** 终态 Stage 为 COMPLETED、WAITING_REVIEW、FAILED、CANCELLED。优先同时呈现 Stage、Overall、Gate、Answer 四个维度。RUNNING + recovery_required=true 表示需要后端恢复处理，不是自动重跑许可。

## 9. Agent Run / Task Run / Trace

本节为 API_NOT_EXPOSED 的 Runtime / 专业 Agent 内部协议。旧 HTTP Trace 见第5节。

- Runtime RunSnapshot：run_id、trace_id、status:string、result:object|null。
- 持久化 AgentRun.status：queued / running / succeeded / partial / failed / timeout / cancelled。
- Runtime TaskState：CREATED / PENDING / READY / RUNNING / SUCCESS / FAILED / WAITING_REVIEW / BLOCKED。**没有 PARTIAL。**
- Runtime TaskArtifact：artifact_id、run_id、task_id、status、result、evidence[]、tool_calls[]、confidence|null、unresolved_questions[]、warnings[]、errors[]、start_time|null、end_time。它不是三个专业 Artifact 之一。
- Runtime TaskTrace：run_id、task_id、task_type、start_time/end_time|null、status、tools_called[]、model_called[]、error[]、artifact_id|null、dependencies[]、transitions[]。
- AgentRunTrace：agent_id、agent_type、task_id、run_id、input_artifact[]、output_artifact|null、execution_time（毫秒整数）|null、status:TaskState、attempted、capability_state（interface_only / implementation_registered）、errors[]。
- InvestigationTrace：schema_version、根 logical_investigation_id、original_question、planner|null、events[]、agent_runs[]（最多3）、integration_result_id|null、integration_status|null、answer_id|null、warnings[]、unresolved_items[]、error_code|null、historical_snapshot。
- planner 摘要：planner_run_id、validation_status、retry_count、prompt_version、task_ids。
- agent_runs 项：run_id、status（数据库小写状态）、artifact_references、task_statuses:Record<string,string>、tool_calls。
- tool_calls 项：record_id、task_id、tool、status、duration_ms、evidence_ids。
- StageEvent：stage、code、at、overall_status|null、references:Record<string,string>。

缺少某个 Agent Run 可能是调查准入/核验条件未满足。不要把数组第1/2/3项机械当成 I/V/A；应按状态里的三个 Run ID 做关联。Trace 页面展示审计摘要与业务理由，不展示隐藏思维链、原始 Prompt、数据库连接配置或任意 Tool 输入输出全文。

## 10. Investigation Artifact

API_NOT_EXPOSED；schema_version=investigation-artifact-v1；agent_id=investigation_agent。

字段完整列表：
artifact_id、task_id、agent_id、run_id、schema_version、status、runtime_status、partial_result、information_status、vulnerability_id|null、canonical_id|null、description|null、component|null、asset|null、affected_versions[]、fixed_versions[]、version_match|null、cvss[]、cwe[]、poc_candidates[]、patch_information[]、evidence[]、uncertainties[]、conflicts[]、confidence|null、failed_tools[]、tool_calls[]、dependency_artifact_ids[]、evidence_storage、receipt_references、findings[]。

- status：COMPLETE / PARTIAL / CONFLICT / INSUFFICIENT_EVIDENCE。
- information_status：CONFIRMED / CANDIDATE / CONFLICT / INSUFFICIENT_EVIDENCE。
- runtime_status 使用 TaskState，不能拿 status=PARTIAL 填入 Runtime status。
- confidence 有限数字0..1或null。
- evidence_storage：artifact / tool_receipts。大证据集可能保存在工具回执中；evidence=[] 不自动表示无证据，要看 receipt_references。
- CVSS/CWE、版本范围、候选项等当前为 list[dict]，没有统一细粒度 Pydantic 模型；TypeScript 应保留 Record<string,unknown>，不能自行编造稳定子字段。
- COMPLETE 代表调查产物完成；POC 候选仍不能显示“已执行可用”。最终事实引用由 Verification 与 Gate 决定。

## 11. Verification Artifact 与 Claim–Evidence

API_NOT_EXPOSED；schema_version=verification-artifact-v1；agent_id=verification_agent。

VerificationArtifact 字段：
artifact_id、task_id、run_id、agent_id、schema_version、
source_run_id、source_artifact_id、source_snapshot_hash、evaluation_time、execution_status、tool_calls；
claims[]、verification_status、confidence、supporting_evidence[]、conflicting_evidence[]、conflicts[]、warnings[]、unresolved_items[]、partial_result、model_calls[]、model_hints[]、rules_version。

VerificationStatus：
CONFIRMED / PENDING / INSUFFICIENT_EVIDENCE / CONFLICT / REJECTED。

claims 不是简单 Claim 数组，而是 ClaimVerification 数组：
claim、status、confidence、supporting_evidence_ids、conflicting_evidence_ids、reason_code、reason_summary、rules_applied、score_components、warnings、unresolved_items。

VerificationClaim：
claim_id:string、statement、claim_type、source_task_id、related_entities、status、value、scope_key、vulnerability_id:string、package_identifier_id|null、branch|null、claim_revision|null、origin（stored / derived）、source_field|null、evidence_ids。

ClaimType：
AFFECTS_PRODUCT / AFFECTS_VERSION / FIXED_VERSION / POC_EXISTS / POC_ASSOCIATION / PATCH_EXISTS / FIX_COMMIT / KNOWN_EXPLOITED / VENDOR_CONFIRMED / EXPLOIT_CONDITION / REMEDIATION / CVSS_SCORE。

VerificationEvidence：
evidence_id:string、claim_id:string、source_id|null、source_key、source_type、source_name、source_time|null、content、reference、hash|null、authority_score、directness_score、authority_level|null、authority_scope|null、lineage_key|null、observation_id|null、raw_document_id|null、published_at|null、retrieved_at|null、excerpt_hash|null、observed_value、scope_key、vulnerability_id|null、stance、directness、evidence_type、is_current、integrity_status、exclusion_reasons、details。

stance=support / contradict / neutral；
directness=direct / mention / unknown；
integrity_status=VALID / MISSING / INVALID；
authority_level=official / authoritative / secondary / community 或null。
authority_score/directness_score/confidence 为0..1有限数字，不是模型准确率或客观概率。

Claim 与 Evidence 的 professional ID 是 string，派生 ID 不保证 UUID；不要把所有 Evidence Reference 拼到 /evidence/{id}。现有 HTTP Evidence 只接受真实数据库 UUID，派生快照应由新的调查 Artifact 适配接口展开。

禁止用弱来源/模型推测补成 CONFIRMED。冲突、排除原因及候选证据不能隐藏或覆盖原调查结果。

## 12. Risk Analysis Artifact

API_NOT_EXPOSED；schema_version=risk-analysis-artifact-v1；agent_id=security_analysis_agent。

字段：
artifact_id、task_id、agent_id、run_id、schema_version、context_id、input_artifact_ids、input_snapshot_hash、evaluation_time、source_verification_time、inventory_revision|null、execution_status、tool_calls、historical_snapshot、scope_notice；
verification_status、asset_id|null、component|null、version|null、
asset_match_status、version_match_status、asset_match_result、version_match_result、
exploitation_signal、patch_availability、risk_level、priority、affected:boolean|null、
risk_factors、mitigating_factors、recommended_actions、evidence_refs、reasoning_summary、
claim_dispositions、confidence、confidence_kind、warnings、unresolved_items、rule_ids、rules_version、priority_details、partial_result、coverage_complete、model_assist_used、model_assist_status、model_calls。

| 字段 | 实际枚举 |
|---|---|
| risk_level | CRITICAL / HIGH / MEDIUM / LOW / UNKNOWN |
| priority | P0 / P1 / P2 / P3 / DEFER / REVIEW_REQUIRED |
| asset_match_status | MATCHED / NOT_MATCHED / UNKNOWN |
| version_match_status | AFFECTED / NOT_AFFECTED / UNKNOWN |
| exploitation_signal.status | KNOWN_EXPLOITED / VERIFIED_POC_ASSOCIATION / POC_CANDIDATE / UNKNOWN |
| exploitation_signal.usability | NOT_EVALUATED |
| patch_availability.status | CONFIRMED_PRESENT / UNCONFIRMED / UNKNOWN |
| patch_availability.applied | UNKNOWN |
| patch_availability.applicability | CONFIRMED / UNKNOWN |
| model_assist_status | DISABLED / SUCCEEDED / FAILED / SKIPPED |

未确认、partial_result=true 或 coverage_complete=false 必须弃权：affected=null、risk_level=UNKNOWN、priority=REVIEW_REQUIRED。不能把 null 显示成“不受影响”。CRITICAL/HIGH/MEDIUM 要有确定的资产/版本影响；LOW 要有明确范围内非影响，priority=DEFER。confidence_kind 固定 uncalibrated_heuristic，禁止标成“准确率xx%”。范围只涵盖所选漏洞/组件/库存快照，不代表整台服务器实时安全或已执行扫描。

## 13. IntegrationResult

API_NOT_EXPOSED。字段：
integration_id、logical_investigation_id（Gate 命名空间）、trace_id、run_id|null、source_run_ids；
status、objective_coverage、task_completion_summary、checks、passed_checks、failed_checks、blocking_issues；
warnings、unresolved_items、artifact_references、evidence_references、
replan_reasons、human_review_reasons、final_result_references、partial_result_references；
input_hash、objective_hash、policy_version、created_at、evaluation_time、historical_snapshot=true、persistence。

status：
PASS / PASS_WITH_WARNINGS / REPLAN_REQUIRED / HUMAN_REVIEW_REQUIRED / FAILED。

- 主键实际字段叫 integration_id，不是 integration_result_id。AnswerEnvelope 中的 integration_result_id 引用它。
- GateCheck：gate=completion / integrity / evidence / consistency / objective / freshness；code、outcome=PASS / WARNING / BLOCKED / ERROR / NOT_APPLICABLE；blocking=NONE / REPLAN / HUMAN / FATAL；message、refs、objective|null。
- ObjectiveCoverage：outcome、status=SATISFIED / ABSTAINED / MISSING / CONFLICT、references。
- TaskExecution：run_id、task_id、semantic_type、status:TaskState、run_status:string、required、dependencies、error_codes。
- ArtifactRef：run_id、task_id、artifact_id、schema_version；schema_version 只允许三个专业 Artifact 版本。
- persistence=STORED / NOT_STORED。NOT_STORED 不可被前端包装成“已保存成功”。
- final_result_references 仅为通过验收的结果；partial_result_references 必须以观察/部分结果呈现。
- GET 查询只读取已有冻结结果，不重新运行 Gate，不悄悄吸收最新数据库事实。

## 14. AnswerEnvelope 与 Evidence Reference

API_NOT_EXPOSED。字段：
schema_version=answer-envelope-v1、answer_id、根 logical_investigation_id、original_question、
answer_status、integration_status|null、summary、key_findings、
affected_assets、risk_assessment|null、recommended_actions、
verified_claims、disputed_claims、citations、evidence_observations、evidence_references、
warnings、unresolved_items、integration_result_id|null、
agent_run_references、accepted_source_run_references、trace_reference、generated_at、
historical_snapshot=true、fact_origin=FROZEN_GATE_CONTEXT、explanation_provider=DETERMINISTIC_TEMPLATE。

answer_status：COMPLETE / COMPLETE_WITH_WARNINGS / INCOMPLETE / REVIEW_REQUIRED / FAILED / CANCELLED。

交付约束：

1. verified_claims 是 VerifiedFact 数组：claim_id、claim_type、verification_status=CONFIRMED、value、非空 evidence_ids、source_artifact。
2. disputed_claims 是争议观察：claim_id、claim_type、非确认 verification_status、value、scope_key、supporting/conflicting evidence_ids、verification_artifact、conclusion_scope=OBSERVATION。
3. citations 的每项真实结构：
   evidence_id、claim_id、hash（64位小写hex）、source_id、raw_document_id、observation_id（均UUID）、reference:object、verification_artifact:ArtifactRef。
4. evidence_observations 还保留争议/拒绝证据；含状态、scope_key、stance、directness、integrity_status、is_current，以及可空的哈希/来源IDs和 conclusion_scope=OBSERVATION。
5. evidence_references 是 evidence_observations 的 evidence_id 字符串集合，不是 URL 数组，且不得重复。
6. 每个 VerifiedFact 的 evidence_id 必须有匹配 Citation；Citation 的 claim 与 provenance 要对应 EvidenceObservation。前端不能自行拼出“引用编号”覆盖后端关系。
7. affected_assets 至多1项，provenance=USER_INVENTORY_NOT_SCANNED，包含 asset_id/component_id/deployed_version、source_artifact、claim_ids；是用户库存，不表示主动扫描。
8. recommended_actions 包含 category=IMMEDIATE / FURTHER_INVESTIGATION / LONG_TERM_HARDENING、action_provenance=VERIFIED_CLAIM / GENERAL_PRECAUTION、applicability=CONFIRMED / UNKNOWN / NOT_APPLICABLE、来源与 Claim/Evidence引用。精确 fixed_version 或 patch_reference 必须有被验证的事实支持。
9. REPLAN/HUMAN 状态下风险和建议的 conclusion_scope 为 OBSERVATION；PASS/WARN 才是 ACCEPTED。
10. FAILED/CANCELLED 不交付 verified_claims、风险、修复建议或受影响资产结论。
11. accepted_source_run_references 是 agent_run_references 的子集，不要把“已执行”当作“已采纳”。
12. original_question 仍可能含用户业务信息；生产公开展示需要明确访问范围。

来源 URL / locator 的展示：
只接受 HTTP(S)，拒绝 javascript/data/file 等协议；已有 Answer 投影会去掉 userinfo、query、fragment。locator 是白名单定位符（line/page/index 等整数，受限 json_pointer/json_path/field），不是任意全文或内网路径。不要把 Evidence.content、excerpt、HTML 当可执行页面插入。当前旧 HTTP Evidence 并不自动应用 Answer 的脱敏规则，必须另做安全展示和公开脱敏。

## 15. TypeScript 映射与 API Client

指定 TypeScript 文件已位于本包 contracts/：

| 文件 | 精确导出 |
|---|---|
| InvestigationRequest.ts | 内部 InvestigationRequest/PlannerInput/选项；API_NOT_EXPOSED |
| InvestigationStatus.ts | 内部状态、Stage/Overall联合；API_NOT_EXPOSED |
| AgentTrace.ts | 专业 AgentTrace/InvestigationTrace/Task Trace；旧HTTP Trace分开 |
| EvidenceReference.ts | Answer Citation/观察/ArtifactRef；HTTP Evidence分开 |
| Claim.ts | VerificationClaim作为Claim；HttpClaim保留value_json |
| VerificationResult.ts | 专业VerificationArtifact作为VerificationResult；HttpVerificationResult分开 |
| RiskAnalysis.ts | RiskAnalysisArtifact与专业Risk/priority联合 |
| IntegrationResult.ts | Gate/检查/任务覆盖与IntegrationStatus |
| AnswerEnvelope.ts | 冻结交付Envelope及正确AnswerStatus |
| HttpContracts.ts / index.ts | 现有HTTP类型及统一type-only入口 |

这些文件仅导出类型，没有运行时API Client或新接口。生成的完整字段在 contracts/generated/*.ts，原始 JSON Schema在 api/reference/。以 .js 结尾的 type-only相对导入用于将来 TypeScript ESM编译解析到同名.ts；现在不改动前端构建。

配套类型按边界分包，不把 Python 内部模型冒充已上线 API：

| 文件 | 来源与用途 |
|---|---|
| openapi.json | 当前 app.openapi() 原样输出；仅包含真实路由 |
| http-input.schemas.json / .d.ts | 五个实际 Pydantic HTTP Body |
| tool-input.schemas.json / .d.ts | 注册工具真实参数；工具名与权限见 tools.registry.json |
| http-data-columns.schemas.json / .d.ts | SQLAlchemy 列结构基础映射，不是自动验证的 response_model |
| http-responses.d.ts | 根据查询/序列化函数映射真实 HTTP 返回，处理排除字段、聚合及计算字段 |
| legacy-output.schemas.json / .d.ts | 旧 Task Contract / Artifact 和 ToolEnvelope |
| internal-input.schemas.json / .d.ts | Investigation/Verification/Analysis/Integration 内部请求 |
| internal-output.schemas.json / .d.ts | 内部运行、Trace、Artifact、Gate、Answer及嵌套模型；API_NOT_EXPOSED |
| examples/* | 来源标注见第19节 |

JSON Schema 使用 Draft 2020-12。多根 Schema 文件用 $defs 和 x-roots 指向各模型；验证时选 x-roots 对应的 $ref，而不是只验证文件顶层对象。模型自身的哈希绑定/引用关系等 Python validator 约束不全能用 JSON Schema 表达，仍需后端执行。

映射规则：
UUID / date / date-time → string；int/float → number；bool → boolean；tuple/list → Array；Literal/StrEnum → 字面量联合；None → null；可省略字段 → ?；Any/未约束dict → unknown 或 Record<string,unknown>。null 与缺省不同；默认值应让服务器处理，尤其不能用 false 替换 affected=null。

response Schema 为{}时，自动 Client 只能给出 unknown / any，需接上手工类型和运行时检查。[FastAPI Client 生成说明](https://fastapi.tiangolo.com/advanced/generate-clients/)。

建议优先复用现有 frontend/public/modules/services.js：

- 地址使用同源相对路径；参数用 URLSearchParams；ID 用 encodeURIComponent。
- API Client 集中处理 Authorization、422 detail、409冲突、502超时、AbortSignal。
- HTTP status 与业务 status 分开；ToolEnvelope 的 HTTP200也可能 status=failed 或 no_result。
- Query POST 202不是最终完成；先保存 run_id 再 GET轮询。
- 凭据用服务器代理或当前内存会话，避免 localStorage。不要在控制台打印令牌、问题全文、全部 Trace 或原始证据。
- 新调查方法等 Phase 12 HTTP适配后再启用。不要现在写出一个指向 PROPOSED URL 的“已可用”Client。
- TypeScript 是静态约束，仍需运行时验证和未知状态兜底；不要用强制断言绕过错误。

本次使用本机 Node 24 原生 TypeScript语法检查全部.ts，并核对导入/导出名称与Schema引用；没有安装依赖或运行tsc。语法检查与完整TypeScript语义检查不同，团队纳入自己的tsconfig后仍需运行完整语义检查。

## 16. 错误码与失败处理

现有 HTTP 没有统一 {code,message,request_id} ErrorEnvelope；不能假定这样的字段已实现。

| 层 | 状态/错误 | 前端处理 |
|---|---|---|
| FastAPI 参数 | 422，{detail:[{loc,msg,type,...}]} | 关联表单字段，保留安全摘要 |
| HTTPException | {detail:string} | 不把任意 detail 当机器业务码 |
| 鉴权 | 401 / 403 | 提示缺少权限；避免不停重试 |
| 未拥有/不存在 | 404 | 显示不可访问，不泄露其他用户资源存在性 |
| 幂等/修订冲突 | 409 | 重新读取并人工确认；不能盲换key重发 |
| 过大 | 413 | 提示2MiB限制 |
| 类型/同源 | 前端代理415 / 403 | 修正 Content-Type / Origin /部署适配 |
| 代理限制 | 405 | 表示当前代理未放行，不代表后端API未实现 |
| 队列满 | 旧assistant429 | 退避重试，同一请求保持request_key |
| 未配置/DB不可用 | 503 | 保留当前页面及上次快照 |
| 代理网络/超时 | 502 | 未知提交结果先按幂等键查询/重试，不当作任务已取消 |
| ToolEnvelope | failed/partial/no_result及errors[] | HTTP200仍检查业务状态；无结果≠全球不存在 |

Tool Gateway 常见 code：
UNKNOWN_TOOL、INVALID_INPUT、PERMISSION_DENIED、CALL_BUDGET_EXCEEDED、RUN_TIMEOUT、NOT_FOUND、INVALID_STATE、TOOL_FAILURE、TOOL_TIMEOUT。

Phase 11-D 内部可见 code：
INVESTIGATION_BUSY、PLANNING_FAILED、PLANNING_INCOMPLETE、UNSUPPORTED_TIME_SCOPE、DEADLINE_EXCEEDED、CANCELLED、MODEL_BUDGET_EXCEEDED、CONTROL_STORE_FAILED、CONTROL_CLEANUP_FAILED、GATE_NOT_STORED、ORCHESTRATION_FAILED、STALE_REVISION、AUTHENTICATED_ACTOR_REQUIRED 等。
它们尚没有 HTTP status 映射；Phase 12 可提议 BUSY→429、幂等冲突→409、归属不可读→404、输入无效→422、服务故障→503。这些是建议，不属于当前协议。

内部 provenance/hash/binding 校验失败应保存审计、停止交付并给出安全错误，不把内部异常堆栈、SQL或原始 Prompt返回浏览器。NOT_STORED 或 recovery_required 状态要显示“保存/恢复待确认”，不能显示完整成功或发起自动新的大任务。

## 17. 幂等、取消与超时

旧问答：
request_key + actor 定位，完整请求 fingerprint 相同复用 run；不同内容相同key为409。线程池2个worker、进程内容量8（包含排队/执行）。当前不存在 HTTP cancel、history-list 或 SSE/WebSocket。

资产写/复核：
请求包含 request_key，组件修改和复核有 expected_revision；同请求重试应复用key并保留原 revision。SBOM幂等键是 x-request-key，内容按SHA256绑定。recompute没有 HTTP幂等键，不应自动重试。

Phase 11-D：
幂等按 actor + investigation-orchestrator-v1 + request_key 及语义 fingerprint；request_id 不参与 fingerprint，相同语义请求复用根调查。语义不同同key拒绝。内部副作用受阶段键约束，但阶段键不交给前端生成。

取消是持久化 cancel_requested；返回时可能仍 RUNNING。只有后端实际观察取消、停止后续交接并封存终态，才能显示 CANCELLED。AbortController、关页面、网络断开、前端轮询超时都不会取消后端任务。已经终态的历史结果不会因取消请求被改写。

内部调查默认预算300秒，可请求1..300秒；过程在控制边界检查deadline，不是所有模型I/O的强制中断定时器。同步模型调用还受自身超时约束。进程最多2个活跃调查，实例可更低；没有已实现的持久任务队列或跨进程全局调度。lease过期可能进入 recovery_required，目前不能宣称自动恢复/继续。

当前前端代理30秒超时低于完整调查预算，进一步说明 Phase 12 必须把同步调用适配为真实的异步任务领取/执行。不要通过延长浏览器请求并假装完成来替代生命周期接口。

## 18. 前端刷新机制

现有旧问答实现每2秒读取 run，并并行读取 tasks/trace；最多90次，随后保留runID并允许手动刷新。WAITING_REVIEW、COMPLETED、FAILED停止自动轮询。会话runID存在内存，刷新浏览器后不会自动恢复历史列表。

Phase 12 推荐方案（PROPOSED）：

1. POST202后立即保存根调查ID，轮询status而不是重复提交。
2. 初始2秒，失败退避到5/10秒；只允许一个status请求在途；后台页面降频。
3. revision增加或Stage变化时按需取Trace；每个刷新周期不必重载全部Artifact。
4. current_stage终态时读取Answer/Gate一次并停止普通轮询；WAITING_REVIEW提供人工刷新入口。
5. cancel_requested=true显示“取消中”；recovery_required=true显示恢复待确认，交由后端处理。
6. 利用根ID+revision+artifact_id缓存，拒绝旧响应覆盖新revision；退出页面只终止浏览器请求。
7. 主动重算、人工复核、提交取消均为显式用户动作，GET刷新不触发副作用。
8. SSE/WebSocket尚未实现，本阶段不要声称已有实时推送。状态枚举未知时保留原值并停止确定结论展示。

## 19. 脱敏 JSON 示例与数据真实性

本次没有抓取在线API响应，也没有连接生产数据库。所有JSON fixture外层均明确标记 api_status=MOCK_ONLY、fixture_label=DEMO或MOCK、production_data=false；不把这些包装字段加入真实Pydantic请求。示例来源分开：

- api/reference/examples/orchestration-test-receipts.json：work/orchestration/final_e2e_receipts.json 的10种历史测试回执，只抽取 request/status/answer/trace；排除context.owner/stage_keys等私有控制字段。真实代码执行、合成安全情报与测试Planner，不是真实生产漏洞案例或Benchmark成绩。
- api/reference/examples/integration-test-receipts.json：work/integration/actual_chain_receipt.json 的真实历史IntegrationResult；合成fixture，未调用HTTP。
- api/reference/examples/professional-artifacts-mock.json：三个Artifact的弃权示例，由本次当前Pydantic验证；没有重新执行专业Agent。hash是演示合成占位，不是线上冻结快照证明。
- api/reference/examples/legacy-assistant-query-mock.json：旧HTTP请求及排队响应的人工模拟；request通过Pydantic校验，response按代码映射，没有HTTP抓包。
- prototype/：视觉Mock。真实资产仍用is_demo标识；is_demo不是所有列表或新Answer中都存在的字段。

示例一：可用于说明旧问答提交Body的Mock（CVE是假编号，不是实际情报）：

~~~json
{
  "question": "查询 CVE-2099-0001 的公开情报（模拟数据）",
  "asset_id": null,
  "target": "CVE-2099-0001",
  "mode": "auto",
  "request_key": "frontend-mock-query-001",
  "realtime": false
}
~~~

示例二：真实历史REPLAN_REQUIRED回执的**展示投影**（非完整DTO，不可作为HTTP响应fixture直接替换）：

~~~json
{
  "status": {
    "current_stage": "COMPLETED",
    "overall_status": "INCOMPLETE"
  },
  "answer": {
    "answer_status": "INCOMPLETE",
    "integration_status": "REPLAN_REQUIRED",
    "historical_snapshot": true,
    "fact_origin": "FROZEN_GATE_CONTEXT",
    "explanation_provider": "DETERMINISTIC_TEMPLATE"
  }
}
~~~

示例三：Evidence Reference 的字段示意Mock，example.invalid不是真实公告：

~~~json
{
  "evidence_id": "00000000-0000-4000-8000-000000000011",
  "claim_id": "00000000-0000-4000-8000-000000000012",
  "hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "source_id": "00000000-0000-4000-8000-000000000013",
  "raw_document_id": "00000000-0000-4000-8000-000000000014",
  "observation_id": "00000000-0000-4000-8000-000000000015",
  "reference": {
    "url": "https://example.invalid/advisory",
    "locator": {"line": 2}
  },
  "verification_artifact": {
    "run_id": "00000000-0000-4000-8000-000000000016",
    "task_id": "verify",
    "artifact_id": "00000000-0000-4000-8000-000000000017",
    "schema_version": "verification-artifact-v1"
  }
}
~~~

不要把 data_origin 包装字段注入实际 Pydantic Body（extra='forbid'），应只保留在 fixture 外层/演示元数据中。验证过结构不代表实际数据正确、来源可信或执行成功。

公开演示必须在界面区分“真实采集数据”“测试合成回执”“Mock交互”；用快照时间与覆盖范围说明已知边界，不根据空数组推断不存在漏洞或补丁。

## 20. 接口变更管理与交接验收

1. 当前HTTP v1与内部schema_version分开版本化。实现新调查接口前先冻结公开DTO，不把内部Context直接固化为公共契约。
2. 每次路由、Pydantic、序列化/查询改动后重新导出OpenAPI与Schema，比较required、nullability、enum、默认值、分页、错误及状态语义。
3. 删除字段、缩窄枚举、改变单位/数值类型/ID空间/状态含义属于破坏性变化，需团队确认及兼容期；新增状态也必须有前端未知值兜底。
4. 不同DTO不可共用status枚举；旧问答、TaskState、Source/SyncRun、Verification、Integration、Answer分别建映射。
5. 新response_model引入可能改变Decimal/日期或筛掉字段，必须与现有真实响应逐项比对，不只看静态OpenAPI。
6. frontend Handoff包应记录源码文件hash、OpenAPI hash、导出时间、来源与验证范围；禁止将历史1261测试记录写成本次重跑通过。
7. Phase 12至少验收：鉴权归属隔离、同key同语义重复提交、冲突409、状态读/完整Trace、Gate/Answer引用一致、取消中→终态、超时、恢复待确认、历史分页、代理/CORS、Mock标签。
8. 本次运行离线Schema生成、真实模型/字段比对、JSON示例校验、TypeScript语法与引用检查，以及敏感信息扫描；具体计数以本包 VALIDATION.json 为准。不包含新HTTP端到端测试，历史1261测试未重跑，也未运行tsc。
9. 再次比对业务源码与前端文件hash，确认本次无业务变更。交接文件已保存，实际文件清单与哈希见 [MANIFEST.json](../MANIFEST.json)。

## 21. Phase 12 优先顺序

第一优先：新增受控调查HTTP适配与后台执行领取，保留幂等/actor/预算；并解决当前前端代理与认证。

第二优先：接入status、trace、artifacts、integration、answer；严格按四层状态与来源引用展示完整调查闭环。

第三优先：cancel、history、recovery_required的用户反馈；复核提交和资产写入口的代理适配。

第四优先：确有产品需要时增加全局情报统计和运行遥测。无需重写已有Tool/Model Gateway、Runtime、Planner、三个专业Agent或Integration Gate。

交接后停止，不在此任务实施 Phase 12-B API暴露或前端联调。


## 22. 独立包的五个前端示例入口

推荐 UI 使用 [mock/README](../mock/README.md) 定义的五份展示投影，全部共享同名场景。PASS、带警告、需要复核、未完成、取消、失败等都保留历史原字段。详细说明和跨文件 ID 要求见 [demo-scenario](../examples/demo-scenario.md)。

新目录只调整交接资料位置，不迁移原项目代码或模型。专业 Artifact 弃权示例与独立 Gate 回执不属于 PASS 场景，不得拼接成同一条已通过的调查。包内 generated 类型与当前后端 Schema 保持一致。

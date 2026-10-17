# Phase 12-B：前端调查 API 对接

这份文档对应本分支的实际代码。调查闭环已经有 HTTP 入口，共 8 个操作；原有 34 个操作保留。此前交接中的调查 `API_NOT_EXPOSED` 标记已由本阶段更新，其他产品缺口仍按原交接处理。

## 直接开始

后端仍按现有方式启动 FastAPI，使用已有 PostgreSQL 配置。访问 `/docs` 或 `/openapi.json` 查看真实契约；启动服务需要 `AEGIS_DATABASE_URL`，身份使用原 `AEGIS_ASSET_TOKEN` / `AEGIS_ASSET_OWNER`。凭据只配置在本机或后端，不提交 Git，也不写入前端构建变量。

浏览器可以调用 8769 同源代理的 `/api/investigations`。本地演示的服务端令牌注入沿用 `AEGIS_LOCAL_DEMO=1`；不启用此模式时前端自行提供 Bearer。直接访问后端时，前端开发 Origin 必须在 `AEGIS_CORS_ORIGINS` 的逗号分隔名单中。默认允许 localhost/127.0.0.1 的 5173 和 8769 端口；不允许 `*`。CORS 不提供登录身份。

TypeScript 类型：`frontend-contracts/investigation-http.d.ts`。客户端：`frontend/contracts/investigations.ts`。这两个文件是 HTTP 公共投影；旧 `internal-output.d.ts` 是 Python 内部协议，不能作为浏览器响应使用。

## 调用顺序

1. 创建调查，同时提供稳定幂等键。
2. 使用响应的真实 `investigation_id` 每 1 秒查询 status；页面隐藏时暂停，遇到 429/503 按 Retry-After 退避。
3. revision 变化时刷新 trace 和 artifacts。缺失 Artifact 表示尚未产生或该阶段没有执行；不要创建假节点/假结果。
4. overall_status 不再是 RUNNING 后停止常规轮询，按需读取 answer 和 integration。
5. 取消成功请求不等于已经停止；等待 `overall_status=CANCELLED`。已完成调查不会被逆转。

## 创建请求

```json
{
  "user_query": "查询 CVE-2099-9999001 的影响范围及证据",
  "idempotency_key": "demo-synthetic-001",
  "asset_scope": {
    "target": "CVE-2099-9999001",
    "component": {"name": "vLLM", "ecosystem": "PyPI", "package_name": "vllm", "version": "0.6.0"}
  },
  "options": {"mode": "auto", "realtime": false, "timeout_seconds": 300}
}
```

以上仅为 **MOCK_ONLY 请求格式示例**：CVE-2099 是合成编号，不代表真实安全事实；需按实际数据替换。asset_id/component_id/snapshot_id 为真实所有者库存的 UUID，服务端校验授权。所有字段、限制、默认值以导出的 OpenAPI 为准。

也接受现有 `InvestigationRequest` 完整结构（`planner_input.query.request_key` 等），兼容原交接协议。不能混用两种请求结构。简化请求不接受 owner、permissions、模型配置或工具白名单。

`Idempotency-Key` 请求头或 body 的 `idempotency_key` 至少提供一个；同时提供必须相同。内部请求使用其 request_key。重复键/相同内容返回同一个根 ID，`reused=true`；重复键/不同内容返回 409。比较内容不包含每次生成的 request_id。重复返回当前真实阶段，未必仍为 CREATED。

202 仅表示根记录已经提交保存，不能当成调查成功。模型身份由 model_provider / is_mock 明示。默认 Model Gateway 是 Mock；配置真实供应商后才产生真实模型调用，本阶段不宣称已经完成真实模型评测。

## 8 个操作

| 方法与路径 | 返回 | 约束 |
|---|---|---|
| POST /api/investigations | InvestigationCreateResponse（202） | 复用原原子 claim，后台执行 |
| GET /api/investigations/history | HistoryResponse | offset ≥0、limit 1–100；status 为 Overall 枚举；sort=created_desc/created_asc |
| GET /api/investigations/{id}/status | InvestigationStatusResponse | 保留 Stage/Overall，含 revision、时间、cancel_requested、recovery_required |
| GET /api/investigations/{id}/trace | TraceResponse | 仅已有阶段事件与真实子 run、工具摘要；time 是实际事件时间 |
| GET /api/investigations/{id}/artifacts | ArtifactResponse | investigation/verification/analysis 可为 null |
| GET /api/investigations/{id}/integration | IntegrationResponse | 原 Gate 结果，不重新计算 |
| GET /api/investigations/{id}/answer | AnswerResponse | 已保存 AnswerEnvelope 的脱敏副本，不调用模型 |
| POST /api/investigations/{id}/cancel | InvestigationStatusResponse | 调用原取消机制；幂等重复请求 |

Agent Trace 的 stages 是已发生阶段的最新事件，status 来源于子 run 或真实事件 code，不是百分比进度。agent_runs 是三个专业 Agent 的实际 Runtime 摘要；Planner 和 Gate 的 ID 独立保留。没启动的阶段没有虚构执行时间。

Trace 在调查推进时可能跨两个快照读取。仅在根 revision 确实变更时，对已知绑定竞争最多尝试 3 次；持续推进返回可重试的 SNAPSHOT_BUSY。revision 稳定的绑定异常仍报错，不修补或忽略损坏。工具摘要只包含 record_id、task_id、tool、status、duration_ms 和 evidence_ids，原始工具参数仍不公开。

## 状态与结果

Stage：CREATED、PLANNING、INVESTIGATING、VERIFYING、ANALYZING、INTEGRATING、COMPOSING、COMPLETED、WAITING_REVIEW、FAILED、CANCELLED。

Overall：RUNNING、SUCCEEDED、SUCCEEDED_WITH_WARNINGS、INCOMPLETE、REVIEW_REQUIRED、FAILED、CANCELLED。

Gate：PASS、PASS_WITH_WARNINGS、REPLAN_REQUIRED、HUMAN_REVIEW_REQUIRED、FAILED，原样保留。不能把 REPLAN_REQUIRED 或 HUMAN_REVIEW_REQUIRED 渲染成安全或成功结论。

Answer 使用原字段：summary、key_findings、risk_assessment、recommended_actions、verified_claims、disputed_claims、citations、evidence_observations、warnings 等；不会为了示例改名为 findings/risk/recommendations。完整枚举及字段见生成类型。

Artifact 输出明确移除了工具原始调用、失败工具原文、模型调用/提示、receipt_references 和内部配置，嵌套凭据、URL 用户信息/查询参数、本机路径也过滤。证据仍是外部不可信内容，前端必须按文本显示，不执行 HTML/指令。公共投影不是供后端重新执行的输入，历史 hash 指向原始冻结快照，不是脱敏响应的新 hash。

Gate 完成前，引用必须匹配根调查的各阶段 run、目标漏洞和 Artifact 交接关系；Gate 完成后读取原有冻结输入。不能凭一个可读的其他 run 的引用，替换当前调查的 Artifact。

## 错误与重试

新接口统一 `ApiError`：error_code、message、request_id、retryable；X-Request-ID 方便排查。验证错误不回显请求原文，内部异常不返回数据库信息和堆栈。旧 34 个接口保留原来的 detail 错误格式。

| HTTP | 常见错误 | 前端处理 |
|---|---|---|
| 401 | AUTHENTICATION_REQUIRED | 补充有效凭据 |
| 403 | ACCESS_DENIED | 调整已授权资产范围 |
| 404 | INVESTIGATION_NOT_FOUND | 未找到或无权访问；不要泄露其他用户存在性 |
| 409 | IDEMPOTENCY_CONFLICT | 更换键仅用于新的问题，不能无脑重试 |
| 409 | RESULT_NOT_READY | 仍在运行时按 Retry-After 查询 |
| 409 | RESULT_UNAVAILABLE | 调查已终止且未产生 Gate，不继续轮询 |
| 422 | INVALID_REQUEST / 幂等键错误 | 修正字段，不重复提交错误内容 |
| 429 | INVESTIGATION_BUSY | 退避后用同一键重试 |
| 503 | CREATION_ACK_TIMEOUT / 配置不可用 | 同一键重试；ACK 超时不等于根一定没有保存 |
| 503 | SNAPSHOT_BUSY | 根调查正在更新，按 Retry-After 刷新 Trace |
| 500 | INTERNAL_ERROR | 保存 request_id，不展示技术异常 |

## 容量、重启与部署边界

本阶段使用最多 2 个进程内后台工作线程，沿用 Runtime 的进程级配额，满载不新建无用根记录。它不提供跨实例持久队列、自动恢复或无限排队。进程重启后已存储历史可读，未完成孤立调查通过 recovery_required 明示；前端不能假称自动续跑。部署先采用一个 FastAPI worker；生产多用户身份需后续正式身份系统，当前只有配置的主体，不是多租户登录服务。

正常关闭时向在途调查发送原有协作式取消。关闭前仍未完成 claim 的工作者会保留取消意图，原 claim 提交后先请求取消，再交回 Orchestrator；不会把晚到的 claim 当成新调查继续规划。数据库永久阻塞、进程被强制终止不属于可保证的正常关闭场景。

## 前端客户端

`investigation-client.ts` 和 `investigation-http.d.ts` 已一起导出到本说明对应的契约目录。可复制这两个文件到前端同一目录；客户端的类型导入是相对路径。创建时保留同一个 idempotencyKey，默认每 1–2 秒读 status，在终态停止轮询，再读取 answer/integration。不要以 HTTP 202 判断成功。

HTTP 协议错误抛出 InvestigationApiError，包含 status 和 ApiError；fetch 的网络错误、代理非 JSON 响应仍可能是普通 Error，应由前端网络失败分支处理。客户端没有自动重试、没有保存 token，没有新增 SSE 或 WebSocket；token 回调只应读取获授权的运行时凭据，不能将服务器密钥写入前端源码或构建包。

## 契约变更

新契约源为真实路由和 API DTO，运行 `python scripts/export_investigation_api.py` 更新两份导出；`--check` 和现有 check_contracts 只读检查。旧响应已补充 OpenAPI 描述，但保留兼容序列化、动态 JSON 扩展字段，标注 `LEGACY_DESCRIPTION_ONLY`；不能声称旧响应已全部严格运行时验证。

修改 HTTP 契约必须通过 PR，同时更新生成文件、类型和接口测试。破坏性字段变化需先与前端协商；本阶段没有自动合并队友代码，也没有开发 UI。


## Phase 14-B5：一次受控证据补查

服务端 `AEGIS_EVIDENCE_SUPPLEMENT_ENABLED=1` 启用；默认 `0`。不增加 API 或客户端预算参数。仅支持已知且获授权的资产/组件/部署版本、Gate 原状态为 REPLAN_REQUIRED、结构化 version_impact 缺口，且尚未读到依据的存储 Claim。首版通过 get_evidence 的 claim_id 过滤读取已收集资料；没有新增公网检索或采集来源。

每个逻辑调查最多一轮，每个批次最多一个子调查获得自动补查额度。新增证据采集最多三次（包括失败调用）；不额外调用模型。原调查 deadline 和已发生工具调用继续计入预算；重新核验和风险读取同样计入总预算。缺用户版本、冲突、已有弱证据、目标不明、已查过、库存变化或预算不足不自动扩展。

`GET /api/investigations/{id}/status` 新增 `supplement`、`processing_complete` 和 `result_version`。原 Gate 已终止但 `processing_complete=false` 时继续刷新。补查状态与 Gate 状态分开，首次阻断结果仍真实保留。supplement 中可读取具体 claim_ids、父 Gate、执行状态、固定工具调用记录、new_evidence_ids、resolved_claim_ids、调用数量、停止原因与恢复提示。tool_calls 仅有固定只读工具名、记录 UUID、状态和证据 UUID，不含参数、原始输出、密钥或 worker token。

Trace / Artifacts / Integration / Answer 四个既有 GET 支持 `?version=1|2`。缺省为已完整提交的最新版本；1 永远读取原结果；2 未完整提交返回 409 RESULT_NOT_READY，非法版本返回 422。状态取得 result_version 后应把同一版本传给四个读取，避免同时读取不同版本。TS Client 方法的第三个参数为版本：`client.answer(id, signal, 1)`；JS Client 一致。

补查原 Planner 与调查 Run 不重跑；新增采集 Run、Verification/Risk/Gate 和答案 v2。状态、Trace 和历史读取不会触发补查。取消意图与新步骤创建在同一数据库锁边界协调，过期或取消结果不能发布。进程中断保持未完成状态，过期 heartbeat 标记 recovery_required，未实现自动续跑。取消请求仍不是已取消确认。

批次 items 新增 result_version 与 supplement，可区分生成新判断的资产和未获得额度、仍存在证据缺口的资产。各资产的版本、核验、风险和答案引用独立；公共漏洞资料不代替资产适用核验。history 的 status 筛选仍依据首次根调查状态，返回项可附最新答案与补查摘要；不要用该筛选推断 v2 的 Gate 状态。

类型与枚举以本包生成的 investigation-http.d.ts / investigation-http.openapi.json 为准。程序完整性错误保持错误，不当作证据不足；新证据也可能继续被 Gate 拒绝。没有新可用证据时原答案保留，不推出资料不存在。正向受控资料与真实模型调用分别标识，本阶段不产生 Benchmark 准确率。

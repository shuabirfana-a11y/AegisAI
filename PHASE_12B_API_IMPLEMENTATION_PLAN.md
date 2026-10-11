# Phase 12-B：调查闭环 API 实施计划

状态：已实施并完成验证。依据本轮用户指令，计划完成后直接实施，不等待二次确认。

## 已检查的现状

- FastAPI 当前有 34 个 HTTP 操作；调查 Orchestrator 只有 Python 内部入口。
- 复用 `InvestigationOrchestrator`、持久化 Store、三种 Artifact Reader、`AnswerSourcesLoader`、Trace 和 `AnswerEnvelope`。
- Bearer 认证由 `asset_principal` 提供，主体来自服务端配置；请求不能指定用户身份。
- 旧响应没有 `response_model`，已有交接类型和数据库列 Schema 可以用于补齐描述。
- 旧 `PHASE_12B_IMPLEMENTATION_PLAN.md` 尚未实施。新指令指定 `/api/investigations`，本计划以此为准，不新建 `/api/v1` 调查入口。

## 全局边界

不修改 Planner、Runtime、Agent、Gate、核验/风险算法，不改数据库结构，不开发 UI。Router 只依赖 API Service，查询和创建通过已有服务或只读 Repository。保留旧 34 个操作的路径、处理器和响应行为。

## Task 1：API 协议与失败测试

新增 `backend/app/investigation_api/schemas.py` 和 `backend/tests/investigation_api/`。

- 请求使用 `user_query`、`asset_scope`、`options`；映射已有 InvestigationRequest。兼容已有内部请求 Schema，便于复用前端交接契约。
- 幂等键来自 `Idempotency-Key` 或请求体；缺失/冲突明确拒绝，不偷偷生成随机键。
- 状态保留真实 Stage/Overall，取消以 `cancel_requested` 表达，不能假称已经取消。
- 新接口全部有 Pydantic 请求/响应、错误和枚举；Artifact 使用字段白名单的公共投影，移除工具原始记录、模型提示和配置。
- 测试先验证未暴露入口，观察失败后实施。

## Task 2：Service、工作队列与只读适配

新增 `backend/app/investigation_api/{service,repository,projection,errors}.py`。

- 使用最多两个本进程后台工作线程，无无限排队；复用 Orchestrator 的数据库幂等声明。
- 创建响应只在原 Store.claim 已提交后发出；透明包装 Store 获取声明回执，不能提前创建根记录。
- 同键先查已有所有者根记录并校验指纹；满载仍允许返回已存在调查，不创建重复根记录。
- 读操作先校验所有者、原请求及引用绑定。Gate 完成后读取其冻结输入；之前通过原 Artifact Reader 并校验根引用。
- Answer GET 只读已存储答案，不调用模型；未产出结果返回 `RESULT_NOT_READY`，附重试提示。
- History 仅读当前认证主体的 Orchestrator 根记录，支持 Overall 过滤、offset/limit、时间排序。
- 本进程重启不自动续跑，不宣称有持久队列；沿用现有 `recovery_required`。

## Task 3：8 个 HTTP 操作与安全边界

新增 `backend/app/api/investigations.py`；增量修改 `backend/app/main.py`。

| 方法 | 路径 | 含义 |
|---|---|---|
| POST | /api/investigations | 创建或返回幂等调查，202 |
| GET | /api/investigations/history | 所有者历史分页 |
| GET | /api/investigations/{id}/status | 真实生命周期 |
| GET | /api/investigations/{id}/trace | 已产生的阶段/Agent/工具摘要 |
| GET | /api/investigations/{id}/artifacts | 三类 Artifact 公共投影 |
| GET | /api/investigations/{id}/integration | 冻结 Gate 结果 |
| GET | /api/investigations/{id}/answer | 已存储 AnswerEnvelope 公共投影 |
| POST | /api/investigations/{id}/cancel | 请求取消；完成状态不逆转 |

- 不泄露其他所有者是否存在，统一 404。
- 新接口所有失败使用 `error_code/message/request_id/retryable`；验证错误不回显原始输入，内部异常只写带 request_id 的脱敏日志。
- CORS 使用显式开发地址或配置 allowlist，拒绝 `*`；身份仍需 Bearer。
- 补齐旧 34 个操作的 OpenAPI 响应描述：按真实处理器/已验证列映射生成 Schema，保留旧序列化行为。动态 JSON 字段明确表示扩展对象，不假称严格验证。

## Task 4：前端传输及契约

仅扩展 `frontend/server.mjs` 的代理白名单，允许新调查路径及创建/取消 POST，保持同源与 JSON 检查；转发 Authorization、幂等键和必要响应头。不改页面。

导出实际 `openapi.json`，生成调查 TypeScript 契约、API Client 示例及联调说明。新旧接口边界、真实链路/合成测试标识、重启限制写清楚。

## Task 5：验证、审查与交付

- 在专用本地 PostgreSQL 测试库运行原始回归基线和新增测试。
- HTTP 测试使用真实 Orchestrator/数据库/工具/三 Agent/Gate；仅 Planner 模型使用明确标注的 Mock，不冒充真实安全评测。
- 覆盖幂等并发及冲突、满载、权限/跨用户、读取绑定、原始信息脱敏、取消阻止下一阶段、History、五种 Gate 状态、答案重复 GET 不调用模型。
- 验证新响应与 OpenAPI 一致，旧 34 操作描述不再是空 Schema，代理测试通过。
- 原源码哈希保护仅放行必需的 `main.py` 接线；新增测试验证旧路径和处理器保持不变，不修改原基线哈希。
- 完成全分支独立审查、敏感信息扫描，交付 `PHASE_12B_RESULT.md`；分支 `feature/investigation-api` PR 到 main，不自动合并。

## 审查重点

创建 ACK 必须是已持久化真实根 ID；幂等锁与队列容量竞争；关闭时未 ACK 工作者；GET 时的快照竞争；跨所有者与被篡改引用；嵌套外部 JSON 中的凭据/路径；CORS 不取代认证；旧 API 行为不得因 Schema 补齐被过滤或重写。

## 参考

FastAPI 官方：[响应模型与额外响应](https://fastapi.tiangolo.com/advanced/additional-responses/)、[异常处理](https://fastapi.tiangolo.com/tutorial/handling-errors/)、[CORS](https://fastapi.tiangolo.com/tutorial/cors/)。通过 Context7 核对。历史 1261 通过不作为本次实跑成绩。

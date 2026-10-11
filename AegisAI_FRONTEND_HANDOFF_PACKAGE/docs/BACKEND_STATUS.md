# 后端能力与交付状态

核对日期：2026-10-11，Phase 12-B 开发分支。FastAPI 保留原五组 Router，新增 investigations Router，合计 42 个 HTTP 操作。代码实现不代表服务已部署在线；后端负责人仍需提供运行环境。

## 技术栈

| 部分 | 当前实现 |
|---|---|
| 后端 | Python 3.12 / FastAPI / Pydantic / SQLAlchemy |
| 数据库 | PostgreSQL + pgvector，Alembic Migration |
| 检索 | SQL + Vector + Relation；部分本地 Embedding 调用保留，未强行迁移 |
| 模型 | Model Gateway：Mock、OpenAI Compatible、本地 Embedding 适配 |
| 工具 | Tool Gateway，当前注册清单为 37 个工具 |
| 前端 | 原生 JavaScript ESM、History Router、Node 本地代理；七页存在 |
| 当前部署边界 | 本地 8769 前端 → 8000 后端；不是交接包自带云端网站 |
| Dify | 不在当前运行链路，不需要队友配置 Dify |

## 能力与浏览器可达性

| 模块 | 后端实现 | 当前 HTTP/浏览器边界 |
|---|---|---|
| 多源采集、标准化、富化、数据库读取 | 已有代码；各源接入状态以 sources 为准 | 部分列表/详情/同步状态已开放；不表示每个规划源都已接入 |
| 漏洞、Claim、Evidence、PoC/Patch 候选、复核 | 已有 | 读取 API 已有；复核提交被前端代理拦截 |
| 资产与版本匹配、风险快照 | 已有 | 需 owner/principal 约束；读取可接；多个写入被代理拦截 |
| 旧确定性问答 | 已有 | assistant/query 与 run/tasks/trace 已开放 |
| Model / Tool Gateway | 已有 | 工具入口仅允许 READ_ONLY，不等于允许浏览器直接调用全部内部能力 |
| Planner、Task Contract、DAG、Scheduler、Executor、Trace | 已有内部实现 | 不把 Python 模块当作浏览器 API |
| Investigation / Verification / Security Analysis Agent | 复用原内部实现 | 新调查入口的 trace/artifacts，返回公共脱敏 DTO |
| Integration Gate | 复用原内部实现 | integration 子路径，读取冻结结果，保留 5 种状态 |
| Investigation Orchestrator 与 AnswerEnvelope | 复用原内部实现 | 创建、状态、答案、取消、历史 8 个操作已实现 |

## 当前阶段

Phase 12-B 采用增量 HTTP 接线，未修改 Planner、DAG/Scheduler、三专业 Agent、Gate 或数据库结构，未开发 UI。当前联调说明见 [调查 API](../api/INVESTIGATION_API.md)。

调用链为 HTTP Router → API Service → 原 Orchestrator。地址使用 `/api/investigations`，旧 `/api/v1/investigations` 提案没有实现。TypeScript 客户端和公共类型位于 `api/reference/investigation-client.ts`、`investigation-http.d.ts`；旧内部模型和 Mock 不应直接当成公共响应。

## 工程与验证范围

历史与本轮实跑分别记录。当前验证见包根 `PHASE12B_VERIFICATION.json`；原 `VALIDATION.json` 保留历史交接检查。HTTP 链路测试使用真实 PostgreSQL、工具、三专业 Agent 和 Gate，仅 Planner 模型受控 Mock。合成漏洞/资产不构成业务准确率评测。

旧 34 个操作已补充 OpenAPI 描述，保留 LEGACY_DESCRIPTION_ONLY 边界；新调查响应严格使用 Pydantic。原有 7 个其他写操作仍被代理拦截。当前鉴权是服务端令牌主体，没有多用户登录系统。

最多 2 个进程内工作线程，沿用 Runtime 配额，推荐先用单个 FastAPI worker。没有 SSE/WebSocket、跨实例持久队列或自动恢复承诺；重启后的孤立调查通过 recovery_required 明示。本阶段没有云端部署。

浏览器前端不得依赖内部 Context、worker_token、stage_keys、私有 Prompt 或数据库连接。生成类型中出现内部模型名称，不表示允许向浏览器返回这些内容。

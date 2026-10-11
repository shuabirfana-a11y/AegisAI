# 后端能力与交付状态

核对基线：2026-10-10。当前 FastAPI 挂载 routes、enrichment、assets、assistant、tools 五组 Router。现有 33 个路径、34 个 HTTP 操作；没有 investigations Router。

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
| Investigation / Verification / Security Analysis Agent | 已有内部实现 | 专业 Artifact API_NOT_EXPOSED |
| Integration Gate | 已有内部实现 | 完整 IntegrationResult API_NOT_EXPOSED |
| Investigation Orchestrator 与 AnswerEnvelope | 已有内部实现 | 提交/生命周期/答案等 API_NOT_EXPOSED |

## 当前阶段

Phase 11-D 内部能力已形成，Phase 12-A.5 已完成契约导出。Phase 12-B 的实施计划已生成，仍待实施确认；本次交接包不是 Phase 12-B 开发或验收。

下一步最小适配为 HTTP Router → API Service Adapter → 已有同步 Orchestrator，保留 Task、专业 Agent、Gate 与模型/工具入口。暂定 8 个公开操作，见 [API_NOT_EXPOSED](../api/API_NOT_EXPOSED.md)。任何 URL 和公开错误 DTO 都需实际实施后重新导出。

## 工程与验证范围

历史完整工程验收“1261 项通过”有项目回执；本次没有重跑这套测试，也没有连接生产数据库或抓取实时 HTTP 响应。本包的当前字段校验、路由一致性、文件依赖和打包检查以 [VALIDATION.json](../VALIDATION.json) 为准。

已知限制：成功响应普遍未声明 FastAPI response_model，离线 OpenAPI 不能生成完整业务响应类型；现有代理有方法/Origin/CSP/Host 限制；当前鉴权是服务器令牌方案，没有上线的多用户账户系统；没有完整调查 SSE/WebSocket、持久化任务队列和自动恢复承诺。

浏览器前端不得依赖内部 Context、worker_token、stage_keys、私有 Prompt 或数据库连接。生成类型中出现内部模型名称，不表示允许向浏览器返回这些内容。

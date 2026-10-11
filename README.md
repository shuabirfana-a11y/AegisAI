# AegisAI

**面向 AI 生态的可信安全情报与自主调查智能体系统。**

用于“中国电子杯”第三届高校 ICT 产教融合创新大赛赛题九：智能体驱动的 AI 安全知识情报系统设计与实现。

## 队友从这里开始

- [前端交接入口](AegisAI_FRONTEND_HANDOFF_PACKAGE/README.md)
- [下载交接 ZIP](AegisAI_FRONTEND_HANDOFF_PACKAGE.zip)
- [队友接入、环境与分支协作](docs/TEAM_COLLABORATION.md)
- [快速入门](AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/FRONTEND_QUICK_START.md)
- [页面需求](AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/UI_REQUIREMENTS.md)
- [现有 API 与缺口](AegisAI_FRONTEND_HANDOFF_PACKAGE/api/API_STATUS.md)
- [完整前后端契约](AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/FRONTEND_TEAM_HANDOFF.md)

## 当前状态

截至 2026-10-11，代码已有 Security Intelligence Engine、Tool/Model Gateway、混合检索、受约束 Planner、DAG Runtime、调查/核验/风险分析专业 Agent、Integration Gate 和 Phase 11-D 内部调查总控及 AnswerEnvelope。

**Phase 12-B 只有待实施计划。** FastAPI 目前提供 34 个 HTTP 操作，其中 27 个操作经现有本地前端代理放行、7 个写操作被代理拦截。完整 Phase 11-D 生命周期和结果仍为 API_NOT_EXPOSED；旧 assistant/query 不是完整新调查入口。

前端已有七个页面，采用原生 JavaScript ESM、History Router 和 Node 本地代理。8768 原型是 Mock；真实 API 前端默认 8769，后端默认 8000。GitHub 仓库不等于已经部署的比赛演示网站。

历史全量工程验收记录为 1261 项通过；本次源码上传没有重新执行这套全量测试。交接包提供独立字段/Schema/类型/链接验证记录，所有合成示例都标为 Mock，不能作为真实漏洞情报或 Benchmark 成绩。

## 项目结构

| 目录 | 作用 |
|---|---|
| backend/ | FastAPI 服务、ORM、迁移、采集与富化、工具/模型、Runtime/Agent/Gate，以及测试 |
| frontend/ | 现有七页、HTTP 适配、本地代理、协议测试和类型入口 |
| AegisAI_FRONTEND_HANDOFF_PACKAGE/ | 可独立交给前端队友的文档、类型、示例与离线协议 |
| docs/、design/ | 协议文档、数据库/UX/UI 设计与组件映射 |
| requirements/、research/ | 冻结需求和数据源调研资料 |
| evaluation/、tests/ | 评测集准备、验证脚本与测试素材；未标注部分不宣称 Benchmark 达标 |
| reports/、PHASE_* | 历史阶段报告与实施记录 |
| integrations/ | 历史可选适配；Dify 不在当前运行链路 |
| licenses/、THIRD_PARTY.md | 第三方来源与许可说明 |

## 环境与数据

后端使用 Python 3.12、FastAPI/Pydantic/SQLAlchemy，数据库为 PostgreSQL + pgvector。配置模板在 [backend/.env.example](backend/.env.example)，依赖在 [backend/requirements.txt](backend/requirements.txt)。前端无额外 npm 依赖；Node 环境中进入 frontend/ 后执行 npm start，只启动前端，不启动后端或数据库。

仓库不含开发数据库、真实令牌、虚拟环境、本机运行日志、下载模型与大缓存。新电脑的环境准备和脚本限制见[团队协作说明](docs/TEAM_COLLABORATION.md)。backend/README.md 和部分早期文档保留历史阶段说明，当前能力与 API 状态以本页及最新交接包为准。

团队在功能分支开发，通过 Pull Request 审查合并。前端只调用已开放 HTTP，不直接访问数据库、模型 SDK 或内部 Context；保持引用、未知状态、取消与幂等语义。

**当前可协作版本：C9 已验证基线；C10 正在本地验证。** [最新交付与已知限制](docs/releases/C9_VERIFIED_BASELINE.md)。历史阶段说明与测试数字按 CURRENT_STATUS.md 的最新入口解读。

# AegisAI

**面向 AI 生态的可信安全情报与自主调查智能体系统。**

用于“中国电子杯”第三届高校 ICT 产教融合创新大赛赛题九：智能体驱动的 AI 安全知识情报系统设计与实现。

## 队友从这里开始

- [当前阶段与待办（含24/49题版本说明）](CURRENT_STATUS.md)
- [智能调查 HTTP 接口对接](docs/PHASE12B_INVESTIGATION_API.md)
- [49题人工标注入口](evaluation/ground_truth/annotator_package/README.md)
- [前端交接入口](AegisAI_FRONTEND_HANDOFF_PACKAGE/README.md)
- [下载交接 ZIP](AegisAI_FRONTEND_HANDOFF_PACKAGE.zip)
- [队友接入、环境与分支协作](docs/TEAM_COLLABORATION.md)
- [快速入门](AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/FRONTEND_QUICK_START.md)
- [页面需求](AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/UI_REQUIREMENTS.md)
- [现有 API 与缺口](AegisAI_FRONTEND_HANDOFF_PACKAGE/api/API_STATUS.md)
- [完整前后端契约](AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/FRONTEND_TEAM_HANDOFF.md)
- [贡献与 PR 规范](CONTRIBUTING.md)
- [GitHub 分支和基线流程](docs/GITHUB_WORKFLOW.md)
- [本地检查与基础 CI](docs/DEVELOPMENT_GUIDE.md)
- [版本说明](docs/RELEASE_NOTES.md)

## 当前状态

截至 2026-10-11，代码已有 Security Intelligence Engine、Tool/Model Gateway、混合检索、受约束 Planner、DAG Runtime、调查/核验/风险分析专业 Agent、Integration Gate 和 Phase 11-D 内部调查总控及 AnswerEnvelope。

**Phase 12-B 已实现8个智能调查 HTTP 操作。** 本分支 FastAPI 共42个操作，新入口是 `/api/investigations`，覆盖创建、状态、Trace、Artifact、Integration Gate、AnswerEnvelope、取消和历史。旧34个操作保留；35个操作经本地代理放行，原7个其他写操作仍被拦截。对接以 [调查 API 文档](docs/PHASE12B_INVESTIGATION_API.md)为准；旧 assistant/query 保留兼容用途。

前端已有七个页面，采用原生 JavaScript ESM、History Router 和 Node 本地代理。8768 原型是 Mock；真实 API 前端默认 8769，后端默认 8000。GitHub 仓库不等于已经部署的比赛演示网站。

Phase 12-B 实施时全量回归为1288项通过（原1261项加新增27项），记录见 [PHASE_12B_RESULT.md](PHASE_12B_RESULT.md)。集成准备的检查另行记录，不能重复宣称又运行了全套数据库测试。AegisBench 新版候选为49题，人工批准尚未登记；旧v0.1的24题保留，标注人员使用新版题目与规范。合成示例、Mock模型和机器参考不能当作人工标准答案或正式准确率。

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

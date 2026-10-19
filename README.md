# AegisAI

智能体驱动的 AI 安全知识情报系统设计与实现。用于“中国电子杯”第三届高校 ICT 产教融合创新大赛赛题九，参赛组号 F9-014。

AegisAI 面向 AI 软件组件的安全情报调查：采集漏洞公告与技术资料，核对产品、包身份、维护分支和登记资产版本，返回带证据引用的影响判断与处置建议。当前交付用于本地研究和演示，需要分析人员复核重要安全结论。

## 从这里启动

1. 阅读 [Windows 快速启动](QUICKSTART_WINDOWS.md)，准备 Python、Node.js、PostgreSQL 和真实模型服务。
2. 按说明初始化自己的空数据库、安装依赖，再分别启动后端与前端。
3. 打开 `http://127.0.0.1:8769/assistant`，选择真实 API 模式，提交调查。
4. 按 [演示步骤](docs/release/DEMO.md) 查看任务进度、证据、核验和 Gate 状态。

首次克隆不包含数据库备份、模型权重或个人凭证。默认 Mock 配置用于协议开发，不能完成任意真实调查；运行真实模型前须显式配置供应商及模型名称。

## 系统如何工作

`公开来源 → 采集与富化 → Evidence / Claim → 调查规划 → Runtime → Verification → 资产风险 → Integration Gate → 结构化答案`

- **情报监测**：接入漏洞数据库、安全博客和论文资料，保留原文定位、采集记录及同步状态。
- **情报富化**：组织 CVSS、CWE、版本范围、PoC 和补丁候选；区分上游与下游包，保留维护分支及来源关系。
- **受约束调查**：Planner 选择工具；服务端独立检查必要任务、依赖和权限，缺失条件时拒绝执行或请求补充。
- **可追溯结果**：Evidence 关联原文，Claim 表达待核验事实，Verification 保留支持、冲突和不足；Gate 对当前调查交付作统一检查。
- **现有工作台**：调查提交、进度、Trace、Artifact、结果、引用、风险和人工复核状态均有页面实现。

当前分支已整合团队的新版总览看板、资产/复核详情、全局搜索与调查工作台，并保留后端接口适配。合并来源、冲突处置和本次联通验证见[前后端整合记录](docs/FRONTEND_BACKEND_INTEGRATION.md)。

## 主要入口

|内容|位置|
|---|---|
|后端、数据库迁移|[`backend/`](backend/)、[`backend/alembic/`](backend/alembic/)|
|前端工作台与同源代理|[`frontend/`](frontend/)|
|环境变量模板|[`backend/.env.example`](backend/.env.example)|
|调查接口与 TypeScript 契约|[`docs/PHASE12B_INVESTIGATION_API.md`](docs/PHASE12B_INVESTIGATION_API.md)、[`docs/frontend-contracts/`](docs/frontend-contracts/)|
|当前技术报告|[`docs/submission/AegisAI_Technical_Report.docx`](docs/submission/AegisAI_Technical_Report.docx)|
|架构、核心代码与运行边界|[交付说明](docs/release/ARCHITECTURE.md)、[验证记录](docs/release/VALIDATION.md)|
|演示与视频说明|[`docs/release/DEMO.md`](docs/release/DEMO.md)|
|官方赛题|[`requirements/sources/competition_problem_9.pdf`](requirements/sources/competition_problem_9.pdf)|
|数据源及许可|[`DATA_SOURCES.md`](DATA_SOURCES.md)、[`THIRD_PARTY.md`](THIRD_PARTY.md)、[`licenses/`](licenses/)|

## 环境与适用范围

后端采用 Python 3.12、FastAPI、Pydantic、SQLAlchemy 和 PostgreSQL；前端采用原生 JavaScript ES modules 与 Node 本地代理。模型通过现有兼容接口调用，权重、供应商权限及内存需求由所选模型决定。`frontend` 的 `jsdom` 是 DOM 测试开发依赖。

已保存限定场景的真实调查与完整评测记录；验证范围见[专门说明](docs/release/VALIDATION.md)。Windows Worker 组合执行、并发、取消/超时后的恢复和跨机冷启动仍有未解决或未充分验证的部分。有限真实 HTTP 运行支持本地演示，不构成生产级可靠性证明。

历史 `PHASE_*`、`reports/` 和旧交接说明继续保留供追溯；新机器的操作以本页及 Windows 快速启动为准。

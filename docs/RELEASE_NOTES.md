# AegisAI 发布说明

## v1.0-phase11D

基线提交：d5bf67321fa9641d01260234c0f3c9691fed2ca3。标签固定，不随后续文档/工程提交移动。

包括 Security Intelligence Engine、Tool/Model Gateway、Hybrid Retrieval、受约束 Planner、DAG Runtime、三个专业 Agent、Integration Gate、Investigation Orchestrator 和 AnswerEnvelope 的已有实现，以及 Phase 12-A.5 前端交接契约/独立交接包。

已有七个前端页面；当前 FastAPI 共 34 个 HTTP 操作。Phase 11-D 完整调查闭环为 Python 内部服务，新调查 HTTP 生命周期尚未开放；不要把本标签描述成完整网站已上线。

历史工程验收 1261 项通过，仅为历史记录；不是本次 Phase 13-A 重跑，也不是安全情报准确率。模型/示例 Mock 标签持续保留。

## Phase 13-A 工程维护

- 增加 feature/backend 与 feature/frontend 协作分支。
- 增加贡献规范、开发指南、PR 模板与版本/协作流程。
- 建立基础 GitHub Actions：仓库安全、Python 无数据库单元/契约、前端测试/契约类型。
- Action 使用官方仓库完整 SHA；Gitleaks 官方归档有 SHA256 校验；不配置生产凭据。
- 初始 84 条扫描候选复核为历史非私密内容，使用 60 个准确历史指纹，不排除整个目录或规则。
- 保留所有 Agent、数据库、API、前端业务与历史 Git 基线；未合并队友代码。
- 实际 TypeScript 编译暴露旧 JsonValue 声明 TS2456。仅将类型文档的递归 Record 改为等价索引签名，同步交接元数据与 ZIP；JSON Schema/wire 字段未变。原版本仍在固定标签与 Git 历史中。

本地与 GitHub 执行证据及限制见 [Phase 13-A 报告](../PHASE_13A_RESULT.md)。私有仓库套餐暂不支持强制分支保护。

## 待实施

**Phase 12-B**：已有计划，待授权暴露 Phase 11-D 的 8 项公共调查操作并进行前后端联调。前端队友继续独立开发，无需等待后端工程维护结束。

**Phase 13-B 建议**：AegisBench 业务评测、真实安全数据标注、真实模型对照和场景 Replay。尚未开始，不在本发布中宣称成绩。

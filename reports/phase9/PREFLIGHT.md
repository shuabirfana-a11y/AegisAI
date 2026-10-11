# Phase9依赖检查

本轮依据71节用户阶段要求，复读requirements、research/data_sources、design/database、Phase6—8报告及Tool V0/V1/V2；SHA256与全文目录登记见input_manifest/document_inventory。既有阶段正式状态仍PARTIAL，不改写历史。

现有278漏洞、369原文、48Claim、76Evidence、5个明确演示资产；KnowledgeDocument/Chunk、AgentRun、ToolCallRecord均已预留但无业务记录。产品、版本、PoC、Patch、核验及资产风险全部通过现有service复用。

需要薄封装：Query/Evidence/Timeline、Phase7调查与核验、Phase8资产查询；现有Python服务缺少统一Gateway Envelope、可用权限及运行预算。工具输入需Pydantic严格校验；不接任意SQL/URL/Shell。

需要新增：知识文档/分块入库与本地多语言向量、统一网关、任务DAG/结构化Artifact/验证门禁、并行角色执行、Retry/Replan、Agent审计API、前端骨架与Dify可复现配置。pgvector在本机17.11包中不可用；继续PostgreSQL存Float数组并做有界精确余弦，不引入外部向量数据库。

本机无Docker、WSL未安装，当前进程非管理员；本地Dify正式启动需要Windows组件和运行环境，阶段状态不得冒充PASS。用户已明确选择本地Dify，准备固定版本部署、工作流和凭据说明；当前没有生成式模型服务，确定性角色执行与LLM辅助能力分别说明。

已知问题：真实版本范围冲突/未核验、Phase7/8人工gold待标注、其他生态UNKNOWN、来源覆盖有限、生产IAM/高可用未验收。不能通过Agent隐藏这些限制。所有原文与外部内容保持UNTRUSTED_EXTERNAL_CONTENT。


## 2026-10-06实际复核

真实DEV/Test PG已恢复，DEV0004。Backend8000、Frontend8769实际启动并验证，七路由无mock通过41项。20文档98向量，369历史Raw/551冻结输入不变。三角色为确定性，Dify启动仍缺Docker，生成模型用户选择稍后配置。所有runtime范围/失败见TEST_RESULTS.md和KNOWN_ISSUES.md，不继承旧报告PASS。

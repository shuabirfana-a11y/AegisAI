# Phase 14-B3：AI 安全知识关联推理增强完成报告

日期：2026-10-14；项目：AegisAI（ICT 命题九）。

## 1. 完成内容

新增基于既有 PostgreSQL 模型的轻量知识关联投影，支持 Vulnerability、Component、Version、Asset、Evidence、Risk 六种实体及七种有来源记录的关系。没有图数据库、迁移、新 Agent 或新增模型调用。原 Planner、Runtime、Verification、Risk 和 Integration Gate 业务源码未改。

两个只读 API 已实现并实际通过 HTTP 验证：

- `GET /api/v1/intelligence/vulnerabilities/{id}/graph`
- `GET /api/v1/intelligence/graph/query`

## 2. 实体与关系

Vulnerability → Component → AffectedRange，以及 Component → DeployedVersion → Asset 两条链分别保留。关联依据是持久化包 ID、生态、范围、库存与来源，不靠名字相似或模型猜版本。

Vulnerability → Evidence 保留 Claim、RawDocument、SourceObservation、时间、hash 和状态。Asset → Risk 只读已保存且绑定校验通过的 Gate/Answer；Risk → Evidence 只包含真正参与风险 factor 的证据。

影响范围确认要求现有 trusted_claim 成立，范围语义相同，并存在同一组完整性有效、当前、新鲜、值匹配且获当前 revision 核验引用的支持 Evidence。候选/冲突/未知不提升为确认。超过集合、证据、嵌套和传输预算显式截断。

## 3. Agent 关联方式

通过既有 InvestigationReader / AnswerSourcesLoader 读取原 Investigation、Verification、Analysis、Gate、Answer，保留三 Agent 的 run_id / artifact_id / schema_version。按 owner 和目标绑定验证，不修改不可变 Artifact、不重跑工具或 Agent。

本阶段提供已有调查结果的关联视图，没有给原 InvestigationArtifact 添加 Graph 字段，也没有替换 Agent 检索路径。

## 4. 查询与前端

组件/生态/来源严重程度的 SQL 关系查询支持分页，TypeScript/OpenAPI 与真实 Schema 同步。IntelligenceApiClient 增加 graph/queryGraphs 方法，前端交接包同步导出；本地代理只对精确 Graph 路由附加服务器 Demo 凭据。

复杂问题可以先通过组件关联获得候选漏洞，再读取既有调查的版本、资产和风险决策。本阶段没有新增自然语言 Planner 模板或前端图形页面，界面团队可使用实体/关系契约进行可视化。

## 5. 修改文件

- 新增 `backend/app/knowledge/graph_schemas.py`、`security_graph.py`、`investigation_graph.py`。
- 修改 `backend/app/api/intelligence.py`：两个只读路由。
- 新增 `backend/tests/test_phase14b3_graph.py`、`backend/tests/orchestration/test_knowledge_graph.py`；更新 API 操作清单断言和 CI 便携测试列表。
- 新增 `frontend/contracts/knowledge-graph.ts`；扩展 intelligence client、server 代理及代理测试。
- 更新两个导出脚本，同步 `docs/frontend-contracts/` 与 `AegisAI_FRONTEND_HANDOFF_PACKAGE/` 的 OpenAPI、TS、HTTP 清单及 client。
- 更新 `docs/FRONTEND_HANDOFF.md`，新增 `docs/phase14b3/` 设计、接口、验证、真实演示 JSON。

未提交工作目录数据库、日志、个人环境或无关 Phase 14-C 审查文件。

## 6. 测试结果

新增知识关联/调查联动 **30 项通过**；相关 PostgreSQL 回归 **120 项通过**（包含新增测试）；便携后端 **675 通过、1 排除**；前端 **68 通过**；TS、24 个 JS 语法、OpenAPI/契约和 18 项工程门禁通过。命令、探索性失败和测试隔离说明见 `docs/phase14b3/VALIDATION.md`。没有将数量合计为业务准确率。

独立审查发现的范围借证、Risk 借证、遍历预算和支持证据交集问题已修复；最终复查无剩余 P1/P2。

## 7. 真实演示链

实际读取 CVE-2025-47277 官方公告/OSV 快照和已有真实 Qwen 调查：vLLM → 部署 0.6.5 → 明确标记 Demo 库存 → 已验收历史 HIGH/P1 → 已保存的 0.8.5 修复建议。返回 **19 个实体、23 条关系、三专业 Agent 引用**，Gate PASS。

模式为 `SAVED_REAL_INVESTIGATION_READ_ONLY_PROJECTION`，SQL 只读，无新模型调用。已有模型记录为 REAL / openai_compatible / aegisai-qwen25-planner:latest。不是本阶段新运行的 Online Evaluation，不是生产扫描。

## 8. 当前限制

- 查询覆盖已有持久化 AffectedVersionRange 的本地情报；仅有文字 Claim、没有范围记录的关系不会自动构建。
- 来源严重程度/CVSS 筛选包括保存的来源评分，不等于当前资产风险；默认图不含资产。
- Risk 是历史决策，必须展示 evaluation_time / historical_snapshot / current_safety_evaluated=false。库存变化或 Gate 阻断时保留历史信息，当前结论 UNKNOWN。
- 长内容或集合预算会造成部分图，truncated/warnings 必须显示；完整内容通过原记录读取。
- 未开发图形页面、通用自然语言图查询、复杂图推理引擎；现有调查逻辑保持稳定。
- 没有执行 Benchmark、宣称准确率或改变任何人工 Ground Truth。

## 9. 下一步

本阶段结束于可审查功能分支和 PR，未合并、未冻结初赛版本。下一阶段可由前端使用本次契约展示关系链，或在负责人审查后集成到稳定版本；需新的任务指令。

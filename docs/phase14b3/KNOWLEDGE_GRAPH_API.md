# Phase 14-B3 前端知识关联契约

接口来自实际 FastAPI/Pydantic 实现。两个接口都是 GET，只读取已有数据，不产生调查、采集、模型调用或风险重算。完整结构以 `docs/frontend-contracts/intelligence-http.openapi.json` 和 `intelligence-http.d.ts` 为准。

## 请求

| 接口 | 参数 | 返回 |
| --- | --- | --- |
| `/api/v1/intelligence/vulnerabilities/{id}/graph` | id 为 CVE/漏洞 UUID；可选 asset_id、include_assets（默认 false）、investigation_id | KnowledgeGraph |
| `/api/v1/intelligence/graph/query` | 可选 component、ecosystem、minimum_severity、include_assets；offset ≥ 0，limit 1–10 | KnowledgeGraphPage |

均需现有 Bearer 认证。actor 来自服务端身份配置，客户端不能提交其他 owner。未认证 401、服务端未配置本地认证 503、对象不存在或无权访问 404、投影/调查绑定不一致 409、参数非法 422。错误正文沿用 FastAPI `detail`，与调查 API 的 `ApiError` 不是同一个错误 Schema。

查询按 package_name 或 canonical_name 精确匹配，生态也是精确匹配；`vllm` / `vLLM` 可分别对应包名和产品名，`llm` 不做模糊命中。minimum_severity 使用保存的来源严重程度或 CVSS，不是当前资产 Risk 筛选。查询范围限已采集且有持久化 AffectedVersionRange 的漏洞，total 是 SQL 候选数量；分页内的图可能截断。

## Schema

KnowledgeGraph：schema_version、vulnerability_id、canonical_id、nodes、edges、truncated、warnings、limitations、investigation_id、agent_references、gate_status、answer_id、content_trust_level。

KnowledgeNode：id、type、label、data。type 为 VULNERABILITY / COMPONENT / VERSION / ASSET / EVIDENCE / RISK。

KnowledgeEdge：id、type、source、target、status、source_records、claim_ids、evidence_ids、historical_snapshot。

| 节点 | data 中的实际字段与含义 |
| --- | --- |
| VULNERABILITY | vulnerability_id、cve_id、description、severity、cvss（保存的来源评分和 observation_id） |
| COMPONENT | package_identifier_id、name、display_name、vendor、type、ecosystem、namespace、purl |
| VERSION：AFFECTED_RANGE | version_kind、version、range_id、component_id、status、parse_status、introduced、fixed、last_affected、events、explicit_versions、is_current |
| VERSION：DEPLOYED | version_kind、version、component_id、status KNOWN/UNKNOWN、inventory_revision；component_id 此处是 AssetComponent ID |
| ASSET | asset_id、name、environment、exposure、is_demo、provenance=USER_INVENTORY_NOT_SCANNED |
| EVIDENCE | evidence_id、claim_id、source、reference、type、verification_status、is_current、stance、hash、raw_document_id、observation_id、locator、retrieved_at |
| RISK | level、priority、affected、historical_level、historical_snapshot、is_stale、evaluation_time、current_safety_evaluated=false、version_status、gate_status、source_artifact、conclusion_scope、reason、recommendation |

`data` 是分类型投影字典，当前生成 TypeScript 为 `Record<string, unknown>`。读取字段需要按 node.type / version_kind 校验，不能使用类型断言假定字段始终完整。实体ID是带类型的稳定 UUID5，不能把 graph node.id 当作数据库 UUID。

关系枚举：AFFECTS_COMPONENT、HAS_AFFECTED_RANGE、HAS_VERSION、DEPLOYED_ON、HAS_EVIDENCE、HAS_RISK、SUPPORTED_BY。状态枚举：SOURCE_ASSERTED、CANDIDATE、CONFIRMED、CONFLICT、PENDING、REJECTED、INSUFFICIENT_EVIDENCE、UNKNOWN、USER_INVENTORY。

SOURCE_ASSERTED 表示来源声称；USER_INVENTORY 表示库存登记。只有同一组完整性有效、当前、新鲜、值匹配并获当前 Claim revision 核验引用的支持 Evidence 可以确认影响范围。冲突、未知和候选状态保持原义。HAS_EVIDENCE 表示关联，不能把 neutral/contradict 证据当作支持证据。

## 资产与已保存调查

默认图不含资产。指定 asset_id 或 include_assets=true 只读取当前 actor 的未删除资产，并按精确包关系连接部署版本；组件名字相似不会自动确认受影响。

指定 investigation_id：复用已有 InvestigationReader 和 AnswerSourcesLoader 核对 owner、调查根、Artifact hash 和 Gate/Answer 绑定，再提供三专业 Agent 的 run_id/artifact_id/schema_version。Graph 是原调查结果的补充只读视图，没有修改 InvestigationArtifact。

Risk 只来自已保存 Answer/Risk Artifact；Gate PASS/PASS_WITH_WARNINGS 且接受范围及库存 revision 匹配时，显示已验收的历史决策。Gate 阻断或库存不一致显示 UNKNOWN，不重新推断。所有 Risk 必须连同 `evaluation_time`、`historical_snapshot=true`、`current_safety_evaluated=false` 展示；即使 is_stale=false，也不能表述为当前安全保证。SUPPORTED_BY 仅连接参与该风险决策的 factor evidence，不借用所有 verified_claims。

## Client 和界面

`frontend/contracts/knowledge-graph.ts` 导出类型；现有 `IntelligenceApiClient.graph(id, options)`、`queryGraphs(options)` 负责 transport。交接包有相同副本。

```typescript
const api = new IntelligenceApiClient('', () => inMemoryToken);
const candidates = await api.queryGraphs({ component: 'vllm', ecosystem: 'PyPI', minimum_severity: 'HIGH' });
const linked = await api.graph('CVE-2025-47277', { investigation_id: selectedInvestigationId });
```

凭据只放现有内存会话或服务端 local-demo 配置，不写入源码、浏览器持久化存储或 URL。本地代理只给精确 Graph 路由附加服务器 Demo 凭据，原公开情报路由不接收它。

图节点/边上限 160/320，单图 JSON ≤128 KiB；有集合、嵌套数组和证据预算。`truncated=true` 或 warnings 出现时，必须显示部分视图标记，完整事实通过原 record/Artifact 查询。外部标题和内容为 UNTRUSTED_EXTERNAL_CONTENT，按普通文本渲染，不执行 HTML。

本阶段没有新增前端图形页面，也没有新增自然语言 Planner 模板。复杂问题可以通过组件/生态/来源严重程度关联查询候选漏洞，再关联已完成的调查结果读取风险；完整调查仍由原有接口发起。

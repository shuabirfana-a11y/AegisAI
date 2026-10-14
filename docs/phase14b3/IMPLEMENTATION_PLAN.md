# Phase 14-B3：轻量知识关联实施设计

用户已授权实体、关系、既有调查接入、只读接口、契约、测试和演示链。本阶段在现有 SQL/版本/Evidence/调查链之上增加投影视图，不增加图数据库、Agent、模型或数据库迁移。

## 数据与边界

- Vulnerability、PackageIdentifier/Product、AffectedVersionRange、AssetComponent/Asset、Evidence/Claim 为既有实体来源。
- 同一组件按包 ID 和生态关联；部署版本和影响范围是不同的 Version 节点。名字相似不会产生确定影响关系。
- 每条关系提供来源记录、Claim / Evidence 引用和核验状态；来源断言、库存记录与已验收结论分开。
- 资产严格按 actor 权限过滤；默认不包含资产，显式指定资产或 include_assets 后才查询库存。
- 风险不从 CVSS 自动猜测。指定 investigation_id 时读取已经校验绑定的 Investigation / Verification / Risk / Gate / Answer；只投影已有结果，Gate 阻断不变为 PASS。
- Graph 不改变原 Artifact、不调用模型、不运行扫描、不触发风险重算。调查结果关联通过额外只读 graph 视图展示，并保留原 run / artifact / answer 引用。

## 接口

- GET `/api/v1/intelligence/vulnerabilities/{id}/graph`：CVE/UUID 的关系投影，支持 asset_id、include_assets、investigation_id。
- GET `/api/v1/intelligence/graph/query`：组件/生态/来源严重程度的 SQL 实体关联查询，支持分页；严重程度不等于资产风险。
- 复用现有认证，输出严格 Pydantic；前端生成 KnowledgeNode / KnowledgeEdge / KnowledgeGraph 类型和 HTTP client，不新增页面。

## 实施顺序

先建立失败测试：关系来源、范围与部署版本区分、权限/删除/未知版本、冲突/陈旧证据、查询分页/不存在对象、调查根绑定与 Graph 只读。再实现 Schema、SQL 投影、既有调查结果适配、API、TypeScript/OpenAPI 导出。最后运行专用 PostgreSQL 集成、便携回归、前端契约及 CI，并导出真实官方快照 + 明确 Demo 库存的已保存调查关系链。

所有遍历设固定预算，截断显式标记；不为完整图补造缺失边或事实。完成后停在本阶段 PR 审查，不合并、不进行新模型优化或正式 Benchmark。

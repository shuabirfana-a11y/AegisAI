# Phase 14-A 实施范围

根据用户本轮已给出的实施目标，采用现有采集、知识入库、富化与HTTP链路的增量扩展。赛题本地PDF四页已读取，要求同时覆盖多源监测、知识同步、富化和问答；源个数不等于独立来源类别，也不预先承诺评分。

## 已有与缺口

- 已有CVE/OSV/CISA Collector、SyncService、不可变RawDocument、身份合并和版本/CVSS标准化。
- 已有厂商公告、PoC/Patch/EPSS/版本富化、Claim-Evidence核验及资产匹配；不重写这些模块。
- 已有KnowledgeDocument/Chunk/Relation和本机Embedding检索，但自动RSS/arXiv入库尚缺。
- 缺NVD与原生GHSA接入、固定源监测循环、跨类型的前端情报投影。

## 本阶段补强

1. 原生NVD与GHSA/官方厂商公告适配器，使用原Raw/SyncService/NormalizedIntelligenceRecord；旧三种来源保持。
2. 固定白名单博客RSS和arXiv Atom，小范围有界请求、XML安全检查、条件缓存、逐来源失败隔离。论文仅采集元数据/摘要，不下载全文。
3. 原KnowledgeDocument/Chunk入库，按原文修订保留历史。基于显式漏洞ID/产品词形成可解释候选论文/文章关联；不自动确认版本影响或可用利用。
4. CLI一次运行/周期运行，遵守各源间隔；新增后台数据不进入既有Benchmark隔离库。
5. 新只读HTTP统一情报DTO，展示评分、CWE、版本、PoC候选、关联文献和证据出处。资产数据仅通过现有受保护入口读取，不在公共列表泄露。
6. 调查继续走现有Investigation HTTP API/Orchestrator。知识文档可通过已有semantic_search被问答模块读取；不另建Agent或模型调用。

## 验证

先运行已有正常化/富化测试；针对源字段映射、XML攻击、游标/失败/幂等、文档关系、原文定位、PoC边界和HTTP权限增加测试，先观察失败再实现。数据库验收只使用专用测试库，新演示数据使用独立新库；不运行迁移重构，不动开发/实验数据库。

最后执行相关集成及工程回归、导出OpenAPI/TypeScript契约、完成最小采集→富化展示→已有问答工具验收。实际网络失败、未入库来源、缺资产或待核验结论必须分开报告。测试夹具不冒充实时采集或准确率。

## 保护与停止

Agent/Planner/Runtime/Gate/LLM及全部Benchmark/人工金标/历史实验保持字节；不新建专业Agent、不降低核验标准、不扫描未经提供的资产、不做前端重构。交付PHASE_14A_RESULT.md、源与接口清单、真实测试记录和交付文件夹后停止。

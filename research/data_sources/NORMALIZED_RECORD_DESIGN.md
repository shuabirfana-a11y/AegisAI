# NormalizedIntelligenceRecord（业务契约设计 v0.1）

这是Collector之后Normalizer输出给后续处理的统一契约，不是数据库表/ORM，不是正式业务代码。本轮只保存设计和JSON示例。

| 字段 | 类型/允许缺失 | 说明 |
|---|---|---|
| schema_version / record_type | string / enum | vulnerability, advisory, paper, analysis, ai_event, knowledge, standard, policy |
| external_ids | array of {namespace,value} | CVE/GHSA/OSV/arXiv/DOI/标准ID/官方URL；没有CVE不造 |
| source / external_id / raw_document_id | string，必有 | 源注册ID/源内身份/raw关系；源目录观察无正文不能伪装内容记录 |
| title / description / language | string或null | 按原文；描述性摘要来自源，LLM摘要以后另存derived |
| published_at / modified_at / retrieved_at | RFC3339 UTC或null | retrieved必有；日期原字符串/粒度保留metadata，未知不代填 |
| products | array或null | 产品/vendor/官方repo与别名依据；不能仅同名连实体 |
| packages | array或null | ecosystem/name/PURL，生态大小写按官方规则，原值并存 |
| affected_versions | array或null | 原expression、range_type、events、explicit_versions、package、source locator；不能统一强塞SemVer |
| fixed_versions | array或null | 明确版本/包/适用分支/证据；last_affected不是fixed |
| cvss | array或null | version/vector/base_score/source/provider/scope/locator，多分并存 |
| cwe | array或null | 来源明确的CWE ID，未知不按描述猜 |
| references | array或null | URL/type/tags/publisher，引用默认不自动跟随；去重仍保留原位置 |
| exploitation / epss | object或null | known_exploited/not_listed_as_of/unknown带catalog；分数/date/model版本完整 |
| document_metadata | object或null | 作者/论文版本/标准edition、draft/final、jurisdiction、显式effective日期与来源 |
| record_status / upstream_lineage | enum / array | published/withdrawn/rejected/unknown；提供者和转载关系 |
| field_provenance / extensions | object | 字段→raw locator/原值；未知上游字段仍保留raw及extensions，schema变化隔离 |

null表示未提供/未知，[]仅在确实观测到空集合时使用，不能把未解析的字段写[]造成“没有”。未知另记reason：not_provided/unsupported/ambiguous/not_fetched/withdrawn。Normalizer禁止LLM填CVSS、CWE、包、fixed、时间、POC可用性、commit或license。

各类型可共享来源/时间/引用，vulnerability专属的cvss/versions对paper、standard、policy留null；别用空CVE把知识塞成漏洞。标准/政策区分源明确published/effective与系统observed，时效口径对类型单列。AI事件记录来自出版者文档的候选观察，而不是LLM创造事件。

examples.json含真实结构化样本的最小映射及论文/政策/标准样例，保留实际raw ID/hash和原生时间。它是设计例而非标注gold或正式Normalizer实现。

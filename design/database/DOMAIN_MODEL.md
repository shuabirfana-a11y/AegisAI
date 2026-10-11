# 核心领域模型

共有43张显式表。用户文档列出的38模型全部覆盖；增加SourceObservation、VulnerabilityIdentifier、VerificationEvidence、KnowledgeVulnerabilityRelation与AgentCitation五个对象，分别解决逐次原文来源、一公告多漏洞、核验证据FK、文献关系及回答固定引用，均有当前需求。模型实现不等于相关业务已运行。

| 模型 | 表 | 层 | 当前用途 |
|---|---|---|---|
| AgentRun | `app.agent_runs` | 应用/执行记录 | 用户请求与可审计摘要/状态/时延，尚未连接Agent |
| Asset | `app.assets` | 应用/执行记录 | 授权资产的轻量身份、owner和演示标识，未实现扫描器 |
| AiSecurityCategory | `core.ai_security_categories` | 标准化领域 | 解释性AI风险分类目录，无伪造分类评分 |
| Product | `core.products` | 标准化领域 | 面向用户的产品身份，与分发生态包分开 |
| Vulnerability | `core.vulnerabilities` | 标准化领域 | 去重后的问题主体，不承载全部富化字段 |
| Weakness | `core.weaknesses` | 标准化领域 | CWE身份；不猜缺失分类 |
| EvaluationDataset | `evaluation.datasets` | 独立评测 | 隔离评测集合、split/as_of/rubric和冻结hash |
| Source | `raw.sources` | 原文与获取 | 注册来源/类别/权威范围/覆盖与checkpoint，研究检查时间不充当运行成功 |
| ToolCallRecord | `app.tool_call_records` | 应用/执行记录 | 完成/失败/timeout工具事件，结构化输入输出摘要，不保存私有思维 |
| ExternalIdentifier | `core.external_identifiers` | 标准化领域 | 命名空间内唯一的外部身份，公告身份不等于单一漏洞 |
| PackageIdentifier | `core.package_identifiers` | 标准化领域 | 生态/namespace/包名/PURL的分发身份，CPE/repository作为补充 |
| ProductAlias | `core.product_aliases` | 标准化领域 | 有来源的名称候选；重名可歧义，未审别名不授权自动合并 |
| Reference | `core.references` | 标准化领域 | 原始URL及经明确规则形成的canonical URL |
| EvaluationCase | `evaluation.cases` | 独立评测 | 输入、真值状态、来源快照、lineage分组，draft不是gold |
| EvaluationRun | `evaluation.runs` | 独立评测 | 固定数据集/代码/模型/配置与环境的一次已结束评测 |
| RawDocument | `raw.raw_documents` | 原文与获取 | 不可变源内容修订与准确字节hash，未知字段和原始出版时间并存 |
| SyncRun | `raw.sync_runs` | 原文与获取 | 一次真实同步及分类计数/游标/缺口，失败不推进完整成功 |
| AssetComponent | `app.asset_components` | 应用/执行记录 | 精确/原始版本、包身份及库存修订；歧义可null |
| EvaluationResult | `evaluation.results` | 独立评测 | 每题prediction/correct/status/完整latency与rubric，失败不移除分母 |
| EpssSnapshot | `intel.epss_snapshots` | 可信情报与知识 | 每日分数/percentile/model及更正raw修订，缺失不填0 |
| KnowledgeDocument | `intel.knowledge_documents` | 可信情报与知识 | 论文/公告/分析/事件/标准/政策，保留类型/版次/发布机关/许可 |
| KnownExploitation | `intel.known_exploitation` | 可信情报与知识 | 完整目录下的收录/未在该次目录/未知，不以false宣告没被利用 |
| SourceObservation | `raw.source_observations` | 原文与获取 | 某次获取或标准化完成观察，源/原文/locator/lineage/normalizer独立保留 |
| AffectedVersionRange | `core.affected_version_ranges` | 标准化领域 | 某源/包/分支的原范围和机器表示，失败/unsupported保持原文 |
| AiRelevanceAssessment | `core.ai_relevance_assessments` | 标准化领域 | relevant/irrelevant/uncertain、方法/版本/理由及时间 |
| CvssAssessment | `core.cvss_assessments` | 标准化领域 | 来源/评估版本/范围独立评分，选择由typed Claim表达 |
| VulnerabilityIdentifier | `core.vulnerability_identifiers` | 标准化领域 | 精确身份关联；CVE单一归属，公告可连接多个漏洞 |
| VulnerabilityReference | `core.vulnerability_references` | 标准化领域 | 公告/引用对多漏洞的关联和原始观察 |
| VulnerabilityWeakness | `core.vulnerability_weaknesses` | 标准化领域 | 多CWE及各自来源观察 |
| KnowledgeChunk | `intel.knowledge_chunks` | 可信情报与知识 | 冻结文档revision/chunker/index与原文定位，尚未切块或生成向量 |
| PatchCandidate | `intel.patch_candidates` | 可信情报与知识 | 完整commit/PR/release/fixed候选及包/分支适用关系 |
| PocCandidate | `intel.poc_candidates` | 可信情报与知识 | PoC线索；关联可信度与可用性分别保存，不执行代码 |
| VulnerabilityAiCategory | `core.vulnerability_ai_categories` | 标准化领域 | 多类别关系及评估依据 |
| Claim | `intel.claims` | 可信情报与知识 | 带scope的结构化候选/采用结论，当前投影与历史核验分开 |
| AssetVulnerabilityMatch | `app.asset_vulnerability_matches` | 应用/执行记录 | 三态影响、版本/库存/Claim/范围快照与理由，旧结果不可覆盖 |
| ReviewTask | `app.review_tasks` | 应用/执行记录 | 围绕Claim的人工复核，P1工作状态、乐观revision和前后决定 |
| Evidence | `intel.evidence` | 可信情报与知识 | Claim支持/反驳/中立原文、immutable raw/observation、定位和lineage |
| KnowledgeVulnerabilityRelation | `intel.knowledge_vulnerability_relations` | 可信情报与知识 | 知识到漏洞的typed关系及Claim，不以相似度直接确认 |
| VerificationResult | `intel.verification_results` | 可信情报与知识 | 不可变核验修订，记录四态、理由、执行者和采用值 |
| AgentCitation | `app.agent_citations` | 应用/执行记录 | 回答断言对应Evidence及真实Claim核验revision，旧引用不漂移 |
| AuditLog | `app.audit_logs` | 应用/执行记录 | actor/action/before/after/reason/request指纹的追加审计 |
| IntelligenceEvent | `intel.intelligence_events` | 可信情报与知识 | 有主体与证据的业务变化，源发生时间与系统发现时间分开 |
| VerificationEvidence | `intel.verification_evidence` | 可信情报与知识 | 某次核验确实使用哪些同Claim Evidence，FK防串证据 |

Product是产品，PackageIdentifier是生态分发身份；RawDocument是内容修订，SourceObservation是获取/标准化尝试；Claim是命题，Evidence是依据，VerificationResult是特定修订的审查结果。Review只以Claim为target，其typed subject可以是版本/PoC/Patch/CVSS/知识；不设计没有FK的万能target_id。

数据库使用unknown资产态，与文档示例uncertain语义一致，沿用冻结UX的affected/not_affected/unknown。公开API未来负责统一映射，不能把未知视为不受影响。

全部38用户模型都有表；KnowledgeChunk、Agent运行表和Evaluation四表仅预留存储并做约束，不启动这些业务。产品ecosystem来自包关系，一产品可在多个生态分发，不在Product硬编码单一生态。

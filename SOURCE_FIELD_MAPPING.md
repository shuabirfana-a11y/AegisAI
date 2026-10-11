> 历史预案。当前第2阶段已冻结的数据源方案见 [最终选型](research/data_sources/FINAL_DATA_SOURCE_SELECTION.md) 与 [字段映射](research/data_sources/SOURCE_FIELD_MAPPING.md)；本文件保留为调研历史，不作为当前范围依据。

# 源字段到内部事实的映射

本表是开发契约；`[]`表示逐项迭代的文档记法，实际Evidence必须生成确定的JSON Pointer（例如 `/containers/adp/0/metrics/0/other/content`），并关联raw sha256。原文和未识别扩展留在raw/metadata；不依靠字段名相似自动覆盖。来源目录与调度见 [DATA_SOURCES.md](DATA_SOURCES.md)。

## 结构化源

| 源 | 外部路径 | 内部字段/Claim | 转换与来源约束 |
|---|---|---|---|
| CVE | cveMetadata.cveId / state | vulnerability.cve_id / state | 规范CVE格式；REJECTED保留历史与理由并影响查询 |
| CVE | cveMetadata.datePublished / dateUpdated | source_published_at / source_modified_at | UTC，缺失null；container provider dateUpdated另存 |
| CVE CNA | containers.cna.title / descriptions[] | title / descriptions | 语言保留，描述为不可信内容；无title用安全的显示回退并记录basis |
| CVE CNA/ADP | affected[].vendor/product/packageName/collectionURL/packageURL/cpes | product/package/cpe_candidates | PURL验证后保留；名字映射按生态/官方repo规则，歧义UNKNOWN，CPE不是PyPI范围 |
| CVE CNA/ADP | affected[].versions[] / defaultStatus / versionType | affected_version_claim / raw ranges | 保存status/lessThan/lessThanOrEqual/changes等原语义；只支持已验证的生态解析，不猜SemVer |
| CVE CNA/ADP | metrics[].cvssV* | cvss_claim | vector/version/baseScore/提供者/时间保留；无metric不造0分 |
| CVE CNA/ADP | problemTypes[].descriptions[].cweId | cwe_claim | 逐来源保留；没有明确ID的文本留metadata |
| CVE所有容器 | references[].url/tags/name | reference_claim | container/provider/source_record+locator一起保存；相同URL不删来源关系 |
| CISA ADP | providerMetadata.orgId/shortName | evidence.publisher / lineage | 按已知provider识别，不依赖固定数组序号或title字符串 |
| CISA ADP | metrics[].other（type=ssvc）.content | ssvc_claim | options/id/timestamp/role/version原样保留；旧Exploitation=none不是今天未利用的结论 |
| OSV | id / aliases / related / withdrawn | source_record.external_id / identity_candidate / state | CVE别名精确对齐；多CVE别名不自动传递合并，related非identity |
| OSV | published / modified | source_published_at / source_modified_at | 与CVE时间独立；撤销/修订留事件 |
| OSV | affected[].package.ecosystem/name/purl | package / product规则候选 | PyPI名只规范大小写/-_.；PyTorch→torch由显式规则，不靠字符串相似 |
| OSV | affected[].ranges[].type/events | affected_range.events / intervals / parse_status | introduced含、fixed不含、last_affected含、limit不含；introduced=0是起点哨兵；未知生态/GIT返回UNSUPPORTED |
| OSV | affected[].versions[] | explicit_affected_versions | 保留显式枚举，不仅靠区间；与区间不一致时待复核 |
| OSV | events[].fixed | fixed_version_claim | 只采显式fixed，不由last_affected推下一版；一个漏洞可多个包/修复分支 |
| OSV | severity[] / database_specific.cwe_ids/severity | source-qualified cvss/cwe/severity | OSV severity.score可能是vector而非数字；不直接float，不覆盖CNA |
| OSV | affected[].database_specific.source | evidence.upstream_lineage | 指向Advisory Database等上游，聚合平台一致不增加独立发现票数 |
| OSV | references[] | reference_claim / patch_candidate | type是源标签；commit链接先Candidate，不自动verified |
| KEV | catalogVersion / dateReleased / count | catalog_snapshot元信息 | 整份响应hash与结构核验；count与数组长度不符则负匹配UNKNOWN |
| KEV | vulnerabilities[].cveID / dateAdded | kev_membership_claim / observed_effective_time | source snapshot下IN_CATALOG / NOT_IN_CATALOG / UNKNOWN；后者不表示未利用 |
| KEV | vendorProject/product/vulnerabilityName/cwes | 来源产品文本 / name / cwe_claim | 是CISA描述，不直接合并包实体；cwes及未知新增字段保留 |
| KEV | requiredAction/dueDate/knownRansomwareCampaignUse/notes | cisa_guidance_claim / context | 原文来源化；不把CISA日期当本组织必须的资产修复期限；Unknown保持Unknown |
| NVD | vulnerabilities[].cve.id/published/lastModified/vulnStatus | identity / 源时间 / analysis_status | 状态是NVD分析状态，非CVE身份状态 |
| NVD | cve.metrics.cvssMetricV*[] | cvss_claim | 区分每项source/type/version及vector；多分数并存 |
| NVD | cve.weaknesses[] / configurations[] / affected（如存在） | cwe_claim / cpe_configuration / metadata | CPE节点AND/OR、negate、vulnerable和边界保留；未验证逻辑不扁平化为包范围 |
| NVD | cve.references[] | reference_claim | source/tags保存；缺patch标签不否认存在修复 |
| GHSA | ghsa_id/cve_id/identifiers/published_at/updated_at/withdrawn_at | external identity / 源时间 / state | 与OSV同GHSA合并上游lineage；withdrawn留历史 |
| GHSA | vulnerabilities[].package/vulnerable_version_range/first_patched_version | package / affected/fixed_claim | 解析器按生态；原范围完整留存，fixed=null合法 |
| GHSA | cvss / cvss_severities / cwes / references | cvss/cwe/reference_claim | 当前字段兼容按实际schema；不丢未知新版本字段 |
| EPSS | data[].cve/epss/percentile/date | epss_daily_claim | decimal [0,1]，每日独立值；日期非抓取时间，缺记录为UNKNOWN |

字段依据：[CVE schema](https://github.com/CVEProject/cve-schema)、[OSV schema](https://ossf.github.io/osv-schema/)、[KEV JSON/schema](https://github.com/cisagov/kev-data)、[CISA ADP](https://github.com/cisagov/vulnrichment)、[NVD API](https://nvd.nist.gov/developers/vulnerabilities)、[GHSA API](https://docs.github.com/en/rest/security-advisories/global-advisories)、[EPSS](https://www.first.org/epss/data.html)。具体真实路径见 [契约验证](evaluation/source_contracts/validation.json)。

## 文章、代码和知识源

| 源 | 映射对象 | 边界 |
|---|---|---|
| GitHub公告/repo/commit | vendor_advisory / patch_candidate / poc_candidate；repo、完整SHA、diff hash、文件、引用依据 | 不执行PoC；静态diff存在只证明代码线索，不证明修复覆盖所有分支 |
| Vendor网页/公告 | advisory_document、厂商/产品/发布日期/URL、原文locator | 每站parser单独验证；任意正文不能发起工具调用 |
| arXiv Atom | paper_id/version/title/authors/published/updated/summary/links；paper_candidate与关联理由 | 标题/关键词不确认漏洞关联；全文许可与元数据分开 |
| RSS/博客 | feed_id/guid/link/title/published/summary与raw正文 | URL/guid仅帮助去重，转载保留lineage；具体feed未验证就disabled |
| ATLAS | technique/case ID、版本、名称、官方URL；technique_mapping_candidate | 需要上下文与证据审阅，不能靠CWE自动确证攻击技术 |
| OWASP | 风险类别ID、版本、说明、出处；risk_category_candidate | 是解释标签，不作为独立漏洞影响证据 |

## 每个事实必需的证据包

`claim=(predicate,scope,value,value_hash,status)`；`evidence=(source_record,raw_hash,locator,excerpt_hash,publisher,retrieved_at,source_modified_at,upstream_lineage)`；通过多对多链接保存support/refute/context。raw哈希针对实际响应字节；excerpt哈希针对有明确规则的提取内容，二者不能混用。

版本、CVSS、KEV和SSVC冲突先并列显示来源/时间/适用范围，再进入复核；不按来源个数投票或用最后到达记录覆盖。API返回所有来源化事实、缺失原因和审核状态，projection只是展示选择，不删除Evidence。

时间区分published/modified/retrieved/first_seen/last_seen/created/updated。URL、CVE、raw hash分别用于定位、主体身份和字节复用；同raw跨源仍保留两个source_record。本轮source_contracts仅验证映射与快照可回查，持久化/事务/接口验收留正式开发。

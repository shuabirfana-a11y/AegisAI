# 字段→优先来源与冲突策略

| 字段/信息 | 优先来源 | 真实字段/位置 | 补充/发现来源 | 适用与未知规则 |
|---|---|---|---|---|
| CVE ID/状态 | CVE_LIST | /cveMetadata/cveId；state | OSV aliases；GHSA identifiers | 拒绝/撤销原文保留；无CVE事件不用造ID |
| Description/Title | CVE CNA/厂商 | containers.cna.descriptions/title；vendor summary/description | OSV summary/details；NVD | 保留语言和发布者；并行来源，不LLM补空 |
| CVSS | 厂商/CNA，CISA ADP补充 | metrics[].cvssV3_1/cvssV4_0；GHSA cvss_severities | NVD metrics按source/type | 记录版本/vector/baseScore/source/scope；不同版本不平均、不报假冲突 |
| CWE | CNA/厂商；CISA ADP | problemTypes[].descriptions[].cweId；GHSA cwes | NVD weaknesses[].description | 无分类null；不得从描述自动确认CWE |
| Affected Product | CNA+厂商 | affected[].vendor/product/packageURL | OSV affected[].package | 包/生态身份优先；产品别名须规则/审阅依据 |
| Package affected range | OSV+厂商明确公告 | affected[].ranges[].events；versions；package.ecosystem/name | CVE affected[].versions；NVD configurations CPE范围 | 原表达和事件并存；ECOSYSTEM/GIT/SEMVER区分，unsupported UNKNOWN |
| Fixed Version | 厂商+OSV | OSV events.fixed；GHSA vulnerabilities[].first_patched_version | CVE版本明确unaffected边界，需解释适用范围 | 不从last_affected或最新版推下一版，不把所有unaffected边界当修复版本 |
| Vendor Advisory | 官方vendor repo/官网 | repository_advisory_url/html_url；原文refs | CVE/OSV reference入口 | 来源引用仅发现线索；获取原文后才确认发布者/内容 |
| POC | 公告明确引用+GITHUB_CODE | reference type/tags；repo/issue/commit元数据 | 研究文章的明确代码链接 | 仅candidate/related；可用性需独立授权隔离核验记录，本阶段不实现 |
| Exploit状态 | KEV/CISA ADP+明确事件报告 | KEV cveID/dateAdded；SSVC Exploitation options | 公告/研究案例 | poC_exists/known_exploited/unknown分开；“none”是发布者当时评估 |
| Patch/Fix Commit | 厂商+GITHUB_CODE | commit.sha/files[].patch；PR merge_commit_sha/发布引用 | OSV references(type=FIX等) | 完整SHA、分支、产品版本scope；仅候选，不运行代码 |
| EPSS | EPSS | data[].cve/epss/percentile/date；CSV头model_version | 无替代源 | 概率和日期整体绑定；缺失null；不乘CVSS当官方风险指数 |
| Known Exploited | CISA_KEV | 完整目录vulnerabilities[].cveID及dateAdded | CISA ADP/正式事件报告另列 | 在完整目录收录=true；未收录=not_listed_as_of而非false exploitation |
| Technical Analysis | TOB_BLOG/GOOGLE_SECURITY_BLOG | RSS guid/link/pubDate；Atom id/updated/content | 厂商security公告 | 论文/文章与漏洞关联独立Evidence；不是名字相似自动确认 |
| Paper | ARXIV | entry.id/title/summary/author/published/updated/link | DOI只保留显式值 | arXiv ID+版本；全文license逐篇，不将预印本当已审事实 |
| AI Security Event | 官方博客/厂商/ATLAS案例 | entry metadata、case ID/references/时间 | 软件漏洞的event关系 | 无CVE有稳定source external ID；事件日期缺失不造 |
| AI产品/组件 | 官方repo+OSV/CNA | full_name/homepage；ecosystem/name/PURL | 厂商发布/项目安全政策 | 同名不同生态不合并；Triton产品歧义保留 |
| AI Security Knowledge | ATLAS/OWASP_GENAI | 技术/风险ID、描述、缓解、references/edition | NIST AI规范 | 风险知识不是具体漏洞状态；版本化引用 |
| Published At | 各source原生字段 | CVE datePublished；OSV published；GHSA published_at；Atom published；HTML显式日期 | 只保存观测时间作为不同字段 | KEV dateAdded不是漏洞发布；HTTP Last-Modified不是发布日期 |
| Modified At | 各source原生字段 | CVE dateUpdated；OSV modified；GHSA updated_at；Atom updated | Git commit/HTTP观察时间另列 | Git传输时间不冒充源修改；dateAdded不能代替KEV条目修订时间 |
| Evidence | 所有源RawDocument | raw hash + resolved JSON Pointer/XPath/PDF page/text span + excerpt/hash | upstream provider/references | Claim可多Evidence支持/反驳/context，镜像不独立投票 |
| Technical Standard | SAMR_AI_STANDARD + NIST_AI | 标准号/语种/状态/发布/实施日期；NIST出版物ID/DOI/版本与链接 | 供应链schema作为补充知识 | 正式标准与NIST指导框架分开；全文权限另核，不冒充法律或ISO认证 |
| Policy/Regulation | CAC_POLICY | 正式原文URL、发布机关、日期、文号、显式生效/修订状态 | EUR-Lex暂缓 | 新闻解读与正式文本分开；不自动判某组织违法 |

优先来源是默认选取策略，不是自动绝对正确。先比较包/产品/版本、CVSS版本、分支、评估时间和发布者scope；同scope矛盾保留两条Claim/Evidence并进入复核。无证据或模糊范围保留unknown。

CVE-2025-32434本轮CVE/OSV/GHSA/NVD真实响应用于格式确认。其GHSA被CVE CNA/OSV/NVD引用/转录，归同一lineage；不同平台相同文本不算四次独立验证。CNA CVSS4.0=9.3与NVD CVSS3.1=9.8是两个版本，不能当冲突投票。实例是历史回放，日期不改成当前。CISA ADP按providerMetadata.orgId/shortName找到容器，不能固定adp[0]；locator索引在每份raw内解析后保存。

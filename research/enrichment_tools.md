# 富化工具与自研边界

**可复用语法、数据和候选发现；实体语义、证据关联和不确定性处理仍由 AegisAI 掌握。** 不存在本轮核实可直接覆盖所有 AI 产品的“CVE→真实 PoC→正确 patch→资产影响”万能组件。

## 实体统一：身份库与别名表不是同一件事

| 成熟能力 | 直接复用 | AegisAI 仍需实现 |
|---|---|---|
| PURL / packageurl-python | 生态、namespace、name、version、qualifier、subpath 的结构与规范化 | 品牌、产品、GitHub 仓库、PyPI 名称之间有依据的关联 |
| packaging canonicalize_name | Python 包名大小写及 `-_.` 规范化 | PyTorch→torch 属于产品语义映射，不能靠大小写完成 |
| CPE / NVD configurations | 厂商产品身份与平台/版本条件 | PURL↔CPE 并非天然一一对应；以公告、包注册信息和人工映射保存候选 |
| univers | 多生态比较和版本范围抽象 | 源字段解释、范围置信度、别名、无法解析分支与输出证据 |

实测 `canonicalize_name('PyTorch')='pytorch'`、`canonicalize_name('torch')='torch'`；两者不会自动合并。`vLLM→vllm` 只做大小写，`vllm-project` 仍是另一个规范名。实体表包含 product ID、ecosystem+package、PURL、CPE、repo、aliases、evidence、validity/review；一个品牌可对应多个包，不能未经核实合并同名仓库。

## 版本范围：按生态解释，保留原文

PyPI 第一选择 [packaging](https://packaging.pypa.io/en/stable/specifiers.html)；npm 第一选择 [node-semver](https://github.com/npm/node-semver)。python-semver 适合严格 SemVer，不替代 npm 全部语法。其他生态 V0.2 评估 univers，不使用一套 SemVer 规则处理 Debian/RPM/PEP 440/日期版本/厂商版号。

| 输入 | 可做的标准化 | 必须保留的限制 |
|---|---|---|
| `<0.8.4` | 生态 comparator + exclusive upper bound | 可能包含 .post、预发布策略等，不能换写成 <=0.8.3 |
| `<=0.8.3` | inclusive upper bound | 与小于下一版本仅在额外假设下可能覆盖相同已发布集合 |
| `before 0.8.4` | 解析为候选 `<0.8.4` | 自然语言解释要有源上下文；不能仅凭字符串高置信入库 |
| `0.7.x - 0.8.3` | 下界候选与包含上界分别表达 | x 的语义/下界要核实；不等于无限早期版本 |
| OSV events | introduced/fixed/last_affected/limit；GIT/ECOSYSTEM/SEMVER 类型 | 同一范围可能多个区间；GIT 用 commit 图而不是文本大小比较 |

本机 packaging 26.3 的实际结果：

| 版本 | `<0.8.4` | `<=0.8.3` |
|---|---|---|
| 0.7.9 | true | true |
| 0.8.3 | true | true |
| 0.8.3.post1 | true | false |
| 0.8.4rc1 | false | false |
| 0.8.4 / 0.8.4+local | false | false |

这里是 SpecifierSet 默认的成员判断；预发布过滤与纯 Version 排序不同，不能把表解释成所有生态的通用定律。[实测证据](evidence/validation.json)。资产影响结果应为 affected/not_affected/unknown 三态：生态不明、未锁定版本、发行版回移、范围无下界、解析失败都允许 unknown。

## PoC：有候选方案，没有本轮验证的通用真实性判定

[trickest/cve](https://github.com/trickest/cve) 可发现候选 GitHub 链接；GitHub search、厂商公告的 exploit 引用、CISA SSVC 的 exploitation=poc/active 也是信号。它们不等于已经验证 PoC 能利用目标产品；SSVC 信号也不必包含可下载代码。

首期只保存候选与证据，不运行。证据阶梯：仅 README 提及 CVE→内容中有目标产品/条件→公告/研究者明确关联→人工核对代码和版本→未来隔离实验复现。记录“提及/声称/人工确认/隔离复现”四种不同状态、关联理由、分析人和时间。仓库 owner、fork、commit、发布时间与文件内容共同核验；不以 Star、CVE 字符串或单一 LLM 分数确证。

未经核实的社区漏洞聚合网站可以提供线索；本轮没有验证其付费接口和数据授权，不列为 V0.1 默认服务。不能把 README 搜索结果当 exploit 数据库。

## Patch / Fix Commit：数据集可复用，在线关联要自己掌握

优先：厂商/GHSA/OSV 的明确 reference → 对应仓库 commit/PR → 同分支 release 和固定版本 → 静态核对改动和测试。GitHub REST 提供 commit/PR/files/release；平台不会替我们证明每个 CVE 与 commit 的因果关系。

[CVEfixes](https://github.com/secureIT-project/CVEfixes) 与 [MoreFixes](https://github.com/JafarAkhondali/Morefixes) 是成熟研究种子，可做 historical patch linking benchmark。两者基于采集/启发式，包含 cherry-pick、同 CVE 多修复、分支与代码授权，不能当每条都人工确认的生产 API。V0.1 只采集源显式引用与“待复核候选”，V0.2 扩展方法级分析。

实际 PyTorch 样本：OSV 引用 commit，公开改动包含 serialization.py 和测试；commit message 没有 CVE 编号，仍可能是正确线索。反过来 commit message 有 CVE 编号也不能单独确证。数据模型保存 `(CVE,repo,commit,branch,parent,release,association_basis,status,evidence)`；固定版本和 fixing commit 是两种不同事实。

## 攻击与防御映射

官方数据通路：CVE 的 CWE字段 → CWE XML → CAPEC 的 Related_Weaknesses/Taxonomy_Mappings → ATT&CK STIX 或 ATLAS 数据 → D3FEND 关系。映射是多对多、可缺失且含粒度差异，并不存在每条 CVE 必有完整链的保证。

V0.1 只接 CWE 标识/名称和 ATLAS/OWASP 标签参考。CAPEC、ATT&CK V0.2；D3FEND 决赛。每条关系必须记录 mapping source、版本、显式/推断、适用条件；无法回查的 LLM 建议只能进入候选审核区。[CWE XML](https://cwe.mitre.org/data/downloads.html)、[CAPEC 下载](https://capec.mitre.org/data/downloads)、[ATT&CK 官方 STIX](https://github.com/mitre-attack/attack-stix-data)、[D3FEND 官方资源](https://d3fend.mitre.org/resources/)。D3FEND 提供 RDF/OWL、TTL、JSON-LD 和推断输出，不能把推断边当原始事实。

## Web / 文档的最终选择

V0.1 官方 API/RSS 优先；网页正文用 Jina Reader API 辅助，后端保存原始 HTTP/HTML 响应（站点允许且可获取时）和正文，标明 reader 是转换服务而非原始发布者。Jina 失败不阻塞 JSON 主链。不要把转换后的 Markdown 当原始字节证据。

复杂 crawl/map/动态网页 V0.2 选 Firecrawl；不要同时维护两套浏览器采集。文件首期选择 Dify Extractor 辅助，后端用标准 JSON/CSV 与安全 YAML/Office 解析并保留源文件；复杂 OCR 选 Docling 做后续验证，Unstructured 是比较备选。Jina 自托管仓库和云服务不保证完整同构；README 提及云端组件及额外数据/字体许可，不能按 Apache 仓库推导 SaaS 数据条款。

## Jina 公共请求实测

本轮用匿名 Reader 请求 FIRST 官方 EPSS 数据说明页，HTTP 200，返回28946字节，证明一次公共正文转换请求可用；结果见 evidence/final_probes.json。不代表私有资料处理、长期可用性、费用或所有站点都已验证。

## 候选档案

所有时间来自本次快照。资源和部署级别为选型估计，没有冒充部署实测。原始 JSON 见 [候选清单](candidate_catalog.json)。

### aboutcode-org/univers · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/aboutcode-org/univers)；https://github.com/aboutcode-org/univers（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | enrichment_tools；跨生态版本与范围处理 |
| 能力 / 接入 / 语言 | 跨生态版本与范围处理；SDK；Python |
| License | Apache-2.0 主体；其他组件 BSD/MIT 等逐文件授权；[授权来源](https://github.com/aboutcode-org/univers/tree/92b1a2498e60779775ac9351fd7c38a035f97eb1) |
| 最近更新 / Star | 2026-05-01T16:36:05Z；50（快照统计，不作为质量结论） |
| Release | v32.0.1；2026-05-01T16:39:54Z；https://github.com/aboutcode-org/univers/releases/tag/v32.0.1 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-09-13T17:52:53Z；API open_issues_count=82（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 本地输入解析；无须高权限，安装依赖另审；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；工程 |
| 最终建议 | B；V0.2 适配其他生态；先查具体实现与组件许可证，不能统一成一种比较规则 |
| 核查来源 | [README/文档](https://github.com/aboutcode-org/univers/blob/92b1a2498e60779775ac9351fd7c38a035f97eb1/README.rst)；源码 SHA 92b1a2498e60779775ac9351fd7c38a035f97eb1；README 已下载 |

### CAPEC · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | 无独立仓库指标；相关镜像见专题；[官网](https://capec.mitre.org/data/downloads) |
| 类别 / 解决问题 | enrichment_tools；攻击模式 XML、Related_Weaknesses 与映射 |
| 能力 / 接入 / 语言 | 攻击模式 XML、Related_Weaknesses 与映射；Data；JSON/XML/HTTP 或规范 |
| License | MITRE CAPEC Terms of Use；[授权来源](https://capec.mitre.org/data/downloads) |
| 最近更新 / Star | 文档查询 2026-10-03；持续服务无可比统一 commit；不适用（快照统计，不作为质量结论） |
| Release | 服务/规范版本见官方文档，不套用 GitHub Release |
| Issue / 维护 | 服务支持/标准维护，不适用 GitHub Issue；官方服务/标准；不构成 SLA 验证 |
| 部署 / 资源 | 低 / 低；调用/解析成本估计，未部署量测 |
| 收费 / Key | 见 key/专题和官方条款；不得把免费额度理解成无限免费；不需要 |
| 权限 / 风险 | 只读指定官方 endpoint；检索字符串可能外发；不提交私有清单/文档；MEDIUM；限制为官方公共只读接口；第三方外发/输入投毒风险仍存在 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；富化 / 问答 / 创新 |
| 最终建议 | B；核心/分阶段封装，具体时机见 final_recommendation.md |
| 核查来源 | [README/文档](https://capec.mitre.org/data/downloads)；官方文档查询；README 未下载/不适用，按专题说明 |

### CWE · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | 无独立仓库指标；相关镜像见专题；[官网](https://cwe.mitre.org/data/downloads.html) |
| 类别 / 解决问题 | enrichment_tools；弱点分类 XML、层级与引用 |
| 能力 / 接入 / 语言 | 弱点分类 XML、层级与引用；Data；JSON/XML/HTTP 或规范 |
| License | MITRE CWE Terms of Use；[授权来源](https://cwe.mitre.org/data/downloads.html) |
| 最近更新 / Star | 文档查询 2026-10-03；持续服务无可比统一 commit；不适用（快照统计，不作为质量结论） |
| Release | 服务/规范版本见官方文档，不套用 GitHub Release |
| Issue / 维护 | 服务支持/标准维护，不适用 GitHub Issue；官方服务/标准；不构成 SLA 验证 |
| 部署 / 资源 | 低 / 低；调用/解析成本估计，未部署量测 |
| 收费 / Key | 见 key/专题和官方条款；不得把免费额度理解成无限免费；不需要 |
| 权限 / 风险 | 只读指定官方 endpoint；检索字符串可能外发；不提交私有清单/文档；MEDIUM；限制为官方公共只读接口；第三方外发/输入投毒风险仍存在 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；富化 / 问答 / 创新 |
| 最终建议 | B；核心/分阶段封装，具体时机见 final_recommendation.md |
| 核查来源 | [README/文档](https://cwe.mitre.org/data/downloads.html)；官方文档查询；README 未下载/不适用，按专题说明 |

### d3fend/d3fend-ontology · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/d3fend/d3fend-ontology)；[官网](https://d3fend.mitre.org) |
| 类别 / 解决问题 | enrichment_tools；防御本体、官方关系与推断输出 |
| 能力 / 接入 / 语言 | 防御本体、官方关系与推断输出；API / SDK / Docker（见专题选择）；Python |
| License | MIT 代码；D3FEND/ATT&CK 内容另受官方 Terms of Use；[授权来源](https://github.com/d3fend/d3fend-ontology/blob/c102eefe2a158dfb73a61c6637c4df175ec8680a/LICENSE.md) |
| 最近更新 / Star | 2026-09-23T17:23:35Z；116（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 3 个 Issue；最近样本更新 2026-10-02T16:39:02Z；API open_issues_count=223（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；监测 / 富化 / 创新 |
| 最终建议 | B；决赛增强；区分显式与推断关系，不能宣称存在完整 CVE 到防御链 |
| 核查来源 | [README/文档](https://github.com/d3fend/d3fend-ontology/blob/c102eefe2a158dfb73a61c6637c4df175ec8680a/README.md)；源码 SHA c102eefe2a158dfb73a61c6637c4df175ec8680a；README 已下载 |

### docling-project/docling · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/docling-project/docling)；[官网](https://docling-project.github.io/docling) |
| 类别 / 解决问题 | enrichment_tools；布局、表格、OCR 与结构化文档转换 |
| 能力 / 接入 / 语言 | 布局、表格、OCR 与结构化文档转换；API / SDK / Docker（见专题选择）；Python |
| License | MIT；[授权来源](https://github.com/docling-project/docling/blob/a1c5ff2a8c5ab2bf87d7c1eb896b5bc351f51220/LICENSE) |
| 最近更新 / Star | 2026-10-02T15:10:24Z；68316（快照统计，不作为质量结论） |
| Release | v2.132.0；2026-10-01T09:44:36Z；https://github.com/docling-project/docling/releases/tag/v2.132.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 3 个 Issue；最近样本更新 2026-10-03T01:52:49Z；API open_issues_count=987（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；监测 / 富化 / 创新 |
| 最终建议 | B；V0.2 扫描 PDF 与复杂文档；模型权重授权、资源和坐标回链另验证 |
| 核查来源 | [README/文档](https://github.com/docling-project/docling/blob/a1c5ff2a8c5ab2bf87d7c1eb896b5bc351f51220/README.md)；源码 SHA a1c5ff2a8c5ab2bf87d7c1eb896b5bc351f51220；README 已下载 |

### firecrawl/firecrawl · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/firecrawl/firecrawl)；[官网](https://firecrawl.dev) |
| 类别 / 解决问题 | enrichment_tools；浏览器抓取、crawl、map、正文与搜索 |
| 能力 / 接入 / 语言 | 浏览器抓取、crawl、map、正文与搜索；API / SDK / Docker（见专题选择）；TypeScript |
| License | AGPL-3.0；[授权来源](https://github.com/firecrawl/firecrawl/blob/66ebd15b5da3f75e6e3ebccdfe9aef5ddc6e4449/LICENSE) |
| 最近更新 / Star | 2026-10-03T00:03:37Z；187992（快照统计，不作为质量结论） |
| Release | v2.11.0；2026-06-19T15:09:30Z；https://github.com/firecrawl/firecrawl/releases/tag/v2.11.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 1 个 Issue；最近样本更新 2026-10-02T21:28:36Z；API open_issues_count=512（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 托管 API 有免费/计费档位；本次未验证账号报价，预算按官方价格页复核；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；监测 / 富化 / 创新 |
| 最终建议 | B；复杂网页 V0.2 增强；AGPL 自托管与 SaaS 条款分别审查，首期不部署整套 |
| 核查来源 | [README/文档](https://github.com/firecrawl/firecrawl/blob/66ebd15b5da3f75e6e3ebccdfe9aef5ddc6e4449/README.md)；源码 SHA 66ebd15b5da3f75e6e3ebccdfe9aef5ddc6e4449；README 已下载 |

### jina-ai/reader · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/jina-ai/reader)；[官网](https://jina.ai/reader) |
| 类别 / 解决问题 | enrichment_tools；URL 到正文/Markdown、搜索入口 |
| 能力 / 接入 / 语言 | URL 到正文/Markdown、搜索入口；API / SDK / Docker（见专题选择）；TypeScript |
| License | Apache-2.0；[授权来源](https://github.com/jina-ai/reader/blob/1574bfd380d249c86c82db4dace0d9c8fe17e2b1/LICENSE) |
| 最近更新 / Star | 2026-05-22T02:55:53Z；12091（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 6 个 Issue；最近样本更新 2026-10-02T03:02:06Z；API open_issues_count=33（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 托管 API 有免费/计费档位；本次未验证账号报价，预算按官方价格页复核；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；监测 / 富化 / 创新 |
| 最终建议 | B；V0.1 公告页面正文的辅助抓取；直接 API 经后端出站策略，不传私有资料 |
| 核查来源 | [README/文档](https://github.com/jina-ai/reader/blob/1574bfd380d249c86c82db4dace0d9c8fe17e2b1/README.md)；源码 SHA 1574bfd380d249c86c82db4dace0d9c8fe17e2b1；README 已下载 |

### kurtmckee/feedparser · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/kurtmckee/feedparser)；[官网](https://feedparser.readthedocs.io) |
| 类别 / 解决问题 | enrichment_tools；RSS/Atom 解析、时间和条目 |
| 能力 / 接入 / 语言 | RSS/Atom 解析、时间和条目；SDK；Python |
| License | BSD-2-Clause（两项保留声明要求）；[授权来源](https://github.com/kurtmckee/feedparser/blob/a22c5521cbb109871f1a2318948581901bd47e26/LICENSE) |
| 最近更新 / Star | 2026-07-30T14:54:57Z；2433（快照统计，不作为质量结论） |
| Release | v6.0.14；2026-07-30T14:09:21Z；https://github.com/kurtmckee/feedparser/releases/tag/v6.0.14 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-09-22T14:21:46Z；API open_issues_count=113（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 本地输入解析；无须高权限，安装依赖另审；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；工程 |
| 最终建议 | A；直接复用解析器；后端负责 HTTP、安全、调度和去重 |
| 核查来源 | [README/文档](https://github.com/kurtmckee/feedparser/blob/a22c5521cbb109871f1a2318948581901bd47e26/README.rst)；源码 SHA a22c5521cbb109871f1a2318948581901bd47e26；README 已下载 |

### mitre-attack/attack-stix-data · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/mitre-attack/attack-stix-data)；[官网](https://attack.mitre.org/) |
| 类别 / 解决问题 | enrichment_tools；ATT&CK STIX 2.1 技术、关系与版本 |
| 能力 / 接入 / 语言 | ATT&CK STIX 2.1 技术、关系与版本；Data；Python |
| License | MITRE ATT&CK 自定义使用条款；[授权来源](https://github.com/mitre-attack/attack-stix-data/blob/6cda5ad8462c79e14fbb872f4e09059b18e0cfc4/LICENSE.txt) |
| 最近更新 / Star | 2026-08-05T22:56:42Z；676（快照统计，不作为质量结论） |
| Release | v19.2；2026-08-05T22:58:54Z；https://github.com/mitre-attack/attack-stix-data/releases/tag/v19.2 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 3 个 Issue；最近样本更新 2026-09-23T13:45:44Z；API open_issues_count=19（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 结构化公共数据下载；文件读取与解析，不执行引用内容；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；监测 / 富化 / 创新 |
| 最终建议 | B；V0.2 官方数据导入；只接受显式映射或有证据的人工候选 |
| 核查来源 | [README/文档](https://github.com/mitre-attack/attack-stix-data/blob/6cda5ad8462c79e14fbb872f4e09059b18e0cfc4/README.md)；源码 SHA 6cda5ad8462c79e14fbb872f4e09059b18e0cfc4；README 已下载 |

### mitre/cti · C

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/mitre/cti)；https://github.com/mitre/cti（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | enrichment_tools；历史 ATT&CK/STIX 数据组织 |
| 能力 / 接入 / 语言 | 历史 ATT&CK/STIX 数据组织；Data；数据/多语言或 API 未给出 |
| License | MITRE ATT&CK 自定义使用条款；[授权来源](https://github.com/mitre/cti/blob/8543c5b05bd9bbcace9fc37f30bba96b675b6f33/LICENSE.txt) |
| 最近更新 / Star | 2026-08-05T22:53:37Z；2151（快照统计，不作为质量结论） |
| Release | ATT&CK-v19.2；2026-08-05T22:57:35Z；https://github.com/mitre/cti/releases/tag/ATT%26CK-v19.2 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-07-22T11:53:16Z；API open_issues_count=18（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 结构化公共数据下载；文件读取与解析，不执行引用内容；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；监测 / 富化 / 创新 |
| 最终建议 | C；参考兼容；主数据选 attack-stix-data，避免两份仓库当两份证据 |
| 核查来源 | [README/文档](https://github.com/mitre/cti/blob/8543c5b05bd9bbcace9fc37f30bba96b675b6f33/README.md)；源码 SHA 8543c5b05bd9bbcace9fc37f30bba96b675b6f33；README 已下载 |

### npm/node-semver · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/npm/node-semver)；[官网](https://semver.npmjs.com/) |
| 类别 / 解决问题 | enrichment_tools；npm 区间、预发布与版本比较 |
| 能力 / 接入 / 语言 | npm 区间、预发布与版本比较；SDK；JavaScript |
| License | ISC；[授权来源](https://github.com/npm/node-semver/blob/6e05b7637396ac66522cff8731f07cfe0ef49a29/LICENSE) |
| 最近更新 / Star | 2026-06-19T18:28:50Z；5465（快照统计，不作为质量结论） |
| Release | v7.8.5；2026-06-19T18:32:05Z；https://github.com/npm/node-semver/releases/tag/v7.8.5 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-09-29T02:24:15Z；API open_issues_count=68（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 本地输入解析；无须高权限，安装依赖另审；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；工程 |
| 最终建议 | A；JS 生态首选；以受控进程/服务调用并锁版本，禁止拼接 shell |
| 核查来源 | [README/文档](https://github.com/npm/node-semver/blob/6e05b7637396ac66522cff8731f07cfe0ef49a29/README.md)；源码 SHA 6e05b7637396ac66522cff8731f07cfe0ef49a29；README 已下载 |

### pymupdf/PyMuPDF · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/pymupdf/PyMuPDF)；[官网](https://pymupdf.readthedocs.io/?utm_source=github&utm_medium=referral&utm_campaign=pymupdf_github&utm_content=about&utm_term=docs) |
| 类别 / 解决问题 | enrichment_tools；PDF 文本、渲染与坐标 |
| 能力 / 接入 / 语言 | PDF 文本、渲染与坐标；API / SDK / Docker（见专题选择）；Python |
| License | AGPL-3.0；[授权来源](https://github.com/pymupdf/PyMuPDF/blob/8d1906fe738565ca741d4636c27134fd54aa0089/COPYING) |
| 最近更新 / Star | 2026-10-02T15:39:57Z；10818（快照统计，不作为质量结论） |
| Release | 1.28.2；2026-08-06T22:16:34Z；https://github.com/pymupdf/PyMuPDF/releases/tag/1.28.2 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 4 个 Issue；最近样本更新 2026-10-03T01:55:10Z；API open_issues_count=70（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；监测 / 富化 / 创新 |
| 最终建议 | D；功能好但 AGPL/商业双路线；首期已有官方 extractor，不增加授权复杂度 |
| 核查来源 | [README/文档](https://github.com/pymupdf/PyMuPDF/blob/8d1906fe738565ca741d4636c27134fd54aa0089/README.md)；源码 SHA 8d1906fe738565ca741d4636c27134fd54aa0089；README 已下载 |

### pypa/packaging · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/pypa/packaging)；[官网](https://packaging.pypa.io/) |
| 类别 / 解决问题 | enrichment_tools；PEP 440 版本、SpecifierSet、包名称规范化 |
| 能力 / 接入 / 语言 | PEP 440 版本、SpecifierSet、包名称规范化；SDK；Python |
| License | Apache-2.0 OR BSD（见实际 LICENSE；BSD 细项本次未完全核对）；[授权来源](https://github.com/pypa/packaging/blob/4a920d632a0e81ef2b06dc94d9048eee9e569c8d/LICENSE) |
| 最近更新 / Star | 2026-10-02T17:47:07Z；751（快照统计，不作为质量结论） |
| Release | 26.3；2026-08-04T21:42:51Z；https://github.com/pypa/packaging/releases/tag/26.3 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=113（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 本地输入解析；无须高权限，安装依赖另审；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；工程 |
| 最终建议 | A；PyPI 第一选择；不负责 PyTorch 到 torch 的产品别名映射 |
| 核查来源 | [README/文档](https://github.com/pypa/packaging/blob/4a920d632a0e81ef2b06dc94d9048eee9e569c8d/README.rst)；源码 SHA 4a920d632a0e81ef2b06dc94d9048eee9e569c8d；README 已下载 |

### python-semver/python-semver · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/python-semver/python-semver)；[官网](https://python-semver.readthedocs.io/en/latest/) |
| 类别 / 解决问题 | enrichment_tools；严格 SemVer 解析与比较 |
| 能力 / 接入 / 语言 | 严格 SemVer 解析与比较；SDK；Python |
| License | BSD-3-Clause；[授权来源](https://github.com/python-semver/python-semver/blob/1d515915d50b31f23fd1fb0f572ef608453e80e3/LICENSE.txt) |
| 最近更新 / Star | 2026-10-01T19:58:07Z；524（快照统计，不作为质量结论） |
| Release | 3.1.0；2026-09-12T18:36:00Z；https://github.com/python-semver/python-semver/releases/tag/3.1.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-10-01T19:58:08Z；API open_issues_count=14（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 本地输入解析；无须高权限，安装依赖另审；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；工程 |
| 最终建议 | A；纯 SemVer 元件可用；不是 npm 所有区间语法的替代品 |
| 核查来源 | [README/文档](https://github.com/python-semver/python-semver/blob/1d515915d50b31f23fd1fb0f572ef608453e80e3/README.rst)；源码 SHA 1d515915d50b31f23fd1fb0f572ef608453e80e3；README 已下载 |

### rbarrois/python-semanticversion · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/rbarrois/python-semanticversion)；https://github.com/rbarrois/python-semanticversion（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | enrichment_tools；SemVer 与 NpmSpec 兼容范围 |
| 能力 / 接入 / 语言 | SemVer 与 NpmSpec 兼容范围；SDK；Python |
| License | BSD-2-Clause；[授权来源](https://github.com/rbarrois/python-semanticversion/blob/2cbbee3154d9011cee873ae3a020cd17c669f6df/LICENSE) |
| 最近更新 / Star | 2023-02-28T10:51:59Z；293（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 4 个 Issue；最近样本更新 2024-12-05T22:50:29Z；API open_issues_count=44（含 PR）；低频/稳定维护或待确认；不按提交日期单独判死 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 本地输入解析；无须高权限，安装依赖另审；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；工程 |
| 最终建议 | D；长期未更新但不能据此断言失效；首期采用生态原生库并减少重复 |
| 核查来源 | [README/文档](https://github.com/rbarrois/python-semanticversion/blob/2cbbee3154d9011cee873ae3a020cd17c669f6df/README.rst)；源码 SHA 2cbbee3154d9011cee873ae3a020cd17c669f6df；README 已下载 |

### trickest/cve · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/trickest/cve)；[官网](https://trickest.com) |
| 类别 / 解决问题 | enrichment_tools；CVE 与 GitHub PoC 候选链接 |
| 能力 / 接入 / 语言 | CVE 与 GitHub PoC 候选链接；API / SDK / Docker（见专题选择）；HTML |
| License | MIT；[授权来源](https://github.com/trickest/cve/blob/0a11ab945b81964bf0f31210f21587ee380b7cef/LICENSE) |
| 最近更新 / Star | 2026-10-02T12:33:03Z；8116（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 4 个 Issue；最近样本更新 2026-08-20T18:27:57Z；API open_issues_count=21（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；监测 / 富化 / 创新 |
| 最终建议 | B；候选发现补充；MIT 仓库不替 PoC 本体授权，关联必须复核 |
| 核查来源 | [README/文档](https://github.com/trickest/cve/blob/0a11ab945b81964bf0f31210f21587ee380b7cef/README.md)；源码 SHA 0a11ab945b81964bf0f31210f21587ee380b7cef；README 已下载 |

### Unstructured-IO/unstructured · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/Unstructured-IO/unstructured)；[官网](https://www.unstructured.io/) |
| 类别 / 解决问题 | enrichment_tools；多格式 partition 与文档预处理 |
| 能力 / 接入 / 语言 | 多格式 partition 与文档预处理；API / SDK / Docker（见专题选择）；HTML |
| License | Apache-2.0；[授权来源](https://github.com/Unstructured-IO/unstructured/blob/0242693483896008daf80e4c324205d31dce1de8/LICENSE.md) |
| 最近更新 / Star | 2026-10-02T21:07:27Z；15524（快照统计，不作为质量结论） |
| Release | 0.27.10；2026-09-27T19:10:55Z；https://github.com/Unstructured-IO/unstructured/releases/tag/0.27.10 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=332（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | enrichment_tools；监测 / 富化 / 创新 |
| 最终建议 | B；V0.2 备选，首期不与 Docling 双栈；模型与商业 API 条款不等同 Apache 核心 |
| 核查来源 | [README/文档](https://github.com/Unstructured-IO/unstructured/blob/0242693483896008daf80e4c324205d31dce1de8/README.md)；源码 SHA 0242693483896008daf80e4c324205d31dce1de8；README 已下载 |

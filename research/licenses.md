# 许可证与服务条款登记

**代码许可、情报数据、抓取内容、模型权重和在线服务不是一份授权。** GitHub 的 NOASSERTION 只表示分类器未识别；无 LICENSE 不意味着可以直接复制。以下是选型管理记录，未将页面可访问性当作发布/商业再分发授权。

## 影响选型的具体发现

| 对象 | 本次核查 | AegisAI 处理 |
|---|---|---|
| Dify 主项目 | 修改版 Apache，含多租户与品牌/标识等额外条件 | 比赛自托管方案与未来企业多租户产品分别审查，不能写成普通 Apache |
| Dify 官方插件 | monorepo Apache-2.0；第三方 API 内容另受条款 | 逐插件 pin、保留 LICENSE/NOTICE，核对依赖和云服务 |
| langgenius/dify-plugins | 仓库级 LICENSE 未确认 | 作为发现入口，不默认复制整个仓库 |
| GH Advisory Database | CC-BY-4.0 | 公告/数据使用署名并记录上游；REST 服务条款独立 |
| CVE List / CVE schema | Schema CC0；CVE List 使用 Terms of Use，本轮条款页未完整提取 | 不把 schema 许可传递给全部公告文本；正式再分发前补条款核对 |
| CISA KEV / Vulnrichment | 实际 README/许可 CC0；分类器有时为 NOASSERTION | 可接公共数据，保留官方归属与数据版本 |
| OSV | 实现 Apache-2.0；聚合的数据按各 upstream | 每条保存 upstream及许可；不写“全库数据 Apache” |
| ATLAS | 实际 LICENSE Apache-2.0 | 引用版本与 MITRE 归属，商标/上游来源另登记 |
| ATT&CK/CWE/CAPEC/D3FEND | MITRE 具体 Terms；D3FEND代码MIT不等于全部内容无条件MIT | 保存官方条款版本、署名与内容来源，不跨规范乱套许可证 |
| OWASP GenAI/LLM Top10 | CC-BY-SA-4.0 | 内容改编/分发遵守署名与相同方式共享条件；分类设计参考和复制材料区分 |
| OpenCTI | 社区 Apache/企业专有，逐文件头 | 只借鉴模型，不复制企业组件 |
| MISP / IntelOwl / VulnMCP | AGPL-3.0 路线（VulnMCP README说明 or-later） | 首期不嵌入为主体；后续如修改/提供服务，需要按具体许可履行义务 |
| Firecrawl | 核心 AGPL；云服务商业条款 | V0.1不整套部署；API调用不是取得代码或数据再分发授权 |
| Jina Reader | Apache 核心，README有额外数据/字体及云端组件说明 | 使用API仍需条款；不能推导完全同构自托管或无限免费 |
| Docling / Unstructured | 代码MIT/Apache；模型、OCR、weights和服务另审 | V0.2按选中组件生成许可清单 |
| PyMuPDF | AGPL/商业路径 | 首期不选，减少许可和依赖负担 |
| packageurl-python / univers | 主体MIT / Apache，有第三方组件授权 | 保留第三方NOTICE，不能只记录根许可 |
| SPDX | Community-Spec-1.0，既有部分CC-BY-3.0，脚本MIT | 规范实现与复制规范文本分开 |
| CTIBench | CC-BY-NC-SA-4.0 | 比赛研究用途审查后使用；企业商用不默认包含 |
| CVEfixes | 代码MIT，数据Zenodo CC-BY-4.0，上游代码独立 | 保留数据署名和每个代码项目许可 |
| MoreFixes v4 | Zenodo数据CC-BY-4.0；实现修改MIT/Apache | 数据集不能替代码片段、patch上游授权 |
| PurpleLlama | CybersecurityBenchmarks MIT；模型及其他组件Llama专用等 | 逐子目录/模型复核，不将整个仓库标成MIT |
| Semantic Scholar | 当前 API 协议含非商业研究/教育与归属要求；商用需扩展授权 | V0.1淘汰默认使用，后续价值明确再确认 |
| OpenAlex | 元数据CC0；全文权利与付费API独立 | 不把元数据开放等同文章全文/服务无限免费 |

依据为候选档案中的锁定 LICENSE；服务文档：[Dify LICENSE](https://github.com/langgenius/dify/blob/main/LICENSE)、[CWE Terms](https://cwe.mitre.org/about/termsofuse.html)、[CVE Terms](https://www.cve.org/Legal/TermsOfUse)、[EPSS获取](https://www.first.org/epss/data.html)、[Semantic Scholar 当前协议](https://api.semanticscholar.org/license/)、[OpenAlex费用](https://help.openalex.org/access/pricing/)、[CVEfixes数据](https://zenodo.org/records/13118970)、[MoreFixes数据](https://zenodo.org/records/20776007)。需要具体条款判断时以实际锁定文本为准；本轮未完整取回的条款没有宣称已获商用放行。

## 使用、接入与借鉴的区分

- A 直接使用 SDK/CLI：按实际发行包保留 copyright、LICENSE、NOTICE 和依赖清单；二进制发行还需核对包内组件。
- B API/Data 接入：应用独立，不因此免除数据/服务条款；存数据时记录 license/terms/source/retrieved_at，输出引用与更新。
- C 借鉴设计：用自己的 schema/实现描述思想，引用来源；不能把复制模型代码/测试/文档改名当“借鉴”。
- D 未选：许可证未知、维护归档、权限过大、运维过重或价值重复；不是断言这类许可本身无法用于所有比赛。

## 下一阶段必须落到项目中的文件

生成依赖与数据的 `THIRD_PARTY_NOTICES`、源码依赖SBOM、服务 terms 快照、数据来源署名策略；锁定版本并定期更新。PoC仓库、模型文件、学术全文和网页内容单独登记。商业多租户、受限数据再分发与 GPL/AGPL 修改分发是具体情景的审查点，本轮未部署这些情景，也不引入额外购买/审批流程。

下面的自动台账列出所有候选，详细条件仍以专题和原文为准。

## 全部候选许可台账

| 候选 | 类别 | 代码/数据/服务授权摘要 | 原文 |
|---|---|---|---|
| arXiv API | B | 元数据/API 使用要求；论文内容按每篇授权 | [许可来源](https://info.arxiv.org/help/api/user-manual.html) |
| Crossref REST API | B | 元数据与摘要/全文权利分开；服务条款独立 | [许可来源](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) |
| mitre-atlas/atlas-data | B | Apache-2.0（实际 LICENSE） | [许可来源](https://github.com/mitre-atlas/atlas-data/blob/3259f388d19cbcca11bacf12a0ef97f4198f711b/LICENSE) |
| NVIDIA/garak | B | Apache-2.0 | [许可来源](https://github.com/NVIDIA/garak/blob/bb30a7e79f4e78ef633a92295f142105a0e69941/LICENSE) |
| OpenAlex API | B | 元数据 CC0；全文权利和 API 计费独立 | [许可来源](https://help.openalex.org/access/example-costs/) |
| OWASP/www-project-top-10-for-large-language-model-applications | B | CC-BY-SA-4.0 | [许可来源](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/99f4395589bdbd120ae961f9cd179e79d7f9b27f/LICENSE.md) |
| protectai/llm-guard | D | MIT | [许可来源](https://github.com/protectai/llm-guard/blob/168c1034ffdb33837e7ae6fd6a16b80567c1be03/LICENSE) |
| protectai/modelscan | B | Apache-2.0 | [许可来源](https://github.com/protectai/modelscan/blob/61fcec9c2a37c24c1fb12d84ede30fe248a364bd/LICENSE) |
| Semantic Scholar API | D | 当前 API 协议含非商业研究/教育授权及展示归属要求；商用需另谈 | [许可来源](https://api.semanticscholar.org/license/) |
| cisco-foundation-ai/faith | B | Apache-2.0 | [许可来源](https://github.com/cisco-foundation-ai/faith/blob/9471073caf8b48d78d7b21e3b45a4c51d32bc92c/LICENSE) |
| ethz-spylab/agentdojo | B | MIT | [许可来源](https://github.com/ethz-spylab/agentdojo/blob/089ed468cf3ed0322acc66b0211f26d9d90dbf60/LICENSE) |
| JafarAkhondali/Morefixes | B | 代码 MIT/Apache-2.0；Zenodo v4 数据 CC-BY-4.0；上游代码单独授权 | [许可来源](https://github.com/JafarAkhondali/Morefixes/blob/7e78f1b477d3f656cdb06336fd0af6861d6bca40/LICENSE.txt) |
| maveryn/cti-bench | B | CC-BY-NC-SA-4.0（数据/仓库 LICENSE） | [许可来源](https://github.com/maveryn/cti-bench/blob/4543e5b6560d3204e1205ced4fa286adc7452d07/LICENSE.txt) |
| meta-llama/PurpleLlama | B | 组件多许可：CybersecurityBenchmarks MIT；模型 Llama 专用许可 | [许可来源](https://github.com/meta-llama/PurpleLlama/blob/172c1074069eb88ec834124272c1b1c4f8893445/LICENSE) |
| secureIT-project/CVEfixes | B | 代码 MIT；Zenodo 数据 CC-BY-4.0；收集的代码各有上游授权 | [许可来源](https://github.com/secureIT-project/CVEfixes/blob/9283b50b3f04e3c5b0a17fc419ab0feea23fc438/LICENSE.txt) |
| intelowlproject/IntelOwl | C | AGPL-3.0 | [许可来源](https://github.com/intelowlproject/IntelOwl/blob/bf75e8b2f465f27c590cd0d7fea61d65fb6aab56/LICENSE) |
| MISP/MISP | C | AGPL-3.0 | [许可来源](https://github.com/MISP/MISP/blob/fb54b3e4a4ddd7ad7913fffd94284dd0e81b2120/LICENSE) |
| oasis-open/cti-python-stix2 | A | BSD-3-Clause | [许可来源](https://github.com/oasis-open/cti-python-stix2/blob/2270361774215de49717c1a6028a80c91075b400/LICENSE) |
| OpenCTI-Platform/opencti | C | 社区 Apache-2.0 / 企业组件专有条款，按文件头区分 | [许可来源](https://github.com/OpenCTI-Platform/opencti/blob/b97fbc534ec69ba374a2fe0e8665cf87b5e75b72/LICENSE) |
| STIX 2.1 | A | OASIS 规范条款；Python SDK BSD-3-Clause | [许可来源](https://oasis-open.github.io/cti-documentation/stix/intro) |
| contrastcyber/contrastapi | D | API仓库MIT；插件包与线上数据条款未完整核实 | [许可来源](https://github.com/UPinar/contrastapi/blob/07957c19576aaaa4b27014201e7c184bdc15fc7f/LICENSE) |
| hjlarry/database | D | 未确认 | [许可来源](https://github.com/hjlarry/dify-plugin-database/tree/e9156f71e799591cb80026cdc80a4b296c2a3e01) |
| hjlarry/dify-plugin-database | D | 未确认 | [许可来源](https://github.com/hjlarry/dify-plugin-database/tree/e9156f71e799591cb80026cdc80a4b296c2a3e01) |
| langgenius/agent | A | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/arxiv | B | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/crossref | B | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/dify | B | Dify Open Source License（Apache-2.0 修改版） | [许可来源](https://github.com/langgenius/dify/blob/43af5082d3c4ab8a96067370d2f86f214e3c85ae/LICENSE) |
| langgenius/dify-official-plugins | B | Apache-2.0 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/dify-plugins | C | 未发现可确认的仓库级 LICENSE；逐插件确认 | [许可来源](https://github.com/langgenius/dify-plugins/tree/175ba426e20e673aa673f11e09563a3763b1ec21) |
| langgenius/dify_extractor | A | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/duckduckgo | D | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/firecrawl | B | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/firecrawl_datasource | B | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/github | B | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/github_datasource | B | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/github_trigger | B | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/jina_tool | B | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/rsshub_trigger | D | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/sqlite | D | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| langgenius/websearch | D | Apache-2.0（官方仓库）；外部服务条款另核实 | [许可来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| aboutcode-org/univers | B | Apache-2.0 主体；其他组件 BSD/MIT 等逐文件授权 | [许可来源](https://github.com/aboutcode-org/univers/tree/92b1a2498e60779775ac9351fd7c38a035f97eb1) |
| CAPEC | B | MITRE CAPEC Terms of Use | [许可来源](https://capec.mitre.org/data/downloads) |
| CWE | B | MITRE CWE Terms of Use | [许可来源](https://cwe.mitre.org/data/downloads.html) |
| d3fend/d3fend-ontology | B | MIT 代码；D3FEND/ATT&CK 内容另受官方 Terms of Use | [许可来源](https://github.com/d3fend/d3fend-ontology/blob/c102eefe2a158dfb73a61c6637c4df175ec8680a/LICENSE.md) |
| docling-project/docling | B | MIT | [许可来源](https://github.com/docling-project/docling/blob/a1c5ff2a8c5ab2bf87d7c1eb896b5bc351f51220/LICENSE) |
| firecrawl/firecrawl | B | AGPL-3.0 | [许可来源](https://github.com/firecrawl/firecrawl/blob/66ebd15b5da3f75e6e3ebccdfe9aef5ddc6e4449/LICENSE) |
| jina-ai/reader | B | Apache-2.0 | [许可来源](https://github.com/jina-ai/reader/blob/1574bfd380d249c86c82db4dace0d9c8fe17e2b1/LICENSE) |
| kurtmckee/feedparser | A | BSD-2-Clause（两项保留声明要求） | [许可来源](https://github.com/kurtmckee/feedparser/blob/a22c5521cbb109871f1a2318948581901bd47e26/LICENSE) |
| mitre-attack/attack-stix-data | B | MITRE ATT&CK 自定义使用条款 | [许可来源](https://github.com/mitre-attack/attack-stix-data/blob/6cda5ad8462c79e14fbb872f4e09059b18e0cfc4/LICENSE.txt) |
| mitre/cti | C | MITRE ATT&CK 自定义使用条款 | [许可来源](https://github.com/mitre/cti/blob/8543c5b05bd9bbcace9fc37f30bba96b675b6f33/LICENSE.txt) |
| npm/node-semver | A | ISC | [许可来源](https://github.com/npm/node-semver/blob/6e05b7637396ac66522cff8731f07cfe0ef49a29/LICENSE) |
| pymupdf/PyMuPDF | D | AGPL-3.0 | [许可来源](https://github.com/pymupdf/PyMuPDF/blob/8d1906fe738565ca741d4636c27134fd54aa0089/COPYING) |
| pypa/packaging | A | Apache-2.0 OR BSD（见实际 LICENSE；BSD 细项本次未完全核对） | [许可来源](https://github.com/pypa/packaging/blob/4a920d632a0e81ef2b06dc94d9048eee9e569c8d/LICENSE) |
| python-semver/python-semver | A | BSD-3-Clause | [许可来源](https://github.com/python-semver/python-semver/blob/1d515915d50b31f23fd1fb0f572ef608453e80e3/LICENSE.txt) |
| rbarrois/python-semanticversion | D | BSD-2-Clause | [许可来源](https://github.com/rbarrois/python-semanticversion/blob/2cbbee3154d9011cee873ae3a020cd17c669f6df/LICENSE) |
| trickest/cve | B | MIT | [许可来源](https://github.com/trickest/cve/blob/0a11ab945b81964bf0f31210f21587ee380b7cef/LICENSE) |
| Unstructured-IO/unstructured | B | Apache-2.0 | [许可来源](https://github.com/Unstructured-IO/unstructured/blob/0242693483896008daf80e4c324205d31dce1de8/LICENSE.md) |
| badchars/cve-mcp | C | MIT | [许可来源](https://github.com/badchars/cve-mcp/blob/31ee55553a39f0c5d8270977ea308e7a733a57ee/LICENSE) |
| blazickjp/arxiv-mcp-server | B | Apache-2.0 | [许可来源](https://github.com/blazickjp/arxiv-mcp-server/blob/e477454fcda4e1ece0202a0cdeca0ad99d8d07df/LICENSE) |
| crystaldba/postgres-mcp | D | MIT | [许可来源](https://github.com/crystaldba/postgres-mcp/blob/15c8e33353546148acc2d8bd784551cf3905d1e2/LICENSE) |
| github/github-mcp-server | B | MIT | [许可来源](https://github.com/github/github-mcp-server/blob/f10e4e1f923d46b86f2e80e849aa74084c847184/LICENSE) |
| gperdrizet/rss-mcp-server | D | GPL-3.0 | [许可来源](https://github.com/gperdrizet/rss-mcp-server/blob/2b63658953d76c5de7b2245a5d58b9ee90239b68/LICENSE) |
| modelcontextprotocol/servers | C | GitHub 未识别 SPDX；以实际 LICENSE 为准，未作放行 | [许可来源](https://github.com/modelcontextprotocol/servers/blob/f46d9578190b476b3501923ea8977d899e8db2cb/LICENSE) |
| ptelang/osv-mcp | D | MIT | [许可来源](https://github.com/ptelang/osv-mcp/blob/b28952fd5a1b470ee38b5e6f5ba0ee34b061febd/LICENSE) |
| SalehKamil/mcp-mitre-attack | D | 未核实根 LICENSE，禁止默认复制代码 | [许可来源](https://github.com/SalehKamil/mcp-mitre-attack/tree/82a2c16039dc6045009e2527ea3d61971a406654) |
| UPinar/contrastapi | D | MIT | [许可来源](https://github.com/UPinar/contrastapi/blob/07957c19576aaaa4b27014201e7c184bdc15fc7f/LICENSE) |
| vulnerability-lookup/VulnMCP | C | AGPL-3.0 | [许可来源](https://github.com/vulnerability-lookup/VulnMCP/blob/3f9bc2a990724d25211d8498bc1181d997c9dbd8/LICENSE) |
| anchore/grype | B | Apache-2.0 | [许可来源](https://github.com/anchore/grype/blob/4759e396277871feb6530dcc45ae9d3acd074980/LICENSE) |
| anchore/syft | A | Apache-2.0 | [许可来源](https://github.com/anchore/syft/blob/bc68299565d1d2bc7f54159db2f1eb5567144aff/LICENSE) |
| CycloneDX/specification | A | Apache-2.0 | [许可来源](https://github.com/CycloneDX/specification/blob/1ce97b2a7b8cf2429da248560d2aa671c6bce74a/LICENSE) |
| google/osv-scanner | A | Apache-2.0 | [许可来源](https://github.com/google/osv-scanner/blob/1b86129be1f0285c403616cb362ac188de676c6e/LICENSE) |
| guacsec/guac | C | Apache-2.0 | [许可来源](https://github.com/guacsec/guac/blob/fd86ccd19863ae5f6b019e151cb07444302c03cc/LICENSE) |
| openvex/spec | A | CC0-1.0 | [许可来源](https://github.com/openvex/spec/blob/61b5f885d0f481f48683c93345e49ef1a6e9fdff/LICENSE) |
| package-url/packageurl-js | A | MIT | [许可来源](https://github.com/package-url/packageurl-js/blob/4cfc3681c245c6346e2bef3f3e6a54f011203960/LICENSE) |
| package-url/packageurl-python | A | MIT 核心；thirdparty 中有其他授权 | [许可来源](https://github.com/package-url/packageurl-python/tree/c7c7b46346eebcd86ec61d4ee7c6a84c3fe5fcc4) |
| package-url/purl-spec | A | MIT（实际 LICENSE） | [许可来源](https://github.com/package-url/purl-spec/blob/7cd2d3442fb9c88155db17ada7c911b40ec22d41/LICENSE) |
| spdx/spdx-spec | A | Community-Spec-1.0 / 既有部分 CC-BY-3.0 / 脚本 MIT | [许可来源](https://github.com/spdx/spdx-spec/blob/b0f290ffdb31b5682ff90bd99636d1d29e79d3b2/LICENSE) |
| cisagov/kev-data | B | CC0-1.0（README/LICENSE） | [许可来源](https://github.com/cisagov/kev-data/blob/7009facc2019306d41f6d6df6c8a057b99b4b468/LICENSE) |
| cisagov/vulnrichment | B | CC0-1.0 | [许可来源](https://github.com/cisagov/vulnrichment/blob/bdf8720c255290447ee5273457e02dd2431ca23f/LICENSE) |
| CVEProject/cve-schema | A | CC0-1.0 | [许可来源](https://github.com/CVEProject/cve-schema/blob/ce5f5c865f14dc40a6548d36b74751abca1c588a/LICENSE.txt) |
| CVEProject/cvelistV5 | B | CVE Terms of Use；本次未完整提取条款，不标成 CC0 | [许可来源](https://github.com/CVEProject/cvelistV5/tree/281e4a53d95c7e8cbc68e428a7469e67dc02d960) |
| FIRST EPSS | B | 免费公开，按 FIRST 要求署名；不是默认 CC0 | [许可来源](https://www.first.org/epss/data.html) |
| GitHub Global Security Advisories API | B | API Terms；Advisory Database CC-BY-4.0 | [许可来源](https://docs.github.com/en/rest/security-advisories/global-advisories) |
| github/advisory-database | B | CC-BY-4.0 | [许可来源](https://github.com/github/advisory-database/blob/95c24a9af2a1a089b062a575b5a2f9055f36c4e4/LICENSE.md) |
| google/osv.dev | B | Apache-2.0 | [许可来源](https://github.com/google/osv.dev/blob/7d0483198bef3059311832bcbe00faf895991f46/LICENSE) |
| NVD API | B | 公共数据使用声明；本次条款页提取不完整 | [许可来源](https://nvd.nist.gov/developers/vulnerabilities) |
| ossf/osv-schema | A | Apache-2.0 | [许可来源](https://github.com/ossf/osv-schema/blob/2780d2ad3f897abc4e12ea62a724db5ff67e5b1a/LICENSE) |

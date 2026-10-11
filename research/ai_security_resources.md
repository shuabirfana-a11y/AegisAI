# AI 安全资源：分类、真实漏洞与研究知识分开

**ATLAS 和 OWASP 用于知识分类；GHSA/OSV/CVE 用于可追溯的软件漏洞；注入评测用于验证 Agent 边界。** 这三种资料不是可互换的事实库。

## 分类与知识资源

| 资源 | 可用于 | 不应推导 |
|---|---|---|
| MITRE ATLAS | AI 攻击战术/技术、案例、风险解释、标签候选 | 单个 CVE 一定对应某条 ATLAS 技术；覆盖全部 AI 漏洞 |
| OWASP GenAI / LLM Top 10 | prompt injection、数据/模型供应链、输出处理等分类与开发检查 | 每条 CVE 的 ground truth；某工具通过分类检查就安全 |
| AI 框架 GHSA/OSV/CVE | torch、vllm、transformers、mlflow、ray、langchain 等有明确包身份的真实漏洞 | 描述含“AI”就等于高风险 AI 漏洞；库名同名即可确证 |
| ModelScan | 模型文件的静态格式/不安全构造信号 | 扫描通过证明无后门、无恶意行为；可以安全反序列化 |
| garak | LLM 行为 probe 与检测器、配置化安全评测 | 生产漏洞 feed；测试分数可代替证据可信度 |
| AgentDojo / CyberSecEval | prompt injection、工具滥用的对抗测试 | AegisAI 所有情报问答与资产影响正确率 |

ATLAS 官方 [atlas-data](https://github.com/mitre-atlas/atlas-data) 有版本化源数据及生成 YAML/STIX/Excel/Navigator 的工具。主接入读取锁定的正式 release/源 YAML，校验官方 schema、保留 AML 稳定 ID、版本、技术/案例及显式关系；更新保留新增/修订/废弃状态。禁止按网站页面标题手写无法回查的关系。

OWASP 内容按 CC-BY-SA 管理，保留项目与版本署名。Protect AI 生态必须逐仓库判断：ModelScan 本次未归档但更新低频；llm-guard 已归档，不能默认推荐为正在持续维护的核心扫描依赖。garak 的规范仓库是 NVIDIA/garak，旧 leondz URL 会重定向。维护结论均见候选 commit 与 archived 字段。

## AI 相关性识别的落地规则

首期建立带来源的小型产品/包注册表：AI 框架、推理/Serving、模型与序列化、训练/数据处理、Agent/RAG 编排、AI 应用。可以用目标产品注册信息和公告证明包身份，先以 torch/vllm 等明确目标为范围，逐步扩张。

输出结构建议：`related=true/false/unknown`、产品、AI 作用、漏洞条件、分类标签、支持 evidence、review_status。类别规则和已审核别名先判；LLM 只对不确定项提出带证据的候选。通用依赖如 OpenSSL/urllib3 只有在资产/产品依赖关系有证据时才成为间接 AI 影响；不是看到某 AI 项目使用它就把所有 CVE 标成 AI 专属。

知识中区分软件漏洞、模型不安全格式、prompt injection 行为、恶意包/模型、研究性攻击案例。prompt injection 往往没有 CVE；允许自有稳定 ID 和文献/案例来源，但不可伪造 CVE/CVSS/修复版本。分类是多标签，severity/confidence/exploit/affected 是不同维度。

## 学术资源与授权

| 候选 | 接入价值 | 首期取舍 |
|---|---|---|
| arXiv | 论文 ID、版本、作者、摘要；版本可追踪 | V0.2 优先，只取元数据和许可允许的原文；直接 API 足够 |
| Crossref | DOI、出版时间、引用/出版关系 | V0.2 与 arXiv 配合；DOI 不是漏洞确认标志 |
| OpenAlex | 聚合学术元数据、引用网络 | V0.2 可选；当前服务按用量计费，数据许可与服务费用分开 |
| Semantic Scholar | 引用与文献检索 | V0.1 不选；当前 API 协议的非商业授权与展示要求需明确，商用另确认 |

OpenAlex 的当前帮助页说明匿名仅适合少量试用，生产应使用 key；单记录、列表、检索和全文请求计费不同，不沿用“无限免费 API”的旧建议。[当前费用/额度](https://help.openalex.org/access/example-costs/)。本轮未开户、未购买额度，未执行付费查询。Semantic Scholar 以 [当前 API 协议](https://api.semanticscholar.org/license/) 为准，不能把第三方文章的旧许可摘要当最新授权。

论文关联策略：产品/版本/漏洞 ID 的确切引用优先，其次作者/公告引用，再其次语义候选；保留论文版本、段落、匹配依据和人工状态。论文描述一次攻击概念不代表已经证明该攻击影响某个包版本；付费/受版权保护全文不能因可获取就转存公开基准。

## 没有找到的成熟能力

本次未核实覆盖“AI 包身份、CVE 软件漏洞、恶意模型、RAG/Agent 行为攻击、PoC/patch 和证据”全主线、持续维护且授权清晰的统一 AI 漏洞数据库。因此用权威软件漏洞 + ATLAS/OWASP + 自有证据关联；不为补齐表格硬推一个名字相关的社区数据库。

## 候选档案

所有时间来自本次快照。资源和部署级别为选型估计，没有冒充部署实测。原始 JSON 见 [候选清单](candidate_catalog.json)。

### arXiv API · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | 无独立仓库指标；相关镜像见专题；[官网](https://info.arxiv.org/help/api/user-manual.html) |
| 类别 / 解决问题 | ai_security_resources；论文 ID、版本、标题、作者与摘要 |
| 能力 / 接入 / 语言 | 论文 ID、版本、标题、作者与摘要；API；JSON/XML/HTTP 或规范 |
| License | 元数据/API 使用要求；论文内容按每篇授权；[授权来源](https://info.arxiv.org/help/api/user-manual.html) |
| 最近更新 / Star | 文档查询 2026-10-03；持续服务无可比统一 commit；不适用（快照统计，不作为质量结论） |
| Release | 服务/规范版本见官方文档，不套用 GitHub Release |
| Issue / 维护 | 服务支持/标准维护，不适用 GitHub Issue；官方服务/标准；不构成 SLA 验证 |
| 部署 / 资源 | 低 / 低；调用/解析成本估计，未部署量测 |
| 收费 / Key | 见 key/专题和官方条款；不得把免费额度理解成无限免费；公共接口通常无需 key；本次未执行查询 |
| 权限 / 风险 | 只读指定官方 endpoint；检索字符串可能外发；不提交私有清单/文档；MEDIUM；限制为官方公共只读接口；第三方外发/输入投毒风险仍存在 |
| AegisAI 模块 / 比赛价值 | ai_security_resources；富化 / 问答 / 创新 |
| 最终建议 | B；核心/分阶段封装，具体时机见 final_recommendation.md |
| 核查来源 | [README/文档](https://info.arxiv.org/help/api/user-manual.html)；官方文档查询；README 未下载/不适用，按专题说明 |

### Crossref REST API · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | 无独立仓库指标；相关镜像见专题；[官网](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) |
| 类别 / 解决问题 | ai_security_resources；DOI、出版时间、作者与关系 |
| 能力 / 接入 / 语言 | DOI、出版时间、作者与关系；API；JSON/XML/HTTP 或规范 |
| License | 元数据与摘要/全文权利分开；服务条款独立；[授权来源](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) |
| 最近更新 / Star | 文档查询 2026-10-03；持续服务无可比统一 commit；不适用（快照统计，不作为质量结论） |
| Release | 服务/规范版本见官方文档，不套用 GitHub Release |
| Issue / 维护 | 服务支持/标准维护，不适用 GitHub Issue；官方服务/标准；不构成 SLA 验证 |
| 部署 / 资源 | 低 / 低；调用/解析成本估计，未部署量测 |
| 收费 / Key | 见 key/专题和官方条款；不得把免费额度理解成无限免费；公共 API；mailto polite pool 可选 |
| 权限 / 风险 | 只读指定官方 endpoint；检索字符串可能外发；不提交私有清单/文档；MEDIUM；限制为官方公共只读接口；第三方外发/输入投毒风险仍存在 |
| AegisAI 模块 / 比赛价值 | ai_security_resources；富化 / 问答 / 创新 |
| 最终建议 | B；核心/分阶段封装，具体时机见 final_recommendation.md |
| 核查来源 | [README/文档](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)；官方文档查询；README 未下载/不适用，按专题说明 |

### mitre-atlas/atlas-data · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/mitre-atlas/atlas-data)；[官网](https://atlas.mitre.org) |
| 类别 / 解决问题 | ai_security_resources；AI 攻击战术、技术、案例与版本化数据 |
| 能力 / 接入 / 语言 | AI 攻击战术、技术、案例与版本化数据；Data；Python |
| License | Apache-2.0（实际 LICENSE）；[授权来源](https://github.com/mitre-atlas/atlas-data/blob/3259f388d19cbcca11bacf12a0ef97f4198f711b/LICENSE) |
| 最近更新 / Star | 2026-09-10T16:25:07Z；190（快照统计，不作为质量结论） |
| Release | v2026.09；2026-09-15T15:03:27Z；https://github.com/mitre-atlas/atlas-data/releases/tag/v2026.09 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 5 个 Issue；最近样本更新 2026-09-15T20:19:11Z；API open_issues_count=21（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 结构化公共数据下载；文件读取与解析，不执行引用内容；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | ai_security_resources；创新 / 工程 / 问答 |
| 最终建议 | B；核心 AI 知识资源；以稳定 ID、版本和案例证据导入，不强制每个 CVE 对应技术 |
| 核查来源 | [README/文档](https://github.com/mitre-atlas/atlas-data/blob/3259f388d19cbcca11bacf12a0ef97f4198f711b/README.md)；源码 SHA 3259f388d19cbcca11bacf12a0ef97f4198f711b；README 已下载 |

### NVIDIA/garak · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/NVIDIA/garak)；[官网](https://discord.gg/uVch4puUCs) |
| 类别 / 解决问题 | ai_security_resources；LLM probe、检测器与安全测试 |
| 能力 / 接入 / 语言 | LLM probe、检测器与安全测试；API / SDK / Docker（见专题选择）；Python |
| License | Apache-2.0；[授权来源](https://github.com/NVIDIA/garak/blob/bb30a7e79f4e78ef633a92295f142105a0e69941/LICENSE) |
| 最近更新 / Star | 2026-10-02T17:55:54Z；9411（快照统计，不作为质量结论） |
| Release | v0.17.0；2026-09-09T18:56:03Z；https://github.com/NVIDIA/garak/releases/tag/v0.17.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-10-02T06:55:55Z；API open_issues_count=484（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | ai_security_resources；创新 / 工程 / 问答 |
| 最终建议 | B；V0.2/决赛离线评测；昂贵、可能外发提示，不能当实时情报源 |
| 核查来源 | [README/文档](https://github.com/NVIDIA/garak/blob/bb30a7e79f4e78ef633a92295f142105a0e69941/README.md)；源码 SHA bb30a7e79f4e78ef633a92295f142105a0e69941；README 已下载 |

### OpenAlex API · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | 无独立仓库指标；相关镜像见专题；[官网](https://help.openalex.org/access/example-costs/) |
| 类别 / 解决问题 | ai_security_resources；学术元数据、机构与引文 |
| 能力 / 接入 / 语言 | 学术元数据、机构与引文；API / Data；JSON/XML/HTTP 或规范 |
| License | 元数据 CC0；全文权利和 API 计费独立；[授权来源](https://help.openalex.org/access/example-costs/) |
| 最近更新 / Star | 文档查询 2026-10-03；持续服务无可比统一 commit；不适用（快照统计，不作为质量结论） |
| Release | 服务/规范版本见官方文档，不套用 GitHub Release |
| Issue / 维护 | 服务支持/标准维护，不适用 GitHub Issue；官方服务/标准；不构成 SLA 验证 |
| 部署 / 资源 | 低 / 低；调用/解析成本估计，未部署量测 |
| 收费 / Key | 见 key/专题和官方条款；不得把免费额度理解成无限免费；生产使用 API key；每天免费额度，查询按用量计费 |
| 权限 / 风险 | 只读指定官方 endpoint；检索字符串可能外发；不提交私有清单/文档；MEDIUM；限制为官方公共只读接口；第三方外发/输入投毒风险仍存在 |
| AegisAI 模块 / 比赛价值 | ai_security_resources；富化 / 问答 / 创新 |
| 最终建议 | B；核心/分阶段封装，具体时机见 final_recommendation.md |
| 核查来源 | [README/文档](https://help.openalex.org/access/example-costs/)；官方文档查询；README 未下载/不适用，按专题说明 |

### OWASP/www-project-top-10-for-large-language-model-applications · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications)；http://genai.owasp.org |
| 类别 / 解决问题 | ai_security_resources；GenAI 风险分类与 LLM Top 10 |
| 能力 / 接入 / 语言 | GenAI 风险分类与 LLM Top 10；Data；Python |
| License | CC-BY-SA-4.0；[授权来源](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/99f4395589bdbd120ae961f9cd179e79d7f9b27f/LICENSE.md) |
| 最近更新 / Star | 2026-08-05T19:19:47Z；1432（快照统计，不作为质量结论） |
| Release | 2024；2024-11-18T00:35:51Z；https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/releases/tag/2024 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 4 个 Issue；最近样本更新 2026-10-02T03:00:29Z；API open_issues_count=87（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 结构化公共数据下载；文件读取与解析，不执行引用内容；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | ai_security_resources；创新 / 工程 / 问答 |
| 最终建议 | B；分类与解释参考；CC-BY-SA，不能充当逐漏洞 ground truth |
| 核查来源 | [README/文档](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/99f4395589bdbd120ae961f9cd179e79d7f9b27f/README.md)；源码 SHA 99f4395589bdbd120ae961f9cd179e79d7f9b27f；README 已下载 |

### protectai/llm-guard · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/protectai/llm-guard)；[官网](https://protectai.github.io/llm-guard/) |
| 类别 / 解决问题 | ai_security_resources；输入输出扫描器与内容控制 |
| 能力 / 接入 / 语言 | 输入输出扫描器与内容控制；API / SDK / Docker（见专题选择）；Python |
| License | MIT；[授权来源](https://github.com/protectai/llm-guard/blob/168c1034ffdb33837e7ae6fd6a16b80567c1be03/LICENSE) |
| 最近更新 / Star | 2026-07-08T23:58:39Z；3212（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=38（含 PR）；已归档 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | ai_security_resources；创新 / 工程 / 问答 |
| 最终建议 | D；仓库已归档；不作为持续维护的核心防护依赖 |
| 核查来源 | [README/文档](https://github.com/protectai/llm-guard/blob/168c1034ffdb33837e7ae6fd6a16b80567c1be03/README.md)；源码 SHA 168c1034ffdb33837e7ae6fd6a16b80567c1be03；README 已下载 |

### protectai/modelscan · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/protectai/modelscan)；http://modelscan.ai |
| 类别 / 解决问题 | ai_security_resources；模型文件静态不安全格式扫描 |
| 能力 / 接入 / 语言 | 模型文件静态不安全格式扫描；API / SDK / Docker（见专题选择）；Python |
| License | Apache-2.0；[授权来源](https://github.com/protectai/modelscan/blob/61fcec9c2a37c24c1fb12d84ede30fe248a364bd/LICENSE) |
| 最近更新 / Star | 2026-02-18T21:05:38Z；777（快照统计，不作为质量结论） |
| Release | v0.8.8；2026-02-18T21:14:19Z；https://github.com/protectai/modelscan/releases/tag/v0.8.8 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 3 个 Issue；最近样本更新 2026-09-27T01:25:34Z；API open_issues_count=84（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | ai_security_resources；创新 / 工程 / 问答 |
| 最终建议 | B；V0.2 模型供应链可选；静态结果是信号，不能证明模型安全 |
| 核查来源 | [README/文档](https://github.com/protectai/modelscan/blob/61fcec9c2a37c24c1fb12d84ede30fe248a364bd/README.md)；源码 SHA 61fcec9c2a37c24c1fb12d84ede30fe248a364bd；README 已下载 |

### Semantic Scholar API · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | 无独立仓库指标；相关镜像见专题；[官网](https://api.semanticscholar.org/license/) |
| 类别 / 解决问题 | ai_security_resources；学术搜索与引用网络 |
| 能力 / 接入 / 语言 | 学术搜索与引用网络；API；JSON/XML/HTTP 或规范 |
| License | 当前 API 协议含非商业研究/教育授权及展示归属要求；商用需另谈；[授权来源](https://api.semanticscholar.org/license/) |
| 最近更新 / Star | 文档查询 2026-10-03；持续服务无可比统一 commit；不适用（快照统计，不作为质量结论） |
| Release | 服务/规范版本见官方文档，不套用 GitHub Release |
| Issue / 维护 | 服务支持/标准维护，不适用 GitHub Issue；官方服务/标准；不构成 SLA 验证 |
| 部署 / 资源 | 低 / 低；调用/解析成本估计，未部署量测 |
| 收费 / Key | 见 key/专题和官方条款；不得把免费额度理解成无限免费；key/配额随端点；本次未拿账号验证 |
| 权限 / 风险 | 只读指定官方 endpoint；检索字符串可能外发；不提交私有清单/文档；MEDIUM；限制为官方公共只读接口；第三方外发/输入投毒风险仍存在 |
| AegisAI 模块 / 比赛价值 | ai_security_resources；富化 / 问答 / 创新 |
| 最终建议 | D；V0.1 不选；先明确商业授权与额外价值 |
| 核查来源 | [README/文档](https://api.semanticscholar.org/license/)；官方文档查询；README 未下载/不适用，按专题说明 |

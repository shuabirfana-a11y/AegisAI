# Dify 插件：复用交互能力，保护情报真值

**V0.1 使用 Dify 作单条问答/解释和受限工具编排；不使用插件直接把事实写入可信情报库。** 现成能力足够覆盖 GitHub 辅助查询、多格式文本提取、论文查找、Function Calling 和网页正文；稳定监测、修订历史和证据来源则需要后端适配器。

## 来源与版本

源码快照：[dify-official-plugins](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee)。市场对照：[GitHub 0.3.10](https://marketplace.dify.ai/plugin/langgenius/github)、[Dify Extractor 0.1.1](https://marketplace.dify.ai/plugin/langgenius/dify_extractor)。插件的独立版本来自 manifest；monorepo 的默认分支或 Star 不能替代具体安装包校验。市场描述可能落后于实际 tools 列表。

| 候选 | 已核查的能力/版本 | 选型与边界 |
|---|---|---|
| GitHub / 0.3.10 | 仓库、README、内容、issues、commits、release、PR、code search；也含创建/评论/合并等写入工具 | B；辅助查找可用。正式漏洞/公告采集直连 REST，令牌、缓存、ETag、分页、限流与日志统一在后端 |
| Firecrawl / 0.2.3 | scrape、crawl、map、search、monitor | B；V0.2 复杂站点；不是 V0.1 的免费万能采集器 |
| Jina Tool / 0.0.14 | Reader 和检索工具 | B；首期直接 API 更便于保留 URL、抓取时间、原始响应与费用 |
| Dify Extractor / 0.1.1 | PDF、DOCX、PPTX、Excel、MD、HTML、CSV、JSON、YAML、文本 | A；文档辅助解析，但不能替代不可变原文件与页/行/段落回链 |
| Agent / 0.0.50 | Function Calling、ReAct、显式工具允许列表 | A；首期选 Function Calling，输出 JSON schema，限制工具和步数 |
| arXiv / 0.0.8；Crossref / 0.0.8 | 论文/DOI 元数据，部分工具会调用模型总结 | B；V0.2，摘要和原始元数据分开存 |
| DuckDuckGo / 0.0.13 | 搜索；README 明示旧 AI chat、translate 已弃用 | D；不能把旧功能列成可用能力；搜索只作候选发现 |
| GitHub datasource / 0.4.8 | 内容导入知识库 | B；RAG 辅助，不是漏洞增量监测或证据血缘实现 |
| Firecrawl datasource / 0.2.14 | 网页导入知识库 | B；V0.2，避免和后端重复采集计作独立来源 |
| GitHub trigger / 1.5.1 | webhook 触发 | B；只适用于可配置 webhook 的授权仓库；签名和重放保护另落实 |
| RSSHub trigger / 0.1.1 | webhook 触发组件 | D；不能替代 RSS 定时拉取与持久化游标 |
| SQLite / Websearch | SQL/搜索工具 | D；SQLite 不替代 PostgreSQL，通用 SQL 不对 Agent 开放 |

GitHub 功能覆盖判断以 [tools 目录](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/github/tools) 为依据，本快照未发现专用全局 Security Advisory 工具。REST 的 [global advisories](https://docs.github.com/en/rest/security-advisories/global-advisories) 是正式接入的选择；“插件没有此专用工具”不表示 GitHub 平台没有 API。

## 文档解析为什么仍需后端

Extractor 现在给出全文 Markdown 与格式相应结构化 records，PDF 有页、表格有行、Markdown 有节；其他格式不一定有精细坐标。后端先保存原文件和 hash，解析输出标注 parser/version、页/节定位及提取错误；LLM 引用必须回到证据片段。扫描 PDF/OCR 和复杂版面放 V0.2 的 Docling 验证。

本快照依赖为 pypdfium2 等，不应拿早期 PyMuPDF 依赖印象判断现在的许可。Extractor manifest 声明 256 MiB，最低 Dify 1.9.0；这不是容量实测。远程图片下载限制协议和字节数，但没有仅凭 URL scheme 就能证明阻止私网请求；受控出站/无外链图片模式必须在部署验收中测试。[Extractor 源码](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/dify_extractor)。

## 编排和接入约束

[Dify Tools 官方文档](https://docs.dify.ai/en/cloud/use-dify/workspace/tools)支持插件、OpenAPI、Workflow Tool 和 HTTP MCP。首期把后端的 `lookup_vulnerability`、`get_evidence`、`explain_conflict` 等少数只读语义操作发布为 OpenAPI 工具；不暴露任意 SQL、shell、任意 URL 和任意写入路径。无需为这些只读操作另造 MCP Server。

Agent 的 allowed_tools 未设/为空会启用节点内全部工具，不能把空数组当拒绝所有。只配置后端允许的 2—4 个只读操作、工具请求预算、输出 schema、模型和提示模板版本。ReAct 可研究，第一版没有必要让模型自由规划长链采集。[允许列表说明及源码](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/agent-strategies/cot_agent)。

动态 MCP 头可能因请求上下文缺失变成空值或原样占位文本。后端从已认证会话/令牌导出租户与用户权限；缺失或不可信 header 必须拒绝，不能默认管理员或公共租户。Dify 的知识库可重建，后端才保存审核状态、证据版本和来源冲突。

## 明天的安装清单

下一个开发阶段才执行：固定一个受支持 Dify 版本；只启用需要的模型供应商与官方 Agent 策略。Extractor 是首期文件通路的可选安装；纯 JSON/API 漏洞闭环不依赖它。GitHub、Firecrawl、论文、datasource 和 trigger 插件按阶段再加，避免同时存放多组外部密钥。本轮没有安装或配置 Dify 应用，以上是冻结选型。

## 可信第三方插件与市场安全工具检索

实际市场检索找到了 [hjlarry/database 0.0.6](https://marketplace.dify.ai/plugin/hjlarry/database) 和 [ContrastAPI 0.8.0](https://marketplace.dify.ai/plugin/contrastcyber/contrastapi)。前者支持 PostgreSQL 等数据库、SQL/text2sql、连接 URI 覆盖和入站 SQL HTTP endpoint，源码非 SELECT/WITH 分支会执行并提交事务；归 D。endpoint 是接收请求，不应误读成通用出站网页抓取。后者市场列53个工具，除漏洞/ATLAS查询外还包含主动网站扫描；与 API/MCP README的55 tools是不同发布单位，不强行视为同一个版本。市场有隐私/数据处理说明，但本轮没有完整验证其线上落实或在当前仓库定位插件打包源码；归 D，不据“Verified”或安装量推荐。其他 db_query/sql-db/HelloDB 等数据库候选只完成发现，未完整审查，不计入候选清单或采用推荐。

## 候选档案

所有时间来自本次快照。资源和部署级别为选型估计，没有冒充部署实测。原始 JSON 见 [候选清单](candidate_catalog.json)。

### contrastcyber/contrastapi · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/UPinar/contrastapi)；[官网](https://marketplace.dify.ai/plugin/contrastcyber/contrastapi) |
| 类别 / 解决问题 | dify_plugins；53工具：CVE/KEV/EPSS、ATLAS/D3FEND、OSINT 与主动网站扫描 |
| 能力 / 接入 / 语言 | 53工具：CVE/KEV/EPSS、ATLAS/D3FEND、OSINT 与主动网站扫描；Dify Plugin；插件语言/完整源及运行未全部核实 |
| License | API仓库MIT；插件包与线上数据条款未完整核实；[授权来源](https://github.com/UPinar/contrastapi/blob/07957c19576aaaa4b27014201e7c184bdc15fc7f/LICENSE) |
| 最近更新 / Star | 2026-10-02T15:44:47Z；33（快照统计，不作为质量结论） |
| Release | 市场版本 0.8.0（2026-10-03核对）；仓库 Release 与插件包不混同 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 1 个 Issue；最近样本更新 2026-09-14T14:35:01Z；API open_issues_count=3（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 目标域名/IP/代码向第三方，含主动扫描工具；不调用扫描；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | D；市场有隐私声明但本轮未完整核对在线落实；当前仓库树未定位插件打包源码；不默认依赖 |
| 核查来源 | [README/文档](https://marketplace.dify.ai/plugin/contrastcyber/contrastapi)；源码 SHA 07957c19576aaaa4b27014201e7c184bdc15fc7f；README 未下载/不适用，按专题说明 |

### hjlarry/database · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/hjlarry/dify-plugin-database)；[官网](https://marketplace.dify.ai/plugin/hjlarry/database) |
| 类别 / 解决问题 | dify_plugins；多数据库 SQL、text2sql、schema、CSV 与 SQL HTTP endpoint |
| 能力 / 接入 / 语言 | 多数据库 SQL、text2sql、schema、CSV 与 SQL HTTP endpoint；Dify Plugin；Python 3.12（manifest已核实） |
| License | 未确认；[授权来源](https://github.com/hjlarry/dify-plugin-database/tree/e9156f71e799591cb80026cdc80a4b296c2a3e01) |
| 最近更新 / Star | 2025-08-15T09:33:40Z；105（快照统计，不作为质量结论） |
| Release | 市场版本 0.0.6（2026-10-03核对）；仓库 Release 与插件包不混同 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 5 个 Issue；最近样本更新 2026-09-22T10:50:33Z；API open_issues_count=30（含 PR）；低频/稳定维护或待确认；不按提交日期单独判死 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 数据库凭证/任意SQL/动态连接URI与HTTP endpoint；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | dify_plugins；问答 / Agent / 工程 |
| 最终建议 | D；任意 SQL 与动态连接 URI；根 LICENSE 未确认；不用业务数据库通用工具 |
| 核查来源 | [README/文档](https://marketplace.dify.ai/plugin/hjlarry/database)；源码 SHA e9156f71e799591cb80026cdc80a4b296c2a3e01；README 未下载/不适用，按专题说明 |

### hjlarry/dify-plugin-database · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/hjlarry/dify-plugin-database)；https://github.com/hjlarry/dify-plugin-database（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | dify_plugins；PostgreSQL 等数据库的任意 SQL、text2sql、schema 和 SQL HTTP endpoint |
| 能力 / 接入 / 语言 | PostgreSQL 等数据库的任意 SQL、text2sql、schema 和 SQL HTTP endpoint；API / SDK / Docker（见专题选择）；Python |
| License | 未确认；[授权来源](https://github.com/hjlarry/dify-plugin-database/tree/e9156f71e799591cb80026cdc80a4b296c2a3e01) |
| 最近更新 / Star | 2025-08-15T09:33:40Z；105（快照统计，不作为质量结论） |
| Release | 0.0.6；2025-04-25T02:03:38Z；https://github.com/hjlarry/dify-plugin-database/releases/tag/0.0.6 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 5 个 Issue；最近样本更新 2026-09-22T10:50:33Z；API open_issues_count=30（含 PR）；低频/稳定维护或待确认；不按提交日期单独判死 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | dify_plugins；问答 / Agent / 工程 |
| 最终建议 | D；源码有事务提交分支，动态数据库 URI；许可未确认，首期不向 Agent 提供数据库连接 |
| 核查来源 | [README/文档](https://github.com/hjlarry/dify-plugin-database/blob/e9156f71e799591cb80026cdc80a4b296c2a3e01/README.md)；源码 SHA e9156f71e799591cb80026cdc80a4b296c2a3e01；README 已下载 |

### langgenius/agent · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/agent-strategies/cot_agent)；[官网](https://marketplace.dify.ai/plugin/langgenius/agent) |
| 类别 / 解决问题 | dify_plugins；Function Calling / ReAct、工具允许列表 |
| 能力 / 接入 / 语言 | Function Calling / ReAct、工具允许列表；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-28T02:36:05Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.0.50；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；HIGH；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | A；选择 Function Calling，显式 allowed_tools 与调用预算 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/agent-strategies/cot_agent/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/arxiv · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/arxiv)；[官网](https://marketplace.dify.ai/plugin/langgenius/arxiv) |
| 类别 / 解决问题 | dify_plugins；论文检索与可选摘要 |
| 能力 / 接入 / 语言 | 论文检索与可选摘要；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.0.8；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；MEDIUM；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | B；V0.2 论文富化；证据引文保持原文和版本 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/arxiv/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/crossref · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/crossref)；[官网](https://marketplace.dify.ai/plugin/langgenius/crossref) |
| 类别 / 解决问题 | dify_plugins；DOI、标题与出版元数据 |
| 能力 / 接入 / 语言 | DOI、标题与出版元数据；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.0.8；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；MEDIUM；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | B；V0.2；直接 API 比 Agent 内总结更易留证 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/crossref/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/dify · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify)；[官网](https://dify.ai) |
| 类别 / 解决问题 | dify_plugins；Workflow、Chatflow、RAG、工具调用 |
| 能力 / 接入 / 语言 | Workflow、Chatflow、RAG、工具调用；API / SDK / Docker（见专题选择）；TypeScript |
| License | Dify Open Source License（Apache-2.0 修改版）；[授权来源](https://github.com/langgenius/dify/blob/43af5082d3c4ab8a96067370d2f86f214e3c85ae/LICENSE) |
| 最近更新 / Star | 2026-10-03T03:16:11Z；157733（快照统计，不作为质量结论） |
| Release | 1.17.1；2026-09-10T10:04:06Z；https://github.com/langgenius/dify/releases/tag/1.17.1 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=974（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | dify_plugins；问答 / Agent / 工程 |
| 最终建议 | B；复用会话与编排，独立部署；保留证据真值在后端；自定义许可证需登记 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify/blob/43af5082d3c4ab8a96067370d2f86f214e3c85ae/README.md)；源码 SHA 43af5082d3c4ab8a96067370d2f86f214e3c85ae；README 已下载 |

### langgenius/dify-official-plugins · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins)；https://github.com/langgenius/dify-official-plugins（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | dify_plugins；官方插件源码、manifest 与版本 |
| 能力 / 接入 / 语言 | 官方插件源码、manifest 与版本；API / SDK / Docker（见专题选择）；Python |
| License | Apache-2.0；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-29T02:24:08Z；634（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-10-02T15:53:26Z；API open_issues_count=89（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | dify_plugins；问答 / Agent / 工程 |
| 最终建议 | B；逐插件锁定审核版本；不能把整个仓库的权限视为同一权限 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/dify-plugins · C

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-plugins)；https://github.com/langgenius/dify-plugins（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | dify_plugins；插件生态与提交组织 |
| 能力 / 接入 / 语言 | 插件生态与提交组织；API / SDK / Docker（见专题选择）；Python |
| License | 未发现可确认的仓库级 LICENSE；逐插件确认；[授权来源](https://github.com/langgenius/dify-plugins/tree/175ba426e20e673aa673f11e09563a3763b1ec21) |
| 最近更新 / Star | 2026-09-30T13:35:49Z；556（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=43（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | dify_plugins；问答 / Agent / 工程 |
| 最终建议 | C；作为发现入口；仓库许可未确认，不能替代逐插件审查 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-plugins/blob/175ba426e20e673aa673f11e09563a3763b1ec21/README.md)；源码 SHA 175ba426e20e673aa673f11e09563a3763b1ec21；README 已下载 |

### langgenius/dify_extractor · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/dify_extractor)；[官网](https://marketplace.dify.ai/plugin/langgenius/dify_extractor) |
| 类别 / 解决问题 | dify_plugins；PDF/DOCX/HTML/MD/JSON/YAML/CSV 等文本与结构化提取 |
| 能力 / 接入 / 语言 | PDF/DOCX/HTML/MD/JSON/YAML/CSV 等文本与结构化提取；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.1.1；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 中；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；HIGH；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | A；辅助文档通路直接复用；原始文件与定位回链由后端持有 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/dify_extractor/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/duckduckgo · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/duckduckgo)；[官网](https://marketplace.dify.ai/plugin/langgenius/duckduckgo) |
| 类别 / 解决问题 | dify_plugins；搜索；AI chat/translate 已弃用 |
| 能力 / 接入 / 语言 | 搜索；AI chat/translate 已弃用；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-15T02:44:52Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.0.13；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；MEDIUM；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | D；不作稳定核心源；工具存在不代表每个旧功能可用 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/duckduckgo/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/firecrawl · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/firecrawl)；[官网](https://marketplace.dify.ai/plugin/langgenius/firecrawl) |
| 类别 / 解决问题 | dify_plugins；scrape、crawl、map、search、monitor |
| 能力 / 接入 / 语言 | scrape、crawl、map、search、monitor；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.2.3；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；MEDIUM；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | B；V0.2 复杂抓取；首期 Jina API 优先 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/firecrawl/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/firecrawl_datasource · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/datasources/firecrawl_datasource)；[官网](https://marketplace.dify.ai/plugin/langgenius/firecrawl_datasource) |
| 类别 / 解决问题 | dify_plugins；网页批量导入知识库 |
| 能力 / 接入 / 语言 | 网页批量导入知识库；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.2.14；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；MEDIUM；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | B；V0.2 可选，不与后端证据采集重复计票 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/datasources/firecrawl_datasource/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/github · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/github)；[官网](https://marketplace.dify.ai/plugin/langgenius/github) |
| 类别 / 解决问题 | dify_plugins；仓库、README、issues、commit、release、code search 及写入工具 |
| 能力 / 接入 / 语言 | 仓库、README、issues、commit、release、code search 及写入工具；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.3.10；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；HIGH；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | B；只作受限辅助；正式采集直连 API |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/github/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/github_datasource · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/datasources/github)；[官网](https://marketplace.dify.ai/plugin/langgenius/github_datasource) |
| 类别 / 解决问题 | dify_plugins；GitHub 内容进入知识库的 datasource |
| 能力 / 接入 / 语言 | GitHub 内容进入知识库的 datasource；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.4.8；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；HIGH；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | B；可选辅助 RAG；不是带来源修订历史的漏洞采集器 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/datasources/github/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/github_trigger · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/triggers/github_trigger)；[官网](https://marketplace.dify.ai/plugin/langgenius/github_trigger) |
| 类别 / 解决问题 | dify_plugins；GitHub webhook 事件 |
| 能力 / 接入 / 语言 | GitHub webhook 事件；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 1.5.1；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；HIGH；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | B；V0.2 对授权仓库使用签名校验 webhook；公共监测仍需轮询 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/triggers/github_trigger/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/jina_tool · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/jina)；[官网](https://marketplace.dify.ai/plugin/langgenius/jina_tool) |
| 类别 / 解决问题 | dify_plugins；Reader、搜索、正文获取 |
| 能力 / 接入 / 语言 | Reader、搜索、正文获取；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.0.14；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；MEDIUM；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | B；后端 API 优先，Dify 插件只作可选便捷入口 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/jina/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/rsshub_trigger · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/triggers/rsshub_trigger)；[官网](https://marketplace.dify.ai/plugin/langgenius/rsshub_trigger) |
| 类别 / 解决问题 | dify_plugins；RSSHub webhook 事件触发 |
| 能力 / 接入 / 语言 | RSSHub webhook 事件触发；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-22T09:03:34Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.1.1；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；MEDIUM；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | D；不能替代定时 RSS 采集；首期 feedparser 即可 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/triggers/rsshub_trigger/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/sqlite · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/sqlite)；[官网](https://marketplace.dify.ai/plugin/langgenius/sqlite) |
| 类别 / 解决问题 | dify_plugins；SQL 数据库工具 |
| 能力 / 接入 / 语言 | SQL 数据库工具；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-22T09:14:26Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.0.7；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；HIGH；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | D；SQLite 不是业务 PostgreSQL 方案；禁止直接 SQL Tool 进入证据写入路径 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/sqlite/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

### langgenius/websearch · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/websearch)；[官网](https://marketplace.dify.ai/plugin/langgenius/websearch) |
| 类别 / 解决问题 | dify_plugins；通用网页搜索聚合 |
| 能力 / 接入 / 语言 | 通用网页搜索聚合；Dify Plugin；Python 3.12（manifest） |
| License | Apache-2.0（官方仓库）；外部服务条款另核实；[授权来源](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:57:04Z；634（快照统计，不作为质量结论） |
| Release | manifest 0.0.8；monorepo 无独立 GitHub Release；仅 GitHub/Extractor 的市场版本本次另核对一致 |
| Issue / 维护 | 宿主仓库 Issue 样本见库记录；逐插件问题需按名称复查，不能按仓库星数推稳定性；有 2026 年目录提交；marketplace 与源码可能不同步 |
| 部署 / 资源 | 低 / 低；manifest 为声明上限；未运行 Dify 量测 |
| 收费 / Key | 插件无订阅费；模型及 API 调用按外部平台计费；由 provider 配置；GitHub/Firecrawl 等需凭证，Extractor 不要求服务密钥 |
| 权限 / 风险 | manifest/model/tool 声明和 Python 实际网络/文件权限分别审查；详见安全矩阵；MEDIUM；外部输入、写入或工具执行权限的场景风险，非已证实漏洞 |
| AegisAI 模块 / 比赛价值 | 编排/辅助检索/文件解析；Agent / 工程 / 问答 |
| 最终建议 | D；核心线索优先官方公告与受控 API；外部搜索只提供候选 |
| 核查来源 | [README/文档](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/websearch/README.md)；源码 SHA 60fd178450bf76fa651f348113a9bc93783dd1ee；README 已下载 |

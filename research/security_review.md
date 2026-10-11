# 安全审查：按实际能力与接入场景授权

**首期不向 Agent 暴露通用 SQL、shell、任意文件或任意 URL 抓取。** 外部情报始终是数据；所有可信写入、权限、引用校验和源请求由后端控制。

## 等级和检查范围

LOW：在固定官方 endpoint/本地解析的有限输入场景，无业务写权限。MEDIUM：网络、外部内容、云端提交、文件解析或复杂依赖，需要出站/输入/凭证约束。HIGH：默认写能力、自由工具执行、任意URL/文件面、浏览器/模型/扫描任务或第三方数据外发可影响机密/完整性。等级代表未受控接入的场景风险，不是已证明漏洞严重度。

下表检查 eval/exec、shell、文件、任意URL/SSRF、DB写入、密钥、secret日志、第三方上传、远程代码与高权限。标记“未全审”保留未知；未在所读文件发现危险调用不能证明整个依赖树没有。源码审查和文档审查分开，未进行漏洞利用或线上渗透。

| 组件/服务 | eval/exec 与 shell | 文件/任意 URL/SSRF | 数据库/外部写入 | Key 保存与日志 | 外发/下载执行/高权限 | 风险与选择 |
|---|---|---|---|---|---|---|
| Dify 主体+官方 Agent | 策略调度允许工具，不因此拥有 OS exec；平台代码未全审 | 工具决定输入面；Allowed tools 空=节点内全工具 | 应用/知识库写入；可信库写入由后端授权 | workspace/provider配置；必须对日志实测脱敏 | LLM可外发；不提供shell/任意URL；部署非root | HIGH；受限 Function Calling，A/B 条件使用 |
| GitHub plugin / datasource / trigger | 所读工具主要HTTP，未做完整依赖审计 | 动态GitHub URL、内容注入；webhook需验签 | 创建/评论/合并等写操作；datasource写知识库 | provider PAT/OAuth；错误响应/原始header禁止入日志 | 私有仓库内容可能发LLM；无须root | HIGH；公开只读API首期优先，禁写工具与大权限令牌 |
| GitHub 官方 MCP | README及关键入口，未全树审计 | HTTP和远程工具内容 | 默认工具集合可含写操作，readonly/allowlist需配置 | PAT/OAuth在服务端；不让model读环境 | 远程GitHub接收查询；不传私有内容给无授权模型 | MEDIUM至HIGH；V0.2仅只读工具和小权限令牌 |
| Firecrawl tool/datasource/SaaS | 浏览器/执行能力依模式；未全树审 | 任意目标crawl，redirect/私网请求面 | 创建monitor/服务任务；不直接可信DB | provider key/base URL；审查日志与自托管环境 | URL/页面交云；自托管浏览器权限高，不默认root | MEDIUM云端公共站点/HIGH自托管；V0.2限制域名、深度、字节和预算 |
| Jina tool/Reader API | 本地插件HTTP；服务未全审 | 任意目标URL，需统一出站策略和隐藏目标/敏感query约束 | 无业务库写入；服务可能缓存内容 | provider key仅采集侧，query/URL也需脱敏 | 目标URL/内容经第三方；不发送私有文档/内网 | MEDIUM；首期公共公告辅助，可失败降级 |
| Dify Extractor | YAML安全解析和native PDF等分别核查；无全依赖证明 | 上传文件、远程MD/DOCX图片；HTTP(S)scheme检查不证明禁私网 | 上传图片/结果到Dify，非可信DB写入 | 无独立服务key；解析错误/URL可能写日志 | 下载外链图片；native parser；不应root | HIGH未受控外链/文件；限制输入、隔离出站并验证，不只看市场S评级 |
| arXiv/Crossref plugins | 元数据请求与可选模型摘要；未全审 | 论文/检索输入；下载链接需检查 | 知识库/缓存随工作流 | 邮箱/模型配置；日志不含输入原文默认 | 摘要发送模型；论文授权逐篇 | MEDIUM；V0.2，仅元数据/受许可文本 |
| DuckDuckGo / Websearch | 第三方依赖未全审 | 查询、返回URL和内容注入 | 无自有DB权限 | 参数/外部key依provider；脱敏日志 | 检索词外发；旧功能失效 | MEDIUM；不作主数据通路 |
| RSSHub trigger | webhook处理；未全审 | 外部事件、URL/载荷 | 触发工作流 | 事件认证/signature或shared secret需实测 | RSS服务和后续模型可外发 | MEDIUM；首期不引入 |
| VulnMCP | 模型/工具依赖；关键server非全审 | 外部CIRCL等API、自定义服务URL | 可创建sighting，首期禁用 | 环境API key只在server；日志需验证 | NLP权重/内容外发；不自动执行漏洞代码 | MEDIUM至HIGH；C，不给写密钥 |
| badchars/cve-mcp | 关键入口/README，未全审 | 多外部数据API | 查询为主，完整工具写范围未证实 | 多服务环境key；日志未实测 | query/CVE向第三方；包管理安装必须pin | MEDIUM未知项；C，不作为首期默认 |
| ContrastAPI | 在线实现未完全核实 | 多HTTP安全查询/目标输入 | 作者声明只读不能覆盖未审实现 | 托管服务保留/密钥策略未知 | 目标域名/IP/内容向第三方，terms未知 | HIGH机密输入；D |
| 社区 ATT&CK / OSV / RSS MCP | 文件不完整或未运行；不作安全认证 | RSS可抓URL；OSV固定源与具体实现核查不足 | 数据写入/缓存未全审 | key/日志策略未验证 | RSS可能调用模型，安装依赖需pin | MEDIUM未知；D；使用官方Data/API/解析库 |
| arxiv-mcp-server | server入口核查，下载器未全审 | 本地paper/LaTeX/watch文件、远程归档 | 本地watch/cache写入 | 环境key/HTTP服务auth与日志需验收 | 论文下载、引用查询至SemanticScholar；源归档不执行 | MEDIUM至HIGH；V0.2磁盘隔离、认证、限下载 |
| PostgreSQL MCP / SQLite SQL Tool | SQL执行是主要能力，不能靠没有shell判断安全 | 库连接/输入SQL | Postgres源码默认unrestricted、可写；只读仍可能泄密/DoS | DB凭证/connection string不可进日志 | DB外发/批量读；禁止owner/superuser | HIGH；D，不暴露业务库，提供语义只读API |
| CVE/GHSA/OSV/NVD/CISA/EPSS | 官方JSON/API读取，无下载后代码执行需求 | 仅固定官方host；引用URL隔离抓取 | 后端受控落库；不给Agent DB凭证 | GitHub/NVD key服务端，令牌/headers禁日志 | 包查询可能泄露私有包；仅公共目标，bulk方式按官方 | LOW受限公共只读；B，原始值仍防投毒 |
| ATLAS/OWASP/CWE/CAPEC/ATT&CK/D3FEND/STIX数据 | 数据解析不执行script，禁XML外部实体 | 下载指定版本；JSON/YAML/XML大小深度限制 | 受控数据导入 | 通常无key；源文件不会作为指令 | 不执行构建脚本/宏；内容原始许可保留 | LOW至MEDIUM解析；A/B按阶段 |
| Crossref/arXiv/OpenAlex/SemanticScholar API | 读取元数据，无执行需求 | 固定官方host，不任意follow全文URL | 后端受控缓存 | key/邮件与query脱敏；业务日志不保存key | 查询/全文请求外发；授权/收费独立 | MEDIUM；学术V0.2，SemanticScholar先不选 |
| packaging/PURL/semver/univers/feedparser/stix2 | 解析库/进程调用，禁止字符串拼shell；完整依赖未审 | 不可信文本；feedparser仅解析已抓取内容 | 无业务写权，工具结果受控 | 无key；错误消息避免整文件/秘密 | 安装固定包非latest脚本；默认非root | LOW受限解析；A/B，保留unknown与输入限额 |
| Docling/Unstructured/PyMuPDF | native解析/OCR/模型依赖；未全审 | 文件/归档/native攻击面 | 临时文件和输出写入 | 云API/模型key依方式；日志脱敏 | 权重/依赖下载；复杂worker隔离，禁止root | HIGH未隔离；V0.2 Docling，PyMuPDF首期D |
| Syft/Grype/OSV-Scanner | 固定CLI，用户命令/项目脚本禁执行 | 镜像/目录/归档与DB更新 | 只写隔离结果，不授业务DB | registry key独立；镜像路径/私有名脱敏 | package清单可能外发；禁止Docker socket/特权 | HIGH未隔离；V0.2 scanner worker |
| ModelScan/garak/评测harness | 模型扫描与探测，部分benchmark可能运行攻击环境 | 模型/数据文件、模型endpoint | 输出/cache；不获业务DB | 模型服务key与prompt日志隔离 | 不反序列化不可信模型；不执行PoC；预算限制 | HIGH；V0.2/决赛选定静态/离线子集 |
| OpenCTI/MISP/IntelOwl/GUAC | 大型平台/分析器依赖，未全审 | connectors与文件/URL扩展面 | 大量平台DB和外部事件写入 | 各连接器密钥、logs与role需系统审计 | 文件/IOC可能上传分析服务，权限依组件 | HIGH整体接入成本；C，首期只借鉴设计 |
| Trickest/CVEfixes/MoreFixes/基准data | 只下载文本/metadata；任何restore/script都不自动执行 | 仓库链接/patch/SQL dump含不可信内容 | 未导入SQL dump；后续隔离无特权解析 | 无密钥，不保存个人token | 引用PoC禁止执行；dataset不默认作为instruction | MEDIUM数据/HIGH运行采集或攻击；B种子 |

## 有直接源码依据的关键发现

1. GitHub 插件列出 merge/create/comment 等写工具；不能按“仓库查询插件”描述把全权限PAT交给Agent。[源码目录](https://github.com/langgenius/dify-official-plugins/tree/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/github/tools)。
2. Agent 的 empty/unset allowlist 放行节点全部工具，需显式子集。[策略 README](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/agent-strategies/cot_agent/README.md)。
3. Extractor image_assets.py 会 requests.get 引用图片，先检查HTTP(S)，有数目/字节/时间约束；所读函数未见私网地址与DNS/redirect的完整阻断。标为SSRF输入面与部署约束，**未声称已证实可利用SSRF**。[源码](https://github.com/langgenius/dify-official-plugins/blob/60fd178450bf76fa651f348113a9bc93783dd1ee/tools/dify_extractor/tools/image_assets.py)。
4. Postgres MCP server.py 的默认 AccessMode 为 unrestricted，有受限模式；需要DB角色和语义接口限制，不能只靠名称里“safe”。README传输描述较旧，源码已含streamable-http。[源码](https://github.com/crystaldba/postgres-mcp/blob/15c8e33353546148acc2d8bd784551cf3905d1e2/src/postgres_mcp/server.py)。

## 首期可执行的安全验收要求

外部文件包含“忽略上文/运行命令/发往某网址”时，模型只能作为被引用内容处理；任何非允许工具请求被后端拒绝。引用证据 ID、页/段位置必须存在且来自本请求可访问的已审核数据，不能凭LLM生成ID。模型只提审核候选，不能改可信状态。

抓取只允许http(s)且逐跳校验目的地址：拒绝localhost、内网/链路本地/metadata、非允许端口；DNS解析与连接目标一致、防重绑定、出站网络再限制。限制大小、解压比、重定向、并发与超时；文件路径固定在隔离目录，不跟随越界symlink；YAML安全加载、XML禁外部实体、Office不执行宏。

密钥通过服务端secret机制提供，分服务和用途；日志只保留操作/ID/脱敏错误，不记Authorization、完整连接串、env、原始私有文档。LLM供应商、Jina/Firecrawl及scanner的输入外发有明确数据分类；公共公告与私有资产默认分开。升级插件重新比较工具、依赖、endpoint和权限，不因“官方/市场S”跳过复核。

以上是下一阶段实现与验收要求。本轮没有执行恶意payload、访问内网、导入SQL dump、部署容器或运行PoC；没有用grep无命中宣称依赖不存在漏洞。

## 新发现的第三方数据库与安全插件

数据库插件 hjlarry/database 源码 sql_execute.py 在非 SELECT/WITH 分支执行 SQL 并提交事务，支持连接URI覆盖；provider配置是secret-input，manifest有model/tool/endpoint权限，入站endpoint把请求参数交给SQL工具。它不是通用网页抓取器。数据库写入、动态数据库地址与HTTP暴露风险为HIGH；完整依赖、endpoint认证和根许可未全审，首期D。ContrastAPI Dify插件不只是只读CVE查询，还列主动站点扫描与代码/目标输入外发，风险为HIGH；市场隐私声明有具体内容，但本轮未核实保留策略线上执行，未调用扫描或上传私有数据，首期D。

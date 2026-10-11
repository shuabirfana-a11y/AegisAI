# MCP：按接口收益选用，不按协议名称堆栈

**V0.1 不新增业务 MCP Server。** 官方漏洞 API 已提供可校验 JSON，后端直接接入少一层身份、缓存和协议维护。Dify 支持 HTTP MCP；stdio-only 项目需要另一个桥接服务，这会增加凭证与运行边界。[Dify 官方说明](https://docs.dify.ai/en/cloud/use-dify/workspace/tools)。

## 候选兼容性与可信来源

| Server | 来源 | 已核实传输/能力 | Dify 适配与决定 |
|---|---|---|---|
| github/github-mcp-server | GitHub 官方 | 远程 HTTP、工具集合、只读配置；本地运行另配置 | B，V0.2 可选；用令牌权限+toolset+readonly 共同限制，首期 REST 更便于取证 |
| vulnerability-lookup/VulnMCP | CIRCL 生态项目，不是 NVD/CISA 官方 Server | README 有 FastMCP HTTP；多聚合查询、CPE 猜测、模型；包含创建 sighting 功能 | C；模型和外发依赖、AGPL 与写入边界，不作为首期真值层 |
| badchars/cve-mcp | 社区 | 多漏洞源、EPSS/KEV/OSV/GHSA 等包装；文档以 stdio 为主 | C；不能据名称当官方资源，直连 API 优先 |
| UPinar/contrastapi | 社区/第三方在线服务 | README 远端 `/mcp/`，55 tools/7 resources 是作者声明 | D；未核实服务条款、数据保留和所有工具实现；不上传私有资料 |
| SalehKamil/mcp-mitre-attack | 社区 | 树中是场景/skills/资料；缺根 README 和已确认 LICENSE，未核实独立部署入口 | D；不把命名当可运行 MCP 的证据 |
| blazickjp/arxiv-mcp-server | 社区 | 当前源码有 stdio、Streamable HTTP；下载论文/LaTeX、本地缓存和 watches，可能调用 Semantic Scholar | B，V0.2 隔离选用；首期论文元数据不需 Server |
| crystaldba/postgres-mcp | 社区 | README 提 stdio/SSE；当前源码还实现 `streamable-http`。默认 `UNRESTRICTED`，有 SQL/诊断 | D；HTTP 支持不会消除 SQL 权限问题，首期不用 |
| ptelang/osv-mcp | 社区 | 轻量 OSV 包装，最后提交 2025-04 | D；直接 OSV API 更明确；未做运行测试 |
| gperdrizet/rss-mcp-server | 社区 | RSS+摘要/RAG，GPL；模型/运行依赖 | D；feedparser+受控 HTTP 足以解决首期问题 |
| modelcontextprotocol/servers | 官方参考集合 | 参考实现和历史归档组件，范围随目录不同 | C；不是针对 AegisAI 数据库已审计的通用授权层 |

Postgres Server 的 README 与源代码出现了传输能力更新不一致。报告以 [当前 server.py](https://github.com/crystaldba/postgres-mcp/blob/15c8e33353546148acc2d8bd784551cf3905d1e2/src/postgres_mcp/server.py) 的三种传输选项为依据，未声称其只有旧 SSE；同时源码默认 unrestricted 的证据仍然有效。完整 SHA 见候选档案。

## 未找到可靠官方包装时的处理

GitHub repository search 覆盖 CVE/NVD/OSV/KEV/EPSS、ATLAS、ATT&CK、arXiv/RSS 和 security intelligence。结果中大量关键词相似但无关的项目没有纳入。未核实一个由 NVD、FIRST、CISA 或 MITRE 官方维护并能替代其数据接口的统一 MCP；因此选官方 API/Data，而不宣布这些 Server 全网不存在。

ATLAS 官方已有版本化 YAML/派生数据；ATT&CK 官方已有 STIX，CWE/CAPEC 官方有 XML，CISA 有 JSON，EPSS 有 API/CSV。包一层 MCP 并不能产生独立证据、解决版本语义或判断 PoC 真假。

## 接入门槛

允许进入下一阶段的 MCP 必须有：锁定源码/依赖与工具清单、HTTP endpoint 的访问控制、工具级允许列表、只读和写入分离、密钥只在服务端、公开查询和私有输入的分类、日志脱敏、超时/配额/错误码、可导出的原始响应。与 Dify 的 initialize、tools/list、auth、call、timeout、streaming 等测试仍需实际部署完成。

本轮只做文档、源码和公共 API 核查，没有把任何候选部署为 Dify MCP，也没有冒充“稳定运行已验证”。成本比较：只读 REST 数据源通常低；增加单个 Python/Node Server 为中；额外模型、向量库、全文下载/浏览器依赖可升到高。未来若多个客户端必须共享同一套 AegisAI 只读语义工具，才考虑由后端导出 MCP。

## 候选档案

所有时间来自本次快照。资源和部署级别为选型估计，没有冒充部署实测。原始 JSON 见 [候选清单](candidate_catalog.json)。

### badchars/cve-mcp · C

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/badchars/cve-mcp)；[官网](https://www.npmjs.com/package/cve-mcp) |
| 类别 / 解决问题 | mcp_servers；多个漏洞情报 API 的 TypeScript 包装 |
| 能力 / 接入 / 语言 | 多个漏洞情报 API 的 TypeScript 包装；MCP / HTTP 或 stdio 见专题；TypeScript |
| License | MIT；[授权来源](https://github.com/badchars/cve-mcp/blob/31ee55553a39f0c5d8270977ea308e7a733a57ee/LICENSE) |
| 最近更新 / Star | 2026-07-06T21:21:43Z；29（快照统计，不作为质量结论） |
| Release | v0.2.0；2026-07-06T19:27:37Z；https://github.com/badchars/cve-mcp/releases/tag/v0.2.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=5（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；GitHub/NVD 等服务按工具需要，禁止提供全权限开发者令牌 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | C；借鉴字段与适配器；stdio 与第三方密钥依赖，优先直连接口 |
| 核查来源 | [README/文档](https://github.com/badchars/cve-mcp/blob/31ee55553a39f0c5d8270977ea308e7a733a57ee/README.md)；源码 SHA 31ee55553a39f0c5d8270977ea308e7a733a57ee；README 已下载 |

### blazickjp/arxiv-mcp-server · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/blazickjp/arxiv-mcp-server)；[官网](https://www.pulsemcp.com/servers/blazickjp-arxiv-mcp-server) |
| 类别 / 解决问题 | mcp_servers；论文搜索、下载、原始 LaTeX、引用与本地 watches |
| 能力 / 接入 / 语言 | 论文搜索、下载、原始 LaTeX、引用与本地 watches；MCP / HTTP 或 stdio 见专题；Python |
| License | Apache-2.0；[授权来源](https://github.com/blazickjp/arxiv-mcp-server/blob/e477454fcda4e1ece0202a0cdeca0ad99d8d07df/LICENSE) |
| 最近更新 / Star | 2026-10-03T01:24:21Z；3187（快照统计，不作为质量结论） |
| Release | v0.8.0；2026-10-03T01:25:25Z；https://github.com/blazickjp/arxiv-mcp-server/releases/tag/v0.8.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-10-03T01:30:03Z；API open_issues_count=4（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | B；HTTP 源码已核实；V0.2 隔离运行并限制磁盘、下载与外发，首期直接元数据 API |
| 核查来源 | [README/文档](https://github.com/blazickjp/arxiv-mcp-server/blob/e477454fcda4e1ece0202a0cdeca0ad99d8d07df/README.md)；源码 SHA e477454fcda4e1ece0202a0cdeca0ad99d8d07df；README 已下载 |

### crystaldba/postgres-mcp · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/crystaldba/postgres-mcp)；https://github.com/crystaldba/postgres-mcp（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | mcp_servers；SQL、执行计划、诊断与索引建议 |
| 能力 / 接入 / 语言 | SQL、执行计划、诊断与索引建议；MCP / HTTP 或 stdio 见专题；Python |
| License | MIT；[授权来源](https://github.com/crystaldba/postgres-mcp/blob/15c8e33353546148acc2d8bd784551cf3905d1e2/LICENSE) |
| 最近更新 / Star | 2026-08-16T05:33:37Z；3364（快照统计，不作为质量结论） |
| Release | v0.3.0；2025-05-16T14:45:33Z；https://github.com/crystaldba/postgres-mcp/releases/tag/v0.3.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=91（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 数据库连接，默认可写 SQL；只读开关不替代数据库角色权限；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | D；源码默认 unrestricted，可写数据库；即使改只读也不向 Agent 暴露业务库 SQL |
| 核查来源 | [README/文档](https://github.com/crystaldba/postgres-mcp/blob/15c8e33353546148acc2d8bd784551cf3905d1e2/README.md)；源码 SHA 15c8e33353546148acc2d8bd784551cf3905d1e2；README 已下载 |

### github/github-mcp-server · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/github/github-mcp-server)；https://github.com/github/github-mcp-server（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | mcp_servers；GitHub 官方 MCP、工具集合与只读配置 |
| 能力 / 接入 / 语言 | GitHub 官方 MCP、工具集合与只读配置；MCP / HTTP 或 stdio 见专题；Go |
| License | MIT；[授权来源](https://github.com/github/github-mcp-server/blob/f10e4e1f923d46b86f2e80e849aa74084c847184/LICENSE) |
| 最近更新 / Star | 2026-10-02T14:31:11Z；33332（快照统计，不作为质量结论） |
| Release | v1.14.0；2026-10-02T20:14:37Z；https://github.com/github/github-mcp-server/releases/tag/v1.14.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=341（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；GitHub/NVD 等服务按工具需要，禁止提供全权限开发者令牌 |
| 权限 / 风险 | PAT/OAuth；可读写 GitHub，显式 toolsets + readonly + 令牌权限三层约束；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | B；V0.2 可选；V0.1 后端直接调用 API，避免增加协议与凭证层 |
| 核查来源 | [README/文档](https://github.com/github/github-mcp-server/blob/f10e4e1f923d46b86f2e80e849aa74084c847184/README.md)；源码 SHA f10e4e1f923d46b86f2e80e849aa74084c847184；README 已下载 |

### gperdrizet/rss-mcp-server · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/gperdrizet/rss-mcp-server)；[官网](https://huggingface.co/spaces/Agents-MCP-Hackathon/rss-mcp-server) |
| 类别 / 解决问题 | mcp_servers；RSS、摘要与 RAG 的社区 Server |
| 能力 / 接入 / 语言 | RSS、摘要与 RAG 的社区 Server；MCP / HTTP 或 stdio 见专题；Python |
| License | GPL-3.0；[授权来源](https://github.com/gperdrizet/rss-mcp-server/blob/2b63658953d76c5de7b2245a5d58b9ee90239b68/LICENSE) |
| 最近更新 / Star | 2025-06-12T02:18:32Z；2（快照统计，不作为质量结论） |
| Release | 1.0.0；2025-06-12T01:30:14Z；https://github.com/gperdrizet/rss-mcp-server/releases/tag/1.0.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=0（含 PR）；低频/稳定维护或待确认；不按提交日期单独判死 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | D；GPL、外部模型和服务依赖；用 feedparser 加自有受控采集更简单 |
| 核查来源 | [README/文档](https://github.com/gperdrizet/rss-mcp-server/blob/2b63658953d76c5de7b2245a5d58b9ee90239b68/README.md)；源码 SHA 2b63658953d76c5de7b2245a5d58b9ee90239b68；README 已下载 |

### modelcontextprotocol/servers · C

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/modelcontextprotocol/servers)；[官网](https://modelcontextprotocol.io) |
| 类别 / 解决问题 | mcp_servers；参考 Server 与协议示例 |
| 能力 / 接入 / 语言 | 参考 Server 与协议示例；MCP / HTTP 或 stdio 见专题；TypeScript |
| License | GitHub 未识别 SPDX；以实际 LICENSE 为准，未作放行；[授权来源](https://github.com/modelcontextprotocol/servers/blob/f46d9578190b476b3501923ea8977d899e8db2cb/LICENSE) |
| 最近更新 / Star | 2026-09-22T14:30:15Z；90961（快照统计，不作为质量结论） |
| Release | 2026.8.31；2026-08-31T20:34:32Z；https://github.com/modelcontextprotocol/servers/releases/tag/2026.8.31 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=551（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | C；参考接口设计；其中历史数据库示例不能成为业务授权边界 |
| 核查来源 | [README/文档](https://github.com/modelcontextprotocol/servers/blob/f46d9578190b476b3501923ea8977d899e8db2cb/README.md)；源码 SHA f46d9578190b476b3501923ea8977d899e8db2cb；README 已下载 |

### ptelang/osv-mcp · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/ptelang/osv-mcp)；https://github.com/ptelang/osv-mcp（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | mcp_servers；OSV 查询的轻量包装 |
| 能力 / 接入 / 语言 | OSV 查询的轻量包装；MCP / HTTP 或 stdio 见专题；Python |
| License | MIT；[授权来源](https://github.com/ptelang/osv-mcp/blob/b28952fd5a1b470ee38b5e6f5ba0ee34b061febd/LICENSE) |
| 最近更新 / Star | 2025-04-22T16:39:47Z；1（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=0（含 PR）；低频/稳定维护或待确认；不按提交日期单独判死 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | D；少更新且 API 已足够；首期不多维护一层 MCP |
| 核查来源 | [README/文档](https://github.com/ptelang/osv-mcp/blob/b28952fd5a1b470ee38b5e6f5ba0ee34b061febd/README.md)；源码 SHA b28952fd5a1b470ee38b5e6f5ba0ee34b061febd；README 已下载 |

### SalehKamil/mcp-mitre-attack · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/SalehKamil/mcp-mitre-attack)；https://github.com/SalehKamil/mcp-mitre-attack（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | mcp_servers；ATT&CK 使用场景、技能和映射资料 |
| 能力 / 接入 / 语言 | ATT&CK 使用场景、技能和映射资料；MCP / HTTP 或 stdio 见专题；Python |
| License | 未核实根 LICENSE，禁止默认复制代码；[授权来源](https://github.com/SalehKamil/mcp-mitre-attack/tree/82a2c16039dc6045009e2527ea3d61971a406654) |
| 最近更新 / Star | 2026-09-26T12:13:20Z；0（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=0（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | D；缺根 README/LICENSE，未核实独立可运行 Server；名称不能证明兼容性 |
| 核查来源 | [README/文档](https://github.com/SalehKamil/mcp-mitre-attack/tree/82a2c16039dc6045009e2527ea3d61971a406654)；源码 SHA 82a2c16039dc6045009e2527ea3d61971a406654；README 未下载/不适用，按专题说明 |

### UPinar/contrastapi · D

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/UPinar/contrastapi)；[官网](https://api.contrastcyber.com) |
| 类别 / 解决问题 | mcp_servers；社区聚合安全 API 与远端 MCP |
| 能力 / 接入 / 语言 | 社区聚合安全 API 与远端 MCP；MCP / HTTP 或 stdio 见专题；Python |
| License | MIT；[授权来源](https://github.com/UPinar/contrastapi/blob/07957c19576aaaa4b27014201e7c184bdc15fc7f/LICENSE) |
| 最近更新 / Star | 2026-10-02T15:44:47Z；33（快照统计，不作为质量结论） |
| Release | v1.36.2；2026-08-24T22:31:47Z；https://github.com/UPinar/contrastapi/releases/tag/v1.36.2 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 1 个 Issue；最近样本更新 2026-09-14T14:35:01Z；API open_issues_count=3（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | D；协议可用性不等于可审计来源；未验证在线服务条款、保留策略和独立性，首期不用 |
| 核查来源 | [README/文档](https://github.com/UPinar/contrastapi/blob/07957c19576aaaa4b27014201e7c184bdc15fc7f/README.md)；源码 SHA 07957c19576aaaa4b27014201e7c184bdc15fc7f；README 已下载 |

### vulnerability-lookup/VulnMCP · C

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/vulnerability-lookup/VulnMCP)；https://github.com/vulnerability-lookup/VulnMCP（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | mcp_servers；CIRCL 漏洞查询、sightings、CPE 推断与 NLP |
| 能力 / 接入 / 语言 | CIRCL 漏洞查询、sightings、CPE 推断与 NLP；MCP / HTTP 或 stdio 见专题；Python |
| License | AGPL-3.0；[授权来源](https://github.com/vulnerability-lookup/VulnMCP/blob/3f9bc2a990724d25211d8498bc1181d997c9dbd8/LICENSE) |
| 最近更新 / Star | 2026-10-02T12:53:11Z；42（快照统计，不作为质量结论） |
| Release | v2.0.0；2026-08-30T09:35:57Z；https://github.com/vulnerability-lookup/VulnMCP/releases/tag/v2.0.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=2（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | CIRCL 外发查询、模型下载、本地缓存；可创建 sightings 的 API key 必须禁用；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | mcp_servers；创新 / 工程 / 问答 |
| 最终建议 | C；借鉴聚合工具接口；AGPL、外部服务与 sightings 写入使其不适合首期默认依赖 |
| 核查来源 | [README/文档](https://github.com/vulnerability-lookup/VulnMCP/blob/3f9bc2a990724d25211d8498bc1181d997c9dbd8/README.md)；源码 SHA 3f9bc2a990724d25211d8498bc1181d997c9dbd8；README 已下载 |

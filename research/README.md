# AegisAI 第一步技术调研与 V0.1 选型

调研日期：2026-10-03（北京时间）。任务依据：用户提供的《空白文档(1).docx》，以及“直接开始按文档”的执行授权。本轮范围为调研、真实数据验证、取舍和技术选型；至此停止，不进入正式业务开发。

**结论：采用“官方漏洞 API/数据 + 后端证据与确定性判断 + Dify 受限问答”的小闭环。** 不从零写包解析和扫描器；不把情报真值交给通用 Agent；不将 OpenCTI/MISP/IntelOwl 整套搬入第一版。详细决定及文档要求的 18 个问题见 [最终选型](final_recommendation.md)。

## 阅读顺序

| 文档 | 直接解决的决定 |
|---|---|
| [final_recommendation.md](final_recommendation.md) | 明天用什么、接什么、自己写什么；12 节、18 个答案和架构 |
| [dify_plugins.md](dify_plugins.md) | 插件实际功能、版本、权限与 Dify 边界 |
| [mcp_servers.md](mcp_servers.md) | 官方/社区 MCP、HTTP 兼容与 API 对比 |
| [vulnerability_sources.md](vulnerability_sources.md) | CVE/GHSA/OSV/NVD/CISA/EPSS 字段与真实样本 |
| [enrichment_tools.md](enrichment_tools.md) | 实体、版本、PoC、patch 与知识映射 |
| [ai_security_resources.md](ai_security_resources.md) | ATLAS、OWASP、AI 相关性及学术资源 |
| [cti_projects.md](cti_projects.md) | Evidence、lineage、冲突与分析人员工作流 |
| [supply_chain.md](supply_chain.md) | SBOM/资产匹配的复用与分期 |
| [benchmark.md](benchmark.md) | 公开评测与自建 AegisBench 真值方案 |
| [licenses.md](licenses.md) | 代码、数据、模型和服务条款分开登记 |
| [security_review.md](security_review.md) | 外部请求、文件、数据库、密钥和 Agent 的权限检查 |
| [candidate_catalog.json](candidate_catalog.json) | 所有候选的完整字段、分类和快照统计 |
| [evidence/validation.json](evidence/validation.json) | 实际 HTTP 数据对齐、版本边界与文件哈希 |

## 核查方法和统计口径

GitHub 元数据、README、LICENSE、默认分支 commit、最新 GitHub Release 和近期 Issue 样本均从官方仓库读取；关键插件额外读取 Python 源码、manifest、provider 和策略。正文链接尽量锁定源码 commit，服务文档标明查询日。发布日期、源码日期、市场发布版本分别记录，不混为“最近更新”。Star 仅为快照字段，未用于决定质量。

清单按“独立仓库、具体 Dify 插件、无独立仓库的官方服务/标准”分别计数。插件与宿主仓库属于不同选型单位；CISA/GHSA/OSV 的重叠记录不算独立证据。搜索命中数、错误猜测的仓库路径、同一仓库旧名和 API 样本条数都不计入候选数量。准确总数见本文后面的自动统计。

安全结论是接入场景与所读源码的审查，未做完整渗透测试。LOW 不表示零风险；HIGH 也不表示已经证明存在可利用漏洞。部署难度、资源为估计，没有实际部署峰值数据。Issue 只抽取最近一页，不能声称完成维护者响应时延统计。

## 完成了哪些实际验证

- 读取 Dify 官方插件源码并核对 GitHub/Extractor 的 Marketplace 版本。GitHub 插件含写操作；Agent 的空 allowed_tools 表示允许节点内全工具；Extractor 可抓远程引用图片。
- 调用真实 CVE、NVD、GHSA、OSV、KEV、Vulnrichment、EPSS 接口/数据，核对 CVE-2025-32434 的包身份、范围和来源。获取对应公开修复 commit 和改动文件；未执行 PoC 或受影响软件。
- 使用本机 packaging 26.3 验证名称规范化与 6 个版本边界，发现 `<0.8.4` 与 `<=0.8.3` 在 `0.8.3.post1` 上不同。
- 下载并检查 CVEfixes、MoreFixes 的 Zenodo 元数据，区分发布日、截止日期、代码许可证和数据许可证。
- 下载 CWE 官方 XML ZIP，检查 ATLAS 官方仓库的数据组织与授权，确认 ATT&CK/D3FEND 使用官方版本化数据而非猜测 MCP 名称。

## 证据与限制

交付的 `evidence/` 保存候选元数据、插件 manifest/关键源文件、API 样本、验证结果与文件哈希。完整原始调研缓存保留在工作目录 `work/research_evidence/`；交付包只附与结论必要的轻量快照。第三方 LICENSE 随对应源码快照保留；原始公告/代码版权仍属于原发布者。

原赛题 PDF 的微信临时路径本次已失效，未重新读取，因而没有编造赛题条款或评分要求。本报告的“比赛价值”依据任务文档的系统主线；正式开发前应与可读取的完整赛题再次对照。

部分网络请求发生 TLS 中断，已重试并保留结果。404 路径区分错误猜测和真实项目；例如 AgentDojo 实际位于 ethz-spylab，garak 已以 NVIDIA/garak 为规范仓库名。没找到可靠官方 ATLAS/CVE MCP 的证据不等于断言全网不存在。未做 Dify 运行集成、插件安装或商业服务账户试用；Context7 本轮原生工具连接失败，相关结论改用官方文档和源码核查。

本轮未建立正式数据库、后端、前端、Dify Workflow、多 Agent 或知识图谱；`work/` 脚本只用于采集公开调研证据和生成本报告。

## 自动统计

按候选单位，共 **87项**：61个已取得元数据的独立仓库、16个具体Dify插件、10个官方服务/标准；A=18、B=44、C=9、D=16。这是选型清单数量，不是全部项目已部署数量，也不是独立情报源数量。

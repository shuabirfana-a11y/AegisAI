# 候选源逐项调查

核验日期2026-10-03；以官方资料和实际HTTP/仓库响应为准。全部候选均发出本轮查询；存在入口不代表返回正文、可稳定采集或已有生产SLA。`UNKNOWN / NEED_VERIFY`不伪装已确认。原始调查响应在evidence/；JSON清单记录URL、时间、HTTP、hash、重定向、partial。研究probe只读不执行下载内容。

代码许可证与情报文本许可证分别登记；API成功不等于自由再分发。GitHub API元数据NOASSERTION/null时读取真实许可，不能直接判“无许可证”。

## CVE Program / cvelistV5

| 属性 | 调研结果 |
|---|---|
| 名称/ID | CVE Program / cvelistV5 / CVE_LIST |
| 类别/权威 | 漏洞目录 / 身份/状态权威；CNA内容依发布者 |
| 官方地址/资料 | [官方1](https://github.com/CVEProject/cvelistV5)；[官方2](https://github.com/CVEProject/cvelistV5/blob/main/README.md)；[官方3](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2025/32xxx/CVE-2025-32434.json)；[官方4](https://www.cve.org/Legal/TermsOfUse) |
| 数据与字段 | cveMetadata；containers.cna/adp；描述/affected/metrics/references |
| 获取方式/用途 | Official Git；最直接的CVE身份与CNA/ADP原文；官方Git支持持续修订 |
| Token/Rate Limit | 不需要；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | README约7分钟；不是SLA |
| 增量 | Git commit diff；release baseline/hourly delta为备选 |
| License/限制 | CVE Terms of Use：保留MITRE版权与许可；不是schema的CC0 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T05:36:26Z；不是运行SLA |
| 采用/阶段 | 采用：第一批；M0→M1；Tier 1 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## OSV.dev

| 属性 | 调研结果 |
|---|---|
| 名称/ID | OSV.dev / OSV |
| 类别/权威 | 漏洞目录/包生态 / 生态包版本；聚合来源需lineage |
| 官方地址/资料 | [官方1](https://api.osv.dev/v1)；[官方2](https://github.com/google/osv.dev)；[官方3](https://github.com/google/osv.dev/blob/master/README.md)；[官方4](https://github.com/google/osv.dev/blob/master/LICENSE)；[官方5](https://api.osv.dev/v1/vulns/GHSA-53q9-r3pm-6pq6)；[官方6](https://google.github.io/osv.dev/data/)；[官方7](https://google.github.io/osv.dev/api/)；[官方8](https://storage.googleapis.com/osv-vulnerabilities/PyPI/modified_id.csv)；[官方9](https://api.osv.dev/v1/query) |
| 数据与字段 | id/aliases/modified/published/withdrawn；affected.package/ranges/versions；references |
| 获取方式/用途 | Official Dataset + API；原生生态包与版本事件；官方增量索引明确，不虚构全库modified API |
| Token/Rate Limit | 不需要；官方当前无API限额承诺；项目仍限并发/字节 |
| 上游更新频率 | 持续导入/导出，无固定SLA |
| 增量 | PyPI modified_id.csv按时间及ID；changed ID→GET；query/page_token仅查询分页 |
| License/限制 | 记录继承上游：GHSA/PyPI CC-BY-4.0等；服务代码Apache-2.0不是数据许可 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-02T04:17:36Z；不是运行SLA |
| 采用/阶段 | 采用：第一批；M0→M1；Tier 1 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## CISA Known Exploited Vulnerabilities

| 属性 | 调研结果 |
|---|---|
| 名称/ID | CISA Known Exploited Vulnerabilities / CISA_KEV |
| 类别/权威 | 漏洞目录/利用信号 / 已知利用入目录的正证据 |
| 官方地址/资料 | [官方1](https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json)；[官方2](https://github.com/cisagov/kev-data)；[官方3](https://github.com/cisagov/kev-data/blob/7009facc2019306d41f6d6df6c8a057b99b4b468/README.md)；[官方4](https://github.com/cisagov/kev-data/blob/7009facc2019306d41f6d6df6c8a057b99b4b468/LICENSE) |
| 数据与字段 | catalogVersion/dateReleased/count；cveID/dateAdded/requiredAction/knownRansomwareCampaignUse/cwes |
| 获取方式/用途 | Official Dataset (official mirror)；区别于预测/严重度：收录意味着已知利用；轻量完整目录可校验完整性 |
| Token/Rate Limit | 不需要；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 官方源变化后镜像通常分钟级；工作日美东时间，非固定周期 |
| 增量 | ETag条件获取；有变化才下载，按cveID/hash计算新增/更正/删除 |
| License/限制 | CC0-1.0（README和LICENSE文本；API元数据NOASSERTION不改结论） |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-02T20:23:41Z；不是运行SLA |
| 采用/阶段 | 采用：第一批；M0→M1；Tier 1 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## NVD

| 属性 | 调研结果 |
|---|---|
| 名称/ID | NVD / NVD |
| 类别/权威 | 漏洞目录/补充评估 / NIST分析；非CVE身份主源 |
| 官方地址/资料 | [官方1](https://services.nvd.nist.gov/rest/json/cves/2.0)；[官方2](https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2025-32434)；[官方3](https://nvd.nist.gov/developers/start-here)；[官方4](https://nvd.nist.gov/developers/vulnerabilities)；[官方5](https://nvd.nist.gov/general/legal-disclaimer) |
| 数据与字段 | cve.id/published/lastModified；metrics/weaknesses/configurations/references |
| 获取方式/用途 | Official API；真实API成功；首批已有身份/包/利用，NVD补充CPE和评分，不增加独立投票 |
| Token/Rate Limit | 公开可不带key；key可选；UNKNOWN / NEED_VERIFY |
| 上游更新频率 | 持续更新；SLA UNKNOWN |
| 增量 | 官方lastModStartDate/lastModEndDate + startIndex/resultsPerPage；当前文档为JS壳，参数上限需复核 |
| License/限制 | NIST使用声明；本轮NVD声明正文未得到，NEED_VERIFY |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 暂缓：文档/限额与许可正文复核后按需补充；M2；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## GitHub Security Advisories / Advisory Database

| 属性 | 调研结果 |
|---|---|
| 名称/ID | GitHub Security Advisories / Advisory Database / GHSA |
| 类别/权威 | 安全社区/包公告 / Reviewed状态不等于修复/PoC可用性认证 |
| 官方地址/资料 | [官方1](https://api.github.com/advisories)；[官方2](https://github.com/github/advisory-database)；[官方3](https://github.com/github/advisory-database/blob/507dc0b177fc5ea3834af147c1f06f3d1d9b8f19/README.md)；[官方4](https://github.com/github/advisory-database/blob/507dc0b177fc5ea3834af147c1f06f3d1d9b8f19/LICENSE.md)；[官方5](https://api.github.com/advisories/GHSA-53q9-r3pm-6pq6)；[官方6](https://docs.github.com/en/rest/security-advisories/global-advisories) |
| 数据与字段 | ghsa_id/cve_id/identifiers/vulnerabilities/first_patched_version/cvss_severities/updated_at/withdrawn_at |
| 获取方式/用途 | Official API / Git；与OSV的GHSA记录高度同源；不另接一份相同全文凑来源数量 |
| Token/Rate Limit | 公开端点不要求token；预算可用认证；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 连续更新；SLA UNKNOWN |
| 增量 | updated过滤（按官方参数编码）+Link分页；数据库Git diff |
| License/限制 | Advisory Database CC-BY-4.0；代码/引用对象另许可 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T05:32:13Z；不是运行SLA |
| 采用/阶段 | 暂缓：OSV已聚合；需未覆盖记录才独立接；M2；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## CISA Vulnrichment

| 属性 | 调研结果 |
|---|---|
| 名称/ID | CISA Vulnrichment / VULNRICHMENT |
| 类别/权威 | 漏洞目录/富化 / CISA ADP/SSVC判断，带时间/模型版本 |
| 官方地址/资料 | [官方1](https://github.com/cisagov/vulnrichment)；[官方2](https://github.com/cisagov/vulnrichment/blob/e35b475b1f73d3e6e43f8c246cfc65bac6e9ce85/README.md)；[官方3](https://github.com/cisagov/vulnrichment/blob/e35b475b1f73d3e6e43f8c246cfc65bac6e9ce85/LICENSE) |
| 数据与字段 | containers.adp[].providerMetadata；metrics.other.ssvc；CVSS/CWE/影响补充 |
| 获取方式/用途 | Official Git / CVE ADP container；补SSVC/缺失评估；同份ADP不重复采集、不当第二个独立结论 |
| Token/Rate Limit | 不需要；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 持续开发更新，无固定SLA |
| 增量 | 首先解析CVE中的CISA ADP；独立repo用Git commit diff |
| License/限制 | CC0-1.0 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T04:16:41Z；不是运行SLA |
| 采用/阶段 | 采用：第二批7；先复用已采ADP；M1→M2；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## FIRST EPSS

| 属性 | 调研结果 |
|---|---|
| 名称/ID | FIRST EPSS / EPSS |
| 类别/权威 | 漏洞目录/风险预测 / 预测概率权威发布；不证明已真实利用 |
| 官方地址/资料 | [官方1](https://api.first.org/data/v1/epss)；[官方2](https://github.com/FIRSTdotorg/epss)；[官方3](https://github.com/FIRSTdotorg/epss/blob/8753b3978446a68f5bac3c3a15c5d9102e4494a3/LICENSE)；[官方4](https://api.first.org/data/v1/epss?cve=CVE-2025-32434)；[官方5](https://www.first.org/epss/data.html)；[官方6](https://api.first.org/epss/)；[官方7](https://www.first.org/epss/) |
| 数据与字段 | cve/epss/percentile/date；CSV头model_version |
| 获取方式/用途 | Official API (small lookup) / Daily Dataset (bulk)；风险优先级补充；API只用于小批量，批量按官方指向CSV |
| Token/Rate Limit | 不需要；FIRST通用公开API文档1000次/分钟；以429及服务策略为准 |
| 上游更新频率 | 每日 |
| 增量 | date版本化；每日CSV只按新日期下载，不用updated增量；少量监测CVE批次查询 |
| License/限制 | 免费无注册已确认；数据再分发授权未明确 UNKNOWN / NEED_VERIFY；旧研究代码MIT不等于数据许可 |
| 稳定性 | 官方仓库；archived=False；最近push=2022-06-01T13:23:43Z；不是运行SLA |
| 采用/阶段 | 采用：第二批5；内部查询/不公开再分发完整集；M1→M2；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## GitHub Repository/Issue/PR/Commit/Release

| 属性 | 调研结果 |
|---|---|
| 名称/ID | GitHub Repository/Issue/PR/Commit/Release / GITHUB_CODE |
| 类别/权威 | 安全社区/代码引用 / 维护者明确引用优先；第三方代码只是候选 |
| 官方地址/资料 | [官方1](https://api.github.com)；[官方2](https://docs.github.com/en/rest/security-advisories/repository-advisories)；[官方3](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)；[官方4](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)；[官方5](https://docs.github.com/en/rest/commits/commits)；[官方6](https://docs.github.com/en/rest/releases/releases)；[官方7](https://docs.github.com/en/rest/issues/issues)；[官方8](https://docs.github.com/en/rest/pulls/pulls) |
| 数据与字段 | full_name/default_branch；issue id/url；PR head/merge SHA；commit sha/files；release tag/published_at |
| 获取方式/用途 | Official REST API；精确引用→commit/PR/release/Issue元数据；禁止开发全站复杂搜索 |
| Token/Rate Limit | 公开读可无token；用最小只读认证；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 事件发生时；没有全站完整增量流承诺 |
| 增量 | 批准repo的updated/since（仅支持端点）+Link/ETag；commit SHA不变；release重新观察 |
| License/限制 | 各repo/文件自身许可；公共访问不授予复制/执行权 |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 采用：第二批6；仅白名单与明确references；M1（PoC线索）→M2（Patch）；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## PyTorch

| 属性 | 调研结果 |
|---|---|
| 名称/ID | PyTorch / VENDOR_PYTORCH |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/pytorch/pytorch/security-advisories)；[官方2](https://github.com/pytorch/pytorch)；[官方3](https://github.com/pytorch/pytorch/blob/0fbc42e05edb6a418b1ef124530767eead77e337/README.md)；[官方4](https://github.com/pytorch/pytorch/blob/0fbc42e05edb6a418b1ef124530767eead77e337/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回1条（0只表示当次空列表）；官方repo/安全文档已查。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 NOASSERTION；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T05:40:03Z；不是运行SLA |
| 采用/阶段 | 采用：第二批1；有限3产品；M1；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## TensorFlow

| 属性 | 调研结果 |
|---|---|
| 名称/ID | TensorFlow / VENDOR_TENSORFLOW |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/tensorflow/tensorflow/security-advisories)；[官方2](https://github.com/tensorflow/tensorflow)；[官方3](https://github.com/tensorflow/tensorflow/blob/6b749b04976aabfce8bf2fc60138cf932cd6721b/README.md)；[官方4](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回1条（0只表示当次空列表）；官方repo/安全文档已查。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 Apache-2.0；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T05:41:45Z；不是运行SLA |
| 采用/阶段 | 暂缓：首批厂商只做3产品；按缺口扩展；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## vLLM

| 属性 | 调研结果 |
|---|---|
| 名称/ID | vLLM / VENDOR_VLLM |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/vllm-project/vllm/security-advisories)；[官方2](https://github.com/vllm-project/vllm)；[官方3](https://github.com/vllm-project/vllm/blob/1a001d584244bd21829a5e5bd4a376ea141c0ce3/README.md)；[官方4](https://github.com/vllm-project/vllm/blob/1a001d584244bd21829a5e5bd4a376ea141c0ce3/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回1条（0只表示当次空列表）；官方repo/安全文档已查。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 Apache-2.0；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T04:43:07Z；不是运行SLA |
| 采用/阶段 | 采用：第二批1；有限3产品；M1；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## Ollama

| 属性 | 调研结果 |
|---|---|
| 名称/ID | Ollama / VENDOR_OLLAMA |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/ollama/ollama/security-advisories)；[官方2](https://github.com/ollama/ollama)；[官方3](https://github.com/ollama/ollama/blob/42e911bc3d05798cad729cb474bf62f378cb2e26/README.md)；[官方4](https://github.com/ollama/ollama/blob/42e911bc3d05798cad729cb474bf62f378cb2e26/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回0条（0只表示当次空列表）；官方repo/安全文档已查。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 MIT；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T04:09:34Z；不是运行SLA |
| 采用/阶段 | 暂缓：首批厂商只做3产品；按缺口扩展；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## Hugging Face Transformers

| 属性 | 调研结果 |
|---|---|
| 名称/ID | Hugging Face Transformers / VENDOR_HUGGINGFACE |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/huggingface/transformers/security-advisories)；[官方2](https://github.com/huggingface/transformers)；[官方3](https://github.com/huggingface/transformers/blob/02d8fb9784e8f14a1251e4c992cd82a5762417c6/README.md)；[官方4](https://github.com/huggingface/transformers/blob/02d8fb9784e8f14a1251e4c992cd82a5762417c6/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回0条（0只表示当次空列表）；官方repo/安全文档已查。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 Apache-2.0；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T03:54:50Z；不是运行SLA |
| 采用/阶段 | 暂缓：首批厂商只做3产品；按缺口扩展；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## LangChain

| 属性 | 调研结果 |
|---|---|
| 名称/ID | LangChain / VENDOR_LANGCHAIN |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/langchain-ai/langchain/security-advisories)；[官方2](https://github.com/langchain-ai/langchain)；[官方3](https://github.com/langchain-ai/langchain/blob/57236d55d9ffc8634bda987861e6fce460aff268/README.md)；[官方4](https://github.com/langchain-ai/langchain/blob/57236d55d9ffc8634bda987861e6fce460aff268/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回1条（0只表示当次空列表）；官方repo/安全文档已查。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 MIT；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-02T22:57:27Z；不是运行SLA |
| 采用/阶段 | 暂缓：首批厂商只做3产品；按缺口扩展；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## LlamaIndex

| 属性 | 调研结果 |
|---|---|
| 名称/ID | LlamaIndex / VENDOR_LLAMAINDEX |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/run-llama/llama_index/security-advisories)；[官方2](https://github.com/run-llama/llama_index)；[官方3](https://github.com/run-llama/llama_index/blob/962940ddc079cc21701d28d1237c84c82a7c5164/README.md)；[官方4](https://github.com/run-llama/llama_index/blob/962940ddc079cc21701d28d1237c84c82a7c5164/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回0条（0只表示当次空列表）；官方repo/安全文档已查。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 MIT；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-01T18:39:47Z；不是运行SLA |
| 采用/阶段 | 暂缓：首批厂商只做3产品；按缺口扩展；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## NVIDIA Triton Inference Server

| 属性 | 调研结果 |
|---|---|
| 名称/ID | NVIDIA Triton Inference Server / VENDOR_TRITON |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/triton-inference-server/server/security-advisories)；[官方2](https://github.com/triton-inference-server/server)；[官方3](https://github.com/triton-inference-server/server/blob/eb74dea5d400b92f54eacbd5f3f84903c786e4cd/README.md)；[官方4](https://github.com/triton-inference-server/server/blob/eb74dea5d400b92f54eacbd5f3f84903c786e4cd/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回0条（0只表示当次空列表）；官方repo/安全文档已查。 Triton是NVIDIA推理服务器，不与triton-lang编译器混淆；公告归NVIDIA。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 BSD-3-Clause；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-02T18:14:50Z；不是运行SLA |
| 采用/阶段 | 暂缓：首批厂商只做3产品；按缺口扩展；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## Ray

| 属性 | 调研结果 |
|---|---|
| 名称/ID | Ray / VENDOR_RAY |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/ray-project/ray/security-advisories)；[官方2](https://github.com/ray-project/ray)；[官方3](https://github.com/ray-project/ray/blob/de9feace338285782b1b5aacb1420748f551124d/README.rst)；[官方4](https://github.com/ray-project/ray/blob/de9feace338285782b1b5aacb1420748f551124d/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回1条（0只表示当次空列表）；官方repo/安全文档已查。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 Apache-2.0；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T05:30:40Z；不是运行SLA |
| 采用/阶段 | 暂缓：首批厂商只做3产品；按缺口扩展；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## MLflow

| 属性 | 调研结果 |
|---|---|
| 名称/ID | MLflow / VENDOR_MLFLOW |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/mlflow/mlflow/security-advisories)；[官方2](https://github.com/mlflow/mlflow)；[官方3](https://github.com/mlflow/mlflow/blob/10653cab3ee7e1b80737e770e9adc5059c72bf22/README.md)；[官方4](https://github.com/mlflow/mlflow/blob/10653cab3ee7e1b80737e770e9adc5059c72bf22/LICENSE.txt)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回1条（0只表示当次空列表）；官方repo/安全文档已查。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 Apache-2.0；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T05:42:54Z；不是运行SLA |
| 采用/阶段 | 采用：第二批1；有限3产品；M1；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## Jupyter

| 属性 | 调研结果 |
|---|---|
| 名称/ID | Jupyter / VENDOR_JUPYTER |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/jupyter/security/security-advisories)；[官方2](https://github.com/jupyter/security)；[官方3](https://github.com/jupyter/security/blob/6e04eff4318ef3ae28f70512d6e857d44f7ce37b/README.md)；[官方4](https://github.com/jupyter/security/blob/6e04eff4318ef3ae28f70512d6e857d44f7ce37b/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回0条（0只表示当次空列表）；官方repo/安全文档已查。 中央安全repo不是所有子项目公告全集。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 BSD-3-Clause；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-09-21T16:04:57Z；不是运行SLA |
| 采用/阶段 | 暂缓：首批厂商只做3产品；按缺口扩展；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## Kubernetes中AI基础设施

| 属性 | 调研结果 |
|---|---|
| 名称/ID | Kubernetes中AI基础设施 / VENDOR_KUBERNETES |
| 类别/权威 | 厂商公告 / 产品维护者公告；发布身份可核对 |
| 官方地址/资料 | [官方1](https://api.github.com/repos/kubernetes/kubernetes/security-advisories)；[官方2](https://github.com/kubernetes/kubernetes)；[官方3](https://github.com/kubernetes/kubernetes/blob/99a4ea72fe6fe258d2e2875e7f83223bfbd50463/README.md)；[官方4](https://github.com/kubernetes/kubernetes/blob/99a4ea72fe6fe258d2e2875e7f83223bfbd50463/LICENSE)；[官方5](https://docs.github.com/en/rest/security-advisories/repository-advisories)；[官方6](https://kubernetes.io/docs/reference/issues-security/security/) |
| 数据与字段 | ghsa_id/cve_id/summary/description/vulnerabilities/published_at/updated_at/withdrawn_at/references |
| 获取方式/用途 | Official Repository Advisories API；公开仓库advisory单条探测返回0条（0只表示当次空列表）；官方repo/安全文档已查。 仅明确AI部署/组件关联，不把全部K8s CVE标AI；官方security页另有公告入口。 |
| Token/Rate Limit | 公开已发布可不带token；未发布不访问；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 安全披露时；SLA UNKNOWN |
| 增量 | Link分页+ETag；无专用modified筛选时对小repo目录重新比hash |
| License/限制 | repo代码许可 Apache-2.0；公告文本许可另核，优先映射CC-BY-4.0的Advisory Database记录 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-02T23:37:18Z；不是运行SLA |
| 采用/阶段 | 暂缓：首批厂商只做3产品；按缺口扩展；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## NVIDIA Product Security

| 属性 | 调研结果 |
|---|---|
| 名称/ID | NVIDIA Product Security / VENDOR_NVIDIA |
| 类别/权威 | 厂商公告 / 厂商正式安全公告 |
| 官方地址/资料 | [官方1](https://www.nvidia.com/en-us/security/) |
| 数据与字段 | bulletin ID/CVE/产品/严重度/发布/更新/修复建议 |
| 获取方式/用途 | Official HTML；官方入口存在；本轮HTML与索引展示差异需复核，不伪造JSON API |
| Token/Rate Limit | 不需要；UNKNOWN / NEED_VERIFY |
| 上游更新频率 | 按披露发布 |
| 增量 | 列表及详情条件GET/hash；未确认公开稳定机器API |
| License/限制 | NVIDIA站点/公告内容条款 UNKNOWN / NEED_VERIFY |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 暂缓：HTML/机器接口与许可需补核；M2/M3；Tier 3 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## arXiv

| 属性 | 调研结果 |
|---|---|
| 名称/ID | arXiv / ARXIV |
| 类别/权威 | 学术论文 / 作者预印本平台；不是事实核验机构 |
| 官方地址/资料 | [官方1](https://export.arxiv.org/api/query)；[官方2](https://info.arxiv.org/help/api/user-manual.html)；[官方3](https://info.arxiv.org/help/api/tou.html)；[官方4](https://export.arxiv.org/api/query?search_query=all%3A%22prompt%20injection%22&start=0&max_results=1&sortBy=lastUpdatedDate&sortOrder=descending) |
| 数据与字段 | Atom entry id/title/summary/author/category/published/updated/link；论文版本 |
| 获取方式/用途 | Official API (Atom)；官方API真实返回Atom；先摘要/元数据，全文按单篇权限 |
| Token/Rate Limit | 不需要；legacy API≤1请求/3秒、单连接；全部机器共享 |
| 上游更新频率 | 作者提交/修订；固定源SLA UNKNOWN |
| 增量 | lastUpdatedDate排序+start/max_results；时间重叠及ID版本去重；不是强一致CDC |
| License/限制 | 描述性元数据CC0-1.0；论文全文每篇license，不默认可复制 |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 采用：第二批2；M1；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## Trail of Bits Blog

| 属性 | 调研结果 |
|---|---|
| 名称/ID | Trail of Bits Blog / TOB_BLOG |
| 类别/权威 | 安全研究博客 / 研究机构原创技术分析；结论仍需scope |
| 官方地址/资料 | [官方1](https://blog.trailofbits.com/index.xml)；[官方2](https://blog.trailofbits.com/feed/) |
| 数据与字段 | RSS guid/link/title/pubDate/description/content |
| 获取方式/用途 | Official RSS；真实feed从/feed/重定向至/index.xml；技术分析及无CVE事件 |
| Token/Rate Limit | 不需要；UNKNOWN / NEED_VERIFY |
| 上游更新频率 | 文章发布时；SLA UNKNOWN |
| 增量 | ETag+guid/link+entry hash；有限feed保留期，停机后允许补查批准归档 |
| License/限制 | 正文再分发许可 UNKNOWN / NEED_VERIFY；元数据/链接先行 |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 采用：第二批3；不公开复制全文；M1；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## Google Security Blog

| 属性 | 调研结果 |
|---|---|
| 名称/ID | Google Security Blog / GOOGLE_SECURITY_BLOG |
| 类别/权威 | 安全厂商博客 / 厂商/研究团队原创发布 |
| 官方地址/资料 | [官方1](https://feeds.feedburner.com/GoogleOnlineSecurityBlog)；[官方2](https://security.googleblog.com/feeds/posts/default?alt=atom) |
| 数据与字段 | Atom id/title/published/updated/link/content |
| 获取方式/用途 | Official linked Atom Feed；官方blog入口曾降级跳HTTP；本轮补验证同feed HTTPS200，生产拒绝HTTPS降级 |
| Token/Rate Limit | 不需要；UNKNOWN / NEED_VERIFY |
| 上游更新频率 | 文章发布时；SLA UNKNOWN |
| 增量 | Last-Modified条件GET+entry id/updated/hash；有限窗口，不保证所有文章回补 |
| License/限制 | 正文适用Google/作者条款；再分发 UNKNOWN / NEED_VERIFY |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 采用：第二批3；HTTPS限定、元数据/链接先行；M1；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## NIST AI标准/风险技术出版物

| 属性 | 调研结果 |
|---|---|
| 名称/ID | NIST AI标准/风险技术出版物 / NIST_AI |
| 类别/权威 | 技术标准/规范 / 官方技术规范/框架；不把voluntary guidance写成法律 |
| 官方地址/资料 | [官方1](https://www.nist.gov/itl/ai-risk-management-framework)；[官方2](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)；[官方3](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)；[官方4](https://www.nist.gov/open/license) |
| 数据与字段 | publication ID/DOI/title/author/日期/版本/status/PDF link |
| 获取方式/用途 | Official HTML Index + Official PDF；官方AI RMF目录/出版页/PDF真实存在；只采该AI规范范围，无稳定专用API确认 |
| Token/Rate Limit | 不需要；UNKNOWN / NEED_VERIFY |
| 上游更新频率 | 修订/发布驱动；不承诺每日新版本 |
| 增量 | 批准官方目录定时观察/条件GET；发现新链接和content hash；保留draft/final/superseded |
| License/限制 | 按NIST Technical Series许可声明与单文档第三方标注；不是笼统全部CC0 |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 采用：第二批4；M1必需；M1；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## 国家标准信息平台AI安全标准

| 属性 | 调研结果 |
|---|---|
| 名称/ID | 国家标准信息平台AI安全标准 / SAMR_AI_STANDARD |
| 类别/权威 | 技术标准 / 官方国家标准发布/状态元数据 |
| 官方地址/资料 | [官方1](https://std.samr.gov.cn/gb/search/gbDetailed?id=301E0388CB75788DE06397BE0A0AE1B4)；[官方2](https://std.samr.gov.cn/search/stdPage?q=GB45438)；[官方3](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F32EA2A561F1886CD8D606513512D547) |
| 数据与字段 | 标准号/中文英文名称/发布日期/实施日期/状态/主管部门/官方阅读链接 |
| 获取方式/用途 | Official HTML metadata / official reading link；已核GB 45438-2025正式标准元数据与官方阅读入口；不以NIST指导框架替代正式技术标准 |
| Token/Rate Limit | 不需要；UNKNOWN / NEED_VERIFY |
| 上游更新频率 | 标准发布/修订时；非固定SLA |
| 增量 | 批准标准清单与检索页观察；标准号+语种+版本/hash；无机器API确认 |
| License/限制 | 正文在线阅读不等于可批量下载/再分发；标准内容许可 UNKNOWN / NEED_VERIFY；先元数据/官方链接 |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 采用：第二批4；M1必需；M1；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## 中国网信办AI政策法规

| 属性 | 调研结果 |
|---|---|
| 名称/ID | 中国网信办AI政策法规 / CAC_POLICY |
| 类别/权威 | 政策法规 / 正式发布机关；新闻解读与正式文本分开 |
| 官方地址/资料 | [官方1](https://www.cac.gov.cn/wxzw/zcfg/bmgz/A09370303index_1.htm)；[官方2](https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm)；[官方3](https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm) |
| 数据与字段 | title/官方URL/发布机关/发布日期/原文/文号/生效（仅显式）/版本状态 |
| 获取方式/用途 | Official HTML；正式办法原文与目录200；取代失效/zcfg/index.htm，不作自动法律结论 |
| Token/Rate Limit | 不需要；UNKNOWN / NEED_VERIFY |
| 上游更新频率 | 发布/修订驱动 |
| 增量 | 批准部门规章/规范性文件目录观察+URL/hash；自动分页发现；无API或RSS确认 |
| License/限制 | 未确认通用开放许可 UNKNOWN / NEED_VERIFY；先元数据/链接/必要证据引用，避免站点全文再分发 |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 采用：第二批4；M1必需；M1；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## EUR-Lex AI Act

| 属性 | 调研结果 |
|---|---|
| 名称/ID | EUR-Lex AI Act / EURLEX_AI |
| 类别/权威 | 政策法规 / 欧盟官方法令发布 |
| 官方地址/资料 | [官方1](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng)；[官方2](https://eur-lex.europa.eu/content/legal-notice/legal-notice.html) |
| 数据与字段 | ELI/CELEX/title/publication/文本版本/语言/修订关系 |
| 获取方式/用途 | Official document / possible feed；政策需求首期由中国官方源承担；不绕过202/站点限制 |
| Token/Rate Limit | 不需要；UNKNOWN / NEED_VERIFY |
| 上游更新频率 | 法令及修订发布 |
| 增量 | 可用feed/Cellar接口范围本轮未验证 UNKNOWN / NEED_VERIFY |
| License/限制 | 正文复用声明本轮202未取到 UNKNOWN / NEED_VERIFY |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 暂缓：本轮正文202空响应；不能作为已可自动采集源；M3；Tier 3 |
| 存在性验证 | False；失败与空响应仍保留，不算成功内容 |

## MITRE ATLAS

| 属性 | 调研结果 |
|---|---|
| 名称/ID | MITRE ATLAS / ATLAS |
| 类别/权威 | AI安全知识 / 维护威胁技术与案例；案例不等于实时攻击遥测 |
| 官方地址/资料 | [官方1](https://github.com/mitre-atlas/atlas-data)；[官方2](https://github.com/mitre-atlas/atlas-data/blob/3259f388d19cbcca11bacf12a0ef97f4198f711b/README.md)；[官方3](https://github.com/mitre-atlas/atlas-data/blob/3259f388d19cbcca11bacf12a0ef97f4198f711b/LICENSE)；[官方4](https://raw.githubusercontent.com/mitre-atlas/atlas-data/main/dist/ATLAS.yaml) |
| 数据与字段 | technique/tactic/case-study IDs/name/description/references；data schema |
| 获取方式/用途 | Official Git Dataset YAML；官方ATLAS.yaml真实获取；补非软件CVE风险与知识标签 |
| Token/Rate Limit | 不需要；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 维护者发布；没有固定SLA |
| 增量 | Git commit/tag diff；按schema版本和ID观察 |
| License/限制 | Apache-2.0（实际LICENSE，不照抄GitHub NOASSERTION） |
| 稳定性 | 官方仓库；archived=False；最近push=2026-09-15T15:03:16Z；不是运行SLA |
| 采用/阶段 | 采用：第二批8；M1→M2；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## OWASP GenAI / LLM Top 10

| 属性 | 调研结果 |
|---|---|
| 名称/ID | OWASP GenAI / LLM Top 10 / OWASP_GENAI |
| 类别/权威 | AI安全知识 / 社区维护风险与防护知识；不是厂商修复认证 |
| 官方地址/资料 | [官方1](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications)；[官方2](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/99f4395589bdbd120ae961f9cd179e79d7f9b27f/README.md)；[官方3](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/99f4395589bdbd120ae961f9cd179e79d7f9b27f/LICENSE.md)；[官方4](https://genai.owasp.org/llm-top-10/) |
| 数据与字段 | risk ID/name/edition/description/mitigations/references |
| 获取方式/用途 | Official Git / versioned site；维护风险分类/安全建议，不把无CVE知识强制变漏洞 |
| Token/Rate Limit | 不需要；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 版本/文档维护时 |
| 增量 | Git commit/tag；website按批准版本URL/hash，旧版本并存 |
| License/限制 | CC-BY-SA-4.0（实际LICENSE；署名/衍生文本同许可） |
| 稳定性 | 官方仓库；archived=False；最近push=2026-08-05T19:19:48Z；不是运行SLA |
| 采用/阶段 | 采用：第二批8；M1→M2；Tier 2 |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## Package URL

| 属性 | 调研结果 |
|---|---|
| 名称/ID | Package URL / PURL |
| 类别/权威 | 供应链数据标准 / 规范维护者（规范权威，非漏洞事实源） |
| 官方地址/资料 | [官方1](https://github.com/package-url/purl-spec)；[官方2](https://github.com/package-url/purl-spec/blob/7cd2d3442fb9c88155db17ada7c911b40ec22d41/README.md)；[官方3](https://github.com/package-url/purl-spec/blob/7cd2d3442fb9c88155db17ada7c911b40ec22d41/LICENSE) |
| 数据与字段 | 版本化schema/identifier/component/status语义 |
| 获取方式/用途 | Official Git Specification；生态包身份，第一版采用；不是漏洞源 |
| Token/Rate Limit | 不需要；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 规范版本发布 |
| 增量 | Git tag/commit修订；固定支持版本，不按情报周期采集 |
| License/限制 | MIT |
| 稳定性 | 官方仓库；archived=False；最近push=2026-09-29T22:26:06Z；不是运行SLA |
| 采用/阶段 | 采用规范：PURL首期；其余适配暂缓；M0；Standard |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## CycloneDX

| 属性 | 调研结果 |
|---|---|
| 名称/ID | CycloneDX / CYCLONEDX |
| 类别/权威 | 供应链数据标准 / 规范维护者（规范权威，非漏洞事实源） |
| 官方地址/资料 | [官方1](https://github.com/CycloneDX/specification)；[官方2](https://github.com/CycloneDX/specification/blob/1ce97b2a7b8cf2429da248560d2aa671c6bce74a/README.md)；[官方3](https://github.com/CycloneDX/specification/blob/1ce97b2a7b8cf2429da248560d2aa671c6bce74a/LICENSE) |
| 数据与字段 | 版本化schema/identifier/component/status语义 |
| 获取方式/用途 | Official Git Specification；M2授权SBOM输入；不是实时情报源 |
| Token/Rate Limit | 不需要；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 规范版本发布 |
| 增量 | Git tag/commit修订；固定支持版本，不按情报周期采集 |
| License/限制 | Apache-2.0 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-02T15:54:19Z；不是运行SLA |
| 采用/阶段 | 暂缓实现：保留规范调查；M2/M3；Standard |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## SPDX

| 属性 | 调研结果 |
|---|---|
| 名称/ID | SPDX / SPDX |
| 类别/权威 | 供应链数据标准 / 规范维护者（规范权威，非漏洞事实源） |
| 官方地址/资料 | [官方1](https://github.com/spdx/spdx-spec)；[官方2](https://github.com/spdx/spdx-spec/blob/b0f290ffdb31b5682ff90bd99636d1d29e79d3b2/README.md)；[官方3](https://github.com/spdx/spdx-spec/blob/b0f290ffdb31b5682ff90bd99636d1d29e79d3b2/LICENSE) |
| 数据与字段 | 版本化schema/identifier/component/status语义 |
| 获取方式/用途 | Official Git Specification；M2 SPDX文档/SBOM输入，按版本；不是源数量 |
| Token/Rate Limit | 不需要；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 规范版本发布 |
| 增量 | Git tag/commit修订；固定支持版本，不按情报周期采集 |
| License/限制 | Community-Spec-1.0；legacy portions CC-BY-3.0；script MIT |
| 稳定性 | 官方仓库；archived=False；最近push=2026-10-03T01:02:08Z；不是运行SLA |
| 采用/阶段 | 暂缓实现：保留规范调查；M2/M3；Standard |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## OpenVEX

| 属性 | 调研结果 |
|---|---|
| 名称/ID | OpenVEX / OPENVEX |
| 类别/权威 | 供应链数据标准 / 规范维护者（规范权威，非漏洞事实源） |
| 官方地址/资料 | [官方1](https://github.com/openvex/spec)；[官方2](https://github.com/openvex/spec/blob/61b5f885d0f481f48683c93345e49ef1a6e9fdff/README.md)；[官方3](https://github.com/openvex/spec/blob/61b5f885d0f481f48683c93345e49ef1a6e9fdff/LICENSE) |
| 数据与字段 | 版本化schema/identifier/component/status语义 |
| 获取方式/用途 | Official Git Specification；M3适用性声明，需发行者/产品范围和证据，非无条件安全认证 |
| Token/Rate Limit | 不需要；REST公共60次/小时；普通认证5000次/小时；search另限，secondary/响应头优先 |
| 上游更新频率 | 规范版本发布 |
| 增量 | Git tag/commit修订；固定支持版本，不按情报周期采集 |
| License/限制 | CC0-1.0 |
| 稳定性 | 官方仓库；archived=False；最近push=2026-09-09T19:51:21Z；不是运行SLA |
| 采用/阶段 | 暂缓实现：保留规范调查；M2/M3；Standard |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

## Common Platform Enumeration

| 属性 | 调研结果 |
|---|---|
| 名称/ID | Common Platform Enumeration / CPE |
| 类别/权威 | 供应链数据标准 / NIST标准/字典管理 |
| 官方地址/资料 | [官方1](https://csrc.nist.gov/projects/security-content-automation-protocol/specifications/cpe) |
| 数据与字段 | CPE2.3 formatted/binding/matching；字典版本 |
| 获取方式/用途 | Official Specification / NVD CPE API candidate；CPE不是PURL等价物，不能无证据互转 |
| Token/Rate Limit | 不需要；UNKNOWN / NEED_VERIFY |
| 上游更新频率 | 标准/字典更新 |
| 增量 | 标准版固定；字典API增量另按官方文档，不在本轮实现 |
| License/限制 | 规范出版条款；第三方parser LGPL另算；字典条款 NEED_VERIFY |
| 稳定性 | 官方入口已查询；服务SLA UNKNOWN / NEED_VERIFY |
| 采用/阶段 | 暂缓实现：首期包身份用PURL；CPE原文保留；M2；Standard |
| 存在性验证 | True；失败与空响应仍保留，不算成功内容 |

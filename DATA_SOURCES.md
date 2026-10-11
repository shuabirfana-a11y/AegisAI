> 历史预案。当前第2阶段已冻结的数据源方案见 [最终选型](research/data_sources/FINAL_DATA_SOURCE_SELECTION.md) 与 [字段映射](research/data_sources/SOURCE_FIELD_MAPPING.md)；本文件保留为调研历史，不作为当前范围依据。

# 数据源体系与接入顺序

基准：2026-10-03已完成的真实接口/仓库调研、12条开发种子及本轮官方文档复查。机器配置见 [source_registry.json](source_registry.json)，字段路径见 [SOURCE_FIELD_MAPPING.md](SOURCE_FIELD_MAPPING.md)。这里冻结接入安排，正式采集器尚未开发。周期是本项目的初始调度配置，不是外部服务SLA。

## 第一批：3个数据入口，分两段跑通

1. **CVE List V5＋OSV**：先以已有6个PyPI产品、12条真实种子跑通原始字节→标准化→身份/版本→Evidence→数据库/API的最小切片。
2. **CISA KEV＋CVE内CISA ADP**：同一首批补上KEV快照、CISA评估和可回查的利用信号。KEV是第三个数据入口；ADP是CVE中的provider容器，单独标记发布者和locator，不另算一次独立发现。

| 来源 | 数据与权威范围 | 获取方式 | 上游节奏 / 本项目初始调度 | 本期位置 |
|---|---|---|---|---|
| CVE List V5 | CVE身份、PUBLISHED/REJECTED状态；CNA/Program/ADP内容按各自发布者保留 | 官方仓库记录，Git/release delta；种子用固定commit raw JSON | 官方说明约7分钟更新；项目每60分钟增量、每日对账 | 第一批主干 |
| OSV | 生态/包/PURL、aliases、events/ranges/versions、references；包范围适合生态解析，上游并非每条独立 | POST /v1/query、/querybatch发现ID；GET /v1/vulns/{id}保存详情 | 来源驱动，未采用固定发布SLA；项目每60分钟检查配置包与已知ID | 第一批包/版本 |
| CISA KEV | 收录漏洞的已知利用信号及处置原文；未收录仅表示该快照不在目录 | CISA官方JSON或cisagov官方镜像，保存整份catalog和hash | 随目录变更；项目每60分钟检查/下载变化快照 | 第一批第三入口 |
| CISA ADP / Vulnrichment | CISA的SSVC及可用的CWE/CVSS/CPE补充；缺失允许unknown | 读CVE containers.adp，按provider识别；独立仓库留作对账候选 | 随CVE修订一起处理 | 第一批容器解析，独立repo延后 |

官方依据：[CVE List](https://github.com/CVEProject/cvelistV5)、[OSV API](https://google.github.io/osv.dev/api/)、[KEV镜像/更新说明](https://github.com/cisagov/kev-data)、[CISA Vulnrichment](https://github.com/cisagov/vulnrichment)。CISA网页本轮403；实际目录快照已由官方仓库取得，失败路径不影响现有离线证据。

## 补充批次和知识资源

| 来源 | 解决什么 / 获取 | 频率安排 | 首批接入与限制 |
|---|---|---|---|
| NVD | API2.0补CVSS、CWE、CPE配置、引用标签、分析状态；不能当作每条都完整及时 | 按lastModified增量，初始每6小时，每日回补；具体窗口/额度按安装时官方文档配置 | 补充批次；不阻塞CVE落库；CPE AND/OR与vulnerable保留 |
| GHSA / Advisory Database | 包公告、reviewed、vulnerable_version_range、first_patched_version、撤销 | 官方REST或仓库增量，初始每6小时 | 补充批次；OSV已引用同一GHSA时复用lineage，不重复计票 |
| EPSS | FIRST每日CVE预测值、percentile和日期；小规模API，批量每日CSV | 项目每日检查最新日期，晚到保留旧值和stale | 富化扩展；不作为事实可靠性或CVSS替代 |
| GitHub仓库/公告/commit | 厂商公告及引用指向的commit diff作为Patch/PoC候选 | 受控引用按需获取，候选每日回补；缓存与token额度 | 扩展；不通用全站搜索、不执行仓库/PoC，不因存在diff就verified |
| Vendor Advisory | 原始公告、修复/缓解说明；优先已有references的官方域名 | 先保存引用；以后按厂商feed按日检查 | 扩展；6产品官方repo已在种子登记，网页parser逐站验证，不承诺万能抓取 |
| arXiv | 论文元数据/摘要及研究线索，API Atom | 小规模查询每日批处理；请求间隔按官方API使用要求 | V0.2；论文不自动证明某CVE受影响，全文授权另登记 |
| RSS / 安全博客 | 订阅监测、事件和待审核线索 | 逐feed配置，默认每6小时，HTTP缓存 | V0.2；当前没有验证完的具体feed清单，未配置则禁用；转载不是独立证据 |
| ATLAS | 攻击技术、案例、稳定ID和版本化标签 | 官方仓库版本变化时导入，项目每周检查 | V0.2知识资源；不强制把每个CVE映射为某技术 |
| OWASP GenAI | 风险分类和解释背景 | 官方版本发布时更新，项目每周检查 | V0.2知识资源；分类不充当漏洞事实/评分源 |

依据：[NVD API](https://nvd.nist.gov/developers/vulnerabilities)、[GHSA API](https://docs.github.com/en/rest/security-advisories/global-advisories)、[EPSS数据](https://www.first.org/epss/data.html)、[GitHub commits API](https://docs.github.com/en/rest/commits/commits)、[arXiv API](https://info.arxiv.org/help/api/user-manual.html)、[ATLAS](https://github.com/mitre-atlas/atlas-data)、[OWASP](https://genai.owasp.org/llm-top-10/)。NVD文档本轮正文提取仍不完整，真实API样本可用；未把历史限额数当作当前承诺。

## 字段选择、覆盖与失败

CVE身份按官方记录，包/范围先按有明确生态的OSV事实；CVSS/CWE/厂商说明全部来源化保存。不同CVSS版本并列，不取平均。版本无法解析返回UNKNOWN，保留原表达和events；last_affected不推算fixed。CVE5.2可提供packageURL，出现时保留并验证，不假设每条都有。

首期包范围为torch、vllm、transformers、mlflow、gradio、ray。OSV查包发现候选CVE，再到CVE List确认身份/状态；CVE delta对已知ID和可控产品规则作补充监测。这里的覆盖是配置产品集合，不是“覆盖所有AI安全漏洞”。无CVE的OSV公告保留external_id与待映射状态，不伪造CVE。

每份响应记录source/外部ID/URL、published/modified、retrieved、literal raw hash、schema/parser版本；每个事实记录JSON pointer/文本定位及上游lineage。429尊重Retry-After并限预算，timeout/5xx延迟回补，坏JSON/缺身份隔离单条；游标只在持久化成功后推进。KEV负匹配须整份目录结构及count检查成功，否则UNKNOWN。CVE ADP中的旧SSVC不覆盖更晚的KEV证据；时间和发布者决定适用范围。

引用默认不自动请求。source host、路径、返回大小与重试上限由采集配置控制；外部正文不提供工具授权。keys只在服务环境，日志/fixtures无secret。引用、代码、数据、全文、商业API条款分别登记；本轮仅公开源开发验证，无私有资产外发。

## 验收与当前证据

- 12个CVE各有CVE/OSV快照，产品/版本/引用可回查；3条修复版本未知、2条CNA评分缺失如实保留。
- 60个JSON定位与16个范围边界已通过设计probe；这不等于数据库事务、API或人工gold验收。
- 本轮 source_contracts 对KEV全快照与12条CVE连接作检查，并核对CISA ADP、NVD、GHSA、EPSS字段定位。记录见 [数据契约验证](evaluation/source_contracts/validation.json)。
- 新的正式采集器须覆盖重复同步、修订/撤销、429/timeout/坏JSON、DB失败、来源不同但内容相同、来源相同但字段冲突，默认离线fixture回归。

下一步用这些真实字段和缺失情况校准产品模块、UX/UI；数据库和后端预案随后复核。Agent接入需先有稳定可引用的事实API。

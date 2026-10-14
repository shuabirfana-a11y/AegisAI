# 来源与能力边界

原始来源目录保持字节不变。新增原生源放 `backend/app/monitoring/native_sources.json`，固定Feed放 `catalog.py`。这样不会遮蔽既有厂商核验规则。

| 类别 | 来源 | 本阶段接入/复用 | 本次实时情况 |
| --- | --- | --- | --- |
| 漏洞数据库 | CVE_LIST | 复用原Git Collector、游标与Raw流程 | 本次未重新下载CVE仓库 |
| 漏洞数据库 | OSV | 复用原索引/记录采集 | 1条成功、1条超时，整体PARTIAL |
| 漏洞数据库 | NVD | 原生JSON适配，精确已知CVE刷新 | 2条入库；有待处理ID，PARTIAL |
| 利用目录 | CISA_KEV | 复用原完整目录/缺席语义 | 本次无命中不能解释为安全 |
| 安全社区 | GHSA | reviewed/pip有限窗口+原生逐条获取 | 监测请求失败，有解析夹具验证 |
| 官方厂商 | PyTorch / vLLM / MLflow | 固定官方仓库公告，published状态 | vLLM监测请求失败；另两个未实跑 |
| 安全博客 | Trail of Bits RSS | 安全XML解析、原Raw、KnowledgeIndex | 2条文章入库并使用实际Embedding |
| 安全博客 | Google Security Blog RSS | 同一有界Feed流程 | 连接超时，未入库 |
| 学术论文 | arXiv Atom | LLM/security元数据与摘要 | 重试窄查询成功，1篇论文入库 |

配置11个监测源、6类（同类CVE/NVD/OSV不重复计类别）。本次最低验收使用三类真实入库：漏洞数据库、博客、论文。期间原富化服务的部分GitHub PoC检索成功，不把它替代失败的GHSA或厂商公告监测。

论文：ACE: A Security Architecture for LLM-Integrated App Systems。博客本次抓取是安全研究材料，并非每篇都是AI专属；保留相关性不确定，不强制标成AI漏洞。

## 标准化与富化

- 原 NormalizedIntelligenceRecord / Raw / SourceObservation / SyncRun / 原身份合并流程继续使用。
- NVD版本环境CPE树原样留在extensions，不猜PyPI名称、不把环境AND谓词扁平化成修复版本。
- GHSA上、下界按区间含义转换为原匹配算法可读的事件；明确修复字段与排除上界分开。非法修复表达式保留原文而不猜发布版本。
- CVSS/CWE、受影响/修复版本、PoC/Patch候选、论文/文章候选关联、库存风险和Evidence共同投影；不把字段存在当作核验通过。
- 原生CVSS事实桥使用原ClaimStore/EvidenceService，先验证精确原生JSON pointer，只生成未采纳来源声明。验证与最终答案仍由既有流程决定。
- 同源重复内容不追加规范化实体；skip fetch可回查既有parsed版本，继续使用原日更富化Scheduler。
- Feed修订保存历史并归档旧检索可见性；RSS回滚与arXiv版本ID都有回归测试。重复回放明确旧版可能增加归档副本，作为非阻塞优化项保留。

本次实时候选文献关联为0：没有发现足够的确切漏洞ID/包名关联。不强行给论文挂CVE。相应关联规则及证据追溯由合成集成测试验证；论文已经通过原语义检索/问答可读。

## 官方接口参考

- [NVD开发接口](https://nvd.nist.gov/developers/vulnerabilities)
- [GitHub全局安全公告接口](https://docs.github.com/en/rest/security-advisories/global-advisories)
- [arXiv API说明](https://info.arxiv.org/help/api/user-manual.html)
- [Trail of Bits原始Feed](https://blog.trailofbits.com/index.xml)

这些参考支持获取方式，不代表本次所有请求成功或已达到比赛评分档位。具体来源失败与Raw哈希见live-validation.json。

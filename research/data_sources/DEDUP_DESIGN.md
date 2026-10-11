# 去重与实体解析设计

三层分开：来源记录身份、raw内容、业务主体。去重合并主体，不删除来源/证据；相似度只能产生待审候选。

| Key | 用途与边界 |
|---|---|
| source + external_id | 同源稳定记录身份，修订不另造主体；源内ID可能代表多CVE集合 |
| content_hash | raw字节复用/重复观察；同hash多publisher仍保留来源关系，不能算独立验证 |
| CVE ID | 明确单一CVE身份的强key；一条advisory含多个CVE不能把这些CVE并成一个 |
| GHSA ID / OSV ID | advisory与source record身份；显式aliases连CVE但先检查一对多与withdrawn，冲突进复核 |
| ecosystem + package + advisory | 无CVE/GHSA的包公告稳定标识；同包不同漏洞不合并 |
| canonical URL | 文档/引用去重候选；只移除已知tracking params与fragment，保留语义query/id/version；http/https等价需实际依据 |
| arXiv ID + version / DOI | paper主体与版本分开；v2修订不新建独立研究主体；DOI必须源明确给出 |
| 标准ID/政策文号+发布机关+edition | 文档主体与版本；草案/正式/解释文档不自动互相覆盖 |
| repo+完整commitSHA/PR号 | 代码引用身份；同改动不同分支/适用包独立scope，不能凭短SHA强并 |

同漏洞来自3个源 → 1 Vulnerability + N RawDocuments/Observations + N Evidence；原始source record各自保留。多CVE的一条advisory → 一个advisory连接多个Vulnerability，raw可以复用；不能用aliases连通分量无条件union把多个独立CVE吞并。

撤销/rejected更新主体适用状态但保留旧事实和证据。HTTP404单次不作为撤销真值；RSS窗口外不代表文档删除；官方明确withdrawn或有效范围修订才更改状态。不同CVSS版本不构成重复/冲突；同Scope不同值保留双方。

Entity Resolution只采用精确生态包/PURL或审核别名，如PyTorch→PyPI torch；CPE与PURL不是等价编码，NVIDIA Triton与triton-lang不同，LangChain主包和拆分集成包也不同。产品名相同/关键词含AI/agent都不是自动合并依据。版本比较遵循生态，unsupported保留UNKNOWN。

本阶段不实现复杂去重/向量聚类或数据库约束；实现阶段须验证重复输入幂等、同URL改正文、一对多alias、不同生态同名、撤销及内容转载。

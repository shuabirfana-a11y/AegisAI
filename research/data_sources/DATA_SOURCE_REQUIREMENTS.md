# 数据源信息需求（Phase 2）

2026-10-03。已完整复读 requirements/ 的13份文档及赛题4页原文；本文件先于本轮接口调研建立。冻结需求优先，旧预案仅作背景。本阶段只调研与设计，不实现服务。

| 信息需求 | 业务用途 | 待核验的候选来源 | 需求依据 |
|---|---|---|---|
| 01 漏洞身份 | 跨源统一、撤销处理 | CVE Program；OSV/GHSA外部ID | REQ-DATA-001/002 |
| 02 描述 | 理解问题与影响 | CNA、厂商公告；NVD补充 | REQ-ENRICH-002 |
| 03 CVSS | 来源化评分、向量和版本 | CNA/厂商、NVD、CISA ADP | REQ-ENRICH-002 |
| 04 CWE | 缺陷类别 | CNA/厂商、NVD、CISA ADP | REQ-DATA-005 |
| 05 受影响产品 | 产品/包实体对齐 | CNA、OSV、厂商 | REQ-DATA-003 |
| 06 受影响版本 | 生态版本判断 | OSV、厂商；CVE原范围、NVD CPE | REQ-DATA-004 |
| 07 修复版本 | 有依据的升级建议 | OSV fixed、厂商明确版本、GHSA | REQ-ENRICH-005 |
| 08 厂商公告 | 缓解与修复原文 | 官方公告页/官方仓库advisory | REQ-ENRICH-005 |
| 09 POC | 公开代码线索、关联/可用性分离 | 公告references、GitHub明确引用 | REQ-ENRICH-004 |
| 10 Exploit状态 | 存在/武器化/利用信号分开 | KEV、CISA SSVC、官方研究文章 | REQ-VERIFY-003 |
| 11 Patch | 修复候选及适用范围 | 厂商引用、GitHub commit/PR | REQ-ENRICH-006 |
| 12 Fix Commit | 完整SHA、分支与改动出处 | GitHub commit API、官方公告 | REQ-ENRICH-006 |
| 13 EPSS | 某日期预测概率/百分位 | FIRST EPSS | REQ-ENRICH-002 |
| 14 已真实利用 | 已知利用正证据 | CISA KEV；明确事件报告 | REQ-VERIFY-003 |
| 15 分析文章 | 关联研究与技术解释 | 官方安全博客RSS/Atom | REQ-ENRICH-003 |
| 16 论文 | 最新研究元数据与版本 | arXiv | REQ-MON-002 |
| 17 AI安全事件 | 无CVE事件与风险 | 官方研究文章、厂商公告、ATLAS案例 | REQ-DATA-001/005 |
| 18 AI产品/组件 | 白名单与别名证据 | 官方仓库/发布、OSV package、CVE affected | REQ-DATA-003 |
| 19 AI安全知识 | 威胁分类与安全建议 | MITRE ATLAS、OWASP GenAI | REQ-QA-003 |
| 20 发布时间 | 新增时效和时间筛选 | 各源原生日期；缺失明确unknown | REQ-MON-004 |
| 21 修改时间 | 修订和增量 | 各源modified/updated、Git/HTTP观察 | REQ-MON-003 |
| 22 来源证据 | 原文定位与lineage | 每个采集源的RawDocument和元数据 | REQ-VERIFY-001/002 |
| 23 技术标准/规范 | 知识同步与原文引用 | 国家标准信息平台（GB 45438-2025等）+ NIST AI官方出版物 | REQ-MON-002 |
| 24 政策法规 | 官方文本、修订与发布日期 | 中国网信办官方栏目；EUR-Lex候选 | REQ-MON-002 |

上述源名是调研假设，最终来源、获取方式与采用状态以 [最终选型](FINAL_DATA_SOURCE_SELECTION.md)、[字段映射](SOURCE_FIELD_MAPPING.md) 和联网证据为准。缺失值不交给LLM补造。

首批三个入口是基础技术切片，不等于初赛三类覆盖。完整初赛必须有不同业务类别的实际自动更新记录，且论文、技术标准与政策法规三类知识均有真实出处和更新观察。类别计数采用团队操作定义，最终由评审认定；不把镜像/转载或同一来源不同接口重复计数。

Demo使用真实历史案例时明确回放/as_of；POC线索不等于可用性核验。第三方代码只调查许可与可复用边界，不在本阶段安装业务依赖或执行下载代码。

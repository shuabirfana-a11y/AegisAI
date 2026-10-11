# CTI 平台与可信证据模型

**OpenCTI、MISP、IntelOwl 归 C：借鉴设计，第一版不整套部署。** 它们解决企业情报工作流的重要问题，但其运维、连接器、许可证与对象体系会稀释 AegisAI 首期的 AI 情报证据主线。

| 平台 | 成熟可借鉴的对象/机制 | 不在 V0.1 直接引入的理由 | 后续适用条件 |
|---|---|---|---|
| OpenCTI | 来源/实体/关系/置信度/标签/连接器/报告与生命周期 | 数据服务多、资源高；社区/企业许可边界；已有系统主体与本项目重叠 | 企业已有 OpenCTI 时做只读/导出连接器 |
| MISP | event、attribute、object、taxonomy、sighting、共享与关联 | 偏事件/IOC 协作；AGPL；不直接解决产品版本与 AI 标签真值 | 需要与已有 MISP 交换已审核情报 |
| IntelOwl | analyzer、connector、job、错误与富化结果汇聚 | AGPL、多第三方服务/凭证、文件外发；大型分析器生态超首期范围 | 有具体分析器收益且输入外发可控时单适配 |
| STIX 2.1 / python-stix2 | 标准对象、external_references、时间、marking、note/opinion/sighting | 标准可复用，但不强求全部内部表一比一 STIX | V0.2 导出/交换使用 SDK，不自写格式 |

来源：[OpenCTI](https://github.com/OpenCTI-Platform/opencti)、[MISP](https://github.com/MISP/MISP)、[IntelOwl](https://github.com/intelowlproject/IntelOwl)、[STIX 官方介绍](https://oasis-open.github.io/cti-documentation/stix/intro)。这些平台的对象能力是设计参考，不代表本轮已经安装验证全部模块。

## V0.1 必须拥有的六类记录

| 记录 | 最小内容 | 解决的问题 |
|---|---|---|
| Source | 发布者、官方域名/账号、源类型、条款、采集策略、上游 lineage | 区分原始发布与聚合镜像 |
| Evidence | 原始对象 hash/位置、URL、source revision、页/行/段落、fetch_time、parser/version | 引文回查、重放和解析纠错 |
| Claim | 主体/谓词/值、适用包/范围、支持/反驳 evidence、提出者、审核状态 | 事实字段不能只留一段总结 |
| Time | published/modified/fetched/valid_from/valid_to/as_of | 解释“当时知道什么”与现在变更 |
| Confidence | 依据类型、独立 source groups、规则版本、reviewer，不强制虚假概率 | 可靠性和内容可信度分开 |
| Conflict | 冲突 claim、条件差异、解决依据、待审核状态、审计 trail | 两种说法不靠 LLM 最后一句覆盖 |

STIX 的 confidence、external_references、note/opinion、created/modified、revoked 可以借鉴；但 STIX 的一个 confidence 数值不替代证据模型。[FIRST CTI 来源与信息可靠性课程](https://www.first.org/global/sigs/cti/curriculum/)强调来源评价与内容评价分开；本项目不凭几条规则输出未经校准的“97% 真确率”。

## 来源、冲突和状态的规则

同一原公告经 CVE/GHSA/OSV/NVD 四个入口出现，保存四份观察与一条上游 lineage。置信依据按独立发布者分组；提供相同引用 URL、相同 CNA 容器、同一 advisory-database source 的记录不重复计票。独立核验要证明新的观察或不同证据，不只数域名。

字段冲突先检查生态、分支、版本语义、发布时间、CVSS 版本和信息来源；无法解决时保留两条 claim，标记 disputed。REJECTED/withdrawn 不物理抹除历史，而是改变状态并使依赖它的答案重新评估。版本“未知”和“确认不受影响”严格区分。

状态建议：collected→normalized→candidate→needs_review→verified/disputed→superseded/withdrawn。PoC 与 patch 的状态是独立字段，不因漏洞 verified 自动变成 verified。人工审核记录依据、角色、时间和规则版本；临时忽略/误报有 scope、reason、expiry 和 evidence，不能永久静默掉整个 CVE。

## 新增发现：企业真正需要的轻量能力

| 能力 | V0.1 最小实现 | 后续增强 |
|---|---|---|
| 血缘与历史 | 不可变 raw hash、字段到证据、修订链、解析版本 | 事件回放与时点查询 |
| 差异与风险变化 | 比较 affected/fixed、KEV、EPSS日期、审核/撤销状态；变更类型化 | 结合资产/暴露生成影响 diff，避免文本差异告警噪声 |
| 分析人员工作流 | needs_review 列表、理由、接受/驳回、人工备注 | Case、分派、通知和企业系统导出 |
| 注入/投毒 | 外部内容为数据，永不提升到系统指令；只读工具、结构化结果与引文核验 | 对抗评测、来源异常与内容漂移检测 |
| 权限与审计 | 管理/分析/只读角色，服务端授权与审计；原始内容不默认发模型 | 租户隔离与组织级策略；审查 Dify 多租户许可 |
| 调度/缓存 | 有持久状态的单采集进程、source 配额、ETag/hash、幂等与失败回补 | 队列、多 worker、死信与订阅 |
| 可观测/费用 | 每源延迟、错误、最后成功、LLM调用/Token、额度与预算 | Trace、SLO 和自动暂停昂贵任务 |
| 重放/恢复 | raw blob+索引一致备份，解析可重跑；恢复演练计划 | 增量备份、RPO/RTO 与跨故障域存储 |

这里是设计要求，不是本轮已经开发的功能。重放不能再次请求网页后冒称原始历史，灾难恢复不能只备份 Dify 知识库；原文件、metadata、权限、审计和模型/规则版本都须对应。

## 候选档案

所有时间来自本次快照。资源和部署级别为选型估计，没有冒充部署实测。原始 JSON 见 [候选清单](candidate_catalog.json)。

### intelowlproject/IntelOwl · C

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/intelowlproject/IntelOwl)；[官网](https://intelowlproject.github.io) |
| 类别 / 解决问题 | cti_projects；分析器、连接器、任务作业与结果汇聚 |
| 能力 / 接入 / 语言 | 分析器、连接器、任务作业与结果汇聚；API / SDK / Docker（见专题选择）；Python |
| License | AGPL-3.0；[授权来源](https://github.com/intelowlproject/IntelOwl/blob/bf75e8b2f465f27c590cd0d7fea61d65fb6aab56/LICENSE) |
| 最近更新 / Star | 2026-09-02T04:33:26Z；4737（快照统计，不作为质量结论） |
| Release | v6.8.0；2026-08-31T18:53:50Z；https://github.com/intelowlproject/IntelOwl/releases/tag/v6.8.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-10-01T11:04:16Z；API open_issues_count=72（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | cti_projects；创新 / 工程 / 问答 |
| 最终建议 | C；借鉴富化任务编排；AGPL 与大量外部分析器增加运维/外发复杂度 |
| 核查来源 | [README/文档](https://github.com/intelowlproject/IntelOwl/blob/bf75e8b2f465f27c590cd0d7fea61d65fb6aab56/README.md)；源码 SHA bf75e8b2f465f27c590cd0d7fea61d65fb6aab56；README 已下载 |

### MISP/MISP · C

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/MISP/MISP)；[官网](https://www.misp-project.org/) |
| 类别 / 解决问题 | cti_projects；事件、属性、关联、分类、共享和误报管理 |
| 能力 / 接入 / 语言 | 事件、属性、关联、分类、共享和误报管理；API / SDK / Docker（见专题选择）；PHP |
| License | AGPL-3.0；[授权来源](https://github.com/MISP/MISP/blob/fb54b3e4a4ddd7ad7913fffd94284dd0e81b2120/LICENSE) |
| 最近更新 / Star | 2026-09-29T14:57:07Z；6563（快照统计，不作为质量结论） |
| Release | v2.5.48；2026-09-29T08:11:29Z；https://github.com/MISP/MISP/releases/tag/v2.5.48 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 5 个 Issue；最近样本更新 2026-10-02T09:38:52Z；API open_issues_count=2945（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | cti_projects；创新 / 工程 / 问答 |
| 最终建议 | C；借鉴情报流与 analyst 对象；不把 AGPL 平台作为 V0.1 主体 |
| 核查来源 | [README/文档](https://github.com/MISP/MISP/blob/fb54b3e4a4ddd7ad7913fffd94284dd0e81b2120/README.md)；源码 SHA fb54b3e4a4ddd7ad7913fffd94284dd0e81b2120；README 已下载 |

### oasis-open/cti-python-stix2 · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/oasis-open/cti-python-stix2)；[官网](https://stix2.readthedocs.io/) |
| 类别 / 解决问题 | cti_projects；STIX 2.x 对象与序列化 SDK |
| 能力 / 接入 / 语言 | STIX 2.x 对象与序列化 SDK；SDK；Python |
| License | BSD-3-Clause；[授权来源](https://github.com/oasis-open/cti-python-stix2/blob/2270361774215de49717c1a6028a80c91075b400/LICENSE) |
| 最近更新 / Star | 2026-02-12T06:19:32Z；438（快照统计，不作为质量结论） |
| Release | v3.0.2；2026-02-12T06:22:52Z；https://github.com/oasis-open/cti-python-stix2/releases/tag/v3.0.2 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 1 个 Issue；最近样本更新 2026-04-22T18:14:00Z；API open_issues_count=68（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 本地输入解析；无须高权限，安装依赖另审；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | cti_projects；工程 |
| 最终建议 | A；V0.2 导出时直接用；首期数据模型可兼容但不强行全 STIX 化 |
| 核查来源 | [README/文档](https://github.com/oasis-open/cti-python-stix2/blob/2270361774215de49717c1a6028a80c91075b400/README.rst)；源码 SHA 2270361774215de49717c1a6028a80c91075b400；README 已下载 |

### OpenCTI-Platform/opencti · C

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/OpenCTI-Platform/opencti)；[官网](https://opencti.io) |
| 类别 / 解决问题 | cti_projects；实体关系、来源、置信度、连接器和审核 |
| 能力 / 接入 / 语言 | 实体关系、来源、置信度、连接器和审核；API / SDK / Docker（见专题选择）；TypeScript |
| License | 社区 Apache-2.0 / 企业组件专有条款，按文件头区分；[授权来源](https://github.com/OpenCTI-Platform/opencti/blob/b97fbc534ec69ba374a2fe0e8665cf87b5e75b72/LICENSE) |
| 最近更新 / Star | 2026-10-03T02:01:16Z；10082（快照统计，不作为质量结论） |
| Release | 7.261002.0；2026-10-02T09:57:15Z；https://github.com/OpenCTI-Platform/opencti/releases/tag/7.261002.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-10-02T16:01:36Z；API open_issues_count=2155（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | cti_projects；创新 / 工程 / 问答 |
| 最终建议 | C；借鉴模型；多组件部署过重，社区 Apache 与企业条款按文件区分 |
| 核查来源 | [README/文档](https://github.com/OpenCTI-Platform/opencti/blob/b97fbc534ec69ba374a2fe0e8665cf87b5e75b72/README.md)；源码 SHA b97fbc534ec69ba374a2fe0e8665cf87b5e75b72；README 已下载 |

### STIX 2.1 · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | 无独立仓库指标；相关镜像见专题；[官网](https://oasis-open.github.io/cti-documentation/stix/intro) |
| 类别 / 解决问题 | cti_projects；对象、时间、来源与 note/opinion/sighting |
| 能力 / 接入 / 语言 | 对象、时间、来源与 note/opinion/sighting；Data / SDK；JSON/XML/HTTP 或规范 |
| License | OASIS 规范条款；Python SDK BSD-3-Clause；[授权来源](https://oasis-open.github.io/cti-documentation/stix/intro) |
| 最近更新 / Star | 文档查询 2026-10-03；持续服务无可比统一 commit；不适用（快照统计，不作为质量结论） |
| Release | 服务/规范版本见官方文档，不套用 GitHub Release |
| Issue / 维护 | 服务支持/标准维护，不适用 GitHub Issue；官方服务/标准；不构成 SLA 验证 |
| 部署 / 资源 | 低 / 低；调用/解析成本估计，未部署量测 |
| 收费 / Key | 见 key/专题和官方条款；不得把免费额度理解成无限免费；不需要 |
| 权限 / 风险 | 只读指定官方 endpoint；检索字符串可能外发；不提交私有清单/文档；MEDIUM；限制为官方公共只读接口；第三方外发/输入投毒风险仍存在 |
| AegisAI 模块 / 比赛价值 | cti_projects；富化 / 问答 / 创新 |
| 最终建议 | A；核心/分阶段封装，具体时机见 final_recommendation.md |
| 核查来源 | [README/文档](https://oasis-open.github.io/cti-documentation/stix/intro)；官方文档查询；README 未下载/不适用，按专题说明 |

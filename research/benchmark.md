# Benchmark：公开基准作对照，自建证据与关联真值

**没有一个本轮核实的公开基准能完整评测 AegisAI 的主线。** CTI QA 能评测知识，patch 数据能评测关联，注入基准能评测工具边界；必须另外构建带时间和证据的 AegisBench。这里给出方案，未冒称已经完成大规模标注或评测。

## 已核实的公开资源

| 资源 | 任务与规模 | 时间/维护 | 授权与真实数据 | 比赛适用与局限 |
|---|---|---|---|---|
| CTIBench | MCQ 2500、RCM 1000、VSP 1000、ATE 60、TAA 50=4610；另有 RCM-2021 1000，对应仓库 TSV 合计5610 | 2024 论文，仓库本次 2026-05 更新；只有对照 split 明确标 2021，其他逐题时间窗未全核对 | LICENSE CC-BY-NC-SA-4.0；真实 CTI 来源经过题目加工，TAA 标签在 response 文件 | 非商业比赛研究对照；不能默认随企业商用产品分发，也不测全证据链 |
| CVEfixes v1.0.8 | 11873 CVE、12107 fixing commits、4249项目、51342文件、138974函数 | 覆盖截至2024-07-23；2024-07发布，仓库低频 | 代码MIT；Zenodo数据CC-BY-4.0；真实仓库采集但非逐条人工确证 | patch linking 历史种子，按 repo/CVE 分组防泄漏，人工抽验 |
| MoreFixes v4 | 43357 unique CVE、9972 GitHub项目、47616数据库commits、52672 patch files，计数口径不同 | 发布2026-06-20，数据截至2026-06-02；仓库2026-09更新 | Zenodo CC-BY-4.0；实现 MIT/Apache；上游代码许可保留 | 更近的 patch 关联候选；16GB级全库不在首期下载/建库 |
| CyberSecEval / PurpleLlama | 多代、多任务基准；本轮未把整套计成固定一个规模 | 当前官方 README 提 CyberSecEval4；各子集发布时间不同 | benchmark 子组件 MIT；模型、网站与其他组件另有许可；合成攻击和真实弱点场景混合 | 注入/工具安全补充；只选锁定子集，不运行攻击执行环境 |
| AgentDojo | Agent 任务与注入安全评测；任务与攻击规模随 suite/version变化，本轮未逐项清点 | 仓库2026-06更新，API会变化；非真实 CVE 时间序列 | MIT 项目；模拟工具/任务，不是逐漏洞事实 | 迁移设计到 Aegis 工具；任务成功和攻击成功分别报 |
| FAITH | 可复用评测执行框架；README包含 CTI-Reasoning 200 test、CWE Prediction 3000及其他套件 | 框架2026-07更新；各数据单独维护 | 框架Apache-2.0，所载数据各有条款，不能一并推 Apache | 执行框架可选；首期不用复杂 harness替代基础数据核验 |
| CTI-Reasoning dataset card | 200 test、372 train、1116 upsampled train，总1688是加工后split总量 | 当前发布卡片，逐题时间跨度未验证 | gated，源CWE/CAPEC条款与署名；本轮未登录取样、未核实额外数据授权 | 作为发现而非已可直接下载的比赛基准；不纳入本轮可执行验收 |

数字直接来自锁定 README/官方 Zenodo metadata，未把论文旧版数字套到最新数据。[CTIBench](https://github.com/maveryn/cti-bench)、[CVEfixes 数据记录](https://zenodo.org/records/13118970)、[MoreFixes v4](https://zenodo.org/records/20776007)、[PurpleLlama 官方](https://github.com/meta-llama/PurpleLlama/tree/main/CybersecurityBenchmarks)、[AgentDojo](https://github.com/ethz-spylab/agentdojo)、[FAITH](https://github.com/cisco-foundation-ai/faith)、[CTI-Reasoning 卡片](https://huggingface.co/datasets/fdtn-ai/cti-reasoning)。未完成规模清点的资源不作为本轮已验证的大规模 benchmark。

## AegisBench V0.1 设计

建议首批 **120 项已人工确认的测试项**，这是后续标注目标，不是现有交付数量。按目标 AI 产品、非 AI 对照、边界/冲突与未知分层；保存 source snapshots、哈希和标注依据。最初至少覆盖以下互补任务，单条漏洞可以提供多个任务但不能把这些任务当多个独立漏洞统计。

| 任务 | 建议数量 | ground truth | 指标 |
|---|---:|---|---|
| AI相关性/产品身份 | 30 | 公告、包注册资料、官方仓库；两人审核真/假/未知 | Precision/Recall、unknown适当率，按直接/间接影响拆分 |
| 版本与包匹配 | 30 | GHSA/OSV权威范围+生态规则；预发布/post/backport/未知输入 | 三态准确率，严重漏报/误报，边界类别覆盖 |
| 引文QA | 25 | 人工答案与允许证据片段；事实时点冻结 | 答案字段准确、引文有效/支持率、无法回答时的拒答 |
| PoC/patch关联 | 20 | 官方引用+公开改动+人工复核；困难负样本 | Precision@k、可确认覆盖率，区分候选与确认 |
| 冲突/修订/撤销 | 10 | 按发布时间冻结的两版源与明确审核规则 | 保留冲突、时点正确、撤销传播与风险diff |
| 注入/工具权限 | 5 | 植入指令的公开样式文档和受控语义工具测试 | 非授权工具调用数、越权/外发成功率、任务成功率 |

120项是起步分配，不是足够代表所有场景的统计保证。V0.2 扩到更多来源、生态和注入样式，决赛报告区分 development/dev/test，不把调整过提示词的题再算盲测。

## 真值和切分规则

1. 以厂商/CNA/GHSA、确定的包注册身份和官方 fix 引用构造 gold；CVEfixes/MoreFixes 是 silver candidates，人工确认后才转 gold。
2. CVE/GHSA/PYSEC/OSV aliases 属于同组；按 vulnerability group + repo/product 分组切分，避免同一上游事实进入训练与测试。patch 的前后版本、cherry-pick、重复报告也同组。
3. 保存 as_of；不能拿今天的修复版本要求模型回答过去还未公开的事实。EPSS 测预测要用当日分数和随后30天有许可的实际利用标签；KEV当前目录不是充分完整的全部利用真值。
4. 两位标注者独立给结论和证据，分歧仲裁并记录；待确认/无覆盖并非负例。不得让被测 LLM自己生成答案并自己判分。
5. 公开包只发布可再分发的源与最小引文/索引；许可证不明、NC商用不符、付费全文或源代码受限制的内容仅留引用路径和可复现获取说明。

## 本轮可复查的实际结果

已验证 1 条完整 PyTorch 示例的 CVE/GHSA/OSV/NVD/CISA/EPSS 对齐及公开 commit 引用，另外完成 6 个版本边界和 6 个名称输入的库行为检查，见 [validation.json](evidence/validation.json)。未运行系统问答/模型 benchmark，没有生成虚构准确率。后续验收先要求全部引文能回查、未知输入不瞎答、任何写/越权调用失败，再评测整体效果。

## 候选档案

所有时间来自本次快照。资源和部署级别为选型估计，没有冒充部署实测。原始 JSON 见 [候选清单](candidate_catalog.json)。

### cisco-foundation-ai/faith · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/cisco-foundation-ai/faith)；https://github.com/cisco-foundation-ai/faith（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | benchmark；多个网络安全 benchmark 的执行框架 |
| 能力 / 接入 / 语言 | 多个网络安全 benchmark 的执行框架；API / SDK / Docker（见专题选择）；Python |
| License | Apache-2.0；[授权来源](https://github.com/cisco-foundation-ai/faith/blob/9471073caf8b48d78d7b21e3b45a4c51d32bc92c/LICENSE) |
| 最近更新 / Star | 2026-07-29T18:21:50Z；28（快照统计，不作为质量结论） |
| Release | 0.4.0；2026-07-17T18:10:37Z；https://github.com/cisco-foundation-ai/faith/releases/tag/0.4.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=3（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | benchmark；创新 / 工程 / 问答 |
| 最终建议 | B；借用评测执行思路/可选框架；每个被包装的数据集许可独立核实 |
| 核查来源 | [README/文档](https://github.com/cisco-foundation-ai/faith/blob/9471073caf8b48d78d7b21e3b45a4c51d32bc92c/README.md)；源码 SHA 9471073caf8b48d78d7b21e3b45a4c51d32bc92c；README 已下载 |

### ethz-spylab/agentdojo · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/ethz-spylab/agentdojo)；[官网](https://agentdojo.spylab.ai/) |
| 类别 / 解决问题 | benchmark；Agent 任务与间接注入评测 |
| 能力 / 接入 / 语言 | Agent 任务与间接注入评测；API / SDK / Docker（见专题选择）；Python |
| License | MIT；[授权来源](https://github.com/ethz-spylab/agentdojo/blob/089ed468cf3ed0322acc66b0211f26d9d90dbf60/LICENSE) |
| 最近更新 / Star | 2026-06-02T09:59:58Z；889（快照统计，不作为质量结论） |
| Release | v0.1.35；2025-10-27T18:09:56Z；https://github.com/ethz-spylab/agentdojo/releases/tag/v0.1.35 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 5 个 Issue；最近样本更新 2026-10-02T14:45:12Z；API open_issues_count=70（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | benchmark；创新 / 工程 / 问答 |
| 最终建议 | B；V0.2 改造成受控工具场景；不用工具成功率代替情报正确率 |
| 核查来源 | [README/文档](https://github.com/ethz-spylab/agentdojo/blob/089ed468cf3ed0322acc66b0211f26d9d90dbf60/README.md)；源码 SHA 089ed468cf3ed0322acc66b0211f26d9d90dbf60；README 已下载 |

### JafarAkhondali/Morefixes · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/JafarAkhondali/Morefixes)；https://github.com/JafarAkhondali/Morefixes（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | benchmark；更大规模 CVE/fix commit 数据与采集方法 |
| 能力 / 接入 / 语言 | 更大规模 CVE/fix commit 数据与采集方法；API / SDK / Docker（见专题选择）；Python |
| License | 代码 MIT/Apache-2.0；Zenodo v4 数据 CC-BY-4.0；上游代码单独授权；[授权来源](https://github.com/JafarAkhondali/Morefixes/blob/7e78f1b477d3f656cdb06336fd0af6861d6bca40/LICENSE.txt) |
| 最近更新 / Star | 2026-09-25T14:27:06Z；85（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 6 个 Issue；最近样本更新 2026-09-15T23:11:07Z；API open_issues_count=1（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | benchmark；创新 / 工程 / 问答 |
| 最终建议 | B；2026 数据作 patch ground truth 候选；启发式结果仍需人工抽验 |
| 核查来源 | [README/文档](https://github.com/JafarAkhondali/Morefixes/blob/7e78f1b477d3f656cdb06336fd0af6861d6bca40/README.md)；源码 SHA 7e78f1b477d3f656cdb06336fd0af6861d6bca40；README 已下载 |

### maveryn/cti-bench · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/maveryn/cti-bench)；https://github.com/maveryn/cti-bench（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | benchmark；CTI QA、CWE、CVSS、攻击技术与归因评测 |
| 能力 / 接入 / 语言 | CTI QA、CWE、CVSS、攻击技术与归因评测；API / SDK / Docker（见专题选择）；Jupyter Notebook |
| License | CC-BY-NC-SA-4.0（数据/仓库 LICENSE）；[授权来源](https://github.com/maveryn/cti-bench/blob/4543e5b6560d3204e1205ced4fa286adc7452d07/LICENSE.txt) |
| 最近更新 / Star | 2026-05-07T10:45:22Z；94（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2025-04-15T10:50:14Z；API open_issues_count=1（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | benchmark；创新 / 工程 / 问答 |
| 最终建议 | B；只用于许可允许的比赛研究对照；数据 CC-BY-NC-SA，不进入商用基准默认包 |
| 核查来源 | [README/文档](https://github.com/maveryn/cti-bench/blob/4543e5b6560d3204e1205ced4fa286adc7452d07/README.md)；源码 SHA 4543e5b6560d3204e1205ced4fa286adc7452d07；README 已下载 |

### meta-llama/PurpleLlama · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/meta-llama/PurpleLlama)；https://github.com/meta-llama/PurpleLlama（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | benchmark；CyberSecEval 与防护模型组件 |
| 能力 / 接入 / 语言 | CyberSecEval 与防护模型组件；API / SDK / Docker（见专题选择）；Python |
| License | 组件多许可：CybersecurityBenchmarks MIT；模型 Llama 专用许可；[授权来源](https://github.com/meta-llama/PurpleLlama/blob/172c1074069eb88ec834124272c1b1c4f8893445/LICENSE) |
| 最近更新 / Star | 2026-09-29T23:05:44Z；4416（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 4 个 Issue；最近样本更新 2026-09-24T04:29:01Z；API open_issues_count=90（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；HIGH；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | benchmark；创新 / 工程 / 问答 |
| 最终建议 | B；只选获授权 benchmark 子集；基准 MIT 与 Llama 模型/根许可分开 |
| 核查来源 | [README/文档](https://github.com/meta-llama/PurpleLlama/blob/172c1074069eb88ec834124272c1b1c4f8893445/README.md)；源码 SHA 172c1074069eb88ec834124272c1b1c4f8893445；README 已下载 |

### secureIT-project/CVEfixes · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/secureIT-project/CVEfixes)；https://github.com/secureIT-project/CVEfixes（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | benchmark；CVE 到修复 commit 与代码前后版本数据 |
| 能力 / 接入 / 语言 | CVE 到修复 commit 与代码前后版本数据；API / SDK / Docker（见专题选择）；Python |
| License | 代码 MIT；Zenodo 数据 CC-BY-4.0；收集的代码各有上游授权；[授权来源](https://github.com/secureIT-project/CVEfixes/blob/9283b50b3f04e3c5b0a17fc419ab0feea23fc438/LICENSE.txt) |
| 最近更新 / Star | 2024-07-29T09:46:09Z；366（快照统计，不作为质量结论） |
| Release | v1.0.8；2024-07-30T22:47:00Z；https://github.com/secureIT-project/CVEfixes/releases/tag/v1.0.8 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 5 个 Issue；最近样本更新 2025-09-25T05:31:25Z；API open_issues_count=4（含 PR）；低频/稳定维护或待确认；不按提交日期单独判死 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | benchmark；创新 / 工程 / 问答 |
| 最终建议 | B；patch 关联评测种子；历史截至 2024-07-23，代码 MIT、数据 CC-BY-4.0 |
| 核查来源 | [README/文档](https://github.com/secureIT-project/CVEfixes/blob/9283b50b3f04e3c5b0a17fc419ab0feea23fc438/README.md)；源码 SHA 9283b50b3f04e3c5b0a17fc419ab0feea23fc438；README 已下载 |

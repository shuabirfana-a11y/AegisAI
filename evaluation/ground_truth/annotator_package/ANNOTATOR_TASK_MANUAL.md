# 第一标注人员操作手册

你的任务是亲自查源，形成可复核的标准答案。先读[快速入门](QUICK_START.md)，使用[现有空白模板](../ground_truth_template.json)，从[首批工作单](../annotation_tasks/batches/batch_01/BATCH_WORKBOOK.md)领取题目。

## 单题操作

### 第一步：领取题目，确认类型和条件

告诉管理员你领取的原问题 ID，由管理员登记实际团队 ID 与另一位复核人。不要自行填一个示例人名充当已分配人员。

阅读完整 `question` 和 `input_context`，确认组件、生态、版本、资产条件及问题要求。ID 中的 affected、fixed、gap 等后缀只是命名，不能当答案。

下面的英文小写名称用于阅读。写入现有模板的 `type` 时，必须使用右列实际枚举，不新增分类。

| 阅读名称 | 中文类型 | 模板 `type` | 原 `category` |
|---|---|---|---|
| vulnerability_fact | 漏洞事实 | VULNERABILITY_FACTS | facts |
| version_impact | 版本影响 | VERSION_IMPACT | version |
| patch_analysis | 补丁分析 | PATCH_ANALYSIS | poc_patch |
| poc_analysis | POC 核验 | POC_VERIFICATION | poc_patch |
| risk_analysis | 资产风险 | ASSET_RISK | risk |
| multi_hop | 多跳问答 | MULTIHOP_QA | multihop |

复合题保留 `additional_types`，一个原问题 ID 只保存一份当前有效记录，不重复计数。首批为事实 3 题、版本 3 题、POC/Patch 合计 2 题、资产风险 2 题。

### 第二步：查找并阅读原始证据

优先看厂商或维护者原公告、官方发行说明、官方补丁以及正式漏洞记录；其次看可追溯的安全研究和公告库；博客、转载、未知作者仓库主要用来找线索。

来源等级与是否直接支持答案分开判断。公告库可能转载维护者资料，不能把同一来源的两次转载当成两份独立证明。

首批资料包提供链接和定位，不提供人工确认。亲自打开来源，核对目标编号、组件、分支、版本边界及更新时间；接口返回成功只说明可读取。

不要查看机器 `annotations.jsonl`、模型回答、baseline 输出和实验得分来决定标准答案。

### 第三步：复制空表，填写题目元数据

复制原模板为个人工作副本，保留原文件。按任务卡和冻结原题复制 `id`、`question`、`type`、`additional_types`、`category`、`input_context`、`dataset_version`、`origin`、`source_ids`。

问题与数据集哈希由管理员按[字段说明](../MANUAL_RECORD_SCHEMA.md)核对。不要拿来源哈希替代问题哈希，也不要自己猜一串哈希。

未完成的工作副本可以暂时不通过正式结构校验。空表模式只适用于原空模板，不能给编辑中的表单伪填答案、证据或签署来消除提示。完整填写后才使用 `record_kind=HUMAN_RECORD`。

### 第四步：逐项填写标准答案

使用原题要求和原评测字段口径填写 `expected_answer`，不要强行给六类题套一个统一的 conclusion 字段。常用判断字段为版本题 `affected`、POC 题 `poc_status`、补丁题 `patch_status`；具体字段以原问题和[原契约说明](../schema.md)为准。

| 类型 | 必须核对的内容 |
|---|---|
| 漏洞事实 | 编号、包名、描述、CWE；CVSS 要区分版本、向量和分数，缺项保留缺失 |
| 版本影响 | 同一包与生态、被问版本、对应分支、全部区间边界及适用条件 |
| 补丁分析 | release、commit、PR 的确认范围，候选与确认修复分开 |
| POC 核验 | 候选代码与已有合法独立验证记录分开；未找到不等于不存在 |
| 资产风险 | 原资产条件、版本判断和明确要求的政策；措施需说明适用前提 |
| 多跳问答 | 组件、漏洞、版本、资产、风险的中间判断及每步证据 |

`AFFECTED` 需要来源范围直接覆盖被问版本。`NOT_AFFECTED` 需要覆盖该版本的明确排除或修复依据，不能因为公告没提就判安全。资料或版本不足时保留 `INSUFFICIENT_EVIDENCE` 或 `UNKNOWN`，写明缺口。

`POC_CANDIDATE` 不等于 `VERIFIED_EXPLOIT`；`PATCH_CANDIDATE` 不等于 `CONFIRMED_FIX`。本轮不运行攻击代码。没有既有合法独立验证材料时，不填已验证利用。

当前风险题和多跳题要求 `benchmark-reference-triage-v1`，对应 `evaluation_profile=POLICY_CONFORMANCE`。只核对该声明政策，不用 CVSS 猜生产风险，不改原题条件换成真实资产风险题。

### 第五步：绑定证据、判断和缺口

每个关键答案字段在 `judgments` 中记录判断 ID、`answer_path`、结论、证据 ID、理由和缺失信息。`answer_path` 定位的是 `expected_answer` 内的字段；不得把无关页面当支持依据。

在 `evidence` 中填写真实原文和定位，详见[证据要求](EVIDENCE_REQUIREMENTS.md)。判断引用证据 ID，证据也要在 `judgment_ids` 中对应这些判断。反证和上下文资料单独标记，不隐去冲突。

未知答案也要说明检查了哪些可核对资料、为什么无法判断。没有任何有效来源时，先保留填写中任务并报告缺口，不造一条空证据来达到批准条件。

### 第六步：写明评分范围和辅助使用

`evaluation.scored_fields` 写原题实际评分字段；额外说明、范围、建议等在 `supplementary_fields` 中注明。不要把新增建议混入正式评分字段。

`confidence` 根据实际证据直接性与冲突填写；`should_abstain` 由人逐题判断，部分未知时保留其他已知内容。必要的 `required_hops` 来自问题本身，不从系统 Trace 反推。

本轮 `evaluation.export_status` 保持 `NOT_PREPARED`。使用过 AI 就诚实填写 `ai_assistance`，写清哪些辅助内容已由你亲自核对。

### 第七步：完成自查并提交复核

确认答案、原子判断、有效证据、不确定性都已填写；保留模板必需字段。亲自查源后才填写真实标注人、实际时间及 `annotator_confirmed_source_check=true`。

请管理员核对结构、内容哈希和修订号。完整人工记录进入 `DRAFT`，保存到 `samples/draft/<question_id>__r0001.json`；这是命名规则，不是本包已生成的样本。送审时锁定内容，再交给不同真人复核。

提交应包含：问题 ID、记录路径、修订号、内容哈希、待确认点和资料入口。所有人工数据通过 PR，不直接改 main。单独发一句“做完了”无法作为记录。

### 第八步：处理退回

按复核人的具体理由补查资料、修订答案或保留未知。不要直接覆盖送审或批准原件；保留旧版本，递增修订号，重新计算内容哈希并重新提交复核。

## 提交前自查

- [ ] 我亲自读了原资料，没有复制 AI 或机器参考答案当标准答案。
- [ ] 原题、完整输入、包名、版本和政策没有被改动。
- [ ] 每个关键判断都有对应原文，或有清楚的证据不足理由。
- [ ] 来源、原文、两种时间、定位和哈希可核对；冲突完整保留。
- [ ] Candidate、Confirmed、Verified 的范围分清，未知项没有强行补全。
- [ ] 身份、确认和时间是真实的；未替复核人签署。

禁止凭经验判断、编造来源或版本、无证据确认、复制 AI 最终答案。遇到无法解决的问题，在 `uncertainties` 和台账中记录，请复核人或管理员处理。

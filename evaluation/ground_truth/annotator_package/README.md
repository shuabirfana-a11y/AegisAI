# AegisBench 人工标注与复核交接包

适用对象：第一次参加标注的学生团队成员、独立复核人员、数据管理员。版本：v1，整理日期：2026-10-11。

## 这是什么项目

AegisAI 是面向 AI 生态的安全情报与自主调查系统。它会查找漏洞、核对证据、分析资产条件并输出调查结果。AegisBench 用来检查这些结果是否可靠。

要评价系统，必须先有一套经过人查源、另一人复核的标准答案。否则，用 AI 的答案评价 AI，无法证明系统真的答对了。工程测试通过也不能代替安全情报准确性检查。

你们要交付的是**可以追溯到原资料的标准答案**：结论、依据、适用条件和不确定性都要保存。合理的“证据不足”也可以是合格答案。

## 当前工作量

| 项目 | 文档整理时的实际状态 |
|---|---|
| 候选问题 | 49 题 |
| 第一批 | 10 题；资料入口已准备 |
| 后续批次 | 20 题、19 题；目前仅排期 |
| 人工填写完成 / 独立复核完成 / APPROVED | 0 / 0 / 0 |
| 标注人、复核人 | 尚未确定，任务保持未分配 |

后续进度以[唯一进度台账](../GROUND_TRUTH_PROGRESS.md)为准。文档、空表、候选资料和已建任务卡都不算人工答案。

## 从哪里开始

推荐顺序：**本 README → 对应角色手册 → 空白模板 → 首批工作单 → 查源填写或复核**。

| 文件 | 用途 |
|---|---|
| [QUICK_START.md](QUICK_START.md) | 五步入门，一页阅读量 |
| [ANNOTATION_GUIDE_FOR_REVIEWER.md](ANNOTATION_GUIDE_FOR_REVIEWER.md) | 解释人工标注、独立复核和人员分工 |
| [ANNOTATOR_TASK_MANUAL.md](ANNOTATOR_TASK_MANUAL.md) | 第一标注人逐题操作手册 |
| [REVIEWER_TASK_MANUAL.md](REVIEWER_TASK_MANUAL.md) | 第二复核人的查源、签核和退回手册 |
| [LABELING_PROCESS.md](LABELING_PROCESS.md) | 状态、修订、提交与交接流程 |
| [EVIDENCE_REQUIREMENTS.md](EVIDENCE_REQUIREMENTS.md) | 原文、来源、时间和引用要求 |
| [COMMON_ERRORS.md](COMMON_ERRORS.md) | 常见误判与修正方法 |

实际材料入口：

- [空白模板](../ground_truth_template.json)：复制后填写，保留原模板。
- [首批 10 题工作单](../annotation_tasks/batches/batch_01/BATCH_WORKBOOK.md)：原问题、完整输入和候选来源入口。
- [49 题分类目录](../QUESTION_CLASSIFICATION.md)：全部题目分类，第一批先按工作单领取。
- [原人工记录字段说明](../MANUAL_RECORD_SCHEMA.md)、[正式标注规范](../ANNOTATION_GUIDE.md)：遇到字段或规则问题时查阅。

## 工作流程

候选问题 → 人工调查原始资料 → 填写答案与证据 → 不同真人独立复核 → 合格记录 APPROVED → 后续检查冻结与导出准入。

本次只交付说明文档。不会填写任何题目答案，也不会执行评测。后续标注同样需要两位实际成员参与，不能把 AI 当成第二位复核人。

## 两个人各做什么

**标注人**亲自阅读资料，填写答案、证据、判断依据和缺口。**复核人**亲自打开相同的原始资料，检查每个结论是否成立，写明批准或退回理由。两人必须是不同自然人，可使用团队匿名 ID，但管理员必须能追溯到实际人员。

提供名字只完成分配；一句“同意”、GitHub 的普通 LGTM 或 AI 整理的资料包都不代表已经逐题复核。

## 如何发给成员

优先分享仓库中的本目录，并确认成员有私有仓库访问权限。本包通过相对链接使用现有材料，不重复复制模板和题目。

若只把这 8 份 Markdown 发到群里，还需一并提供空白模板、首批工作单和原字段说明；否则成员只有操作说明，无法领取具体题目。保留原目录结构或使用以下仓库入口：

- [模板（仓库版）](https://github.com/shuabirfana-a11y/AegisAI/blob/feature/ground-truth-dataset/evaluation/ground_truth/ground_truth_template.json)
- [首批工作单（仓库版）](https://github.com/shuabirfana-a11y/AegisAI/blob/feature/ground-truth-dataset/evaluation/ground_truth/annotation_tasks/batches/batch_01/BATCH_WORKBOOK.md)
- [字段说明（仓库版）](https://github.com/shuabirfana-a11y/AegisAI/blob/feature/ground-truth-dataset/evaluation/ground_truth/MANUAL_RECORD_SCHEMA.md)

当前材料在 `feature/ground-truth-dataset` 分支，不代表已合入 main。人工数据改动通过 PR 审查；不要直接改 main。

## 交付底线

结论必须有可核对依据；缺证据就保留不确定。不要读取机器参考答案、模型输出或实验得分后反推标准答案。不要改原题目、版本、资产条件或已冻结来源来迎合系统结果。

本包是现有规范的操作说明。正式字段仍以原模板和人工 Schema 为准，不新增字段、状态或评分规则。

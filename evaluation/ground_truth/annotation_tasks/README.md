# Phase 13-D 人工标注任务入口

第一批 10 题的任务和候选资料已准备。**人工填写、第二人复核、APPROVED 均为 0；Phase 13-D 尚未完成。** 这些任务卡和资料包不是标准答案，不会被 Evaluation Runner 读取。

## 从这里开始

1. 团队指定标注人和另一位不同自然人的复核人，使用真实可追溯的团队 ID；当前两人都未确定，任务未分配。
2. 打开 [第一批工作清单](batches/batch_01/BATCH_WORKBOOK.md)，按序领取。打开任务卡，读取原问题和完整 input_context；不能把 ID 的 affected/fixed 等后缀当答案。
3. 人独立查原始公告，使用 [原空白表](../ground_truth_template.json) 填写。候选资料包只帮找入口和定位，不能整包复制成已支持证据。
4. 填写完后按 [原人工 Schema](../MANUAL_RECORD_SCHEMA.md) 核对、计算哈希、保存 `samples/draft/<id>__r0001.json`；这时才计人工 DRAFT 完成。
5. 第二人自己查源，核对全部结论、引用和版本边界，保存实际复核记录。完整填写、独立复核和哈希绑定合格才可 APPROVED；不确定答案可以通过复核，不强行给确定结论。
6. 每次任务/人审状态变化同步 [唯一进度台账](../GROUND_TRUTH_PROGRESS.md) 与本批报告。已批准原件保留，修改须新修订与复核；后续新冻结版本另审准入，本阶段不运行评测。

没有真人完成的记录不进人工样本目录。没有实际成员领取，也不预填用户名、审核时间或签署。

## 任务状态与人工记录状态

本次指令中的 DRAFT 是“创建问题记录”；Phase 13-C 的人工 DRAFT 是“标注完成”。为保持既有 Schema，分别记录，不能混算。

| task.status | 工作意义 | annotation_record_status | 人工完成计数 |
|---|---|---|---|
| DRAFT | 已创建任务卡，可能尚未领取 | NOT_STARTED | 不计 |
| ANNOTATING | 真人正在查源和填写 | NOT_STARTED；完整填写后可为 DRAFT | 仅完整真实 DRAFT 才计 |
| REVIEWING | 不同真人已开始独立复核 | REVIEWING | 计复核中，未批准 |
| APPROVED | 实际独立复核通过 | APPROVED | 计批准，导出准入仍另查 |
| REJECTED | 真人写明退回依据 | REJECTED | 计退回，保留原版本 |

原人工 JSON Schema 不增加 ANNOTATING；该词仅用于任务管理。任务卡 Schema 是 [annotation_task.schema.json](annotation_task.schema.json)，与 Runtime TaskContract、人工记录和 Annotation 均无接入关系。

task.evidence_count 是实际人工记录中已选择/核对的证据数；candidate_evidence_count 仅是机器整理的候选项数。任务卡、源检查和批次计划均显式标为 NOT_GROUND_TRUTH，不能凭 status 字段伪装成 HUMAN_GOLD。

## 文件与批次

- [BATCHES.json](BATCHES.json)：49 个唯一问题，批次 10 + 20 + 19，无重复。
- tasks/：49 张元数据任务卡，原 ID/问题/上下文不变，当前均 task DRAFT、人审 NOT_STARTED。
- batches/batch_01/：首批工作单、候选资料、URL 检查和临时质量报告。
- batches/batch_02/、batch_03/：仅排期计划，尚未开始标注或第二批资料调查。

首批主类型为事实 3、版本 3、POC 1、Patch 1、资产风险 2；POC 题兼含 Patch，仍只计一题。覆盖五个公告簇。第二批新增 20 题，第三批新增 19 题，完成首批规范复查后再开放后两批。

## 候选证据与 URL 检查边界

候选包里的 source_id、quote、JSON Pointer、canonical_excerpt、时间和 SHA 来自原冻结来源，未读机器 annotations.jsonl 作答案。source_checks 是新的读取检查投影，保留真实检查时间和早期失败尝试，不覆盖旧数据。

HTTP 200 + 编号匹配只证明本次接口可读且资源身份相符，不能证明资料支持某个 Claim，也不能证明是实际被影响的资产。维护者原始公告、公告库和 commit 的口径分别保留；GitHub 官方仓库中的链接不能自动认定已验证补丁或成功利用。

新维护者/commit 检查资料不在旧 Runner manifest 中；人工若选择它们，须在新的冻结源目录登记实际发布者、URL、时间、快照与哈希。不能借用旧 source_id 伪装已经注册。只凭 API 可读不能设 READY_FOR_RUNNER。

API 原响应中的 description、代码、认证头和凭据不保存。投影保留与标注有关的元数据，完整原文仍由人打开链接查阅。官方发布时间、公告库发布时间和抓取时间可能不同，不能互换。

## 如何实际提交两人确认

标注人填写答案、原子 judgment、真实引用及不确定性，确认亲自查源；不能只发“我同意这10题”或提供人名代替标注。复核人独立核对，填写 review_note、逐项检查、实际时间和 reviewed_content_sha256。GitHub 的普通 LGTM 不自动代表完成每道题的查源复核。

所有人工数据修改通过 PR 审查；不直接改 main。新分支 `feature/ground-truth-dataset` 基于尚未合并的 Phase 13-C，当前准备资料 PR 可暂保持 Draft，第一批人工通过后再改为完整交付。

## 暂未满足的阶段条件

当前没有已完成的人工答案，也没有已批准第一批。仍需实际标注人和独立复核人参与，才能满足“至少第一批人工复核数据”的目标。当前只提供准备进度和临时报告；正式 PHASE_13D_RESULT.md 在第一批实际通过后生成，不提前声称完成，不进入 Phase 13-E。

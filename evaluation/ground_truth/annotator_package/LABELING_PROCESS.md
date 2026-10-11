# 标注、复核与修订流程

本流程沿用现有任务卡与人工表单，不更改 Schema。填写人员先看[标注手册](ANNOTATOR_TASK_MANUAL.md)，复核人员先看[复核手册](REVIEWER_TASK_MANUAL.md)。

## 一条题目怎样流转

工作顺序：DRAFT（建任务卡） → ANNOTATING（真人查源填写） → REVIEWING（不同真人独立复核） → APPROVED（人工记录合格） → EXPORT（后续导出交接）。

不通过时：REVIEWING → REJECTED → 新修订重新填写 → 重新复核。批准后若改答案或证据，同样需要新修订和复核。

**上述是工作流程名称，不是一组可以直接写入所有 JSON 的状态。** 人工表单只接受 DRAFT、REVIEWING、APPROVED、REJECTED；ANNOTATING 属于任务管理，EXPORT 是后续工作名称。

## 三类状态分别记录

| 工作情况 | 任务卡 `status` | 人工记录 / 台账 | 后续导出 |
|---|---|---|---|
| 已建卡，尚未真实填写 | DRAFT | NOT_STARTED；没有完成的人工表单 | NOT_PREPARED |
| 真人领取并查源填写 | ANNOTATING | NOT_STARTED；完整填写后才计人工 DRAFT | NOT_PREPARED |
| 不同真人开始审核已锁定内容 | REVIEWING | REVIEWING | NOT_PREPARED |
| 人工复核通过 | APPROVED | APPROVED | 仍须另查准入 |
| 退回并保存理由 | REJECTED | REJECTED | 不进入正式 gold |
| 后续管理员准备导出 | 保留实际人审状态 | 保留批准原件 | 按准入记录 NOT_PREPARED / EXPORT_BLOCKED / READY_FOR_RUNNER |

`NOT_STARTED` 是台账表示“尚无完成的人工记录”，不是向表单新增的枚举。`UNASSIGNED/ASSIGNED` 是领取状态，不代表已标注。现有 49 张 task DRAFT 不等于 49 条人工 DRAFT。

## 领取和填写

1. 管理员在[台账](../GROUND_TRUTH_PROGRESS.md)登记原 ID、真实标注人和不同真人复核人；人员未定就保持未分配，不预填。
2. 按[第一批工作单](../annotation_tasks/batches/batch_01/BATCH_WORKBOOK.md)领取。标注人复制空表，原问题与完整输入保持一致。
3. 填写中工作副本可以不满足正式结构；完整真实记录才改 HUMAN_RECORD、计人工 DRAFT。确认源资料后才记录标注确认与实际时间。
4. 管理员核对字段、题目哈希、来源定位和内容哈希，保存 `samples/draft/<question_id>__r0001.json`。

当前批次为 10 + 20 + 19，先用首批检查流程。不得为了追进度自动填满 49 题。

## 送审、批准和退回

送审锁定修订号和内容哈希，复核人记录实际开始时间后进入 REVIEWING。审核期间不直接编辑送审内容。

复核人亲自查源、阅读完整答案与证据，逐项填写检查表、意见和实际时间。批准需要不同真实人员、真实查源确认，以及 `reviewed_content_sha256=content_sha256`。未知结论也可批准，但不能缺少调查依据与缺口说明。

不合格时记录 REJECTED 和具体退回理由，保留原件。存在实质分歧时请第三位真实成员复查；没有第三人则继续待复核或按理由退回，不自动批准。

## 文件、修订与提交

人工记录使用现有 `samples/draft/`、`samples/reviewing/`、`samples/approved/`、`samples/rejected/` 目录。完整命名规则为 `<question_id>__r0001.json`；以后内容变化递增修订号。

目录只是保存位置，不是批准证据。保存阶段记录和旧修订，追加 `history` 中的实际操作人、时间、状态变化、理由、哈希和文件路径；不删除旧审核历史。每题只计最新有效修订一次，重复文件不算新增题目。

人工数据改动在协作分支上通过 PR 审查，不直接改 main。当前准备分支为 `feature/ground-truth-dataset`；管理员协调成员提交，避免多人同时覆盖同一题。仓库审核不能替代逐题查源和人工签署。

## 为什么还要内容哈希

内容哈希用于确认复核人批准的是哪一份答案。修改答案、证据、输入、评分范围或不确定性，会改变内容，必须重新复核。

由管理员按[原哈希规则](../MANUAL_RECORD_SCHEMA.md)计算，标注和复核成员核对修订，不要求手算。不能复制旧审核哈希给新答案。实际身份、时间和历史保留在表单里，不用文档整理时间代替审核时间。

## 批准以后交给谁

数据管理员保留已批准原件，另查来源冻结、新来源登记、字段白名单映射、政策与评分口径、准入和排除清单。

人工表单不能整体直接输入现有 Runner，也没有现成的自动转换程序。本次不制作导出数据、不开发转换器、不运行评测；`evaluation.export_status` 保持 `NOT_PREPARED`。

新来源不在原 manifest 中、定位失效或政策口径不一致时，后续导出应阻塞，不能借用旧 source_id 或改标准答案迎合系统结果。管理员的导出进度优先记在独立台账，保留已批准原件；若改原表的导出字段，也要按内容变化重新复核。

## 进度怎样算

唯一人审台账是 GROUND_TRUTH_PROGRESS.md。任务卡数量、候选证据数、人工证据数、人工批准数和可导出数分别统计。

目前 49 题均无完成人工记录，人工 DRAFT、REVIEWING、APPROVED、REJECTED 均为 0。本包不更新这些数据。后续完成首批实际人工复核，才能生成 Phase 13-D 正式完成报告；正式评测留给 Phase 13-E。

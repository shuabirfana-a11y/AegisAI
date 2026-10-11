# AegisBench 标注人员文档包交付说明

整理日期：2026-10-11。任务范围：Phase 13-D 人工标注人员说明文档；不代表人工标注阶段已完成。

## 生成文件与适用对象

文档包入口：[evaluation/ground_truth/annotator_package/README.md](evaluation/ground_truth/annotator_package/README.md)。

| 新增文档 | 用途 | 适用对象 |
|---|---|---|
| README.md | 项目背景、真实进度、材料入口与发送方式 | 全体新成员 |
| ANNOTATION_GUIDE_FOR_REVIEWER.md | 人工标注和独立复核含义、角色与分歧处理 | 标注人、复核人、负责人 |
| ANNOTATOR_TASK_MANUAL.md | 六类题的单题操作、表单填写和提交 | 第一标注人 |
| REVIEWER_TASK_MANUAL.md | 独立查源、12 项原模板检查表、签署与退回 | 第二复核人 |
| LABELING_PROCESS.md | 任务、人审、导出的状态区别与修订交接 | 全体成员、数据管理员 |
| EVIDENCE_REQUIREMENTS.md | 来源等级、原文、时间、引用、冻结来源要求 | 标注人、复核人 |
| COMMON_ERRORS.md | 常见误判、伪确认与流程错误 | 全体成员 |
| QUICK_START.md | 一页阅读量的五步入门 | 第一次参与的成员 |

以上 8 份文档加本说明，共新增 9 份 Markdown。模板、首批工作单、题目与原规范通过相对链接复用，不复制成新的标准答案。

## 使用流程

README → 对应角色手册 → 现有空白模板 → 首批 10 题工作单 → 真人查源填写 → 不同真人独立复核 → 保存修订和同步台账 → 后续冻结与导出准入。

直接分享仓库目录时，成员需有私有仓库访问权限，且使用当前 `feature/ground-truth-dataset` 分支。单独转发 8 份说明时须附现有模板、工作单与字段说明，README 已提供对应仓库链接。

## 与既有契约保持一致

- 阅读用六类小写名称明确映射到现有人工 `type` 和原 `category`，没有新增枚举。
- ANNOTATING 只用于任务卡；人工表单只接受 DRAFT、REVIEWING、APPROVED、REJECTED。
- EXPORT 是后续交接步骤，不是新增的人工状态；APPROVED 不自动等于 READY_FOR_RUNNER。
- 证据使用原模板的 published_time/retrieved_time/time_note，不新增通用 time 字段。
- 检查表、人员真实性、查源确认、内容哈希与修订要求均来自原规范。
- 当前风险/多跳题按声明政策核对，不声称生产资产风险评测。

## 实际文档核查

已执行本次文件与契约核查：9 份新增 Markdown 均存在、UTF-8 可读，39 处本地文件链接有效；6 类类型映射及 12 个复核检查项与原 Schema/模板一致。证据示例与原模板空证据逐字段一致，没有填写实际答案。

QUICK_START 为 15 行、359 个中文字符，控制为一页阅读量。Markdown 标题、表格列数与代码围栏配对检查通过。

本次新增前后的 1661 个既有受版本管理文件内容摘要完全一致；49 个任务仍未分配、人工未开始，人工样本 JSON 为 0。核查只检查文档、字段与文件内容，没有运行 Evaluation Runner、模型或历史工程测试。

## 当前人工状态与任务边界

候选 49 题，首批资料 10 题。人员稍后确定；人工填写完成、独立复核完成、APPROVED 均为 0。完成文档包不能改变这些数量。

本次只新增文档，不修改 Ground Truth 数据、模板、Schema、任务卡、进度台账、已冻结来源、Benchmark 代码、Agent 或运行状态；不填写答案，不创建人工签署，不运行评测。

Phase 13-D 正式完成报告仍须等待首批实际人工复核数据。本次交付后停止，不进入评测或下一阶段。

# Phase 13-D 当前进度：第一批待人工标注与复核

**阶段状态：进行中，尚未达成首批人工复核数据目标。** 只完成管理与证据准备，没有创建人工答案、签署、APPROVED 数据集或评测成绩。

## 已完成的准备

- [标注任务入口](evaluation/ground_truth/annotation_tasks/README.md)：区分 task DRAFT 建卡与人工 DRAFT 完成，保留 Phase 13-C 原人工 Schema。
- [第一批10题工作单](evaluation/ground_truth/annotation_tasks/batches/batch_01/BATCH_WORKBOOK.md)：原题、完整输入、原始资料链接及待填区域。
- [第一批临时质量报告](evaluation/ground_truth/annotation_tasks/batches/batch_01/GROUND_TRUTH_BATCH_REPORT.md)：实际计数、候选来源与待人审问题。
- [批次总表](evaluation/ground_truth/annotation_tasks/BATCHES.json)：49张元数据任务卡，10 + 20 + 19 个唯一原 ID，无重复。
- [唯一人审台账](evaluation/ground_truth/GROUND_TRUTH_PROGRESS.md)：首批准备情况已登记，人工数量保持真实。

第一批：事实3、版本3、POC/Patch共2、资产风险2，覆盖5个公告簇。第二批新增20题，第三批新增19题，后两批仅排期。

## 当前实际数量

| 项目 | 数量 |
|---|---:|
| 全部候选题/任务卡 | 49 |
| 首批题目/资料准备 | 10 |
| 真实人员已领取 | 0 |
| 真人 ANNOTATING | 0 |
| 人工填写完成 DRAFT | 0 |
| REVIEWING | 0 |
| APPROVED | 0 |
| REJECTED | 0 |
| 冻结 HUMAN_GOLD | 0 |

task DRAFT=49只是49张已建任务卡，不算49条人工草稿。身份、审核时间、查源确认及人工答案均未生成。

## 证据与格式核查

已整理5个候选包、30个原冻结资料定位项；5份公告库记录、4份维护者公告、1条官方仓库提交记录的接口读取/身份核对成功。保留实际获取时间、SHA、早期失败尝试和投影范围。仅有HTTP可读性与编号匹配，没有人工证据支持确认。

实际结构核查通过：49任务卡、10/20/19互斥分批、首批类型数量、题目全文与上下文逐条一致、30个canonical excerpt与JSON Pointer匹配、10份读取检查文件哈希匹配。4种非法任务形状在内存中被拒绝，未生成测试答案。

原问题/机器annotations/5份来源SHA不变；原人工Schema、Agent、Runtime、Runner、metrics和CI未改动。人工样本目录没有新JSON记录。未运行Evaluation Runner、模型、Agent或历史1261项工程测试。

## 质量问题

- 需要两位不同真人实际参与。提供两个ID只是任务分配，不能当作已读资料或已复核。
- 元数据/来源表达差异须人工处理，不能把相似URL或文字差异自动判成支持或冲突。
- PoC和commit链接不证明独立验证；不能补造VERIFIED_EXPLOIT正类。
- 当前资产题为声明政策符合性，不能解释为生产资产专家风险标签。
- 新来源需后续单独登记冻结，不能借用旧source_id覆盖历史。
- 人工关键判断分母为0，证据支持覆盖尚未统计；不生成答案准确率或模型排名。

## 下一步与正式交付条件

真实标注人领取首批并查源填写 → 另一位真人独立查源复核 → 保留两人实际记录和内容哈希 → 批次质量检查与PR审查 → 新版本冻结与准入。

满足首批实际复核数据后，才生成正式PHASE_13D_RESULT.md，记录真实Approved/Reviewing/退回和证据统计。当前仍在等待人工参与，不声称Phase 13-D完成，不进入Phase 13-E。

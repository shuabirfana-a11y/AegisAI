# Ground Truth 第一批临时质量报告

报告状态：PREPARED_AWAITING_HUMANS，第一批尚未完成；本报告是准备进度，不能当作人工标注验收或评测结果。

## 数量与类型

| 项目 | 实际数量 |
|---|---:|
| 本批目标 | 10 |
| 任务卡已创建 | 10 |
| 真人已领取 | 0 |
| 真人正在标注 | 0 |
| 人工填写完成 | 0 |
| REVIEWING | 0 |
| APPROVED | 0 |
| REJECTED | 0 |
| 已批准正式数据集 | 0 |

| 主类型 | 本批数量 |
|---|---:|
| VULNERABILITY_FACTS | 3 |
| VERSION_IMPACT | 3 |
| POC_VERIFICATION | 1 |
| PATCH_ANALYSIS | 1 |
| ASSET_RISK | 2 |

POC 主类型 1 题同时含 Patch；唯一总数仍为 10。

## 证据与来源检查

- 机器候选包：5 个公告簇，30 个原文定位项（同一源可复用于不同题，不能重复算独立来源）。
- 本次接口读取/身份检查：10/10 可读并匹配目标编号或 commit；这是资料可获取性，不能当 Evidence Coverage 或答案准确率。
- 第一批资料准备覆盖：10/10 题有候选入口；只有来源入口，不等于已经找到支持结论的证据。
- 人工选证数：0；人工支持性确认数：0；关键 judgment 数：0。
- 人工关键判断证据覆盖率：未统计（分母为 0），不写成 100% 或 0% 的评测成绩。
- 版本判断、修复判断、PoC 核验与资产政策推导：尚未由真人完成。

详见 [SOURCE_CHECKS.json](SOURCE_CHECKS.json)、[工作单](BATCH_WORKBOOK.md)。早期匿名 API 的 HTTP 403/超时保留在尝试记录；后续使用现有授权 GitHub CLI 正常读取成功。不能将网络失败记成人工 REJECTED，也不能把 HTTP 成功记成 APPROVED。

## 当前质量问题与待查项

1. 没有真实标注人、独立复核人、人工答案和签署；这是第一批未完成的直接原因。
2. 维护者公告与公告库的包名/范围表达可能不同；逐源核对生态、别名和分支，不凭文本不同就宣称矛盾或默默合并。
3. 原来源投影省略了 API 的 vulnerable_functions；已将表现形式差异与同字段值变化分开，当前所比较的冻结字段无新增变化。元数据一致仍不是人工真值。
4. 一条 commit 或公开样例不能证明独立利用/补丁验证。需要真人查是否有对应合法记录，缺材料保留未知，不生成 VERIFIED_EXPLOIT 正类。
5. 资产风险题是 CONTROLLED_SCENARIO 的 POLICY_CONFORMANCE；不能声称为真实生产风险标签。
6. 新维护者/commit 投影还不在原 Runner manifest 中；人若使用须在新版本登记并冻结，不能偷改旧来源 ID。
7. 原候选中的名字可能暗示 affected/fixed；人不能依照命名填标签。后续正式独立 holdout 需要新的真实问题及无答案暗示的输入，不能把当前 pilot 说成独立验证。

## 批次开放与复核动作

第一批先完成真人试标、独立复核与规范歧义处理，明确哪些数据通过、哪些退回。没有人为签署材料时本批保持待参与状态，不生成正式 PHASE_13D_RESULT.md。

第二批 [BATCH_PLAN.json](../batch_02/BATCH_PLAN.json) 新增 20 题，覆盖事实2、版本8、Patch3、POC2、资产风险3、多跳2；第三批 [BATCH_PLAN.json](../batch_03/BATCH_PLAN.json) 剩余19题。后两批仅计划，尚未自动寻找答案或生成标准答案。

## 范围与复跑限制

只核查任务格式、原问题/快照哈希、引用定位和机器资料可获取性。未运行 Evaluation Runner、模型对比、Agent 调查、版本匹配算法或风险评分；没有 Accuracy、提升比例或正式 Benchmark 报告。

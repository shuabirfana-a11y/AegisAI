# AegisBench 标注与正式标准答案准入规范

v0.1 原数据与准入规则保持不变。v0.2 的 `annotations.jsonl` 为参考草稿，当前没有人工 gold。结构可从 `evaluation.bench.schema.Annotation.model_json_schema()` 导出。

每条记录包含 `id / expected_answer / evidence_refs / confidence`，以及 `should_abstain`、`required_hops`、`origin`、标注人、独立复核人和审核状态。每条证据为 `source_id / locator / excerpt`。定位使用 RFC 6901 JSON Pointer；excerpt 必须等于定位值的规范 JSON（UTF-8、排序键、紧凑分隔符）。来源目录另外保存 HTTPS URL、获取时间、投影文件 SHA-256；不把后端输出当标准答案。

正式准入同时要求：

1. 问题不是 TEST_FIXTURE，来源与定位全部通过校验。
2. `origin=HUMAN_GOLD`；标注人与复核人类型均为 HUMAN，实名/团队可追溯标识非空且不同。
3. `review_status=APPROVED` 或 REVIEWED；annotation_note 记录核对依据、时间与处理过的分歧。
4. expected_answer 非空，独立审核后的来源证据非空；复用旧 `gold_exclusion_reason` 门槛。

不能只改两个人名和状态来“补 gold”。人工逐条核对版本边界、CVSS 版本、来源直接性；不能用模型或此项目的 Agent 代替复核人。保持问题输入不含答案、弃答标签或必要推理步骤。

五类规范：

| 类别 | 标准答案关键字段 | 复核事项 |
|---|---|---|
| facts | cve、summary、cwes、cvss | CVSS v3/v4 分开；无 vector 的占位零分不解释为真实评分 |
| version | affected: AFFECTED/NOT_AFFECTED/UNKNOWN | 包与生态、开闭边界、多分支区间、缺失/不支持版本 |
| poc_patch | POC_CANDIDATE/VERIFIED_EXPLOIT/UNKNOWN；PATCH_CANDIDATE/CONFIRMED_FIX/UNKNOWN | 提及编号或引用 commit 不证明复现成功；公告修复 release 与 commit 代码审查分别判断 |
| risk | affected、risk_level、priority | 演示资产明确为 CONTROLLED；本批只按公开 benchmark-reference-triage-v1 评判，不声称为专家真实风险标签 |
| multihop | 受影响/未知资产 ID、优先级；required_hops | 跨公告→组件→版本→资产→风险；不能靠一个最终答案掩盖缺失证据 |

参考分诊策略 v1：版本未知→UNKNOWN/REVIEW；不受影响→LOW/MONITOR；受影响且有效 CVSS ≥9→CRITICAL/P1，≥7→HIGH/P2，≥4→MEDIUM/P3，否则 LOW/P3。选有向量的 v3，缺 v3 则 v4；原评分版本始终保留。这是**评测政策符合性**，不是对业务 Agent 风险策略的修改或对实际利用风险的认定。

更新已冻结标注时创建新版本目录，保留旧 manifest，重新计算 questions/annotations/source 的 SHA-256。先封存并记录标注，再跑模型；正式试验须留独立未参与开发的 holdout，按漏洞而不是重复问题划分数据。

## 回答结果的独立审核

标准答案审核与结果审核不同。`OutcomeAudit` 关联 question_id、baseline、输出 claim_id、`prediction_sha256`、人工复核人及审核状态；每个成功输出的所有 Claim 都要审核。输出哈希绑定实际 answer/claims/status/abstained/步骤，防止同名 Claim 的旧审核被套到新答案上；不含易变的延迟/metadata。SUPPORTED 要有可定位支持证据；HALLUCINATED 表示人审确认虚构且有反证；CONTRADICTED 表示有证据反驳；UNRESOLVED 表示尚不能裁决。开放世界中“没搜到”不能标为虚构。无完整人工结果审核时 Evidence Coverage/Hallucination Rate 为 null；机器引用校验不能取代支持性审查。

结果与源文档均不得保存账号、真实资产秘密或凭据。新增来源保留原作者、许可、获取时间及投影说明；不执行 PoC。

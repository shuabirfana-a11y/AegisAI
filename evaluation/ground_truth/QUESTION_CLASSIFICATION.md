# 49 条候选问题分类与领取目录

阶段：Phase 13-C。以下只按原问题任务分类，没有填写答案；ID 中 affected、fixed、gap 等后缀不能作为标准答案。

候选来源：[AegisBench-v0.2.1-pilot manifest](../datasets/AegisBench-v0.2.1-pilot/manifest.json)，实际问题复用 [v0.2 questions.jsonl](../datasets/AegisBench-v0.2-pilot/questions.jsonl)。问题文件 SHA-256：
`f1f4be86e202ec263c6ebac66782b74d265840d706b559d913ab0c8c5f45e6f1`。

## 主分类与原 Runner 类别

| 人工主类型 | 中文 | 唯一题数 | 原 Runner category |
|---|---|---:|---|
| VULNERABILITY_FACTS | 漏洞事实查询 | 5 | facts |
| VERSION_IMPACT | 版本影响判断 | 17 | version |
| PATCH_ANALYSIS | Patch 分析 | 5 | poc_patch |
| POC_VERIFICATION | POC 核验 | 5 | poc_patch |
| ASSET_RISK | 资产风险分析 | 10 | risk |
| MULTIHOP_QA | 复杂多跳问答 | 7 | multihop |
| 合计 | 六类互斥主类型 | 49 | 原五类不变 |

5 道 release-and-poc 为复合题：主类型 POC_VERIFICATION，附加类型 PATCH_ANALYSIS。Patch 任务覆盖 10 题，但唯一题仍为 49，不计成 54。原类别分布保持 facts=5、version=17、poc_patch=10、risk=10、multihop=7；不修改问题或 Runner。

## 逐题分类

表中的问题与条件来自已冻结的问题输入。上下文仅做阅读摘要；标注时复制原 JSON 完整字段。单题版本/资产均为原题指定条件，不能据此推断答案。全部 risk/multihop（17 题）的评价目标为声明的 benchmark-reference-triage-v1 政策符合性，非生产资产专家风险标签。

| 序号 | question_id | 主类型 | 附加类型 | 原问题 | 关键输入（摘要） | 来源 ID |
|---:|---|---|---|---|---|---|
| 1 | GHSA-53q9-r3pm-6pq6-facts | VULNERABILITY_FACTS | — | 查询 CVE-2025-32434 的描述、CWE 和按版本区分的 CVSS。 | CVE-2025-32434；torch / PyPI | GHSA-53q9-r3pm-6pq6 |
| 2 | GHSA-53q9-r3pm-6pq6-affected | VERSION_IMPACT | — | torch 版本 2.5.1 是否受 CVE-2025-32434 影响？ | CVE-2025-32434；torch / PyPI；版本 2.5.1 | GHSA-53q9-r3pm-6pq6 |
| 3 | GHSA-53q9-r3pm-6pq6-fixed | VERSION_IMPACT | — | torch 版本 2.6.0 是否受 CVE-2025-32434 影响？ | CVE-2025-32434；torch / PyPI；版本 2.6.0 | GHSA-53q9-r3pm-6pq6 |
| 4 | GHSA-53q9-r3pm-6pq6-unknown | VERSION_IMPACT | — | torch 版本 未提供 是否受 CVE-2025-32434 影响？ | CVE-2025-32434；torch / PyPI；版本 未提供 | GHSA-53q9-r3pm-6pq6 |
| 5 | GHSA-53q9-r3pm-6pq6-release-and-poc | POC_VERIFICATION | PATCH_ANALYSIS | 按公告的修复版本记录判断 CVE-2025-32434 的 release fix；公开 PoC 是否经过独立验证？ | CVE-2025-32434；torch / PyPI | GHSA-53q9-r3pm-6pq6 |
| 6 | GHSA-53q9-r3pm-6pq6-commit-candidate | PATCH_ANALYSIS | — | 此链接仅出现在 CVE-2025-32434 的参考文献列表。没有代码验证记录时，能否认定为已验证补丁？ | CVE-2025-32434；torch / PyPI；参考链接见原问题 input_context.candidate_reference | GHSA-53q9-r3pm-6pq6 |
| 7 | GHSA-53q9-r3pm-6pq6-risk-affected | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2025-32434 的风险与优先级。 | demo-GHSA-53q9-r3pm-6pq6-affected: torch@2.5.1 | GHSA-53q9-r3pm-6pq6 |
| 8 | GHSA-53q9-r3pm-6pq6-risk-fixed | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2025-32434 的风险与优先级。 | demo-GHSA-53q9-r3pm-6pq6-fixed: torch@2.6.0 | GHSA-53q9-r3pm-6pq6 |
| 9 | GHSA-53q9-r3pm-6pq6-multihop | MULTIHOP_QA | — | 按 benchmark-reference-triage-v1 查询公告、比较版本并分析这两个演示资产，哪一个应优先处理？ | demo-GHSA-53q9-r3pm-6pq6-affected: torch@2.5.1；demo-GHSA-53q9-r3pm-6pq6-fixed: torch@2.6.0 | GHSA-53q9-r3pm-6pq6 |
| 10 | GHSA-47fc-vmwq-366v-facts | VULNERABILITY_FACTS | — | 查询 CVE-2022-45907 的描述、CWE 和按版本区分的 CVSS。 | CVE-2022-45907；torch / PyPI | GHSA-47fc-vmwq-366v |
| 11 | GHSA-47fc-vmwq-366v-affected | VERSION_IMPACT | — | torch 版本 1.13.0 是否受 CVE-2022-45907 影响？ | CVE-2022-45907；torch / PyPI；版本 1.13.0 | GHSA-47fc-vmwq-366v |
| 12 | GHSA-47fc-vmwq-366v-fixed | VERSION_IMPACT | — | torch 版本 1.13.1 是否受 CVE-2022-45907 影响？ | CVE-2022-45907；torch / PyPI；版本 1.13.1 | GHSA-47fc-vmwq-366v |
| 13 | GHSA-47fc-vmwq-366v-unknown | VERSION_IMPACT | — | torch 版本 未提供 是否受 CVE-2022-45907 影响？ | CVE-2022-45907；torch / PyPI；版本 未提供 | GHSA-47fc-vmwq-366v |
| 14 | GHSA-47fc-vmwq-366v-release-and-poc | POC_VERIFICATION | PATCH_ANALYSIS | 按公告的修复版本记录判断 CVE-2022-45907 的 release fix；公开 PoC 是否经过独立验证？ | CVE-2022-45907；torch / PyPI | GHSA-47fc-vmwq-366v |
| 15 | GHSA-47fc-vmwq-366v-commit-candidate | PATCH_ANALYSIS | — | 此链接仅出现在 CVE-2022-45907 的参考文献列表。没有代码验证记录时，能否认定为已验证补丁？ | CVE-2022-45907；torch / PyPI；参考链接见原问题 input_context.candidate_reference | GHSA-47fc-vmwq-366v |
| 16 | GHSA-47fc-vmwq-366v-risk-affected | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2022-45907 的风险与优先级。 | demo-GHSA-47fc-vmwq-366v-affected: torch@1.13.0 | GHSA-47fc-vmwq-366v |
| 17 | GHSA-47fc-vmwq-366v-risk-fixed | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2022-45907 的风险与优先级。 | demo-GHSA-47fc-vmwq-366v-fixed: torch@1.13.1 | GHSA-47fc-vmwq-366v |
| 18 | GHSA-47fc-vmwq-366v-multihop | MULTIHOP_QA | — | 按 benchmark-reference-triage-v1 查询公告、比较版本并分析这两个演示资产，哪一个应优先处理？ | demo-GHSA-47fc-vmwq-366v-affected: torch@1.13.0；demo-GHSA-47fc-vmwq-366v-fixed: torch@1.13.1 | GHSA-47fc-vmwq-366v |
| 19 | GHSA-c67j-w6g6-q2cm-facts | VULNERABILITY_FACTS | — | 查询 CVE-2025-68664 的描述、CWE 和按版本区分的 CVSS。 | CVE-2025-68664；langchain-core / PyPI | GHSA-c67j-w6g6-q2cm |
| 20 | GHSA-c67j-w6g6-q2cm-affected | VERSION_IMPACT | — | langchain-core 版本 1.2.0 是否受 CVE-2025-68664 影响？ | CVE-2025-68664；langchain-core / PyPI；版本 1.2.0 | GHSA-c67j-w6g6-q2cm |
| 21 | GHSA-c67j-w6g6-q2cm-fixed | VERSION_IMPACT | — | langchain-core 版本 1.2.5 是否受 CVE-2025-68664 影响？ | CVE-2025-68664；langchain-core / PyPI；版本 1.2.5 | GHSA-c67j-w6g6-q2cm |
| 22 | GHSA-c67j-w6g6-q2cm-unknown | VERSION_IMPACT | — | langchain-core 版本 未提供 是否受 CVE-2025-68664 影响？ | CVE-2025-68664；langchain-core / PyPI；版本 未提供 | GHSA-c67j-w6g6-q2cm |
| 23 | GHSA-c67j-w6g6-q2cm-release-and-poc | POC_VERIFICATION | PATCH_ANALYSIS | 按公告的修复版本记录判断 CVE-2025-68664 的 release fix；公开 PoC 是否经过独立验证？ | CVE-2025-68664；langchain-core / PyPI | GHSA-c67j-w6g6-q2cm |
| 24 | GHSA-c67j-w6g6-q2cm-commit-candidate | PATCH_ANALYSIS | — | 此链接仅出现在 CVE-2025-68664 的参考文献列表。没有代码验证记录时，能否认定为已验证补丁？ | CVE-2025-68664；langchain-core / PyPI；参考链接见原问题 input_context.candidate_reference | GHSA-c67j-w6g6-q2cm |
| 25 | GHSA-c67j-w6g6-q2cm-risk-affected | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2025-68664 的风险与优先级。 | demo-GHSA-c67j-w6g6-q2cm-affected: langchain-core@1.2.0 | GHSA-c67j-w6g6-q2cm |
| 26 | GHSA-c67j-w6g6-q2cm-risk-fixed | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2025-68664 的风险与优先级。 | demo-GHSA-c67j-w6g6-q2cm-fixed: langchain-core@1.2.5 | GHSA-c67j-w6g6-q2cm |
| 27 | GHSA-c67j-w6g6-q2cm-multihop | MULTIHOP_QA | — | 按 benchmark-reference-triage-v1 查询公告、比较版本并分析这两个演示资产，哪一个应优先处理？ | demo-GHSA-c67j-w6g6-q2cm-affected: langchain-core@1.2.0；demo-GHSA-c67j-w6g6-q2cm-fixed: langchain-core@1.2.5 | GHSA-c67j-w6g6-q2cm |
| 28 | GHSA-9rwj-6rc7-p77c-facts | VULNERABILITY_FACTS | — | 查询 CVE-2025-67644 的描述、CWE 和按版本区分的 CVSS。 | CVE-2025-67644；langgraph-checkpoint-sqlite / PyPI | GHSA-9rwj-6rc7-p77c |
| 29 | GHSA-9rwj-6rc7-p77c-affected | VERSION_IMPACT | — | langgraph-checkpoint-sqlite 版本 3.0.0 是否受 CVE-2025-67644 影响？ | CVE-2025-67644；langgraph-checkpoint-sqlite / PyPI；版本 3.0.0 | GHSA-9rwj-6rc7-p77c |
| 30 | GHSA-9rwj-6rc7-p77c-fixed | VERSION_IMPACT | — | langgraph-checkpoint-sqlite 版本 3.0.1 是否受 CVE-2025-67644 影响？ | CVE-2025-67644；langgraph-checkpoint-sqlite / PyPI；版本 3.0.1 | GHSA-9rwj-6rc7-p77c |
| 31 | GHSA-9rwj-6rc7-p77c-unknown | VERSION_IMPACT | — | langgraph-checkpoint-sqlite 版本 未提供 是否受 CVE-2025-67644 影响？ | CVE-2025-67644；langgraph-checkpoint-sqlite / PyPI；版本 未提供 | GHSA-9rwj-6rc7-p77c |
| 32 | GHSA-9rwj-6rc7-p77c-release-and-poc | POC_VERIFICATION | PATCH_ANALYSIS | 按公告的修复版本记录判断 CVE-2025-67644 的 release fix；公开 PoC 是否经过独立验证？ | CVE-2025-67644；langgraph-checkpoint-sqlite / PyPI | GHSA-9rwj-6rc7-p77c |
| 33 | GHSA-9rwj-6rc7-p77c-commit-candidate | PATCH_ANALYSIS | — | 此链接仅出现在 CVE-2025-67644 的参考文献列表。没有代码验证记录时，能否认定为已验证补丁？ | CVE-2025-67644；langgraph-checkpoint-sqlite / PyPI；参考链接见原问题 input_context.candidate_reference | GHSA-9rwj-6rc7-p77c |
| 34 | GHSA-9rwj-6rc7-p77c-risk-affected | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2025-67644 的风险与优先级。 | demo-GHSA-9rwj-6rc7-p77c-affected: langgraph-checkpoint-sqlite@3.0.0 | GHSA-9rwj-6rc7-p77c |
| 35 | GHSA-9rwj-6rc7-p77c-risk-fixed | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2025-67644 的风险与优先级。 | demo-GHSA-9rwj-6rc7-p77c-fixed: langgraph-checkpoint-sqlite@3.0.1 | GHSA-9rwj-6rc7-p77c |
| 36 | GHSA-9rwj-6rc7-p77c-multihop | MULTIHOP_QA | — | 按 benchmark-reference-triage-v1 查询公告、比较版本并分析这两个演示资产，哪一个应优先处理？ | demo-GHSA-9rwj-6rc7-p77c-affected: langgraph-checkpoint-sqlite@3.0.0；demo-GHSA-9rwj-6rc7-p77c-fixed: langgraph-checkpoint-sqlite@3.0.1 | GHSA-9rwj-6rc7-p77c |
| 37 | GHSA-935w-9g4m-p28p-facts | VULNERABILITY_FACTS | — | 查询 CVE-2026-105752 的描述、CWE 和按版本区分的 CVSS。 | CVE-2026-105752；vllm / PyPI | GHSA-935w-9g4m-p28p |
| 38 | GHSA-935w-9g4m-p28p-affected | VERSION_IMPACT | — | vllm 版本 0.29.0 是否受 CVE-2026-105752 影响？ | CVE-2026-105752；vllm / PyPI；版本 0.29.0 | GHSA-935w-9g4m-p28p |
| 39 | GHSA-935w-9g4m-p28p-fixed | VERSION_IMPACT | — | vllm 版本 0.30.0 是否受 CVE-2026-105752 影响？ | CVE-2026-105752；vllm / PyPI；版本 0.30.0 | GHSA-935w-9g4m-p28p |
| 40 | GHSA-935w-9g4m-p28p-unknown | VERSION_IMPACT | — | vllm 版本 未提供 是否受 CVE-2026-105752 影响？ | CVE-2026-105752；vllm / PyPI；版本 未提供 | GHSA-935w-9g4m-p28p |
| 41 | GHSA-935w-9g4m-p28p-release-and-poc | POC_VERIFICATION | PATCH_ANALYSIS | 按公告的修复版本记录判断 CVE-2026-105752 的 release fix；公开 PoC 是否经过独立验证？ | CVE-2026-105752；vllm / PyPI | GHSA-935w-9g4m-p28p |
| 42 | GHSA-935w-9g4m-p28p-commit-candidate | PATCH_ANALYSIS | — | 此链接仅出现在 CVE-2026-105752 的参考文献列表。没有代码验证记录时，能否认定为已验证补丁？ | CVE-2026-105752；vllm / PyPI；参考链接见原问题 input_context.candidate_reference | GHSA-935w-9g4m-p28p |
| 43 | GHSA-935w-9g4m-p28p-risk-affected | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2026-105752 的风险与优先级。 | demo-GHSA-935w-9g4m-p28p-affected: vllm@0.29.0 | GHSA-935w-9g4m-p28p |
| 44 | GHSA-935w-9g4m-p28p-risk-fixed | ASSET_RISK | — | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2026-105752 的风险与优先级。 | demo-GHSA-935w-9g4m-p28p-fixed: vllm@0.30.0 | GHSA-935w-9g4m-p28p |
| 45 | GHSA-935w-9g4m-p28p-multihop | MULTIHOP_QA | — | 按 benchmark-reference-triage-v1 查询公告、比较版本并分析这两个演示资产，哪一个应优先处理？ | demo-GHSA-935w-9g4m-p28p-affected: vllm@0.29.0；demo-GHSA-935w-9g4m-p28p-fixed: vllm@0.30.0 | GHSA-935w-9g4m-p28p |
| 46 | GHSA-c67j-w6g6-q2cm-gap | VERSION_IMPACT | — | langchain-core 0.4.0 是否命中 CVE-2025-68664 的任意影响区间？ | CVE-2025-68664；langchain-core / PyPI；版本 0.4.0 | GHSA-c67j-w6g6-q2cm |
| 47 | GHSA-c67j-w6g6-q2cm-older-fix | VERSION_IMPACT | — | langchain-core 0.3.81 是否命中 CVE-2025-68664 的任意影响区间？ | CVE-2025-68664；langchain-core / PyPI；版本 0.3.81 | GHSA-c67j-w6g6-q2cm |
| 48 | cross-advisory-priorities | MULTIHOP_QA | — | 结合多份公告，按 benchmark-reference-triage-v1 找出须优先处理的演示资产，版本未知者应弃答。 | demo-GHSA-53q9-r3pm-6pq6-cross: torch@2.5.1；demo-GHSA-c67j-w6g6-q2cm-cross: langchain-core@1.2.0；demo-GHSA-9rwj-6rc7-p77c-cross: langgraph-checkpoint-sqlite@未提供版本 | GHSA-53q9-r3pm-6pq6, GHSA-c67j-w6g6-q2cm, GHSA-9rwj-6rc7-p77c |
| 49 | cross-advisory-missing-version | MULTIHOP_QA | — | 这些 AI 组件的部署版本均缺失。能够确认资产不受影响吗？ | demo-GHSA-53q9-r3pm-6pq6-missing: torch@未提供版本；demo-GHSA-c67j-w6g6-q2cm-missing: langchain-core@未提供版本；demo-GHSA-9rwj-6rc7-p77c-missing: langgraph-checkpoint-sqlite@未提供版本 | GHSA-53q9-r3pm-6pq6, GHSA-c67j-w6g6-q2cm, GHSA-9rwj-6rc7-p77c |

## 调查覆盖与批次安排

- 按公告簇领取，先做每簇 facts/version，再复查 Patch/POC，最后政策风险与多跳。这里是推荐顺序，不是人员分配。
- 五个公告簇各有 9 个基础问题，另有 langchain-core 的 2 个版本边界题和 2 个跨公告题。跨公告题要由能查看完整来源的成员独立完成，不能只拼各人的最终答案。
- 首批建议每簇各取 1 个事实/边界样本由两人试标，发现规范歧义后修订规范、重新复核；本阶段未开始试标。
- 全部未分配状态见 [GROUND_TRUTH_PROGRESS.md](GROUND_TRUTH_PROGRESS.md)。人员只由团队真实领取后登记。
- 当前候选缺少已有独立验证材料支撑的 VERIFIED_EXPLOIT 正类，也不足以构成独立 holdout；后续扩充真实来源，不能人为补一个正答案。
- 本表主类型是组织标注用标签，不能偷偷拆改 frozen ID/category 或把 SOURCE_REFERENCE 变成人工 gold。

## 原始来源目录

下列链接指向已有冻结资料，不代表本阶段已经人工查源或批准其中结论。

| 来源 ID | 冻结来源投影 |
|---|---|
| GHSA-53q9-r3pm-6pq6 | [查看冻结来源](../datasets/AegisBench-v0.2-pilot/sources/GHSA-53q9-r3pm-6pq6.json) |
| GHSA-47fc-vmwq-366v | [查看冻结来源](../datasets/AegisBench-v0.2-pilot/sources/GHSA-47fc-vmwq-366v.json) |
| GHSA-c67j-w6g6-q2cm | [查看冻结来源](../datasets/AegisBench-v0.2-pilot/sources/GHSA-c67j-w6g6-q2cm.json) |
| GHSA-9rwj-6rc7-p77c | [查看冻结来源](../datasets/AegisBench-v0.2-pilot/sources/GHSA-9rwj-6rc7-p77c.json) |
| GHSA-935w-9g4m-p28p | [查看冻结来源](../datasets/AegisBench-v0.2-pilot/sources/GHSA-935w-9g4m-p28p.json) |

标注方法、六类判定依据、Unknown 保留和复核规则见 [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md)。

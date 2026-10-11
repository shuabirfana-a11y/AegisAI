# AegisBench Ground Truth 人工标注进度

台账创建日期：2026-10-11（Asia/Shanghai）。这里只记录流程建设完成后的真实状态；日期不是任何人的标注/审核时间。

本文件是唯一进度台账；[progress.md](progress.md) 仅为入口。候选版本 AegisBench-v0.2.1-pilot；问题 SHA-256：
`f1f4be86e202ec263c6ebac66782b74d265840d706b559d913ab0c8c5f45e6f1`。

## 当前总览

| 项目 | 数量 |
|---|---:|
| 唯一候选题 | 49 |
| 领取未分配 UNASSIGNED | 49 |
| 已领取 ASSIGNED | 0 |
| 尚未完成记录 NOT_STARTED | 49 |
| 人工 DRAFT | 0 |
| REVIEWING | 0 |
| APPROVED | 0 |
| REJECTED | 0 |
| 人工批准覆盖率 | 0/49（0%） |
| READY_FOR_RUNNER | 0 |
| 已冻结 HUMAN_GOLD | 0 |

DRAFT 指人实际填写完成，机器参考答案、空表和目录占位文件均不计数。NOT_STARTED + 四个人工状态的最新有效记录数 = 49；领取状态另计，不把两个维度相加。即使批准 UNKNOWN，仍可计为 APPROVED；正式可运行准入另行检查，不能把 APPROVED 自动算成已评测。

## 六类进度

| 主类型 | 候选 | 未分配 | NOT_STARTED | DRAFT | REVIEWING | APPROVED | REJECTED |
|---|---:|---:|---:|---:|---:|---:|---:|
| VULNERABILITY_FACTS | 5 | 5 | 5 | 0 | 0 | 0 | 0 |
| VERSION_IMPACT | 17 | 17 | 17 | 0 | 0 | 0 | 0 |
| PATCH_ANALYSIS | 5 | 5 | 5 | 0 | 0 | 0 | 0 |
| POC_VERIFICATION | 5 | 5 | 5 | 0 | 0 | 0 | 0 |
| ASSET_RISK | 10 | 10 | 10 | 0 | 0 | 0 | 0 |
| MULTIHOP_QA | 7 | 7 | 7 | 0 | 0 | 0 | 0 |
| 合计 | 49 | 49 | 49 | 0 | 0 | 0 | 0 |

POC/Patch 复合题只有一条台账记录；六类详见 [QUESTION_CLASSIFICATION.md](QUESTION_CLASSIFICATION.md)。

## 领取与状态记录

初始领取状态为 UNASSIGNED、流程状态为 NOT_STARTED。`—` 表示实际人员、审核、修订和文件均尚未产生，不能填示例人名后算作已领取。领取后登记真实人员并改为 ASSIGNED；填写尚未完成时仍为 NOT_STARTED，注明“已领取，填写中”，不伪造 DRAFT 完成。两个状态维度分别汇总。

| 序号 | question_id | 主类型 | 领取状态 | 流程状态 | 标注人 | 复核人 | 修订 | 当前人工记录 | 导出状态 | 阻塞/说明 |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | GHSA-53q9-r3pm-6pq6-facts | VULNERABILITY_FACTS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 2 | GHSA-53q9-r3pm-6pq6-affected | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 3 | GHSA-53q9-r3pm-6pq6-fixed | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 4 | GHSA-53q9-r3pm-6pq6-unknown | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 5 | GHSA-53q9-r3pm-6pq6-release-and-poc | POC_VERIFICATION | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 6 | GHSA-53q9-r3pm-6pq6-commit-candidate | PATCH_ANALYSIS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 7 | GHSA-53q9-r3pm-6pq6-risk-affected | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 8 | GHSA-53q9-r3pm-6pq6-risk-fixed | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 9 | GHSA-53q9-r3pm-6pq6-multihop | MULTIHOP_QA | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 10 | GHSA-47fc-vmwq-366v-facts | VULNERABILITY_FACTS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 11 | GHSA-47fc-vmwq-366v-affected | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 12 | GHSA-47fc-vmwq-366v-fixed | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 13 | GHSA-47fc-vmwq-366v-unknown | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 14 | GHSA-47fc-vmwq-366v-release-and-poc | POC_VERIFICATION | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 15 | GHSA-47fc-vmwq-366v-commit-candidate | PATCH_ANALYSIS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 16 | GHSA-47fc-vmwq-366v-risk-affected | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 17 | GHSA-47fc-vmwq-366v-risk-fixed | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 18 | GHSA-47fc-vmwq-366v-multihop | MULTIHOP_QA | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 19 | GHSA-c67j-w6g6-q2cm-facts | VULNERABILITY_FACTS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 20 | GHSA-c67j-w6g6-q2cm-affected | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 21 | GHSA-c67j-w6g6-q2cm-fixed | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 22 | GHSA-c67j-w6g6-q2cm-unknown | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 23 | GHSA-c67j-w6g6-q2cm-release-and-poc | POC_VERIFICATION | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 24 | GHSA-c67j-w6g6-q2cm-commit-candidate | PATCH_ANALYSIS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 25 | GHSA-c67j-w6g6-q2cm-risk-affected | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 26 | GHSA-c67j-w6g6-q2cm-risk-fixed | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 27 | GHSA-c67j-w6g6-q2cm-multihop | MULTIHOP_QA | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 28 | GHSA-9rwj-6rc7-p77c-facts | VULNERABILITY_FACTS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 29 | GHSA-9rwj-6rc7-p77c-affected | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 30 | GHSA-9rwj-6rc7-p77c-fixed | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 31 | GHSA-9rwj-6rc7-p77c-unknown | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 32 | GHSA-9rwj-6rc7-p77c-release-and-poc | POC_VERIFICATION | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 33 | GHSA-9rwj-6rc7-p77c-commit-candidate | PATCH_ANALYSIS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 34 | GHSA-9rwj-6rc7-p77c-risk-affected | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 35 | GHSA-9rwj-6rc7-p77c-risk-fixed | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 36 | GHSA-9rwj-6rc7-p77c-multihop | MULTIHOP_QA | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 37 | GHSA-935w-9g4m-p28p-facts | VULNERABILITY_FACTS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 38 | GHSA-935w-9g4m-p28p-affected | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 39 | GHSA-935w-9g4m-p28p-fixed | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 40 | GHSA-935w-9g4m-p28p-unknown | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 41 | GHSA-935w-9g4m-p28p-release-and-poc | POC_VERIFICATION | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 42 | GHSA-935w-9g4m-p28p-commit-candidate | PATCH_ANALYSIS | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 43 | GHSA-935w-9g4m-p28p-risk-affected | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 44 | GHSA-935w-9g4m-p28p-risk-fixed | ASSET_RISK | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 45 | GHSA-935w-9g4m-p28p-multihop | MULTIHOP_QA | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 46 | GHSA-c67j-w6g6-q2cm-gap | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 47 | GHSA-c67j-w6g6-q2cm-older-fix | VERSION_IMPACT | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 48 | cross-advisory-priorities | MULTIHOP_QA | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |
| 49 | cross-advisory-missing-version | MULTIHOP_QA | UNASSIGNED | NOT_STARTED | — | — | — | — | NOT_PREPARED | 待真实成员领取与查源 |

## 更新规则

1. 领取时改为 ASSIGNED，并登记两个可追溯、不同自然人的团队 ID；同人换账号不算第二人。没有复核人则记录缺口，不自动批准。
2. 实际标注完成后记录 DRAFT、修订号、真实路径和时间；送审锁定内容哈希后改 REVIEWING。
3. 复核人按规范批准或退回；管理员核对目录、reviewed_content_sha256、最新有效修订和上表汇总，不删除退回及旧批准历史。
4. 题目只有一个 active 修订；存在冲突版本时导出阻塞。修改已批准内容需新修订、重新复核，不能直接覆盖。
5. READY_FOR_RUNNER、正式 HUMAN_GOLD 与模型实验分别记录；模板形状通过不证明证据正确。

当前阻塞：尚无人工独立调查/复核；没有填写任何标准答案。Phase 13-C 到此完成流程设施后停止，Phase 13-D 才开始人工执行及冻结。

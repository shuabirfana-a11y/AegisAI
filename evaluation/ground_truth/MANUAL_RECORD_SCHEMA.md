# 人工 Ground Truth 记录 Schema 与原评测契约映射

本文件定义独立的人工审查表单。结构文件为 [ground_truth_workflow.schema.json](ground_truth_workflow.schema.json)，空表为 [ground_truth_template.json](ground_truth_template.json)。原 `evaluation.bench.schema.Annotation`、Runner 与导出契约不修改；人工表单尚未提供自动导入。

## 1. 记录字段

| 字段 | 类型 | 说明 |
|---|---|---|
| schema_version | string | aegisbench-ground-truth-workflow-v1 |
| record_kind | BLANK_TEMPLATE / HUMAN_RECORD | 空表不计进度、不进入标准答案；只有人实际填写后才用 HUMAN_RECORD |
| id / question | string | 冻结候选原 ID、原问题；必须保持一致 |
| type | 六类枚举 / null | VULNERABILITY_FACTS、VERSION_IMPACT、PATCH_ANALYSIS、POC_VERIFICATION、ASSET_RISK、MULTIHOP_QA；空表为 null |
| additional_types | string[] | 复合题标签，不能再计一条样本 |
| category | facts / version / poc_patch / risk / multihop / null | 原 Runner 分类不改 |
| input_context | object | 原题目上下文；不可加入答案、should_abstain、required_hops 或审核标签 |
| dataset_version | string | 实际冻结问题版本，本批 AegisBench-v0.2.1-pilot |
| dataset_questions_sha256 / question_sha256 | SHA-256 / null | 完整问题文件与该问题规范 JSON 的哈希 |
| origin / source_ids | string / string[] | 原题 origin 与冻结来源 ID；不得把 TEST_FIXTURE 改成真实问题 |
| evaluation_profile | POLICY_CONFORMANCE / CONTEXTUAL_ASSET_RISK / FACTUAL / null | 当前风险相关题只能按声明政策或另建新题，禁止跨政策声称准确率 |
| expected_answer | object | 人独立填写的结构化标准答案，空模板为 {} |
| judgments | object[] | 原子判断：judgment_id、answer_path、decision、evidence_ids、rationale、missing_information；answer_path 定位 expected_answer 字段 |
| evidence | object[] | 第 2 节规定的来源记录；空模板占位证据的所有内容为空，不是实际来源 |
| evaluation.confidence | HIGH / MEDIUM / LOW / UNKNOWN / null | 人基于证据直接性与冲突给出，不能由源等级自动计算 |
| evaluation.should_abstain | boolean / null | 由人逐题判断；部分已知/部分未知可为 true，保留已知字段 |
| evaluation.required_hops | string[] | 人确定必要步骤；沿用 vulnerability/version/asset/risk 等已有步骤名称，其他名称先确认适配 |
| evaluation.scored_fields / supplementary_fields | string[] | 哪些答案字段评分、哪些仅补充；旧 Runner 对 expected_answer 的全部键评分，投影时必须显式拆分 |
| evaluation.export_status | NOT_PREPARED / EXPORT_BLOCKED / READY_FOR_RUNNER | 独立于人工 APPROVED；本阶段统一 NOT_PREPARED，不产生导出 |
| evaluation.export_notes | string | 映射/范围/评分政策或阻塞原因 |
| uncertainties | string[] | 缺资料、冲突、歧义、未确认前提与需要补查事项 |
| ai_assistance | object | used、tool、version、used_at、scope、human_source_checks；诚实记录，禁用 AI 冒充人 |
| content_sha256 | SHA-256 / null | 当前送审内容哈希，算法见第 5 节 |
| annotation | object | 第 3 节规定的独立人工身份、状态和签署 |
| history | object[] | revision、from_status、to_status、actor、at、content_sha256、reason、record_path；按事件追加，不改旧审核 |

HUMAN_RECORD 要有非空 ID/问题/版本/上下文依据、主类型、原分类和来源，expected_answer 非空、可用证据和 judgement。APPROVED 对未知结论也有效，只要缺口和依据合格。JSON Schema 检查形状，不验证人的真实性、原文支持或身份独立，这些必须按规范人工审核。

## 2. Evidence 字段

| 字段 | 类型 | 语义 |
|---|---|---|
| evidence_id | string | 记录内唯一，用于 judgment 关联 |
| source_name / source_id | string | 实际发布者/资料名称，以及冻结 manifest 目录 ID |
| url | string | 实际来源 HTTPS URL，不能是凭据链接；必须与相应 manifest 来源一致 |
| quote | string | 可核对的原文，标注前后文，不让模型改写冒充引文 |
| locator | string | 现有资料使用非空、以 / 开头的 RFC 6901 JSON Pointer；原契约不接受根节点的空指针。新增公告定位需后续登记并冻结 |
| canonical_excerpt | string | 定位值的规范 JSON；用于原 Runner 的 EvidenceReference.excerpt |
| snapshot_sha256 | SHA-256 | 对应冻结源文件的字节哈希 |
| authority_level | L1_OFFICIAL / L2_RESEARCH / L3_SECONDARY | 按实际发布者和来源链判断，不直接决定结论 |
| published_time / retrieved_time | RFC 3339 / null | 发布时间可未知，但必须有 time_note；获取时间与发布时间分开 |
| time_note | string | 缺时间、网页更新或时序冲突说明 |
| role | SUPPORTING / CONTRADICTING / CONTEXTUAL | 支持当前结论、反证或上下文，不把仅相关资料当直接支持 |
| judgment_ids | string[] | 关联实际 judgement；证据和判断双向核对 |

未在原 manifest 中的合法新来源不编造成旧 source_id。后续用新版本冻结目录登记，再制作 Runner 引用。空模板占位证据必须实际填写或替换，不能进入 HUMAN_RECORD。

## 3. Annotation 字段与批准要求

`annotator / reviewer` 为可追溯真实团队 ID；类型分别为 HUMAN，不能自动填名字。`annotated_at / review_started_at / reviewed_at` 为实际发生的 RFC 3339 时间；`status` 为 DRAFT、REVIEWING、APPROVED、REJECTED。`revision` 从 1 递增；`reviewed_content_sha256` 绑定当前审核内容；`annotation_note / review_note / rejection_reason` 保存查源、独立复核和退回依据。

`annotator_confirmed_source_check / reviewer_confirmed_source_check` 只有对应人实际查源后才改成 true。`review_checklist` 逐条由复核人勾选；APPROVED 要满足全部项。姓名和类型字段不是身份认证，管理员仍须核对真实参与和不同自然人。复核人不能确认自己的标注。

## 4. 人工枚举到既有 Runner 的白名单投影

| 人工判断 | 原评分字段/枚举 | 保留事项 |
|---|---|---|
| AFFECTED / NOT_AFFECTED | affected 同名枚举 | 精确版本、生态、分支与条件留在人工记录 |
| INSUFFICIENT_EVIDENCE / UNKNOWN | affected=UNKNOWN | 原人工标签与缺口原文不丢；不能改成 NOT_AFFECTED |
| POC_CANDIDATE / VERIFIED_EXPLOIT | poc_status 同名枚举 | VERIFIED_EXPLOIT 必须有独立合法验证材料 |
| NO_EVIDENCE / INSUFFICIENT_EVIDENCE | poc_status=UNKNOWN | 仅表示调查证据不足，不表达不存在利用代码 |
| PATCH_CANDIDATE / CONFIRMED_FIX | patch_status 同名枚举 | release 与 commit 的确认范围分别记录 |
| NO_EVIDENCE / INSUFFICIENT_EVIDENCE | patch_status=UNKNOWN | 不等于确认未修复 |
| 人工流程 DRAFT / REVIEWING | 不进入准入；若作待审投影只能 PENDING | 不使用 HUMAN_GOLD 伪装待审数据 |
| 人工流程 APPROVED | review_status=APPROVED | 双人实际确认、证据/哈希/字段范围通过后才可 origin=HUMAN_GOLD |
| 人工流程 REJECTED | 不导出到正式 gold | 退回与历史保留 |

兼容 Annotation 仅含原契约允许的 `id / expected_answer / evidence_refs / confidence / review_status / annotator_type / reviewer_type / annotator / reviewer / annotation_note / should_abstain / origin / required_hops`。不把整个人工表单直接喂给 Runner；它的严格 Pydantic 会拒绝未知外层字段。

导出时复制 id；expected_answer 仅含人审核通过且声明评分的字段。版本判断用 affected，PoC 用 poc_status，Patch 用 patch_status；更详细的影响/修复/措施等保留为补充，除非问题及评分范围已经明确包含。每条实际来源映射到 `evidence_refs: {source_id, locator, excerpt}`，excerpt 使用 canonical_excerpt，不使用人类 prose quote。confidence、should_abstain、required_hops 来自 evaluation，身份与状态来自实际人工 annotation。annotation_note 汇总人工原标签、版本、内容哈希和查源/复核依据，以便追溯。

本阶段仅提供规范，没有自动投影/导入程序。Phase 13-D 先核对输出 Annotation 的字段/枚举、官方资料、双人真实性、目录哈希和原 `annotation_exclusion`，再封存。风险政策、未知新增标签或待适配的步骤名称无法一致时用 EXPORT_BLOCKED，不擅自改 Runner。人审 APPROVED 不自动等于 READY_FOR_RUNNER。

## 5. 哈希、修订和模板校验

`question_sha256` 对原问题完整 JSON 作 UTF-8、ensure_ascii=false、键排序、紧凑分隔、禁止 NaN 的规范序列化后计算 SHA-256。`dataset_questions_sha256` 是整个原问题文件字节哈希，二者用途不同。

`content_sha256` 对人工表单移除 **content_sha256、annotation、history** 后的全部内容作上述规范 JSON，再算 SHA-256。身份、时间和审核事件可追加；任何答案/来源/输入/评分目标变化都会改变内容哈希。`reviewed_content_sha256` 必须等于当前 content_sha256；annotation_note 不能替代哈希绑定。修订号、真实双人身份和记录来源仍由管理员核对。

后续管理员的导出状态更新优先写在进度台账及新冻结版本的导出清单，保留已批准原件。若更新原表内 evaluation.export_status/export_notes，也会改变内容哈希，必须作为新修订重新复核，不能覆盖原审批绑定。

空模板合法而不属于已标注样本：record_kind=BLANK_TEMPLATE，身份/状态/哈希/结论未填写，expected_answer={}。JSON Schema 明确允许这一模式，同时对 HUMAN_RECORD 强化非空/时间/哈希和审核结构约束。结构验收可离线进行，不涉及调用 Evaluation Runner、Agent、模型或数据写入。

领取中的工作副本可保留 BLANK_TEMPLATE 或未完成的本地草稿，但在完整填写前不宣称它通过正式 HUMAN_RECORD 结构校验，也不计作 DRAFT 完成。模板用严格空表模式验证；编辑中记录允许暂时不通过，团队不能为了消除编辑器提示伪填答案或确认人。

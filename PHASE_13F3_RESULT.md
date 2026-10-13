# AegisAI Phase 13-F.3：问题归一化与 Planner 任务模板适配结果

本阶段已实现归一化和四类任务模板，并完成限定 5 题真实 HTTP 验证。结果为 **PARTIAL_NOT_READY**：4 题进入完整调查链，未知版本题仍在 Planner 被原 Validation 拒绝。未达到“5 题全部进入链路”的实验恢复条件；不运行 39 题、不继续调模型或提示词。

## 1. 根因与范围

原 35 题失败不能全部归因于输入不全。Phase 13-F.2 的逐题记录区分了原调用错误、缺失输入和模型计划问题；本次直接复用其分类，保存在 `evaluation/planner_failure_analysis/phase13f2/`。

F.2 的实际模型文本还显示：重复 JSON type 键、证据工具放入漏洞角色、重复 get_vulnerability 根 Artifact，以及未知版本没有形成正确 input_required。原 Validation/Gate 拒绝这些计划是正确行为。

本次只改字面输入适配、Planner adapter 的输入描述、通用模板/提示 v6 和模型侧 Schema。模型仍生成实际计划，原 strict_json、Pydantic、任务/工具白名单、Validation、Runtime、Agent、Risk/Gate 均未降低标准。

## 2. Question Normalizer

新增 `backend/app/agents/investigation/normalization.py`，版本 question-normalizer-v1。

输出 objective、vulnerability_id、targets、component、version、asset_context、task_type、input_status、missing_fields、warnings、provenance。状态为 READY / INPUT_REQUIRED / AMBIGUOUS；明确缺失保留 null，不从公告范围、修复版本或 CVSS 猜部署版本。

Evaluation Request Builder 只读取原问题、原 input_context 和真实资产绑定。Backend adapter 只描述已冻结 Scope，关闭再次字面提取，避免新目标越过旧 Validator 的范围。冲突输入拒绝，多组件/多版本不悄悄任选一个。

本轮 4 个资产是中性随机名称的受控演示库存，来源为 OWNER_INVENTORY_NOT_SCANNED，不是企业扫描结果。没有填入人工答案、复核状态或题号类别提示。

## 3. 四类模板与模型 Schema

| 意图 | 模板 | 关键约束 |
|---|---|---|
| 漏洞事实 | vulnerability-fact-v1 | 单目标一个漏洞根查询；Claim/Evidence 使用独立 evidence_search |
| 版本影响 | version-impact-v1 | 版本检查与漏洞查询在同一根任务，资产独立查询 |
| 资产风险 | asset-risk-v1 | 使用真实绑定资产和已有版本；Verification/Risk/Gate 仍是后续服务器阶段 |
| 冲突证据 | evidence-conflict-v1 | 保留分歧，由后续核验裁决；不从人工分类标签选模板 |

模板只提供描述和现有角色，不生成 Runtime TaskContract。提示 v6 的通用 wire-format 示例区分 type/task_type，禁止重复键、猜版本、创建资产。

动态模型 Schema 将每个 Task 字段定义一次，引用现有注册工具的输入，约束角色工具和每目标根查询唯一。input_required 只允许当前 Scope 真正需要且缺失的字段，事实题不会误要求部署版本。原 Validation 不改；这也意味着模型遗漏必要任务时仍会失败。

## 4. 冻结环境与隔离

- 仓库：shuabirfana-a11y/AegisAI；分支 codex/phase13f3-normalization-templates。
- 基线：68efb25a9f09a1facd2ac254505d1a21011b9e0d；冻结实现：e28c75b5fba414e0600c6405202d7559dbb8dded。
- 数据集：AegisBench-v0.3-human39-20261013，39 APPROVED / 49 候选；仅取同样 5 个诊断问题，未比较人工答案。
- manifest SHA256：0651efb54fdfe12c6c05493429dac4f73d309bb51f6297b7f66da71f84552002。
- annotations SHA256：6fb41da340507b191c60b1096d85242b85a67818af1c3ba51bc4fbf876ceda83。
- 原模型：OpenAI Compatible，本地 aegisai-qwen25-planner:latest（Qwen2.5）；manifest digest sha256:15aaf3fda3b8e9bb6724e5e9911eec3b9cbdb6bd967646b6bf49ee9846b7ec16。
- temperature 0、timeout 40 秒、max_output_tokens 4096、structured_mode json_object；原模型参数未改。
- Prompt：investigation-plan-v6；Answer 仍为确定性模板，未新增答案生成模型调用。
- 沿用原诊断 profile 的 Mock Embedding 配置；实际 Planner 模型调用标记 REAL，不能描述成整套向量配置全部换为真实模型。
- 使用新隔离源数据副本和 4 个中性演示资产；保留旧实验、旧数据库、失败记录。558 个金标/历史结果/核心规则文件 SHA256 检查无变化，详见 docs/phase13f3/PROTECTED_HASHES.json。

## 5. 五题真实结果

每题只创建一次调查；Planner 自身原有最多两次尝试保留。执行时间为 2026-10-13 22:31 起（北京时间）。共 5 个 HTTP 调查、6 次真实 Planner 模型调用，没有第 6 个调查。

| 场景 / 原题 ID | 归一化 | Planner | Gate | AnswerEnvelope |
|---|---|---|---|---|
| 漏洞事实 / GHSA-53q9-r3pm-6pq6-facts | READY；CVE-2025-32434；无部署版本 | VALIDATED，1 次 | PASS_WITH_WARNINGS | COMPLETE_WITH_WARNINGS |
| 版本影响 / GHSA-935w-9g4m-p28p-affected | READY；vllm 0.29.0；真实演示资产绑定 | VALIDATED，1 次 | REPLAN_REQUIRED | INCOMPLETE |
| 资产风险 / GHSA-53q9-r3pm-6pq6-risk-affected | READY；torch 2.5.1；真实演示资产绑定 | VALIDATED，1 次 | REPLAN_REQUIRED | INCOMPLETE |
| 来源冲突 / GHSA-c67j-w6g6-q2cm-affected | READY；langchain-core 1.2.0；原问题没有写“冲突” | VALIDATED，1 次 | HUMAN_REVIEW_REQUIRED | REVIEW_REQUIRED |
| 未知版本 / GHSA-53q9-r3pm-6pq6-unknown | INPUT_REQUIRED；torch；version=null，missing_fields=[version] | PLANNING_FAILED，2 次 | NOT_REACHED | FAILED |

4 个合法计划均有 Runtime Run、Investigation / Verification / Risk Artifact、Integration Result 和已保存 AnswerEnvelope。Verification/Risk 有 partial/WAITING_REVIEW，不能把“有 Artifact”说成“风险已确认”。读取/传输层 SUCCEEDED 也不是答案准确。

本轮 6 个原始模型文本都能通过 strict_json，未再出现重复键拒绝。未知题第一次输出包含未来占位 `<version>` 的工具调用，被作用域 Schema 拒绝；第二次删掉占位调用，却连必须的 ask-version input_required 任务一起遗漏，原 Validator 返回 VERSION_INPUT_REQUIRED。未补造该任务、猜版本或用 Mock 兜底。

## 6. Gate 阻断和冲突交接

版本/风险题不再缺 Planner 或根 Artifact。已有版本观察和影响证据进入核验，但 Verification 仍 PENDING，风险 UNKNOWN。Gate 保留 REQUIRED_TASK_INCOMPLETE、OBJECTIVE_NOT_COVERED、UNRESOLVED_ANALYSIS；包括缺少明确修复版本、来源证据不够独立和部分影响 Claim 未确认。

langchain-core 的实际调查 Artifact 为 CONFLICT，证据保存在 Artifact；已生成 Verification Artifact，状态 CONFLICT，记录来源 Claim/Evidence 引用。Gate 明确记录 CRITICAL_EVIDENCE_CONFLICT，要求人工复核，不是仅留下冲突文字或缺失 Verification Artifact。

该题原问题仍是版本影响题，实际选中 version-impact-v1；冲突由执行后的源数据发现。没有通过人工题号/答案给 Planner 偷渡“应出现冲突”。这证明冲突交接能走到 Gate，不证明每个源分歧都已人工裁定。

## 7. 关键追踪 ID

| 场景 | HTTP Investigation ID | Runtime Run ID | Integration ID |
|---|---|---|---|
| 事实 | 79fb2088-2c35-48ee-b953-a9fba7ed2852 | e4b46e29-2443-4ee4-83d0-86a70de3aae1 | eaca8d88-527c-4055-97ee-aa82fff60ee1 |
| 版本 | 60bae506-fe8e-40fb-b4c4-ef3489e913c7 | 99846096-595f-47ad-ab45-4441aa2fc417 | 61085169-64d4-4f14-beaf-caf2d61e1e64 |
| 风险 | e5ba5154-f448-4a43-b474-806f252c09a0 | 49e518b9-5ead-42c0-b74b-0c0209921456 | 2f209d72-b9f2-4912-a2dd-21d0d537550b |
| 冲突 | 8656f495-17a6-48f1-8388-3b5a869f4662 | 163d08fa-3721-4642-803d-5fe00f83083e | 2d372560-c8f7-4290-9d9e-ae360a9d7af0 |
| 未知 | 61856917-3c7d-45e8-ade2-6c3ca83bb472 | 未产生 | 未产生 |

以 diagnostic5 原始记录为最终依据：每题文件含请求/响应、Trace、Artifacts、Integration、Answer；planner-audit 含模型原文、逐次错误、重建的冻结归一化目标；runtime-audit 含 Runtime 审计。具体 Artifact ID 在 summary.json 与原始记录中保存。

## 8. 测试与调用统计

- 67 项针对性回归通过；新增归一化 28 项、模板/模型 Schema 6 项、评测输入 2 项。
- 583 项后端 portable 通过，1 项明确 deselected，1 项既有 AnyIO 弃用 warning。
- 128 项评测框架测试通过；OpenAPI/契约检查通过，现有 42 个 HTTP 操作和 10 个导出文件一致。
- 模型实际用量：input_tokens 37821、output_tokens 3818、total_tokens 41639；6 次模型调用耗时合计约 85.37 秒。不把这个数据写为准确率或长期稳定成功率。
- 本轮未重新跑全量带数据库后端套件；上述实际检查与历史 1426 项工程验收、F.2 的全量/新库复跑结果分开说明。

命令/警告/复审记录见 docs/phase13f3/TEST_EVIDENCE.md、REVIEW.md。离线复现统计命令 `python evaluation/failure_analysis/phase13f3/summarize.py` 只读保存的结果，不调模型、API 或评分器。

## 9. 修改文件

实现：normalization.py、templates.py、investigation_plan_v6.txt；Planner adapter/planning/roles；evaluation/bench/http_investigation.py。

测试与兼容：归一化/模板/Builder 新测试，现有 prompt 版本断言、冻结源文件精确哈希链、CI portable 清单。未修改旧冻结资料本体；仅新增本阶段授权哈希证明。

交付：本报告、docs/phase13f3、evaluation/planner_failure_analysis/phase13f3、evaluation/failure_analysis/phase13f3。没有新增 HTTP API 或改变前端 Schema。

## 10. 是否恢复正式实验与下一步

**否。** 当前 4/5 进入真实链路，未知版本题没有 Runtime/Gate，未满足用户的五题准入条件。已执行完限定验证，停止本阶段开发。

本轮是小规模诊断，不生成准确率、不改 Ground Truth/评分、不跑 39 题。相比 F.2 的 2/5 计划合法，本轮观察到 4/5；这是单次过程对照，不是统计显著的能力提升。

下一阶段建议只处理未知输入任务的遗漏，并用已有失败原文先做离线控制；版本/风险 PENDING 和来源冲突须作为后续证据质量问题单独处理，保持 Gate 标准。任何新模型实跑、正式 39 题实验或业务规则修复等待下一阶段指令。

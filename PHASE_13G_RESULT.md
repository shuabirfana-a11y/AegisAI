# Phase 13-G：49题首轮正式实验报告

## 1. 实验目标

按用户确认，使用最新49题全部通过复核包，执行固定系统的第一轮在线基线。全49题进入实验清单，失败/缺上下文/接口不支持均保留。没有调整模型、Prompt、Agent、Gate、评分规则或人工答案。

## 2. 实验环境

- 实验 ID：`aegisbench13g-human49-20261014`；模式：`ONLINE_EVALUATION`。实际 HTTP 采集后用原评分器计算，未使用旧答案代替新调用。
- 冻结代码：`ba92879c364411c8fa10642f3950c9f78370b468`；分支：`codex/phase13g-human49-online`。应用业务源码与 Phase13-F.4 一致。
- 新隔离本机数据库只复制旧冻结原始来源图谱，不复制旧资产、AgentRun 或人审答案；受控库存使用中性随机名称，按原问题输入创建。
- 源文档 12 份；审计确认原始来源哈希及 Planner 输入隔离保持。未联网更新语料。
- 本机 Python、PostgreSQL、Ollama；HTTP超时180秒，原模型单次预算40秒。

## 3. Dataset信息

- 版本：`AegisBench-v0.4-human49-20261014`；APPROVED=49，REJECTED=0。原39题批准包、历史退回记录和旧实验均保留。
- manifest SHA256：`002f021912a56f629c79a6207d30a91abe126c55f3d5f201adbfc358e8ae13e3`。
- annotations SHA256：`1d72276e477fa552bd30364ecfabe749a1a34f6e10e266e512321271e7ce7c99`。
- 原问题 SHA256：`f1f4be86e202ec263c6ebac66782b74d265840d706b559d913ab0c8c5f45e6f1`。
- 原件通过 Schema、问题与签核内容指纹、来源哈希和原文定位检查；39条r2及10条r3依据提供的双人签核导出。格式检查不替代真人查源。
- 只导出原件已声明的 scored_fields，supplementary_fields 和 uncertainties 保留在原件，没有自行扩大或缩小计分字段。
- 分类：`{'facts': 5, 'version': 17, 'poc_patch': 10, 'risk': 10, 'multihop': 7}`；仅5个公告簇，题目相关、非独立留出集；资产为受控场景，非企业真实扫描。

## 4. Model信息

- Provider：openai_compatible；模型：`aegisai-qwen25-planner:latest`。
- 模型摘要：`sha256:15aaf3fda3b8e9bb6724e5e9911eec3b9cbdb6bd967646b6bf49ee9846b7ec16`；temperature=0.0，max_output_tokens=4096，结构化模式=json_object。
- Planner Prompt：investigation-plan-v6；Answer Composer为确定性模板，没有另一次答案生成模型调用。
- 保存的真实模型调用记录：38；各次延迟/token usage/状态见 collection/planner-audit.json。缺信息/未支持的题目不伪称已调用模型。
- 原有Embedding配置仍为mock-embedding-v1（384维），已明确披露；不能把整个检索模型栈说成全部真实模型。

## 5. 实验流程

原Question/input_context → 原Question Normalizer/Question Contract → 原InvestigationRequest → HTTP API → 原Context Check → 原Planner/Validation → 原Runtime/Agents → 原Gate → 原AnswerEnvelope → 原Evaluator。
缺上下文返回 NEED_CONTEXT 时没有创建调查；请求适配器不支持多资产时未调用HTTP；只有输入受支持的题目进入后续链路。没有猜版本、拆题、伪造Artifact或把Gate阻断改为通过。
本轮49题记录完整：HTTP尝试42题，实际创建37次调查，NEED_CONTEXT=5题，请求适配拒绝=7题。记录每题request/endpoints、原生Trace/Artifact/Gate/Answer、规范化输入、错误、原始模型计划、评分字段与对照。

## 6. 指标定义

- Answer Accuracy：原评分器逐题对已声明 expected_answer 的所有计分字段作严格规范JSON匹配；分母49。字段缺失、NOT_EVALUATED/FAILED不计正确。它测量端到端契约一致性，不是自然语言语义准确率。
- Risk Accuracy：仅对标准答案含 risk_level 的题目比较，分母取该字段实际样本数；受控政策符合性不等于生产风险。
- Evidence Coverage / Hallucination Rate：需要原复核人员独立核对本轮所有输出Claim，并绑定输出哈希和证据；Ground Truth批准不能替代输出复核。此轮未代录人工结论。
- Abstention Quality：保留现有STRUCTURED_UNKNOWN_FIELDS_WITH_FLAG_CONSISTENCY公式。合法NEED_CONTEXT目前在Prediction中是NOT_EVALUATED，不自动获得该指标分；另行统计合法上下文处理，不能把它说成Planner失败，也没有改计分器给它加分。
- 不把Gate PASS视为答案正确，不把HTTP适配成功视为业务成功。

## 7. 实验结果

| 指标 | 本轮结果 | 分母/状态 |
|---|---|---|
| Answer Accuracy（严格字段匹配） | 0.00% | 0/49 |
| Risk Accuracy | 0.00% | 0/10 |
| Abstention Quality（原公式） | 4.08% | 49题；合法NEED_CONTEXT另列 |
| Evidence Coverage | 待独立人工复核 | PENDING；不是0% |
| Hallucination Rate | 待独立人工复核 | PENDING；不是0% |

原预测执行状态：`{'SUCCEEDED': 37, 'NOT_EVALUATED': 12}`。Planner状态：`{'VALIDATED': 37}`。Gate状态：`{'PASS_WITH_WARNINGS': 6, 'REPLAN_REQUIRED': 15, 'NOT_REACHED': 12, 'HUMAN_REVIEW_REQUIRED': 16}`。
原Answer状态：`{'COMPLETE_WITH_WARNINGS': 6, 'INCOMPLETE': 15, 'NEED_CONTEXT': 5, 'NO_ANSWER': 7, 'REVIEW_REQUIRED': 16}`。原全对照报告 quality_status=`NOT_EVALUATED`、comparison_status=`NOT_COMPARABLE`，没有改为全量可比实验。

| 题型 | 总数 | 技术适配SUCCEEDED | FAILED | NOT_EVALUATED | 严格匹配 |
|---|---:|---:|---:|---:|---:|
| facts | 5 | 5 | 0 | 0 | 0 |
| version | 17 | 12 | 0 | 5 | 0 |
| poc_patch | 10 | 10 | 0 | 0 | 0 |
| risk | 10 | 10 | 0 | 0 | 0 |
| multihop | 7 | 0 | 0 | 7 | 0 |

完整指标/混淆矩阵/延迟分布见 collection/report.json 和 summary.json。

## 8. 成功案例

这里的成功只指真实链路取得结果，不代替证据复核或严格匹配；逐题查 collection/samples-complete.jsonl。
- GHSA-53q9-r3pm-6pq6-facts：Planner=VALIDATED，Gate=PASS_WITH_WARNINGS，Answer=COMPLETE_WITH_WARNINGS，Run=6b35d36b-abb3-4dbc-88d2-84ecead9bdc7。
- GHSA-53q9-r3pm-6pq6-commit-candidate：Planner=VALIDATED，Gate=PASS_WITH_WARNINGS，Answer=COMPLETE_WITH_WARNINGS，Run=44a94d0f-704d-4e67-b010-f7ecafac3d8a。
- GHSA-9rwj-6rc7-p77c-facts：Planner=VALIDATED，Gate=PASS_WITH_WARNINGS，Answer=COMPLETE_WITH_WARNINGS，Run=b8a27e9c-71cb-4476-9dda-422a3486f13b。

## 9. 失败案例

阶段分类：`{'NONE': 6, 'GATE': 31, 'CONTEXT_PREFLIGHT': 5, 'REQUEST_ADAPTER': 7}`。这与逐题严格匹配失败可以重叠，不能相加当作独立样本。

- REQUEST_ADAPTER（7题）：GHSA-53q9-r3pm-6pq6-multihop；errors=['REQUEST_BINDING_INVALID']；缺失=[]；Gate=None；规则=[]。
- CONTEXT_PREFLIGHT（5题）：GHSA-53q9-r3pm-6pq6-unknown；errors=[]；缺失=['version']；Gate=None；规则=[]。
- GATE（31题）：GHSA-53q9-r3pm-6pq6-affected；errors=[]；缺失=[]；Gate=REPLAN_REQUIRED；规则=['OBJECTIVE_NOT_COVERED', 'REQUIRED_TASK_INCOMPLETE', 'UNRESOLVED_ANALYSIS']。

## 10. 错误分析

- Gate阻断规则（逐题去重计数）：`{'REQUIRED_TASK_INCOMPLETE': 28, 'OBJECTIVE_NOT_COVERED': 22, 'UNRESOLVED_ANALYSIS': 16, 'POC_COMPLETENESS_NOT_SUPPORTED': 5, 'CRITICAL_EVIDENCE_CONFLICT': 16, 'REQUIRED_ARTIFACT_MISSING': 6}`。各规则原文、涉及Artifact引用及未解决信息保存在逐题记录；没有为提高结果放宽要求。
- 7道多资产/多跳题被现有适配器拒绝（MULTI_ASSET_SCOPE_UNSUPPORTED），这是接口能力边界，不能解释为模型回答错误或直接补成单资产题。
- 原投影不会从标准答案补造CVE、summary、CVSS、PoC/版本字段；缺失字段严格失配须结合 field_accuracy 和原生Answer查看，不能把严格匹配率直接解释为模型安全能力为零。
- 同源转载不是独立证据。REPLAN_REQUIRED/HUMAN_REVIEW_REQUIRED要求保留未确认结论；本阶段只记录，不修改业务/证据算法。

## 11. 当前限制与停止点

- 公平、可比的 RAG-only / No Verification Agent 对照仍 NOT_IMPLEMENTED；未生成提升或优越性结论。
- 输出独立复核仍为0；37份成功适配答案、235个Claim待原复核人员检查。文件夹 output-review-package 提供49题观测记录、原始来源、待填表单，没有代替真人批准。
- 不能证明生产安全效果、全部漏洞泛化能力或商业部署效果；数据存在开发样本交叉、样本相关及受控风险政策限制。
- Evidence/Hallucination两项尚无正式值。现有NEED_CONTEXT计分边界与多资产入口限制如实披露，未调整评分规则。
- 本次实际运行 tests/aegisbench：129 passed（26.60秒）。覆盖Evaluation、Runner、Report、数据隔离、拒答与HTTP契约。不是重跑所有后端历史测试，也不是把工程测试当安全准确率。
- 离线复算使用原评分器并对全部metrics逐项相等校验；无新增模型调用。摘要文件、冻结数据及SHA256SUMS用于复现。
- 49题首轮已停止采集。未开展Prompt优化、Agent修改、Gold调整、Gate调整、Baseline伪造或立即重跑。后续仅待独立输出复核/实验分析授权。

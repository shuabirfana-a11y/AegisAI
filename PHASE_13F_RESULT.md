# Phase 13-F：AegisBench 首轮正式实验结果

39题真实HTTP采集与离线评分已完成。严格整题匹配 **0/39（0%）**；37题执行失败，2题产生可投影的结果，均未匹配标准答案。没有Gate通过的调查。Evidence Coverage和Hallucination Rate仍等待原复核人员检查本轮实际输出，保留null。

## 1. 实验目标

在39条人工批准的安全问题上首次测试完整调查入口。保留失败，不调整系统或指标来提高结果。单系统指标与公平Baseline比较分别管理。

## 2. 环境信息

- 采集源码：`bbb3a0fd40e098c52db3dd0499b77bd53aecef86`，分支`codex/phase13f-first-formal-run`；运行时未改业务。
- 评分时用户明确授权一行类别兼容：PoC合法类别新增`NO_EVIDENCE`。它与`UNKNOWN`保持不同；公式、失败处理、金标和分母不变。
- 评分版本：`aegisbench-metrics-v0.2+human-no-evidence-enum-v1`；源码哈希及运行前/后字节检查见[verification.json](evaluation/reports/phase13f-neutral-human39-20261013/verification.json)。运行时commit与后来的评分兼容变更必须一起引用。
- Windows本机，Python 3.12.14；Ryzen 9 8940HX、RTX 5060 Laptop 8GiB。PostgreSQL/pgvector使用新隔离数据库；调查入口为本机8002，不是公网部署。
- 27个库存对象由批准题的Question.input_context登记，资产名称和请求键为中性随机值。环境/暴露未知、无版本时保留unknown/null，标记is_demo；不是企业扫描结果。
- 12份真实公开来源原始记录，7份可支持文本的文档进入实际本地MiniLM检索索引，5份结构投影保留结构化记录而未伪装文本。厂商不支持、来源冲突等真实限制均保留。

## 3. Dataset信息

冻结版本：`AegisBench-v0.3-human39-20261013`。49个问题中39批准、10退回；仅39题调用调查API。批准题为事实2、版本17、PoC/Patch10、风险10、多跳0，覆盖5个公告簇，题目相关而非39个独立漏洞。

- manifest SHA-256：`0651efb54fdfe12c6c05493429dac4f73d309bb51f6297b7f66da71f84552002`。
- annotations SHA-256：`6fb41da340507b191c60b1096d85242b85a67818af1c3ba51bc4fbf876ceda83`。
- questions SHA-256：`f1f4be86e202ec263c6ebac66782b74d265840d706b559d913ab0c8c5f45e6f1`。

原问题、人审批准原件和退回原件未改。Manifest中的formal_evaluation_executed=false是数据冻结时的历史元数据，不回写；本轮执行事实见独立实验回执。

## 4. Model信息

沿用`openai_compatible`本地Ollama，`aegisai-qwen25-planner:latest`（Qwen2.5 7.6B Q4_K_M），temperature=0、40秒Provider timeout、4096输出上限；HTTP单题180秒。模型制品digest为`15aaf3fda3b8e9bb6724e5e9911eec3b9cbdb6bd967646b6bf49ee9846b7ec16`，本轮核对磁盘manifest及服务实际模型身份，未重新计算全部模型blob哈希。

Planner Prompt为`investigation-plan-v4`；Answer Composer沿用确定性模板，没有单独LLM表达Prompt。真实Planner调用回执保留provider/model/is_mock=false。模型配置中的Mock embedding项不用于实际语料检索，实际索引使用原本地MiniLM。

## 5. 实验流程

问题及input_context → Investigation HTTP API → Planner → 原Runtime/专业Agent → 原Verification/Risk/Gate → AnswerEnvelope读取 → 原HTTP投影 → 金标比较。失败在真实阶段停止，未绕过任何验证/Gate。

采集完成后因5条人审PoC标签NO_EVIDENCE不在评分器原合法类别中而停止评分。用户确认仅补合法类别；使用39个已保存预测离线计算，新增模型调用=0、新增调查=0。评分后的39个Prediction与采集原件逐对象完全相同。

Ground Truth只在采集完成后的Evaluator比较阶段读取；批准ID仅用于Evaluator准入，不发进Prompt/Context/Tool。读库核对实际39个Planner上下文及资产元数据，没有金标字段或完整题号；12份来源哈希与运行前冻结一致。Question→资产UUID对应关系只在Evaluator侧保存。

第一次临时库存曾将含分类提示的题号写入资产名称。发现后立即停止，38份checkpoint及第39题终态封存隔离，禁止评分。用户批准后，在新的干净数据库使用中性随机名称完整重跑39题；旧记录保留在本机交付包quarantined-trial/。这是实验库存设置错误，不能将旧试次混入本轮结果。

## 6. Metrics定义

- Answer Accuracy：原评分器对每题全部expected_answer字段作JSON严格匹配；失败、缺字段、不匹配均为0，分母39。它是结构化字段契约指标，不能替代人工语义准确性判断。
- Evidence Coverage / Hallucination Rate：必须有本轮输出哈希绑定的独立Human OutcomeAudit，并完整检查每个实质回答；引用存在或CONFIRMED状态不足以计分。
- Risk Accuracy：风险标签精确匹配，分母10；Priority Accuracy同样按原标签计算。金标风险按benchmark-reference-triage-v1，原生优先级语义可能不同，只衡量这项基准政策符合度。
- Abstention Quality：原STRUCTURED_UNKNOWN_FIELDS_WITH_FLAG_CONSISTENCY定义，失败无预测不能算正确拒答；分母39。NO_EVIDENCE不改写为UNKNOWN。
- 多跳批准样本0，Reasoning Completeness=null，不能声称多跳准确率。

## 7. 实验结果

| 指标 | 本轮结果 | 分母/状态 |
|---|---:|---|
| Answer Accuracy（整题严格匹配） | 0% | 0/39 |
| Version字段准确率 | 0% | 0/27（含风险题版本字段） |
| PoC类别准确率 | 0% | 0/5 |
| Patch类别准确率 | 0% | 0/10 |
| Risk Accuracy | 0% | 0/10 |
| Priority Accuracy | 0% | 0/10 |
| Abstention Quality | 0% | 0/39 |
| Evidence Coverage | null | 待人工输出复核 |
| Hallucination Rate | null | 待人工输出复核 |
| 输出可投影 | 2 | 不代表正确/通过Gate |
| 输出FAILED | 37 | 全部留在39题分母 |
| Gate REPLAN_REQUIRED | 4 | 其中2题缺必要Artifact |
| 未产生可读Gate结果 | 35 | Planner失败 |
| Gate PASS/PASS_WITH_WARNINGS | 0 | 无通过调查 |

平均单题HTTP采集耗时25.172秒，p50=23.812秒、p95=38.972秒、最大57.109秒；保留原始采集耗时，离线评分耗时不计入。

RAG-only、Agent without Verification均`NOT_IMPLEMENTED`，没有对照结果。原报告全局quality_status=NOT_EVALUATED表示完整比较不可用；aegisai变体metrics.status=EVALUATED、scored_count=39表示单系统已评分。不得把二者混为没有执行实验或已有公平比较。

## 8. 失败案例

逐题问题、输出、金标、Gate、错误、运行/Artifact引用保存在[samples-complete.jsonl](evaluation/reports/phase13f-neutral-human39-20261013/collection/samples-complete.jsonl)，原生HTTP记录、模型回执与freeze在同目录，见[39题索引](evaluation/reports/phase13f-neutral-human39-20261013/CASE_INDEX.md)。全部失败保留，10退回题标记NOT_EVALUATED而未调API。

35题PLANNING_FAILED；2题REQUIRED_AGENT_ARTIFACT_MISSING；2个可投影结果是vLLM affected/fixed问题，但返回UNKNOWN、PENDING、Gate REPLAN_REQUIRED，不能算正确版本结论或成功资产风险闭环。

## 9. 错误分析

只读取持久化错误码定位，不改变业务或输出。Planner多个尝试累计错误：COMPONENT_SCOPE_MISMATCH=22、TOOL_INPUT_INVALID=20、ASSET_LOOKUP_REQUIRED=15、VERSION_INPUT_REQUIRED=6、QUERY_SCOPE_MISMATCH=6、DAG_OR_BUDGET_INVALID=1、TIMEOUT=1；这是尝试级计数，不是互斥题数。

主要现象是生成计划无法满足既有输入/作用域约束，另外部分链缺必要Artifact或尚未形成可确认版本证据。两题可投影结果仍未知并被Gate阻断。原HTTP投影也未给事实题提供cve/cvss/cwes/summary等标准字段；本轮没有事后补字段、改优先级映射或降低Gate来改善成绩。

固定少量场景的20/20合法规划和历史工程测试不能外推到本轮39题业务可靠性。结果应以此次实际失败与未匹配为准，不把低分全部归因于模型能力或全部归因于评分器。

## 10. 当前限制与停止位置

39题采集、自动指标、原始记录和报告已完成；2个实质输出共26个claims尚未人工复核，所以两项语义指标未完成。输出复核包有39个案例和2份PENDING表单，没有代替复核人签字。失败案例用于排查，不能改成正确拒答。

本实验只说明该冻结模型/系统/受控库存在人审试点题上的表现。不能证明生产安全效果、所有漏洞泛化能力、商业部署效果或相比RAG的提升；没有独立holdout或多跳批准覆盖。

类别兼容先实际复现2个失败/1个通过，再一行修复；AegisBench **108 passed**，portable后端 **531 passed / 1 deselected**（旧Starlette/AnyIO告警1项）。两组集合不相加，未声称全量历史1426测试已重跑。499个受保护文件中仅quality.py为授权差异，其余498个不变。

下一步仅等待原复核人员返回输出审计，随后再决定实验分析任务；本阶段不改Prompt/模型/业务、不扩基准、不制作PPT、不部署。

评分代码及原始归档提交：`9155b5725649ad743c719c53bc8cbe01042b042d`。另实际完成18项工程门禁、23项前端现有测试、17文件语法及TypeScript契约检查；OpenAPI 42操作检查通过。原CLI离线回放全部指标与首次评分相同，未调用模型或调查服务。

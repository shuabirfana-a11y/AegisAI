# Phase 13-F.1：失败诊断与评测输入适配修复

已定位原39题的失败边界，修复2处评测输入适配遗漏，并实际运行固定3题。事实总览已恢复到Gate `PASS_WITH_WARNINGS`；版本题仍业务不完整，风险题仍Planner拒绝。**正式评测条件尚未全面恢复**，未重跑39题、未改模型/Agent/Gate/金标/评分规则，也未生成新正式准确率。

## 1. 失败分类

原39条批准数据能正确加载，原问题/ID一致；39个请求均通过InvestigationCreateRequest并得到HTTP 202，Trace均记录REAL模式。未发现401、422、Mock混入或question hash/标题错配。

| 分类 | 数量 | 实际断点 | 原评测记录 |
|---|---:|---|---|
| A：Planner验证失败 | 35 | API已受理，生成计划未通过原验证，没有进入专业Agent链 | FAILED / PLANNING_FAILED |
| A：业务链不完整 | 2 | langchain-core来源冲突，漏洞查询WAITING_REVIEW、版本任务BLOCKED；无Verification Artifact，Gate要求重规划 | FAILED / REQUIRED_AGENT_ARTIFACT_MISSING |
| B：结构化结论未匹配 | 2 | vLLM链返回UNKNOWN，Gate REPLAN_REQUIRED；标准答案分别为AFFECTED、NOT_AFFECTED | SUCCEEDED仅表示可投影，不表示正确 |
| C：可交付且匹配的正常回答 | 0 | 原试次没有这类回答 | 不虚构成功 |

因此“37 FAILED”不是37次HTTP故障。评测器将2条不完整业务链也计入FAILED；本阶段用多层日志保留区别，不改原分母或失败计分。

35个Planner最终拒绝原因（题级最终错误，合计35）：VERSION_INPUT_REQUIRED 4、ASSET_LOOKUP_REQUIRED 8、TOOL_INPUT_INVALID 11、COMPONENT_SCOPE_MISMATCH 10、QUERY_SCOPE_MISMATCH 2。与上一报告的“多次尝试累计错误”统计口径不同，不能相加。

每题输入、HTTP/调查/Gate/答案/评测状态与原错误均见[原39题诊断日志](evaluation/failure_analysis/phase13f1/original39-debug.jsonl)及[分类汇总](evaluation/failure_analysis/phase13f1/original39-summary.json)。原正式实验文件没有回写。

## 2. 根因

### 两处确认的评测/数据适配问题

1. **10个风险题单个资产版本遗漏。** 标准问题的版本放在input_context.asset，原input_values只展平assets数组；临时库存创建读取了asset，但调查请求没有读取，导致库存有版本而Planner入参缺版本。
2. **12个总览题触发错误任务语义。** 两个事实题和10个PoC/Patch题使用overview_v1，但请求仍把公告组件提示放进AssetScope.component。既有Planner把非空component视作asset_analysis，因此事实总览也触发资产/版本约束。它们已有明确CVE目标，调查原问题/target即可保持总览语义。

这22个适配影响记录不是22个已证明“唯一因果”的失败；同一题还可能生成非法工具参数或范围不符计划。本阶段不把35个规划错误全部解释为适配遗漏。

### 已确认的真实业务问题

- 两个langchain版本调查遇到真实来源冲突，Task等待人工复核，核验Artifact未产生；原Gate阻断不是评测器捏造的失败。
- 两个vLLM未匹配样本实际字段为UNKNOWN，与人审AFFECTED/NOT_AFFECTED不同。ID、问题及来源绑定正确，不是大小写问题。不能把UNKNOWN改成确定结论以通过评分。
- 无效工具参数、缺资产查询、组件作用域/检索问题作用域不符均是原Planner校验拒绝。修复输入后仍出现的这类问题属于后续真实业务链工作。

### Schema/交付覆盖限制

事实题金标比较cve、summary、cwes、cvss_v3、cvss_v4；现有AnswerEnvelope并不直接提供同名完整事实字段。Investigation Artifact有描述/CVSS/CWE发现数据，但本次事实调查对相关Claim仍INSUFFICIENT_EVIDENCE，最终只确认VENDOR_CONFIRMED。**不能将未核验的发现数据直接升格为最终答案填评分字段。** 完整事实交付及明确、保留来源的映射需要后续业务契约工作。

原评分器做JSON严格比较；本轮两条实际值本来就是UNKNOWN，没有出现合法大写AFFECTED被误判为小写affected的证据，因此没有新增大小写/模糊归一化来提高分数。

## 3. 修复内容

仅修改[evaluation/bench/http_investigation.py](evaluation/bench/http_investigation.py)：

- 支持单对象asset与既有单元素assets；版本从原问题输入传递，不从金标取值。
- 同时给asset/assets、顶层与嵌套值冲突时明确拒绝，不静默覆盖。
- 有明确目标的overview请求不把公告组件提示升级为部署资产；原问题和CVE target保持原文。
- 版本/风险请求继续携带真实拥有的资产/组件ID及原版本；没有明确目标的组件搜索保留原组件提示，避免扩大行为变更。

虚拟场景ID、分类提示、Ground Truth、reviewer等均不进入实际HTTP请求。新增7个针对性控制（含参数化）：先实际复现原遗漏与非法覆盖，再验证修复；另外发现并修复无明确目标搜索提示被删除的局部回归。

原Metrics、Prediction失败计分、39题分母和分类白名单均未改。每题多层诊断输出以独立资料保存，不通过修改Agent Trace或业务响应增加日志字段。

## 4. 3题诊断结果

选择在调用前冻结：事实GHSA-53q9…facts、版本GHSA-935w…affected、风险GHSA-53q9…risk-affected；新隔离数据库复制原12份来源图，排除旧资产/运行/Artifact，创建2个中性演示资产。只创建3个调查，不重试挑选最好的一次，不下载/更换模型或调Prompt。

沿用原Qwen2.5制品、openai_compatible、temperature=0、40秒Provider timeout、180秒HTTP单题预算、investigation-plan-v4。实际服务8003；模型身份核对通过。资产来自Question.input_context，不是企业扫描结果。

| 题型 | 实际请求 | Planner | Gate / Answer | 判断 |
|---|---|---|---|---|
| 事实 | 原问题+CVE-2025-32434；没有部署component | VALIDATED | PASS_WITH_WARNINGS / COMPLETE_WITH_WARNINGS | 总览链恢复；不等于完整事实语义正确或金标匹配 |
| 版本 | vllm 0.29.0+CVE-2026-105752+中性资产ID | VALIDATED | REPLAN_REQUIRED / INCOMPLETE | UNKNOWN仍保留，业务证据/任务未完整 |
| 风险 | torch 2.5.1+CVE-2025-32434+中性资产ID | PLANNING_FAILED | 无Gate / FAILED | 版本已补传；最终QUERY_SCOPE_MISMATCH，不再是版本漏传 |

版本题Gate实际阻断：REQUIRED_TASK_INCOMPLETE、OBJECTIVE_NOT_COVERED、UNRESOLVED_ANALYSIS；核验保留“No explicit normalized fixed version / Insufficient current, explicit, independent evidence”。这些证据要求没有放宽。

运行标识：

- 事实：investigation_id `2804f864-497e-41f6-b075-d819a8478d47`，planner_run_id `b6814289-88d4-47ee-a082-c7d3bec11559`。
- 版本：investigation_id与Artifact引用见[版本原始记录](evaluation/failure_analysis/phase13f1/diagnostic3/GHSA-935w-9g4m-p28p-affected.json)。
- 风险：planner_run_id `657050de-1156-4c0c-a24c-7c315c310dd3`；两次Planner尝试的错误/真实模型回执见[规划审计](evaluation/failure_analysis/phase13f1/diagnostic3/planner-audit.json)。

完整请求、公共状态/Trace/Artifact/Gate/Answer和诊断状态在[diagnostic3](evaluation/failure_analysis/phase13f1/diagnostic3)；无凭据或私有原始模型输出。没有计算3题“准确率”，更没有改写原39题0/39。

## 5. 是否恢复正式评测条件

**部分恢复，尚未全面就绪。** Loader/API/真实模式/来源绑定可用，已知请求适配遗漏修复，1个总览链实际恢复。但风险Planner仍失败、版本任务/Gate仍不完整，事实输出与评分字段尚缺可确认的完整交付，不能声称Benchmark已稳定测出安全语义准确率。

原0/39仍是该冻结系统和原输入适配下的端到端严格匹配结果，包含执行可用性与字段交付失败。不能将其解释为“所有安全知识都错误”或“AegisAI能力为零”；也不能在没有其他实验证据时将其全部解释为仪器错误。

519个受保护文件的校验未变，包含业务、评分器、人工答案与原实验归档；输入适配器单独记录授权变更。12份运行来源哈希未变。实跑失败均保留，没有额外第四题。

最终评测回归 **115 passed**（原108项+7个输入控制）。其中无明确目标搜索控制在诊断后补充，用于保留原行为；3个诊断题都有明确目标，该控制不改变本次已保存请求或结果，未因此再次调用模型。

## 6. 下一步建议与停止

本阶段诊断/输入修复/3题实跑已完成，后续工作需要独立阶段授权：

1. 对真实Planner QUERY_SCOPE_MISMATCH、TOOL_INPUT_INVALID、COMPONENT_SCOPE_MISMATCH、缺资产查询作业务约束分析；本阶段未改Planner/Prompt。
2. 补足来源冲突、固定版本及任务完成证据，保持原Gate规则；未知仍不是安全。
3. 定义受证据约束的事实答案交付，明确哪些字段来自最终确认、哪些仅为发现，之后再增加对应评测映射。
4. 继续原复核人员对Phase13-F实际输出的独立审核；本次没有签署新金标或输出审核。

停止在此，不重跑39题正式实验、不输出新的正式准确率、不优化模型/Agent、不降低标准。

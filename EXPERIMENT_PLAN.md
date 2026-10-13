# AegisBench 首轮实验清单（仅准备，未执行）

数据版本：`AegisBench-v0.3-human39-20261013`。39人工通过/10退回，原Loader实际准入39。旧49题问题/来源快照不变，保留历史0金标版本。所有报告指标仍为NOT_EVALUATED，当前请求没有授权正式运行。

| 实验 | 输入与流程 | 计划输出 | 当前状态 |
|---|---|---|---|
| Experiment-001 | 39合格金标问题→公开HTTP→原Planner/三Agent/Gate→AnswerEnvelope→原Evaluator | Answer/Risk Accuracy、Abstention；输出独立复核后Evidence Coverage/Hallucination | 数据准备通过；本轮禁止启动，库存/运行服务仍待核对 |
| Experiment-002 | 同题目/语料/模型预算→RAG-only | 相同字段和同一输出复核口径 | NOT_READY，独立可比控制未实现 |
| Experiment-003 | 同输入→独立实验调查→直接回答 | 相同字段和同一输出复核口径 | NOT_READY；不给生产链增加跳过核验开关 |

配置入口：`experiments/config/experiment-001-prepared.json`；报告模板：`experiments/config/report-template.json`。配置是计划执行规范，不由Runner自动读取；未来操作者必须核对真实服务profile和Trace，不假定模板会自动配置后台。

模型制品：本机Qwen2.5选定tag的manifest及6个blob摘要已实际校验，不把mutable latest本身当固定版本。计划provider/温度/超时来自既有成功运行profile与Planner源码；本轮不联系服务。Planner为investigation-plan-v4；答案为原确定性Composer，**没有单独answer LLM prompt**。

正式操作顺序（未来）：确认本轮新manifest及审批原件→核对模型/Prompt/源码摘要→登记真实操作者拥有的库存绑定与资料等价性→另获正式运行授权→原Online入口运行→保留失败和实际模型Trace→独立人审输出→原Offline入口重计分。标准答案仅用于最终比较，不进入模型Prompt、检索、Context或工具输入。

39题分布：版本17、POC5、Patch5、风险10、事实2；多跳0。10退回包括事实3和多跳7，不能宣称多跳已有人审验收或49题全量准确率。风险10按benchmark-reference-triage-v1的POLICY_CONFORMANCE，不等于真实企业扫描或专家风险标签；原生风险/优先级口径和旧事实字段映射限制仍需披露，不能改人工答案匹配模型。

Evidence Coverage/Hallucination需要**本次实际输出**绑定prediction_sha256的独立OutcomeAudit，39条GT审批不代替输出审核。两个对照尚未就绪、语料/库存公平性未证明，不能发布相对提高或公平消融结论。

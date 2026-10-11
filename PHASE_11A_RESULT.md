# Phase 11-A 完成报告

日期：2026-10-08。当前状态：**Phase 11-A 已完成**。完整后端回归716项全部通过，零失败、零错误、零跳过；一次独立只读审查发现的重要问题已修复并通过复现测试与完整回归。已停止本阶段开发，未进入 Phase 11-B。

## 完成内容

实现 Professional Multi-Agent Framework 基础层：Agent Contract、注册中心、五种任务类型路由、兼容 Executor、结构化 AgentArtifact 交接和持久化专业 Trace 读取。

三个正式注册项为 investigation_agent、verification_agent、security_analysis_agent，均仅有抽象接口，implementation=None。调用会明确返回 AGENT_NOT_IMPLEMENTED，产生原 Runtime FAILED Artifact，后续依赖 BLOCKED。没有实现新的 CVE 查询、PoC 判断、可信核验或风险评分算法。

成功协作链仅由测试目录内的 TEST_ONLY 实现证明，使用既有隔离工具进程和合成数据库数据；不代表三个生产安全 Agent 已完成，不属于真实模型准确率或比赛 Benchmark。

## Agent Framework 架构

```text
原 PlannerService / 原 Planner Validation
  → ProfessionalRuntimeService（显式注入）
  → 同所有者的已验证 Planner 审计 + 业务任务类型
  → Agent Registry / Router → 不可变绑定快照
  → 原 TaskPlan / compile_graph / Scheduler
  → AgentExecutor → 已注册能力接口
  → 原 ExecutionOutcome / 回执验收 / TaskArtifact
  → 原 Store 保存 → 下一任务接收结构化 AgentArtifact
  → ProfessionalTraceStore 重建专业节点与交接链
```

复用现有 Runtime 执行、状态、预算和存储。原 RuntimeService 只新增 `_make_scheduler(plan)` 兼容钩子及单处调用替换，默认仍返回原 Scheduler。Planner、DAG、Scheduler、原 Executor/worker/ProcessSupervisor、Model/Tool Gateway 均未修改。

专业链是新增内部服务选择；旧网页、原 HTTP API、旧确定性 Agent 和默认 PlannerService 运行入口不切换。框架自己不调用模型；原 Planner 若被调用，仍通过已有 Model Gateway。

## Contract 设计

冻结 Pydantic AgentContract 包含全部要求字段：agent_id、agent_type、description、supported_tasks、allowed_tools、input_schema、output_schema、timeout_seconds。

- Agent ID 使用原 TaskId 字符范围，最大64字符；描述最大500字符。
- 支持原 Planner 的五种类型，列表非空、唯一、最多五项；工具唯一、最多八个且必须已注册。
- input_schema=ProfessionalAgentInput-v1，output_schema=AgentArtifact-v1，都是固定本地 Schema ID；不接受动态模块或执行代码。
- 超时为严格整数1–60秒，默认30秒。实际期限取 Context、Task 和 Agent 上限中的最早值。
- 输入是 AgentExecutionRequest，包含原 TaskContract、WorkerContext 和 typed input_artifacts，整体 JSON 上限沿用4 MiB。
- ProfessionalAgent 提供 execute、cancel_all 和 for_run；三个能力接口分别为抽象 investigate、verify、analyze。for_run 必须返回独立的运行实例，避免取消共享原型影响其他运行。

权限与预算继续来自原 RuntimePolicy，默认 READ_ONLY。注册某工具不会授予权限，也不能扩大当前语义任务的工具范围。

## Registry 设计

AgentRegistry 支持服务端显式注册与冻结；RegistrySnapshot 提供 get(agent_id)、for_task(task_type) 和可序列化、可重新读取的描述。重复 ID 或任务负责者重叠返回 AGENT_REGISTRATION_CONFLICT。

| Agent ID | 能力接口 | 支持任务 | 正式实现状态 |
| --- | --- | --- | --- |
| investigation_agent | InvestigationAgent | vulnerability_lookup、version_match、patch_analysis | interface_only |
| verification_agent | VerificationAgent | evidence_search | interface_only |
| security_analysis_agent | SecurityAnalysisAgent | risk_analysis | interface_only |

注册快照包含版本 professional-agents-v1、Contract 和 implementation_key 的摘要；只有配置在服务器里的对象能作为实现，请求或 LLM 不能传入类名创建 Agent。

## Router 设计

Runtime TaskContract 仍只有 tool_sequence/input_required。专业 Router 按 Planner 的语义类型路由，ProfessionalRuntimeService 从同所有者的 VALIDATED Planner 记录读取 semantic_types_json，并核对候选任务、原计划和 plan_hash。

检查 Task 白名单、既有 Planner Task Registry 和 Agent 白名单的交集，再复用 compile_graph 校验工具输入、服务器权限和 DAG 预算。未知任务/缺少注册明确返回 AGENT_NOT_FOUND；越界工具返回 AGENT_TOOL_FORBIDDEN。不会按描述、工具名或聊天内容猜角色。

服务端绑定写入原 TaskPlan.route.professional_agents_v1，进入原幂等摘要。伪造绑定、跨所有者计划、修改任务或同请求键改变注册内容均拒绝。切换为专业运行需要新的请求键，不能重新解释已执行的旧运行。

input_required 不分配专业 Agent，沿用原 ProcessSupervisor，保持 WAITING_REVIEW。只有原验收接受的 SUCCESS 能解锁下游。

## Artifact 变化

新增 AgentArtifact 继承原 TaskArtifact，补充 agent_id、artifact_type、unresolved_items。artifact_id、run_id、task_id、result、evidence、confidence、调用记录及终态保持原值；unresolved_items 必须等于原 unresolved_questions。

原 Artifact 和 worker 协议不改；新接口输入使用扩展，向原 Runtime/worker 投影时移除新增字段。跨 Agent 交接仅允许本任务依赖列表中、同运行、成功的 Artifact，保留顺序和原 ID，拒绝错运行、错任务、额外/缺失依赖和重复 ID。

原回执验收仍生效；新增适配器还核对成功结果的完整 outputs/dependencies，拒绝改写证据、依赖引用和添加伪造结果字段。保持合法已完成回执，以便追溯失败前的执行。

严格检查原始可变 JSON 字段，避免 Pydantic 把 NaN 序列化为 null 后掩盖非法输入。原 Artifact 512 KiB、worker 4 MiB、运行元数据8 MiB上限不变，不截断证据。框架不生成事实、不提升来源可信度、不用 Planner confidence 填充情报 confidence。

执行验收同时预留 Store 将工具回执替换为正式记录 ID/序号后的字节开销，校验持久化后的 AgentArtifact 投影，避免执行时合格、存储后超过512 KiB而无法读取 Trace。超限明确返回 ARTIFACT_SIZE_LIMIT；若完整失败投影仍超限，使用原回执引用协议保留有界失败 Artifact，完整回执仍由原 Store 保存，不扩容、不截断来源证据。

## Trace 变化

新增 AgentRunTrace，包含 agent_id、agent_type、task_id、run_id、input_artifact、output_artifact、execution_time（毫秒）、status、attempted、capability_state 和 errors。

专业 Trace 从同一数据库事务内读取原 AgentRun 的绑定快照、TaskTrace 和存储后的 TaskArtifact。input/output 是可解析的结构化 Artifact 引用；读取 Artifact 时保留实际 ToolCallRecord ID。

没有新增表、Migration、专业 AgentRun 子行或第二套回执保存。原 AgentRun 表示完整 Runtime 运行，AgentRunTrace 表示其中的专业任务节点。新 Reader 实例可以从持久化记录重建协作链，不依赖内存缓存。

BLOCKED 节点 attempted=false；interface_only 调用 FAILED 并记录 AGENT_NOT_IMPLEMENTED，不能显示为专业调查成功。没有绑定的旧运行返回 AGENT_TRACE_NOT_AVAILABLE；旧 read_trace/API 结构保持原样。

## 修改文件

新增正式包 `backend/app/agents/`：__init__.py、contracts.py、interfaces.py、registry.py、router.py、artifacts.py、executor.py、service.py、trace.py。

唯一既有源码修改：`backend/app/runtime/service.py` 的 Scheduler 工厂钩子。新测试在 `backend/tests/agents/`，包括独立审查问题的 `test_review_regressions.py`；基线、RED/GREEN、JUnit、日志、审查包和执行记录在 `work/agents/`。

251个既有文件的哈希核对：仅该批准的兼容接口有变化，无删除、无未批准变化。前端、数据模型/Migration、旧 Embedding、现有业务算法、Planner 和两个 Gateway 保持原样。没有安装依赖。

## 测试结果

| 检查组 | 实际结果 | 证据 |
| --- | --- | --- |
| Contract / Registry / 抽象接口 | 17通过 | work/agents/task1_green.json |
| 加入类型路由的累计测试 | 29通过 | work/agents/task2_green.json |
| 加入 Artifact 交接的累计测试 | 40通过 | work/agents/task3_final_green.json |
| Agent Executor + 原执行/进程测试 | 34通过 | work/agents/task4_verified.json |
| 专业服务/Trace + 原 Store/Planner兼容 | 28通过 | work/agents/task5_green.json |
| 框架 + Runtime + Planner + Model Gateway | 331通过，零失败/错误/跳过 | work/agents/task6_green.json |
| 完整后端回归（独立审查前） | **710通过，零失败/错误/跳过；150.907秒运行器耗时** | work/agents/acceptance_full_suite.json |
| 持久化 Artifact 大小边界复现与修复 | 修复前6项失败 → 修复后6项通过 | work/agents/final_review_red.json、final_review_green.json |
| 完整后端回归（审查修复后，最终验收） | **716通过，零失败/错误/跳过；149.516秒运行器耗时** | work/agents/reviewed_full_suite.json、.xml、.log |

新增73项：Contract/Registry17、Router12、Artifact11、Executor12、服务/Trace10、端到端5、审查回归6。最终716项包含全部原有643项。实际测试包括注册、五类查询、未知任务拒绝、A→B→C结构化交接、Trace重建、越权/伪造输出拒绝、真实进程超时/取消、同键幂等、并发回执和跨运行取消隔离。

端到端使用真实 PostgreSQL、原隔离工具进程和合成 CVE/证据/EPSS数据；仅模型响应与能力接口实现为受控 TEST_ONLY fixture。未核验证据的 verified=false、原 confidence=None 均保持。未运行真实模型能力 Benchmark。

保存了真实失败和修复：NaN序列化输入检查、直接 Executor 调用的 Task期限边界、合成EPSS fixture唯一键。原 Runtime 取消 PID 测试在首次联合验证中出现一次瞬时失败，之后检查两个 PID 均已消失且无 late.txt，复测34项通过；不宣称已找到或修复旧问题根因。仅有原 Starlette/AnyIO DeprecationWarning。

最终独立只读审查为一次独立上下文审查：Critical 0、Important 1、Minor 0。重要问题是持久化回执引用扩展可使 AgentArtifact 超过大小上限并中断 Trace 读取。使用真实 Store 和新 Reader，对1/2/8条回执及 warnings/evidence 两类边界构造六项测试，均先复现失败，再修复通过；随后完整716项回归通过。审查记录见 `work/agents/final_review.md`。没有延期小问题，没有启动第二轮审查或其他阶段。

## 当前限制

- 三个正式专业 Agent 只有接口和注册；默认专业执行明确失败，不能用于实际调查结论。
- 可执行成功实现只有测试 fixture，委托原 ProcessSupervisor；框架不保证任意未来 Python Agent 的进程隔离或强制中断，Phase 11-B必须明确该执行边界。
- 当前仍使用原 tool_sequence 输出协议，不做模型生成的专业事实总结、风险评分或证据核验。
- 没有跨任务结果参数自动绑定、工具循环、Agent聊天、自动恢复、Integration Gate或长期学习。
- 仅新增内部服务/Trace接口；原网站继续原链路，没有新增专业 Agent 展示页面。
- 保留原权限、来源冲突和 UNKNOWN 等业务限制；真实模型规划质量、价格、延迟及比赛准确率尚未由本阶段评测。
- 原取消测试的历史瞬时问题仍需在目标部署环境关注。

本轮全部执行判断及其代价如下，按发生顺序保留；完整过程见 `work/agents/ledger.md`。

| 判断 | 原因与处理 | 代价或未承诺事项 |
| --- | --- | --- |
| 无 Git，采用文件哈希基线和独立日志并保留证据 | 当前目录不是 Git 仓库，不创建虚构提交或删除唯一历史 | 哈希不能恢复无关的并发编辑 |
| 新增 for_run 运行实例工厂 | 注册原型为每次运行提供独立实例，避免取消串扰 | 未来具体实现必须遵守该生命周期接口 |
| 保留并披露旧取消测试的瞬时失败 | 原进程代码在本阶段禁止重写；后续检查、复测和完整回归通过 | 根因未证明，部署环境仍可能复现 |
| 安全业务质量与真实模型/provider质量另行评测 | 本阶段仅框架，三个正式 Agent 没有业务实现 | Phase 11-B及真实模型评测仍需完成 |
| 任意或恶意实现隔离、伪造回执/工厂及无回执异常恢复不作保证 | 仅支持服务器可信注册实现；未来实现须明确执行边界 | 不支持不可信插件执行，不能据框架测试推断任意代码安全 |
| 历史取消根因与跨平台行为不扩大结论 | 保留原代码，仅陈述已保存的实际测试证据 | 目标部署环境、其他操作系统仍需验证 |
| HTTP API、前端、Migration和部署未新增 | 按批准范围提供内部兼容服务，原产品链路保持稳定 | 框架不能直接等同于新的可见业务功能或云端交付 |
| 不提供手工损坏数据库快照的自动恢复 | 没有允许外部修改这些记录的 API，持久化记录是可信边界 | 人工损坏可能需要运维修复 |
| 报告完整性与专用测试集群停止由本轮交付验证 | 最终测试、基线、报告与停库证据单独核对 | 这些结论来自交付检查，不属于独立代码审查的运行证明 |

## 下一阶段建议

等待新的 Phase 11-B 指令，再逐一接入三个专业能力和明确的结果 Schema/证据边界。优先复用现有查询、版本、证据和风险工具，为实际实现指定运行实例生命周期与隔离方式。不要因接口已经注册就将其视为可执行安全 Agent，不提前进入 Integration Gate 或前端开发。

本阶段专用 PostgreSQL 测试集群55435、55437均已停止：两者 pg_isready 返回2、pg_ctl status 返回3，证据见 `work/agents/cleanup_verified.json`。测试数据库数据、历次失败/通过日志及审查记录全部保留；原前端和项目服务未受此次清理影响。

当前停在 **Phase 11-A 完成**。下一阶段等待新的明确指令。

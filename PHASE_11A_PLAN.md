# AegisAI Phase 11-A：Professional Agent Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Runtime 上增加专业 Agent 的注册、路由、执行适配、结构化交接和审计框架，仅注册三个未来 Agent 的抽象接口。

**Architecture:** 新增 `app.agents` 包，复用原 TaskContract、Scheduler、ProcessSupervisor、TaskArtifact 和持久化。通过显式选择的 ProfessionalRuntimeService 适配现有 Planner；业务任务类型从已有、同所有者的 Planner 审计获取，服务端生成不可变 Agent 绑定。默认三个专业接口没有业务实现，调用返回 AGENT_NOT_IMPLEMENTED；测试使用明确标记的受控实现证明协作协议。

**Tech Stack:** 现有 Python 3.12、Pydantic v2、SQLAlchemy、PostgreSQL、pytest；不新增 SDK、模型、Agent 框架或数据库依赖。

**Spec:** 本会话用户的《AegisAI Phase 11-A：Professional Multi-Agent Framework 开发 Prompt》；约束摘录见本文件 Global Constraints。前置结果：[PHASE_10B_RESULT.md](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/PHASE_10B_RESULT.md)。

日期：2026-10-08。**状态：已检查源码，本计划待确认，尚未实施。** 用户第五节明确要求“输出 PHASE_11A_PLAN.md”“等待确认后实施”。本轮只新增本文件；不改代码、不启动数据库、不调用模型。确认后沿用本会话顺序实施方式。当前目录无 Git，不初始化仓库或编造提交。

## Global Constraints

- 本阶段只建立专业 Agent 框架，不开发漏洞调查 Agent 业务逻辑、证据核验逻辑或风险分析逻辑。
- Agent 采用能力型接口 InvestigationAgent、VerificationAgent、SecurityAnalysisAgent，不采用聊天角色。
- Agent 之间禁止传自然语言计划或聊天消息，必须通过 TaskArtifact 的结构化扩展交接；原工具中的公告文本、证据摘录仍是数据。
- 不重写 Planner、Task Contract、DAG Engine、Scheduler、Executor、Tool Gateway 或 Model Gateway；已有模块仅允许必要的兼容接口。
- 不修改 Hybrid Retrieval、现有业务算法、旧 assistant.roles、Embedding 调用点或前端。
- 未匹配 Agent 返回 AGENT_NOT_FOUND，不动态创建、不按任务描述猜角色。
- 所有工具调用沿用 Tool Gateway；框架本身不调用模型，未来模型调用仍必须经过 Model Gateway。
- 复用原预算：16 任务、8 层、32 次预留工具调用、3 并行；单任务最多 8 次调用、1–60 秒；运行预算最多 120 秒。
- 默认 READ_ONLY；Agent 白名单不能授予 WRITE、REVIEW_ACTION 或 EXTERNAL_NETWORK；不自动刷新、创建资产或重算风险。
- 只有原 Runtime 接受的 SUCCESS 才能解锁依赖；WAITING_REVIEW、FAILED、BLOCKED 均不能被框架升级为成功。
- 完成批准范围、真实测试及 PHASE_11A_RESULT.md 后停止；不进入三个具体 Agent 实现、Evidence Verification、Integration Gate 或前端展示。
- 前置 643 项通过来自 `work/planner/reviewed_full_suite.json`，不是本轮新测试，新增测试数量只按实际运行结果填写。

## Review Focus

1. 规划类型已被转换掉、Agent 绑定被调用方伪造：只使用同所有者的已验证 Planner 快照，并检查任务和类型映射一致。任务 2、5。
2. Agent 拿到本角色工具后扩大任务范围或权限：同时检查 Task Contract、Planner Task Registry、Agent Contract 和服务端 policy。任务 2、4。
3. 跨运行 Artifact、非依赖 Artifact、改写证据或把复核中结果升级成功：严格身份及回执校验，保留原验收。任务 3、4。
4. 并发写入、重复请求、注册表变化、重启后 Trace 丢失：绑定快照进入原幂等哈希，Trace 从已持久化数据重建。任务 5、6。
5. 未实现接口或阻塞节点被展示为专业调查成功；Agent 执行绕开进程取消：明确能力状态和 attempted，测试执行复用原进程监管。任务 4、6。

---

## 1. 当前架构适配

| 源码位置 | 检查结果 | 适配决策 |
| --- | --- | --- |
| `backend/app/runtime/contracts.py` | TaskContract.task_type 只有 tool_sequence / input_required；TaskArtifact 已有 run/task 身份、终态、证据、调用、时间和大小限制 | 保留原协议，新增独立扩展模型，旧 worker 不接收新字段 |
| `backend/app/planner/schemas.py` | PlannerTaskContract 保存五种 planner_type；ValidatedPlan 独立保存 semantic_types_json | 路由按五种语义类型，不按通用 tool_sequence |
| `backend/app/planner/validator.py` | 验证后剥离 planner_type，原 TaskPlan.route 没有语义映射 | 从已有已验证 Planner 审计补回服务端绑定，不修改 Validator |
| `backend/app/planner/service.py` | 重验计划后调用注入的 runtime.run_plan；PlannerTraceStore.read 已限制所有者 | 注入 ProfessionalRuntimeService，维持现有调用签名，不修改 PlannerService |
| `backend/app/runtime/scheduler.py` | Scheduler(executor=...) 已支持替代执行适配器；只有 SUCCESS 解锁依赖 | 不改调度算法，通过既有注入点接入 AgentExecutor |
| `backend/app/runtime/service.py` | _run 内部固定创建 Scheduler() | 只增加 `_make_scheduler(plan: TaskPlan) -> Scheduler` 兼容钩子；默认仍返回原 Scheduler |
| `backend/app/runtime/executor.py` | validate_outcome 校验身份、真实回执、证据、工具结果和成功验收 | AgentExecutor 返回原 ExecutionOutcome，不绕开其校验 |
| `backend/app/runtime/process.py` / `worker.py` | 固定 worker、Windows Job/POSIX 进程组、期限、取消、输出限制已实现 | 本阶段不改 worker 协议；可执行测试适配器委托原 ProcessSupervisor |
| `backend/app/runtime/store.py` | 原 AgentRun JSON 保存计划、每任务 Trace/Artifact；工具回执另存 ToolCallRecord；写入有行锁 | 沿用原持久化；专业 Trace 为同一快照的类型化投影，不双写 |
| `backend/app/tooling/gateway.py` | invoke(name, args, context) 校验注册、参数、权限、预算和超时 | 不修改接口；Agent 不拥有第二套工具注册表 |
| `backend/app/assistant/roles.py` / `handoff.py` | 已有旧确定性 Role 业务；旧交接可接受 partial，与新 Runtime 不同 | 保留旧系统，不把旧 Role 重命名为本阶段三个专业 Agent |

适配后的内部链路：

```text
原 PlannerService / 原 LLM Planner + Validation
  → 显式注入 ProfessionalRuntimeService.run_plan
  → 同所有者 Planner 快照 + 语义类型 → Agent Registry / Router 绑定
  → 原 compile_graph → 原 RuntimeService._run → 原 Scheduler
  → AgentExecutor → 已注册 ProfessionalAgent 接口
  → 原 ExecutionOutcome / TaskArtifact → 原持久化与依赖调度
  → 下一个 Agent 的结构化 AgentArtifact 输入
```

生产默认绑定到 interface_only 接口，执行明确失败，不生成专业分析。完整 A→B 成功链由测试专用实现验证。现有网站、确定性 Agent 和默认 PlannerService 的 Runtime 选择不变。

## 2. Agent Contract 与 Registry

新增冻结 Pydantic AgentContract，extra=forbid，禁止 NaN；重新序列化验证嵌套对象，不能仅依赖 frozen 防止内部修改。

| 字段 | 类型与约束 |
| --- | --- |
| agent_id | 1–64 字符稳定标识，沿用 TaskId 的字符范围 |
| agent_type | investigation / verification / security_analysis |
| description | 1–500 字符能力说明 |
| supported_tasks | 非空、唯一、最多五种 Planner 语义类型 |
| allowed_tools | 唯一、最多八个现有 Tool Registry 名称；不能包含未知工具 |
| input_schema | 固定 Schema ID：ProfessionalAgentInput-v1 |
| output_schema | 固定 Schema ID：AgentArtifact-v1 |
| timeout_seconds | StrictInt，1–60；只能收紧当前任务期限 |

Schema ID 对应本地 Pydantic 模型的注册目录，不是模块路径、URL 或可执行字符串。Registry 用类型化 AgentRegistration 将 Contract、抽象接口和可选服务端实现关联；implementation=None 表示 interface_only。不接受请求/LLM 提供 Python 对象、模块或类名。

| 注册 ID / 抽象接口 | supported_tasks | 初始 allowed_tools |
| --- | --- | --- |
| investigation_agent / InvestigationAgent | vulnerability_lookup、version_match、patch_analysis | get_vulnerability、search_vulnerabilities、resolve_component、relation_query、match_component_vulnerabilities、find_vendor_advisories、find_patch_candidates |
| verification_agent / VerificationAgent | evidence_search | get_evidence、get_claims、relation_query、semantic_search |
| security_analysis_agent / SecurityAnalysisAgent | risk_analysis | get_asset_risks、explain_asset_risk、get_epss、get_known_exploitation |

verification_agent 的注册不代表完成可信核验；evidence_search 本阶段仅表示证据检索任务。初始超时 30 秒；服务端可以配置到 1–60 秒，实际 deadline=min(原任务 deadline, 当前时间+Agent 上限)，不能增加原执行预算。

每种任务只允许一个注册负责者；重复 agent_id 或重叠 supported_tasks 返回 AGENT_REGISTRATION_CONFLICT，不能依赖注册顺序选择。冻结快照含 registry_version=`professional-agents-v1`、Contract 内容摘要和 implementation_key；本阶段正式默认 implementation_key=`interface_only`。测试实现使用明确的 TEST_ONLY 标识。快照只存描述和标识，不序列化实例。

## 3. Router、绑定与兼容入口

- `AgentRouter.route(task: TaskContract, semantic_type: str) -> AgentBinding`：先查语义类型注册，再确认实际步骤和 allowed_tools 同时属于该 Agent 及既有 TASK_REGISTRY 对应任务；未知类型或无注册返回 AGENT_NOT_FOUND，越界工具返回 AGENT_TOOL_FORBIDDEN。
- `AgentBinding` 保存 task_id、semantic_type、agent_id、agent_type、artifact_type、Contract 快照、implementation_key 和规范化 TaskContract 摘要；`BoundAgentPlan` 保存整图绑定及注册表版本/摘要。
- `ProfessionalRuntimeService.run_plan(plan: TaskPlan, actor: str, request_key: str) -> RunSnapshot` 与原接口一致。读取 plan.route.planner_run_id 所指、同 actor、状态 VALIDATED 的 PlannerTrace；校验 ValidatedPlan.plan_hash、候选任务内容、semantic_types_json 和传入原计划的一致性。缺少审计、所有者不符或内容被替换直接拒绝，不调用工具、不按文本推断类型。
- 绑定仅在内部服务生成；拒绝调用方已填的 `professional_agents_v1`。绑定放入原 TaskPlan.route.professional_agents_v1 后再调用原 run_plan/compile_graph，因此纳入原持久化与幂等摘要。
- input_required 是现有用户补全节点，不交给专业 Agent：仍由原 ProcessSupervisor 执行，产生 WAITING_REVIEW，不能为了完整绑定调用调查 Agent。
- `_make_scheduler(plan)` 默认返回 Scheduler()；子类从已捕获的绑定构造 Scheduler(executor=AgentExecutor(...))。不复制 _run，不重写 Scheduler，不更改 Planner prompt、Schema、验证或重试。
- 原 Runtime 同键已经执行过的计划不能切换为专业模式：绑定改变原计划摘要，会得到原 IdempotencyConflict。开始新模式使用新的用户请求键；不自动重用旧调查结果或重新绑定缓存。

## 4. 专业接口与 AgentExecutor

统一 `ProfessionalAgent.execute(request: AgentExecutionRequest, *, database_url: str | None = None) -> ExecutionOutcome`，同时要求 `cancel_all() -> None`。三个能力接口仅定义抽象 investigate(request)、verify(request)、analyze(request)，返回同一 ExecutionOutcome；公共 execute 负责分派到对应抽象方法。

AgentExecutionRequest 是冻结 Pydantic 模型，包含原 TaskContract、收紧后的 WorkerContext 和 input_artifacts: tuple[AgentArtifact, ...]，整体 JSON 不超过原 4 MiB wire 限制。database_url 只作为服务器私有参数传递，不进入 Contract、Artifact、Trace 或模型输入。

AgentExecutor 保持原签名：`execute(task, context, dependencies: dict[str, TaskArtifact], *, database_url=None) -> ExecutionOutcome`，以及 Scheduler 所需的 cancel_all。

执行步骤：检查任务与绑定摘要 → 检查白名单/权限/期限 → 校验依赖 → 将依赖包装成 AgentArtifact → 查询已注册实现 → 调用能力接口 → 原 validate_outcome 校验 → 返回原 ExecutionOutcome，由原 Scheduler 保存和解锁依赖。原验收只校验 SUCCESS.result.outputs 与回执相同；新增适配器还必须核对 SUCCESS.result.dependencies 与实际交接的依赖 ID 完全一致，并拒绝额外的伪造结果字段。

未实现接口返回原 failure() 生成的 FAILED TaskArtifact，错误 AGENT_NOT_IMPLEMENTED；不实例化抽象类。实现异常返回 AGENT_EXECUTION_FAILED，非法输出返回 AGENT_OUTPUT_INVALID；保留可验证的已完成工具回执，错误文本不泄露凭据、数据库 URL 或内部异常内容。Task/Agent 期限不足沿用 TASK_TIMEOUT。cancel_all 必须传播到该运行已创建的执行适配器。

**本阶段生产注册只有抽象接口。** 唯一用于证明成功执行的实现位于测试 fixture：轻量能力方法委托旧 ProcessSupervisor，不含漏洞/核验/风险算法。框架不承诺可安全执行任意 Python Agent；后续具体实现必须明确进程执行边界，不能用线程超时冒充进程停止。本阶段不新增自由工具循环、结果参数自动注入或模型调用。

## 5. AgentArtifact 与结构化交接

AgentArtifact 在独立文件中继承原 TaskArtifact，增加 agent_id、artifact_type、unresolved_items；原 artifact_id、run_id、task_id、status、result、evidence、confidence、tool_calls 和时间保持。

- artifact_type 固定映射 investigation_result / verification_result / security_analysis_result；它表示负责接口的类型，**不表示专业结论已产生或证据已确认**。
- `AgentArtifact.from_task_artifact(source: TaskArtifact, binding: AgentBinding) -> AgentArtifact` 必须重新验证 source，并保持原身份、结果、证据和置信度；unresolved_items 等于 unresolved_questions，不能丢弃 UNKNOWN 或待复核项。
- `AgentArtifact.to_task_artifact() -> TaskArtifact` 只投影原模型字段。旧 Runtime/worker 始终接收原模型，避免 extra=forbid 拒绝扩展字段。
- `build_handoff(task, context, dependencies, bindings) -> tuple[AgentArtifact, ...]` 只允许 task.dependencies 所列、同 run_id、相同 task_id、SUCCESS 的原 TaskArtifact；按依赖顺序输出，拒绝缺失、额外、重复 artifact_id 或错配绑定。
- Agent 输入/输出均检查 JSON 和大小；原 Artifact 512 KiB、worker wire 4 MiB、运行元数据 8 MiB 上限保持。扩展后超限明确拒绝，不截断证据。
- TaskArtifact 的工具结果/evidence 必须匹配原回执；测试不能用无回执的假 SUCCESS 解锁 tool_sequence。框架不得制造 facts、升级来源可信度或使用规划 confidence 填充情报 confidence。
- 本阶段不支持从前序结果重新改写后序 ToolStep 参数。交接是读取结构化结果，现有静态工具步骤与授权继续生效。

## 6. Agent Trace

新增类型化 AgentRunTrace：agent_id、agent_type、task_id、run_id、input_artifact（结构化引用列表）、output_artifact（结构化引用或 None）、execution_time（毫秒或 None）、status、attempted、capability_state、errors。新增 ProfessionalTraceSnapshot 保存这些节点及可解析的 AgentArtifact。

`ProfessionalTraceStore.read(run_id: UUID, actor: str) -> ProfessionalTraceSnapshot` 在单次数据库事务内读取同 actor、类型 runtime-v1 的运行；从已保存的 route.professional_agents_v1、TaskTrace 和 TaskArtifact 重建专业 Trace。

- 不新增表、Migration、AgentRun 子行或第二套工具调用记录；原数据库 AgentRun 仍表示完整 Runtime run，AgentRunTrace 表示其中专业节点。
- 绑定由原 create_run 原子保存，任务终态和回执由原 save_task 原子保存；不另做可能失配的专业结果双写。
- 原 Store 会把 Artifact.tool_calls 换成持久化 ToolCallRecord 引用；读取时从已保存的原 Artifact 生成扩展，不能保存执行前工具摘要当作权威回执。
- BLOCKED / 尚未开始节点 attempted=false，不能记录为“Agent 已执行”；input_required 不产生虚构专业节点。AGENT_NOT_IMPLEMENTED 节点 attempted=true、capability_state=interface_only、status=FAILED。
- 时间从原任务起止时间计算，未开始使用 None；真实成功测试节点可通过 input/output artifact_id 还原 A→B 链。输入引用只对应实际交接的成功依赖。
- 专业 Trace 是新增内部读取接口，原 read_trace 和旧 API 返回结构不变；不做前端页面。旧运行没有专业绑定时返回 AGENT_TRACE_NOT_AVAILABLE。

## 7. 涉及文件

所有路径相对项目根目录；以下为确认后的修改清单，不是已完成文件。

| 操作 | 文件 | 职责 |
| --- | --- | --- |
| 新增 | backend/app/agents/__init__.py | 最小公共导出 |
| 新增 | backend/app/agents/contracts.py | AgentContract、AgentBinding、BoundAgentPlan、错误及 Trace Schema |
| 新增 | backend/app/agents/interfaces.py | ProfessionalAgent 和三个抽象能力接口 |
| 新增 | backend/app/agents/registry.py | AgentRegistration、RegistrySnapshot、注册冲突检查及三个默认接口注册 |
| 新增 | backend/app/agents/router.py | 五种类型路由、工具交集、计划绑定 |
| 新增 | backend/app/agents/artifacts.py | AgentArtifact、AgentExecutionRequest、原模型投影及严格 handoff；输入 Schema 与 Artifact 放同文件避免循环导入 |
| 新增 | backend/app/agents/executor.py | 兼容 Executor、接口调用、取消及原验收 |
| 新增 | backend/app/agents/service.py | 同所有者 Planner 快照适配、专业 Runtime 子类 |
| 新增 | backend/app/agents/trace.py | 已存运行的专业 Trace 类型化投影 |
| **仅加兼容钩子** | backend/app/runtime/service.py | _make_scheduler 与原单处调用替换 |
| 新增 | backend/tests/agents/__init__.py、conftest.py、fixtures.py | 复用原专用测试库/提交型 fixture，受控接口实现 |
| 新增 | backend/tests/agents/test_contracts_registry.py、test_router.py、test_artifacts.py、test_executor.py、test_service_trace.py、test_end_to_end.py | 对应六组验收 |
| 新增 | work/agents/run_tests.py、check_baseline.py、baseline.json、ledger.md 及独立日志 | 实际测试证据及旧代码保护，不覆盖历史报告 |
| 新增 | PHASE_11A_RESULT.md | 用户要求的十节完成报告 |

Planner、DAG、Scheduler、原 Executor/worker/process/store、两种 Gateway、数据库模型及 Migration、旧业务和前端均不修改。不安装新的依赖。若实施发现必须超出清单，先给出具体原因和差异，不能自行扩展。

## 8. 实施步骤与实际验收

确认后先建立 `work/agents` 哈希基线和测试运行器，复用现有 `work/planner/run_tests.py` 的专库限制、JUnit/JSON/log 和历史报告恢复逻辑。只有测试时启动已存在的两个专用集群：提交型测试 55435、空库迁移回归 55437；不连接生产数据库或创建新部署。确认测试库名 aegis_phase5_test 后再运行。

下列命令在项目根目录执行，统一使用现有 `.venv`。每项先 RED 再 GREEN，记录失败原因与真实断言；不把环境缺失当作功能缺陷。阶段原有 643 项必须进入最终回归，新增数目不预设。

### Task 1：Contract、抽象接口与 Registry

**Files:** contracts.py、interfaces.py、registry.py、test_contracts_registry.py；同步创建本阶段测试证据运行器及基线。
**Interfaces:** `AgentRegistry.register(contract: AgentContract, interface: type[ProfessionalAgent], implementation: ProfessionalAgent | None = None) -> None`；`AgentRegistry.freeze() -> RegistrySnapshot`；`create_default_registry() -> AgentRegistry`。registry.py 定义 AgentRegistration 和 RegistrySnapshot；快照提供 `get(agent_id: str) -> AgentRegistration | None`、`for_task(semantic_type: str) -> AgentRegistration | None` 及只读 metadata，不暴露可修改嵌套字典。

- [ ] 编写 `test_default_registration_is_interface_only`：三个 ID 存在、supported_tasks 覆盖五种类型、implementation 为 None、三个能力类仍抽象。
- [ ] 编写 `test_registration_rejects_duplicate_or_overlap`、`test_contract_schema_and_tool_limits`、`test_snapshot_cannot_change_after_registration`：冲突明确拒绝、未知 Schema/工具及非法超时失败、修改原列表不影响快照。
- [ ] RED：`backend/.venv/Scripts/python.exe work/agents/run_tests.py task1_red -q tests/agents/test_contracts_registry.py`；期望缺少 app.agents 或断言失败，保存证据。
- [ ] 实现上述 Contract/接口/Registry，初始白名单严格按第 2 节；不创建专业业务方法体。
- [ ] GREEN：同命令使用 task1_green；预期全部通过，旧协议仍可独立导入。

### Task 2：类型路由与绑定

**Files:** router.py、test_router.py；复用 TaskContract、TASK_REGISTRY、compile_graph 和 Task 1 快照。
**Interfaces:** `AgentRouter(snapshot: RegistrySnapshot)`；`route(task, semantic_type) -> AgentBinding`；`bind_plan(plan: TaskPlan, semantic_types: dict[str, str], policy: RuntimePolicy) -> BoundAgentPlan`。BoundAgentPlan 提供 captured_plan: TaskPlan 和不可变绑定查询。

- [ ] 编写五类参数化 `test_router_selects_registered_capability`：lookup/version/patch→investigation，evidence→verification，risk→security_analysis。
- [ ] 编写 `test_unknown_type_returns_agent_not_found`、`test_agent_tools_do_not_expand_task_permission`、`test_binding_requires_exact_semantic_task_set`、`test_input_required_stays_unassigned`：未知拒绝，角色虽有某工具也不能突破当前语义任务白名单，少/多映射拒绝，补全节点不分配 Agent。
- [ ] RED：运行器 task2_red、`tests/agents/test_router.py`，保存真实失败。
- [ ] 实现路由和冻结绑定；图/权限/预算继续使用 compile_graph；错误类型统一 AgentFrameworkError(code)。
- [ ] GREEN：task2_green 同组全部通过；绑定前后原 task/input/dependencies/验收条件相同。

### Task 3：Artifact 扩展与交接

**Files:** artifacts.py、test_artifacts.py；使用第 5 节签名和 Task 2 的 AgentBinding。

- [ ] 编写 `test_agent_artifact_round_trip_preserves_provenance`：to_task_artifact 与原模型所有字段相等；artifact_id/证据/confidence 不变，unresolved_items 保留。
- [ ] 编写 `test_handoff_accepts_only_same_run_successful_dependencies`：A 的合格原 Artifact 到 B 的 typed input；错运行、错任务、额外依赖、WAITING_REVIEW、重复 ID 均失败。
- [ ] 编写 `test_handoff_revalidates_mutated_nested_data_and_size`：不可信嵌套修改、非法 JSON、扩展后超过512 KiB 明确拒绝，不产生截断结果。
- [ ] RED：task3_red、`tests/agents/test_artifacts.py`。
- [ ] 实现包装和原字段投影；成功 fixture 必须来自旧 WorkerExecutor 的受控 Gateway 回执，不伪造零回执 SUCCESS。
- [ ] GREEN：task3_green 同组全部通过；旧 TaskArtifact 解析拒绝额外字段这一行为不改变。

### Task 4：AgentExecutor 与受控执行链

**Files:** executor.py、test_executor.py、测试 fixtures.py；不修改原 Executor/ProcessSupervisor。
**Interfaces:** `AgentExecutor(bound: BoundAgentPlan, registry: RegistrySnapshot)` 实现原 execute/cancel_all；ProfessionalAgent 的三个方法使用第 4 节的 Request/Outcome。

- [ ] 编写 `test_registered_abstract_agent_returns_not_implemented`：默认注册返回 FAILED/AGENT_NOT_IMPLEMENTED、无工具回执、下游不能解锁。
- [ ] 编写 `test_executor_calls_capability_and_validates_receipts`、`test_executor_rejects_forged_success_or_evidence`、`test_executor_rejects_changed_dependency_refs`：受控能力方法被调用，合法回执成功，改写工具输出、证据、依赖引用或增加结果字段被拒绝，失败保留合法回执。
- [ ] 编写 `test_timeout_and_cancel_propagate_to_process_supervisor`、`test_executor_failure_is_sanitized`：慢 worker 及子进程实际终止、无延迟写入，异常不泄露私有字段。
- [ ] RED：task4_red、`tests/agents/test_executor.py`。
- [ ] 实现分派/缺实现/错误路径；只在测试中提供基于原 ProcessSupervisor 的具体实现，取消广播限本运行；依赖和授权先检查再调用。
- [ ] GREEN：task4_green；再联合运行 `tests/runtime/test_executor.py tests/runtime/test_process.py`，保留完整结果。

### Task 5：专业 Runtime 适配与 Trace

**Files:** service.py、trace.py、runtime/service.py 兼容钩子、test_service_trace.py。
**Interfaces:** 第 3 节的 ProfessionalRuntimeService.run_plan、RuntimeService._make_scheduler，第 6 节的 ProfessionalTraceStore.read；默认原 run/read_trace 不变。

- [ ] 编写 `test_default_runtime_hook_preserves_original_behavior`、`test_professional_runtime_reads_owned_validated_planner_types`：默认路径仍用原 Scheduler；显式新路径从已有 Planner 记录绑定，不凭 TaskContract.task_type 猜测。
- [ ] 编写 `test_forged_plan_binding_or_other_actor_is_rejected`、`test_registry_change_conflicts_on_same_request_key`：伪造 route、任务/类型不一致、其他所有者、同键变化均在工具执行前拒绝。
- [ ] 编写 `test_trace_rebuilds_chain_from_persisted_artifacts`、`test_concurrent_tasks_keep_canonical_tool_record_refs`、`test_blocked_and_interface_only_are_not_reported_success`：新 Reader 实例可读，回执 ID 对应数据库，不覆盖并发节点，未执行和未实现状态明确。
- [ ] RED：task5_red、`tests/agents/test_service_trace.py`，使用现有提交型专用测试库。
- [ ] 增加单一 Scheduler 工厂钩子及子类适配；专业 Reader 单事务读取、从存储后的原 Artifact 投影，不双写、不新增表。
- [ ] GREEN：task5_green；联合 `tests/planner/test_trace_service.py tests/runtime/test_store_compat.py`，实际现有测试路径已核对，不创建重复旧测试。

### Task 6：端到端、全量回归与交付

**Files:** test_end_to_end.py、work/agents 实证记录、PHASE_11A_RESULT.md。
**Interfaces:** 通过原 PlannerService 显式注入 ProfessionalRuntimeService；测试模型仍用原 Mock Provider，角色成功实现标记 TEST_ONLY，不进入正式默认 Registry。

- [ ] 编写 `test_planner_runtime_agent_artifact_chain`：真实 PostgreSQL + 旧隔离工具进程，lookup/get_vulnerability→evidence_search/get_evidence→risk_analysis/get_epss 跨三个测试接口。复用原 runtime_seed 并在新 fixture 中追加明确标记的 EpssSnapshot 合成记录；不是资产影响分析，不绕过资产四段链约束。typed handoff 的 artifact_id/run_id/证据可追踪，原静态工具输入没有被框架修改，evidence_search 保留原 evidence_present 验收。
- [ ] 编写 `test_interface_only_dependency_blocks_next_agent`、`test_repeat_request_does_not_reexecute_or_change_binding`：默认接口失败阻塞后续，同键/同绑定没有第二次执行；并发晚到请求不会覆盖终态。
- [ ] RED：task6_red、`tests/agents/test_end_to_end.py`；实现只修批准的框架适配，不增加实际安全算法。
- [ ] GREEN：task6_green、`tests/agents tests/runtime tests/planner tests/model_gateway`；再运行 `backend/.venv/Scripts/python.exe work/agents/run_tests.py reviewed_full_suite -q` 完整后端测试，实际统计新总数、失败/错误/跳过及耗时。
- [ ] 做一次最终只读审查；必要修复先复现再验证，涉及安全边界或代码变化则重跑相关组与最终全量；审查不允许扩展为具体 Agent 开发。
- [ ] 哈希核对既有代码仅 runtime/service.py 的批准钩子有变化，其他基线文件无删除/改变；测试完成后停止专用测试集群并保留证据。
- [ ] 写 PHASE_11A_RESULT.md 十节：实现内容、Agent Framework设计、Agent Contract、Registry设计、Router设计、Artifact变化、修改文件、测试结果、当前限制、下一阶段建议；区分正式抽象接口与测试专用实现，附实际日志路径。到此停止。

## 9. 风险和边界

| 风险 | 处理与交付边界 |
| --- | --- |
| 语义类型不在原 Runtime 协议中 | 新子类读取已存 Planner 记录并逐任务核对，不修改 Task Contract 或 Planner |
| “注册三个 Agent”被误解为“实现三个安全能力” | 接口 abstract、默认 implementation=None，AGENT_NOT_IMPLEMENTED 明确失败；成功链仅证明框架协议 |
| 抽象 Agent 未来可能执行无界代码 | 本阶段默认没有可执行生产实现，测试委托原进程监管；不宣称任意实现的隔离/超时已解决 |
| Schema 扩展与旧严格模型冲突 | AgentArtifact 仅在新包边界流转，旧 Runtime 始终接收投影后的原 TaskArtifact |
| 外部自然语言混入工具数据 | 保留公告/证据文本作为结构化字段，不将其变成 Agent 间消息或可执行命令 |
| 重复请求与新 Registry 版本 | 绑定快照参与原幂等哈希；版本/实现变化拒绝旧键，旧报告按旧快照解释 |
| Trace 与回执产生第二套不一致事实 | 不双写，单次读取原存储快照，保留原 ToolCallRecord 引用 |
| 原 Runtime 取消测试有历史瞬时失败 | 保留失败及复测证据，不声称已修复根因；若重现，先判断是否为本次适配引入 |
| 真实模型规划质量尚未评测 | 本阶段不新增模型推理，不把 Mock/测试协议当成真实准确率或比赛 Benchmark |

## 10. 计划覆盖与停止点

注册/查询/未知拒绝由任务 1–2 覆盖；Artifact A→B 由任务 3、6 覆盖；Executor 及原回执兼容由任务 4 覆盖；Agent Trace、Planner 接入和幂等由任务 5–6 覆盖。三个能力接口对应任务 1，实际业务全部留空。数据表、模型调用、网页和旧链路不进入修改范围。

**当前停止点：本计划待用户确认。** 确认后仅实施上述六项，不自行进入后续阶段；本计划不会把前置 643 项回归或测试专用能力写成本阶段生产完成证明。

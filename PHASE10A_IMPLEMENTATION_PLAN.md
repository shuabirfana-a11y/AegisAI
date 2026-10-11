# AegisAI Phase 10-A：Agent Runtime 基础框架实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在已有系统上增加有边界、可审计的任务运行时，完成 Task Contract、Artifact、DAG、Scheduler、Executor 和可展示的 Trace。

**Architecture:** 新增独立 `app.runtime` 包，复用现有 Query Router、DAG 校验函数、Tool Gateway、Model Gateway 和数据库模型。规则模板生成计划，调度器控制任务依赖与状态，受监管的任务进程执行工具调用。结果与轨迹写入已有运行记录，并提供现有 Assistant 读取接口所需的兼容视图。

**Tech Stack:** 已安装的 Python 3.12、Pydantic v2、SQLAlchemy、PostgreSQL、pytest，以及 Python 标准库的 subprocess、concurrent.futures、ctypes；不新增模型 SDK、调度框架或依赖。

**Spec:** 用户最新的 [Phase 10-A 指令](<C:/Users/X/.codex/attachments/55797d8c-2461-4bcb-9bc4-40ca55468cae/Pasted text.txt>)。前置实现见 [PHASE_9A_RESULT.md](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/PHASE_9A_RESULT.md)。

日期：2026-10-08。**当前仅完成源码检查与计划编写；本计划尚未实施，需用户确认。**

## Global Constraints

- 不重构或修改现有业务模块，不迁移旧 Embedding 调用点，不删除旧代码，不修改数据库结构。
- 不实现 LLM Planner、无限 ReAct、自我反思循环、新专业 Agent、新 Integration Gate 或前端动画。
- 不重新写安全工具、版本匹配、风险计算、证据核验和检索算法。
- 所有工具调用经过现有 Tool Gateway；未来显式模型调用必须经过已有 Model Gateway。
- 本阶段规则模板不调用生成模型；不需要付费 API，也不启动 Dify。
- 状态、Trace、Artifact 必须来自实际执行；测试 fixture 不能充当真实 CVE 或准确率 Benchmark。
- 超时必须终止实际任务工作及其子进程，不能仅使用 Future.cancel() 或只改变状态。
- 所有新增路径均相对于项目根目录 `C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9`。
- 当前工作目录无 Git；保留文件哈希与测试证据，不初始化仓库或编造提交记录。

## Review Focus

1. 工具失败、无结果或证据不足后，依赖任务不得继续给出确定结论；独立分支仍能完成。对应任务 3、5。
2. 并行任务不能超出全局调用预算，不能混淆 Task/Artifact/工具记录的身份。对应任务 1、4、5。
3. 超时后任务进程、工具子进程不能继续运行或产生迟到的成功结果。对应任务 3、5。
4. 与旧运行共用数据库后，幂等键、所有者和 JSON 结构不能互相污染。对应任务 4、6。
5. 原始来源、候选 PoC、未知影响范围不得自动升级为已核验事实或人为填写置信度。对应任务 1、3、6。

---

## 1. 当前检查结果

### 1.1 已有代码与复用范围

| 实际位置 | 已有能力 | Phase 10-A 决策 |
| --- | --- | --- |
| [assistant/contracts.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/assistant/contracts.py) | QueryRequest、三类专业角色的 TaskContract-v1、TaskArtifact-v1；已有依赖、权限、超时字段 | 复用 QueryRequest；新增 Runtime 通用协议，旧协议保持原样 |
| [assistant/router.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/assistant/router.py) | 确定性 Fast/Deep 路由、CVE/产品/资产识别、危险请求拒绝 | 直接调用 route()；新增固定任务模板，不写 LLM 规划器 |
| [assistant/graph.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/assistant/graph.py) | levels() 的 DAG 校验；run_graph() 的分层并行执行 | 复用 levels() 的算法；旧 run_graph() 的输出绑定旧角色，且线程取消不能保证终止，保持旧实现，不用它承担新的强制超时 |
| [assistant/orchestrator.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/assistant/orchestrator.py) | 已有确定性协调器、角色调用、结果整合 | 保持原运行链路；不迁移或替换 |
| [tooling/gateway.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/tooling/gateway.py) | 工具白名单、输入校验、服务端权限、调用预算、证据收据、进程执行；工具超时会 kill 工作进程 | 原样调用 ToolGateway.invoke()，增加外围任务进程监管 |
| [tooling/contracts.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/tooling/contracts.py) | 30 个注册工具、Pydantic 输入、ToolEnvelope 输出、permission | 由 REGISTRY 派生 ToolContract，不建立第二份工具实现或独立白名单 |
| [llm/gateway.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/llm/gateway.py) | Phase 9-A 的统一模型入口及调用审计 | 保留注入接口；当前任务模板不发起生成调用 |
| [db/models/application.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/db/models/application.py) | AgentRun、ToolCallRecord、AgentCitation，以及业务 ReviewTask/AuditLog | 复用前两张表；任务和 Artifact 放入 AgentRun 的版本化 metadata，不把业务复核表当调度日志 |
| [assistant/storage.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/assistant/storage.py) | 所有者读取、工具记录持久化、旧运行幂等与摘要 | 复用 record_tool()；新的幂等命名空间独立实现，避免旧 create_run() 跨 agent_type 查询造成碰撞 |
| [assistant/service.py](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/app/assistant/service.py) | 原运行启动，以及 read/tasks/trace 读取 | 不修改；新记录提供其需要的 goal、plan、result、events 等兼容字段 |
| [frontend assistant.js](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/frontend/public/modules/pages/assistant.js) | 提问、输入已有 Run ID、状态/任务/工具/事件表、证据展示 | 不修改；可以用已有 Run ID 读取入口展示新 Runtime 已保存的运行 |

**结论：** 当前已有任务协议、DAG 和确定性执行基础，不能说运行时完全空白。主要缺口是通用任务协议、明确状态机、任务级 Artifact/Trace，以及覆盖完整任务进程树的强制超时。

### 1.2 数据库检查

- `app.agent_runs`：支持 queued/running/succeeded/partial/failed/timeout/cancelled，具备 actor、context、metadata、运行时间和结果摘要。
- `app.tool_call_records`：支持工具序号、attempt、输入/输出、耗时、错误；已有 run + sequence + attempt 唯一约束。
- 未发现独立的 Runtime Task、Task Execution 或 Task Artifact 表。
- `ReviewTask` 关联业务 Claim；`AuditLog` 服务于业务审计，二者均不改作通用任务存储。
- 本次只检查模型、迁移和调用代码，未启动数据库、查询实时数据量或执行迁移。

## 2. 范围与接入方式

新增可调用的 `RuntimeService.run(request, actor)` 和 `run_plan(plan, actor, request_key)`，供后续服务层接入及本阶段真实集成测试使用。第一项接受已有 QueryRequest，第二项接受经服务端校验的显式计划。

**本阶段不切换现有 POST /api/v1/assistant/query。** 新服务执行后返回 run_id，现有 Assistant 页的“读取运行”入口及三个 GET 读取接口展示兼容记录。这满足基础框架的运行和 Trace 展示要求，同时遵守“不修改已有模块”。把现有提问按钮切换到新 Runtime，留待单独确认的服务接入阶段。

框架调用链：

```text
QueryRequest / 显式 TaskPlan
  → 现有 Query Router + 固定模板
  → TaskContract / 计划校验
  → 复用 levels() 的 TaskGraph
  → Scheduler（状态、依赖、预算、截止时间）
  → ProcessSupervisor → 固定 Task Worker → Executor
  → 现有 Tool Gateway → 既有安全业务 / Hybrid Retrieval
  → AgentRun + ToolCallRecord → Artifact / TaskTrace / 旧页面兼容视图
```

Model Gateway 作为后续扩展依赖保留，不在本阶段添加模型任务或自定义供应商调用。`model_called` 记录显式 Gateway 调用；已有检索工具内部的旧 Embedding 不迁移，也不冒充已接入新 Gateway。

## 3. 协议、预算与状态决策

### 3.1 Runtime 协议

使用 Pydantic，拒绝额外字段；严格限制身份、数量、数值与 JSON 数据。计划一经校验后不允许在运行中任意添加任务。

- **TaskContract**：用户要求的 task_id、task_type、description、input_data、dependencies、allowed_tools、expected_output、acceptance_criteria、max_tool_calls、timeout_seconds。
- `task_type` 首期只有 `tool_sequence` 和 `input_required`。后者只输出 required_fields/unresolved_questions，零工具预算并进入 WAITING_REVIEW，供缺少 CVE/资产输入的模板使用。
- **TaskPlan**：version 固定为 runtime-v1、tasks 为 1..16 个 TaskContract、route 为原 Router 输出的结构化摘要。Task/Artifact/Trace 的 run_id、artifact_id 使用 UUID；task_id 在 run 内唯一，不超过 64 字符。
- `input_data` 中的 `steps` 使用 `ToolStep(name, arguments)` 校验；只允许注册工具与常量参数，不接受 Python、shell、任意 SQL、代码表达式或动态 import。
- `expected_output` 首期使用已注册的 `ToolSequenceResult-v1`；结果包含工具结构化输出和依赖 Artifact ID，不只返回自然语言。
- `acceptance_criteria` 首期支持固定代码 `tools_succeeded`、`output_nonempty`、`evidence_present`。未知验收代码拒绝；自然语言描述不作为可执行判定。
- **TaskArtifact**：task_id、status、result、evidence、tool_calls、confidence、unresolved_questions；补充 artifact_id、run_id、errors、warnings 和执行时间。
- `confidence` 可空、数值有限且范围为 0..1。本阶段不推算置信度，默认 null；保留工具返回的专业字段，不能把执行成功变成安全判断成功。
- `evidence` 保留工具实际返回的来源、原文定位、版本与 verified 标记，验证属于本任务的工具收据；禁止自行升级 verified。
- **TaskTrace**：run_id、task_id、task_type、start_time、end_time、status、tools_called、model_called、error、artifact_id；追加依赖、状态转换、错误码和预算摘要。
- **ToolContract**：name、description、input_schema、output_schema、permission、timeout。输入来自 ToolSpec.input.model_json_schema()，输出来自 ToolEnvelope.model_json_schema()；权限仍由原 Gateway 执行。

### 3.2 固定限制

复用现有 16 个任务、8 层图深度、全局 32 次工具调用和 3 个并行任务的边界；默认 run 总预算 120 秒，单任务默认 30 秒、范围 1..60 秒。

每任务工具上限为 0..8；预先校验 steps 数量不超过任务预算，以及所有任务预留预算之和不超过 run 的 32 次预算。任务不能借用其他任务预算，也不自动重试；attempt 首期固定为 1。

输入 JSON 上限 64 KiB；任务进程输出协议上限 4 MiB；单 Artifact 上限 512 KiB；运行 metadata 上限 8 MiB。超过限制显式失败，不静默截断证据或生成成功摘要。Trace 不写数据库连接串、API Key、原始异常或隐藏思考过程。

### 3.3 状态机

文档中的 SUCCESS → FAILED → WAITING_REVIEW 改为分支终态：

```text
CREATED → PENDING → READY → RUNNING → SUCCESS
                               ├──→ FAILED
                               └──→ WAITING_REVIEW

PENDING / READY → BLOCKED（必需依赖没有 SUCCESS，或 run 预算已经耗尽）
```

- 增加 BLOCKED 表达“没有执行”，避免把依赖失败伪装成已经运行过的失败。
- FAILED 包含工具失败、任务超时和协议错误；错误码区分 TASK_TIMEOUT、RUN_TIMEOUT 等原因。
- WAITING_REVIEW 用于验收所需数据或证据不足；本阶段停在该状态，不自动创建业务 ReviewTask、重新规划或继续下游。
- 只有 SUCCESS 解锁依赖；独立分支不因某一分支失败而被全部取消。
- 终态不能被迟到结果覆盖；前置验证失败时零工具调用。
- Task SUCCESS 只表示约定任务及验收完成，不表示漏洞影响已确认。

## 4. 任务模板与现有工具映射

`build_plan(QueryRequest, RuntimePolicy)` 仅支持有边界的固定模板：单 CVE 查询、CVE 的 PoC/Patch 并行调查、明确 asset_id 的已有资产风险读取，以及结构化/语义检索。复用 route() 的拒绝规则；不支持的请求返回明确缺项，不启动自由规划循环。

| 用户示例 | 实际复用 |
| --- | --- |
| cve_search | get_vulnerability / search_vulnerabilities |
| version_match | match_component_vulnerabilities；需要明确 component_id 和服务端 WRITE 权限 |
| 影响版本查询 | relation_query / get_vulnerability 的 affected_versions |
| PoC / Patch 查询 | find_poc_candidates / find_patch_candidates，默认 refresh=false |
| 资产与风险解释 | get_asset、get_asset_risks、explain_asset_risk |
| SQL / Vector / Relation 检索 | 现有查询工具、semantic_search、relation_query |

默认规则模板只使用 READ_ONLY，不为回答问题自动刷新资产匹配。显式版本匹配计划可以调用原有写工具，但必须由服务端授予 WRITE；用户填写 allowed_tools 不能获得权限。涉及资产的调用始终带原 actor，继续使用既有所有者检查。

“调查某 CVE 是否影响我的 vLLM 服务”：缺少具体 CVE 或 asset_id 时输出缺项；已指定时读取漏洞、影响版本和该资产已有风险快照。没有风险快照或证据不足时保留不确定性，不输出“不受影响”。本阶段不重写风险分析器。

## 5. 真正终止超时工作的方案

现有工具进程超时终止已经可用，但不足以保证整个 Task 的强制停止。新增外围监管，执行固定 `app.runtime.worker`，worker 内继续调用原 Tool Gateway：

1. Scheduler 在实际开始执行时建立单调时钟截止时间：min(run_deadline, task_start + timeout_seconds)。排队时间受 run 总预算约束。
2. Windows 使用标准库 ctypes 封装 Job Object，设置 KILL_ON_JOB_CLOSE；任务进程先等待 stdin，加入 Job 后才发送请求，使后续工具子进程纳入同一进程树。
3. Linux 使用独立进程组；截止时间到达时终止整个进程组。
4. Gateway 的工具超时继续约束为任务剩余时间；外围监管也处理任务卡死、输出阻塞和进程树清理。
5. 监管失败时返回 TASK_ISOLATION_UNAVAILABLE，禁止降级成无法终止的线程执行。超时终止后回收进程与管道，清理预算最多 2 秒；清理失败必须显式报告，不能宣称成功终止。
6. worker 输出有限 JSONL 事件：tool_started、tool_finished、artifact。父进程校验任务身份、调用顺序和收据。超时前完整的记录保留，未完成调用写入中断错误，迟到 Artifact 不采纳。

Windows Job 的子进程继承与整组终止方式依据 [Microsoft 官方说明](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)；不启用允许子进程脱离 Job 的标志。进程超时后显式终止并回收，遵循 [Python subprocess 文档](https://docs.python.org/3.12/library/subprocess.html#subprocess.Popen.communicate)；communicate 的超时异常本身不等于进程已经停止。这些是拟采用的机制，仍需本阶段的真实进程测试证明实现有效。

数据库保存属于父进程的受控事务，不把“工具进程已停止”描述成“数据库操作已回滚”。默认只读模板避免副作用；显式写工具若已经提交，超时不会自动撤销，Trace 必须保留这种不确定性。持久化失败返回 STORE_FAILED，不能报告一个实际上未保存的成功运行。

## 6. 持久化与页面兼容

### 6.1 权威存储

- `AgentRun.agent_type = runtime-v1`。
- `AgentRun.details['runtime_v1']` 保存 request_key/request_hash、任务协议、Artifact、TaskTrace 和状态事件；整块重赋值，避免 JSONB 嵌套原地修改丢失。
- 新幂等查询同时限定 actor + agent_type + runtime_v1.request_key，并使用独立 advisory lock 命名空间。
- **不向新记录的 context 顶层写 request_key**；旧 create_run() 据此查询，新旧运行不会共享幂等键。
- 复用 record_tool() 写 ToolCallRecord；父进程分配 run 内唯一 sequence_no，并在 TaskTrace 中关联本任务调用序号及记录 ID。
- 并发结果由父进程协调持久化；每次写操作使用独立 Session 和行锁，不能跨线程共享 Session。
- 只读检索按 actor 限定；新 Store 的写入/读取进一步检查 agent_type。
- run 的数据库状态使用已有枚举，任务大写状态保存在 runtime_v1 JSON。全部成功 → succeeded；待复核 → partial；任务失败/超时按原因映射 failed/timeout。失败优先于待复核。

### 6.2 兼容投影

权威记录之外，由 trace.py 派生旧读取接口需要的字段：

- `details.trace_id`、`ui_status`、`route`、`plan`、`events`、`result`。
- plan 条目包含 `goal = description`；不修改旧 tasks() 读取代码。
- result.artifacts 提供任务结果、Artifact ID 和完整 TaskTrace；result 保留 evidence_refs、warnings、unresolved 等现有展示字段。
- UI 运行状态只使用 PLANNING/RUNNING/COMPLETED/WAITING_REVIEW/FAILED；任务真实状态单独保留。
- events 保留 task_id、状态和时间，并放入 Trace 字段，已有事件表可以展开查看。

先用现有 read/tasks/trace 方法和 API 契约实测兼容，再称“可展示”。不声称已经切换前端提问、实现 SSE 或实现动画。

## 7. 新增文件清单

**现有代码、配置、依赖声明、数据库模型、迁移、前端文件的修改清单为空。**

| 新增位置（相对项目根目录） | 唯一职责 |
| --- | --- |
| backend/app/runtime/__init__.py | 公共导出 |
| backend/app/runtime/contracts.py | Task/Artifact/Trace/Plan/Policy 与固定输出协议 |
| backend/app/runtime/tools.py | 从现有注册表派生 ToolContract |
| backend/app/runtime/planning.py | 调用旧 Router，生成固定规则计划 |
| backend/app/runtime/graph.py | 图构建、预算校验，包装已有 levels() |
| backend/app/runtime/states.py | 允许的状态转换及终态保护 |
| backend/app/runtime/executor.py | 调用原 Gateway，生成结构化 Artifact 与工具收据 |
| backend/app/runtime/worker.py | 固定任务进程入口与 JSONL 协议 |
| backend/app/runtime/process.py | Windows Job / Linux 进程组、截止时间、回收、输出上限 |
| backend/app/runtime/scheduler.py | READY 队列、并行执行、依赖解锁/阻塞、运行结束 |
| backend/app/runtime/store.py | Store 协议与既有 PostgreSQL 记录持久化 |
| backend/app/runtime/trace.py | 权威 Trace 与旧页面兼容投影 |
| backend/app/runtime/service.py | 从请求/显式计划到执行和已保存 run_id 的公共入口 |
| backend/tests/runtime/__init__.py、conftest.py、fakes.py | 新测试组织、严格限定测试数据库、可控 Gateway/Store 替身 |
| backend/tests/runtime/test_contracts_plan.py | Schema、预算、模板、工具映射 |
| backend/tests/runtime/test_graph_states.py | 图合法性与状态转换 |
| backend/tests/runtime/test_executor.py | Artifact、收据、工具错误、权限 |
| backend/tests/runtime/test_process.py | 真进程树终止与协议上限 |
| backend/tests/runtime/test_scheduler.py | 串行、并行、失败分支、全局预算 |
| backend/tests/runtime/test_store_compat.py | 真 PostgreSQL、幂等、所有者、旧读取兼容 |
| backend/tests/runtime/test_service_end_to_end.py | 请求 → 计划 → 实际 Gateway → Artifact → Trace |
| backend/tests/runtime/fixtures/slow_worker.py | 仅测试使用的受控阻塞/子进程 fixture，不开放给用户 |
| work/runtime/run_tests.py | 运行测试并保护旧报告，保存本阶段独立结果 |
| docs/AGENT_RUNTIME_IMPLEMENTATION.md | 接口、状态、实际测试与限制说明 |
| PHASE_10A_RESULT.md | 按用户指定格式填写真实完成报告 |

关键模块注释说明设计原因和扩展点，尤其是“为何不替换旧 Agent”“为何任务进程需要监管”“为何复用表而分版本存储”。

## 8. 按任务实施与验收

公共接口约定：

```python
build_plan(request: QueryRequest, policy: RuntimePolicy) -> TaskPlan
tool_contract(name: str, timeout_seconds: float) -> ToolContract
compile_graph(plan: TaskPlan, policy: RuntimePolicy) -> TaskGraph
transition(current: TaskState, target: TaskState) -> TaskState
WorkerExecutor.execute(task: TaskContract, context: WorkerContext,
                       dependencies: dict[str, TaskArtifact]) -> TaskArtifact
ProcessSupervisor.execute(task: TaskContract, context: WorkerContext,
                          dependencies: dict[str, TaskArtifact]) -> ExecutionOutcome
Scheduler.run(graph: TaskGraph, context: RunContext, store: RuntimeStore) -> RunOutcome
RuntimeService.run(request: QueryRequest, actor: str) -> RunSnapshot
RuntimeService.run_plan(plan: TaskPlan, actor: str, request_key: str) -> RunSnapshot
RuntimeService.read_trace(run_id: UUID, actor: str) -> TraceSnapshot
```

WorkerContext 是内部配置协议，承载 actor、服务端权限、预算、run/trace ID 和截止时间；数据库凭据仅通过子进程环境传递。RunContext 只由服务端创建，不由请求控制。ExecutionOutcome 包含已验证收据、Artifact 或执行错误；RunSnapshot 必须具有真实持久化的 run_id。

每任务先写失败测试、确认失败原因，再实现，最后实际运行。下面命令在项目根目录运行；run_tests.py 将 pytest 工作目录设为 backend，恢复旧数据库报告，另存 log/XML/JSON。未创建 runner 前，先在临时测试工作目录验证 runner 本身；不修改旧 conftest。

### 任务 1：协议、工具契约和规则模板

文件：contracts.py、tools.py、planning.py、公共导出；测试 test_contracts_plan.py；同时加入本阶段测试 runner。

接口：产生 TaskPlan、TaskContract、TaskArtifact、TaskTrace、RuntimePolicy、WorkerContext、RunContext、ExecutionOutcome、RunOutcome、RunSnapshot、TraceSnapshot；实现 build_plan()、tool_contract()。

- [ ] 写失败测试：完整字段往返；额外字段/NaN 置信度/重复工具/非法验收代码拒绝；注册表 schema 一致；实际工具名映射；缺 asset_id 生成零工具的 input_required 并保留缺项；规则模板生成模型调用数为零。
- [ ] 运行 `backend/.venv/Scripts/python.exe work/runtime/run_tests.py contracts tests/runtime/test_contracts_plan.py -q`，确认失败来自尚未实现的接口。
- [ ] 实现协议、固定模板和注册表投影；不复制任何安全业务逻辑。
- [ ] 重跑同一命令，要求全部通过、零跳过；保存文件基线和本任务证据。

### 任务 2：DAG 与状态机

文件：graph.py、states.py；测试 test_graph_states.py。

接口：消费任务 1 的 TaskPlan；实现 compile_graph()、transition()。graph.py 中 TaskGraphBuilder.add_task(task: TaskContract) 用于执行前添加任务，重复 ID 立即拒绝；compile() 输出 TaskPlan，再交由 compile_graph() 校验。TaskGraph 提供按 ID 只读索引、前驱/后继与已校验层级，执行中不再允许添加任务。

- [ ] 写失败测试：单任务/串行/分叉图；循环、缺失依赖、重复 ID、自依赖、17 个任务、9 层图、预算超过 32 次、未知工具均在执行前拒绝。
- [ ] 写失败测试：终态不能变更；RUNNING 分别进入三个终态；PENDING 因未满足依赖变为 BLOCKED；已经 READY 但整体截止时间到达的任务变为 BLOCKED 而不启动。
- [ ] 运行 `backend/.venv/Scripts/python.exe work/runtime/run_tests.py graph tests/runtime/test_graph_states.py -q`，确认失败。
- [ ] 包装已有 levels() 并实现状态转换，不复制拓扑算法、不修改旧 run_graph()。
- [ ] 重跑上述测试，要求通过且非法图零工具调用。

### 任务 3：Executor 与任务进程监管

文件：executor.py、worker.py、process.py；测试 test_executor.py、test_process.py、受控慢 worker fixture。

接口：消费 TaskContract、WorkerContext 和已成功的依赖 Artifact；实现 WorkerExecutor.execute()、ProcessSupervisor.execute()。

- [ ] 写失败测试：实际 Tool Gateway 的成功/partial/no_result/异常被正确包装；未授权工具/refresh 请求拒绝；伪造证据、错误任务 ID、非法 Artifact、超预算拒绝；无结果进入 WAITING_REVIEW。
- [ ] 写真实进程测试：worker 创建长期运行子进程；任务截止后两者停止，工具不能写入迟到标记，后续成功 Artifact 不采纳；输出超限/隔离创建失败/worker 崩溃有明确错误。
- [ ] 运行 `backend/.venv/Scripts/python.exe work/runtime/run_tests.py executor tests/runtime/test_executor.py tests/runtime/test_process.py -q`，确认失败。
- [ ] 实现原 Gateway 调用、结构化验收及进程树监管。stdout 只用于有限 JSONL 协议，诊断不能泄露凭据。父进程把收据与任务计划逐项对应。
- [ ] 重跑上述测试，要求主机平台的真实终止测试通过；Windows 上不能用模拟 Job Object 的测试替代实际停止证据。

### 任务 4：Artifact Store 与 Trace 兼容

文件：store.py、trace.py；测试 test_store_compat.py。

接口：RuntimeStore 提供 create_run(request_data, plan, actor, request_key)、save_task(run_id, task, artifact, trace, receipts)、finish_run(run_id, outcome)、read_trace(run_id, actor)。使用事务原子写入任务、工具记录和派生视图。

- [ ] 写失败测试：真实 PostgreSQL 保存并重新读取；同 key 同计划幂等，不同内容冲突；新旧同 key 互不影响；跨 actor 拒绝；JSON 重赋值确实落库；并发任务工具 sequence 唯一。
- [ ] 写失败测试：通过原 AssistantService.read/tasks/trace 读取新记录，不出现缺 goal、未知运行状态或丢失 Artifact/Trace 字段；数据库写失败不能返回成功。
- [ ] 运行 `backend/.venv/Scripts/python.exe work/runtime/run_tests.py storage tests/runtime/test_store_compat.py -q`，确认失败。
- [ ] 实现 agent_type/runtime_v1 命名空间、旧读取投影和 record_tool() 复用；不修改模型、迁移或旧存储模块。
- [ ] 重跑上述测试，使用原允许的专用 `aegis_phase5_test` 数据库，零跳过。进程测试所需 fixture 在此测试库中提交并按本次 ID 清理，不触及项目业务数据库。

### 任务 5：Scheduler

文件：scheduler.py；测试 test_scheduler.py。

接口：消费 TaskGraph、RunContext、RuntimeStore 及执行器；实现 Scheduler.run()。生产执行器固定使用 ProcessSupervisor；测试替身只能经内部依赖注入使用。

- [ ] 写失败测试：依赖成功后才 READY；PoC/Patch 用同步屏障证明重叠执行，不能只比较输出顺序；最多并发 3 个；总调用不超过 32。
- [ ] 写失败测试：一个任务失败或待复核则下游 BLOCKED，独立分支仍完成；run 超时关闭活动进程并阻塞待执行任务；错误注入后仍有 Artifact/Trace，不出现迟到状态覆盖。
- [ ] 运行 `backend/.venv/Scripts/python.exe work/runtime/run_tests.py scheduler tests/runtime/test_scheduler.py -q`，确认失败。
- [ ] 实现 READY 队列、依赖解锁、预留调用预算、截止时间和状态事件；不添加动态扩图、自动重试或自动恢复写操作。
- [ ] 重跑上述测试，验证全部任务具有一个且仅一个终态；对失败进程的清理有实际证据。

### 任务 6：Service、真实端到端验收与交付

文件：service.py、test_service_end_to_end.py、两份实施/结果文档。

接口：整合前五任务，实现 RuntimeService 的三个公共方法。构造时接受 engine、RuntimePolicy 和可选 ModelGateway；生成模型不在规则计划中使用，不创建新的对外提交入口。

- [ ] 写失败测试：原 QueryRequest → 固定计划 → 真实 Gateway → 数据库 → 可读 Trace；拒绝旧 Router 标记的危险请求；幂等请求不重复执行；按 actor 隔离。
- [ ] 写用户五项验收用例：单 CVE；CVE 查询 → 原 component 匹配工具 → 原资产风险查询；PoC/Patch 并行；循环拒绝；Gateway 故障后状态与独立分支正常。版本匹配用明确 component_id 和测试库中的 WRITE 授权，不能用假的匹配结果替代。
- [ ] 运行 `backend/.venv/Scripts/python.exe work/runtime/run_tests.py service tests/runtime/test_service_end_to_end.py -q`，确认失败。
- [ ] 实现服务与注释，完成真实 Gateway/专用数据库的集成测试；不改现有业务启动链路。
- [ ] 执行最终验收：`backend/.venv/Scripts/python.exe work/runtime/run_tests.py final tests/runtime tests/model_gateway tests/test_phase9_orchestration.py tests/test_phase9_api_storage.py -q`。全部真实运行、零失败、零错误；不把旧报告算成本次结果。
- [ ] 核对旧文件哈希、旧数据库报告已恢复；必要时用现有 Assistant 页的 Run ID 读取入口检查实际 Trace。只读浏览页面，不改页面或部署服务。
- [ ] 写 docs/AGENT_RUNTIME_IMPLEMENTATION.md 和 PHASE_10A_RESULT.md，列出执行命令、实际统计、日志路径、限制及尚未接入事项，随后停止。

## 9. 用户要求与验收证据对应

| 要求 | 验收依据 |
| --- | --- |
| Task Contract / Artifact / Tool Contract | 任务 1、3 的严格协议与收据测试 |
| DAG、缺依赖、工具权限 | 任务 2、3；非法输入零执行 |
| 串行与并行 | 任务 5；任务开始/结束记录及屏障证据 |
| Executor 不含安全业务 | 新 executor 只调用已有 Gateway；实际版本匹配由旧工具完成 |
| Artifact Store / Trace / 可前端展示 | 任务 4、6 的 PostgreSQL 重新读取、旧读取接口契约与 Run ID 展示 |
| 工具失败、任务失败、超时 | 任务 3、5 的错误码、状态、依赖阻塞与实际进程终止 |
| 测试真实通过 | 任务 6 的新日志/XML/JSON，不引用历史测试统计 |
| 不改旧模块、不扩大范围 | 原文件哈希核对；新增文件清单；无新依赖或迁移 |

## 10. 风险与当前阶段边界

1. Windows Job Object 需要在当前主机实际验证；若不能建立可靠隔离，停止该执行请求并报告，不采用虚假的强制超时。
2. 同步 RuntimeService 本阶段是可运行基础设施，尚未替换 Web 提问入口，也没有跨服务重启自动续跑。挂起记录的恢复策略留待后续设计。
3. 已提交的写工具副作用不会因外围超时自动撤销；失败测试验证边界并保留证据，不自动重试。
4. 任务 Artifact 使用现有 JSONB 有明确大小限制；超过限制报错。独立任务表、生产规模调度、分布式锁与日志归档不在本阶段。
5. 本机执行 Windows 的真实终止测试；Linux 路径如无可用测试环境，必须在结果里列为未验证，不能宣称跨平台验证完成。
6. 整个阶段不生成新的安全核验结论、不开发新风险引擎；执行状态和事实可信度分开记录。

## 11. 确认门与停止条件

当前交付只有本计划；没有写 Runtime 实现、安装依赖、启动服务、运行本阶段测试或修改现有代码。

用户附件第“四、开发前要求”明确规定：**“输出 PHASE10A_IMPLEMENTATION_PLAN.md，等待确认后开发。”** 因此此处等待确认实施本计划。

获得确认后按任务 1..6 实施；Task Contract、Artifact、DAG、Scheduler、Executor、Trace 及实际测试通过，输出指定完成报告后立即停止。后续 LLM Planner、专业 Agent 协作、Integration Gate 和前端提问入口切换需要新指令。

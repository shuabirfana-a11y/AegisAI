# AegisAI Phase 10-B：受约束 LLM Task Planner 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让模型生成结构化调查计划，经服务端类型、权限、输入范围、预算及 DAG 验证后，交由已完成的 Runtime 执行。

**Architecture:** 新增独立 `app.planner` 包。规划任务复用 Runtime TaskContract，并添加五种业务类型标签；验证后去除标签，转换为原 Runtime TaskPlan。Model Gateway 增加默认关闭的输出诊断回调，Planner 保存自身审计，现有运行链路保持原样。

**Tech Stack:** 已安装的 Python 3.12、Pydantic v2、jsonschema、SQLAlchemy、PostgreSQL、pytest 与现有 Model/Tool Gateway；不安装 SDK、模型或调度框架。

**Spec:** [用户 Phase 10-B 指令](<C:/Users/X/.codex/attachments/9411aea8-5f23-45f1-b43d-1e3aef27f2b3/Pasted text.txt>)。前置结果：[PHASE_10A_RESULT.md](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/PHASE_10A_RESULT.md)。

日期：2026-10-08。**状态：源码检查与方案完成，尚未实施。** 用户明确要求先输出本文件、等待确认后实施。本文件合并设计及实施步骤，确认后延续上一阶段的本会话顺序实施、一次最终独立审查流程。当前目录无 Git，不初始化仓库或编造提交。

## Global Constraints

- LLM 只生成候选计划，不直接调用工具、不访问数据库、不授予权限。
- 所有模型调用通过 Model Gateway 的 `generate_structured()`，不直接调用 Provider 或模型 SDK。
- 五种规划业务类型固定为 vulnerability_lookup、version_match、evidence_search、patch_analysis、risk_analysis。
- 复用原 TaskContract、compile_graph、Scheduler、Executor、Tool Gateway、风险/版本/核验算法及 Hybrid Retrieval。
- 不实现三个专业 Agent、新 Integration Gate、前端优化或长期学习；不迁移旧 Embedding。
- 一次初始规划、最多一次重试；验证失败不得开始工具执行，不用规则计划冒充 LLM 成功。
- Runtime 原有上限保持：16 任务、8 层、32 次预留工具调用、3 并行；单任务最多 8 调用，超时 1–60 秒；执行运行预算最多 120 秒。
- 默认 READ_ONLY、refresh=false，不因模型输出获得 WRITE、EXTERNAL_NETWORK 或 REVIEW_ACTION。
- Trace 保存执行事实及简短规划依据，不记录隐藏思考过程；规划自评置信度不成为情报可信度。
- 本轮仅新增本计划文件，不启动数据库、不调用模型、不修改正式代码。548 项通过是上一阶段的真实回归结果，不冒充本轮新测试。

## Review Focus

1. 模型偷偷更换 CVE、资产/组件 ID、产品版本，或删去必要依赖与验收条件：合法 JSON 仍须拒绝。任务 2、6。
2. 重试把不可信原始输出重新当成系统指令，或实际调用超过两次：只允许受控错误摘要和固定重试上限。任务 4。
3. 非法 JSON/Schema 在 Gateway 内被丢弃，或原始输出进入公共日志/默认返回值：需可追溯且隔离的可选诊断。任务 3、5。
4. 并发重复请求、旧 Agent 同键、权限变化后的缓存计划：不能多次调用模型、重复执行或跨所有者读取。任务 5、6。
5. 有真实模型调用却仍显示 generation_calls=0，或把 Mock、自评置信度、UNKNOWN 变成真实调查结论：审计必须对应调用记录。任务 4、5、6。

---

## 1. 当前架构适配分析

| 检查位置 | 当前事实 | 实施决策 |
| --- | --- | --- |
| `backend/app/runtime/contracts.py` | Runtime TaskContract 只有 tool_sequence / input_required；包含输入、依赖、白名单、验收、预算及期限 | 复用协议，不向 Executor 新增五套执行逻辑 |
| `backend/app/runtime/graph.py` | compile_graph 校验图、工具、参数、权限、预算，并生成不可变快照 | Planner Validator 最后必须调用此接口 |
| `backend/app/runtime/service.py:29` | run_plan 接收原 TaskPlan，校验、幂等、执行和持久化 | 新 PlannerService 调用它，旧 run()/网页 POST 不切换 |
| `backend/app/assistant/router.py` | 原 Router 返回目标、资产标记、产品、检索模式和拒绝结果 | 规划前调用；不能信任模型自行声明路由或授权 |
| `backend/app/llm/gateway.py:122` | generate_structured 支持 JSON Schema / Pydantic；失败 data=None，调用记录不含原文 | 增加可选输出诊断回调，解决失败原文审计缺口 |
| `backend/app/llm/providers/mock.py:26` | Mock 只返回配置的命名 fixture；没有 Planner 默认 fixture | 测试/固定离线示例显式注入 Planner fixture，标记 is_mock；默认 Mock 不伪装理解问题 |
| `backend/app/llm/config.py` | 默认 Mock、prompt_json、1024 输出 token；上限 4096 | 沿用配置，不自动切换模型、升预算或调用付费 API |
| `backend/app/llm/records.py` | 默认 JSONL 只保存脱敏调用元数据，无 prompt/原始输出 | 保持默认日志约定，Planner 原文另存私有审计 |
| `backend/app/runtime/trace.py:34` | 兼容投影硬编码 generation_calls=0 | 仅在存在服务端生成的 Planner 调用摘要时改为真实计数；原规则路径继续为 0 |
| `backend/app/tooling/contracts.py` | 已有真实注册工具，无名为 cve_search / nvd_query / Asset Resolver 的新工具 | 名称映射到原工具，Task Registry 不替代 Tool Registry |
| `backend/app/assets/identity.py` / `matching.py` | resolve_component 是身份识别；match_component_vulnerabilities 需要已有 component_id 和 WRITE，可能写 Claim/Evidence | 不能把身份解析称为已完成版本匹配，也不能自动创建资产或刷新风险 |

尚无集中式业务 Prompt 管理。现有 Adapter 仅附加 Schema 提示，本阶段新增版本化 Planner Prompt 文件。

检查终端实际配置：provider=mock、structured_mode=prompt_json、输出预算=1024；未调用 Provider。Runtime TaskContract Schema 约 1.4 KiB，新增包装 Schema仍须经过 Gateway 的 64 KiB/复杂度限制。

## 2. 设计选择

| 路线 | 代价 | 结论 |
| --- | --- | --- |
| 规划业务类型标签 → 验证 → 原通用执行任务 | 增加转换和角色白名单，执行层稳定 | 采用 |
| 修改 Runtime 类型及 Executor 为五类任务 | 改动已经验收的执行、工作进程和状态链路 | 不选 |
| 模型直接选择整个 Tool Registry | 缺少业务角色和必要依赖约束，审计难解释 | 不选 |

实际调用链：

```text
PlannerInput → 原 Query Router / 可信输入范围
→ LLMTaskPlanner → Model Gateway.generate_structured
→ PlannerPlan → Schema / Type / Scope / Permission / Coverage / DAG Validation
→ 原 Runtime TaskPlan → RuntimeService.run_plan → 既有 Scheduler / Executor
                         ↘ PlannerRun 与 Runtime run_id 关联
```

新入口为显式调用的 `PlannerService.plan_and_run()`。原 Assistant POST 和确定性 RuntimeService.run() 保持原行为；前端正式切换留待后续指令。

## 3. Schema 与接口决策

`PlannerTaskContract` 继承原 Runtime TaskContract，仅新增 `planner_type`，JSON 别名为 `type`，取上述五种 Literal。原 `task_type` 仍为 tool_sequence/input_required。其他原字段、约束及结构化工具步骤保持原样。

`PlannerPlan` 包含用户要求的 plan_id、objective、tasks、reasoning_summary、confidence：

- plan_id 为 UUID；模型提供的 ID 仅是候选标记。权威 PlannerRun ID 由服务端生成，不能用模型 ID 读取或覆盖其他记录。
- objective 1–500 字符，reasoning_summary 1–600 字符，仅简短解释步骤用途。
- tasks 为 1–16 个 PlannerTaskContract，整份候选 JSON 最多 64 KiB。
- confidence 是必填、有限的 0–1 浮点数，标记为未经校准的规划自评，仅留在 Planner Trace；不复制到 TaskArtifact.confidence、Evidence 或风险评分。
- 拒绝额外字段、重复 JSON 键、NaN/Infinity、非法 Unicode、任意代码/SQL/URL执行及未知任务类型。

`PlannerInput` 包含原 QueryRequest，以及可选 component_id、snapshot_id、component（复用原 ResolutionInput）。actor 从服务端认证另传，不属于模型输入的授权字段。

`PlannerContext` 是服务端快照：planner_run_id、trace_id、actor、RuntimePolicy、原 Router 结果、输入范围、Prompt/Registry 版本及实际模型调用元数据（初始为空）。只给模型发送目标和可用能力摘要，不发送认证 Token、连接串或 API Key。`ModelIdentity` 仅含 provider、model、is_mock，来自 Gateway 配置，不包含地址或 Key。

`context.py` 只提取明确的 CVE/已传入 ID、已提供组件字段及有限的“已识别产品 + 明确版本”片段；不比较版本或猜测资产。无法确定唯一版本时保留缺项。

转换：去掉每个任务的业务标签，重新校验为原 TaskContract，使用可信 Router/实际模型调用元数据建立原 TaskPlan，调用 compile_graph。ValidatedPlan 保存不可变 JSON 快照、业务类型映射、验证版本及计划摘要；使用前重新校验，不能继续使用可变的模型对象。

`PlanningOutcome` 包含 status（VALIDATED / PLANNING_FAILED）、validated_plan（ValidatedPlan 或 null）、issues 和 attempts。`PlannerSnapshot` 包含 planner_run_id、trace_id、planning_status（PLANNING / VALIDATED / PLANNING_FAILED）、可空 runtime_run_id/runtime_status。执行运行状态仍由原 Runtime 决定，不能因规划通过标成执行成功。缺项通过已有 input_required 表达。

## 4. Task Registry 与缺项处理

Registry 只规定业务任务能使用哪些原工具、最低验收及前置依赖，不创建工具实现。

| 业务类型 | 原工具白名单 | 额外限制 |
| --- | --- | --- |
| vulnerability_lookup | get_vulnerability、search_vulnerabilities | 精确查询绑定输入 CVE；列表查询绑定已知产品/过滤范围 |
| version_match | resolve_component、relation_query；显式授权时 match_component_vulnerabilities | 前置漏洞查询；真实匹配必须有输入 component_id + WRITE |
| evidence_search | get_evidence、get_claims、relation_query、semantic_search | 查询证据任务最低要求 evidence_present；依赖目标来源明确 |
| patch_analysis | find_vendor_advisories、find_patch_candidates | 前置漏洞查询，refresh=false；保持 source_assertions_only / candidate 警告 |
| risk_analysis | get_asset_risks、explain_asset_risk、get_epss、get_known_exploitation | 资产绑定输入 asset_id；解释绑定输入 snapshot_id；资产版本问题须依赖版本任务及漏洞查询 |

每种实际工具任务最低验收为 tools_succeeded + output_nonempty；模型不得删除、以空数组绕过或用自然语言替代。input_required 必须零工具、零调用预算，required_fields 只能选择服务端确认缺失的字段。

input_required 的字段限于 target、asset_id、component_id、snapshot_id、version、write_authorization；不得索取密码、Token、任意路径或模型自行添加的字段。version_match 实际工具任务必须包含已授权的 match_component_vulnerabilities，resolve_component/relation_query 只能辅助；否则只能声明缺项，不允许用身份查询解锁资产风险结论。

“我的 vLLM 0.6.0 是否受某 CVE 影响”：

- 有确切 component_id/asset_id 且服务端明确授予 WRITE：可规划漏洞查询→原组件匹配→读取原风险快照；不声称匹配已经刷新风险。
- 缺 ID 或缺少需要的授权：规划中保留 version_match 类型的 input_required，风险任务依赖它，执行时等待复核并阻塞下游。
- resolve_component 成功仅代表身份识别，不能替代版本匹配；没有风险快照或证据时保留不确定性。
- 未实现跨任务动态参数绑定。模型不能引用 `$T1.result.id`、Python表达式，或编造 UUID 来填充后续输入；需要发现的新 ID 时明确缺项，等待新的请求。

## 5. Validation

验证顺序固定，任何一步失败均不得调用工具：

1. Gateway 严格 JSON + PlannerPlan Schema/Pydantic 验证；Validator 再验证候选快照及大小。
2. 五种业务类型与 Registry 白名单校验，包括 allowed_tools 本身，不能靠“当前没用到”混入其他工具。
3. 参数按原 ToolSpec.input 校验，禁止新增参数/表达式/refresh；核对 CVE、资产、组件、快照、产品与版本输入范围。
4. 最低验收、问题所需任务覆盖和前置依赖检查。版本/资产影响问题不能只生成漏洞查询；必要依赖必须存在于祖先链。
5. 转换原 TaskContract，交给 compile_graph 检查循环、缺依赖、重复 ID、权限、任务数、层数、调用预算及参数。

ValidationIssue 只包含固定错误码、字段路径、受控描述。不能直接记录/回传 Pydantic 异常字符串以泄露输入或将外部文本变成指令。

## 6. 原始输出、失败与 Planner Trace

### 6.1 Model Gateway 的最小扩展

新增 `app.llm.diagnostics`，定义有界 StructuredOutputDiagnostic 和可调用的 observer 协议。扩展接口：

`generate_structured(request, *, output_model=None, output_observer=None)`。

默认 None，既有返回 Schema、默认 JSONL 日志及原调用行为保持。回调在 Provider 已返回文本、Gateway 尚未进行 JSON/Schema 检查时收到诊断；包括 request_id、trace_id、原输出、字节数、摘要及 redacted/truncated 标记。响应被截断或 JSON/Schema 错误也可审计；没有收到文本则记录 raw_output=null 与明确原因，不伪造原文。

输出诊断最多 64 KiB，超长内容显式标为截断并保留完整长度/摘要；已知模型 API Key 必须脱敏。诊断不进入默认 ModelResult/CallRecord、公共日志或旧运行投影。observer 异常使本次调用失败 AUDIT_WRITE_FAILED，不允许成功计划绕过审计。

### 6.2 重试

初次结构化输出不合格时，记录原诊断及 ValidationIssue，再请求一次完整结构化计划。重试只附加受控错误码/路径，使用相同可信上下文与白名单；不把模型原文或检索内容插入系统指令。

第二次仍不合格返回 PLANNING_FAILED，retry_count=1。永久性认证/配置/不支持能力/拒绝/审计故障立即受控失败；明确可重试的超时、连接或供应商错误最多一次重试。所有情形 Model Gateway 调用不超过两次，不调用 generate_text、不直接 Provider 重试、不悄悄切换供应商或执行规则备用计划。

max_output_tokens 不超过现有模型配置和 4096。实际 Provider 调用数使用 ModelResult.attempt_count 汇总，不能把调用前验证失败计为真实模型推理。沿用 Gateway HTTP/I/O 超时；它不等于规划总墙钟强制期限，Runtime 的 120 秒执行预算也不包含规划。本阶段不新增规划进程监管器。

### 6.3 持久化与幂等

复用 AgentRun，agent_type=planner-v1，私有数据放在 details.planner_v1，不新增表/Migration。PlannerRun 至少保存 id、user_query、model、prompt_version、generated_plan、validation_result、retry_count、latency；补充 actor、provider、is_mock、每次 request_id/usage/error/诊断、任务类型映射及关联 runtime_run_id。

服务端在模型调用前以 actor + planner-v1 + request_key 建立唯一规划行，使用独立 advisory lock 命名空间。请求摘要包括输入、权限/预算、Prompt/Registry 版本及模型身份；同键不同内容冲突。并发重复返回已存在的规划状态，不能重新调用模型。

新行 context 顶层不写 request_key，避免旧 Agent 幂等碰撞。读取按 actor 和 agent_type 限定；原始输出只通过内部所有者限定的 Planner Trace 读取，不加入旧公共事件摘要。

已通过计划的后续执行使用由服务端 PlannerRun ID 派生的固定运行键；原 Runtime 保证不重复执行。缓存计划使用前重新按当前策略校验，权限收紧不能沿用已失效授权。审计保存失败返回受控失败，零工具执行。

Runtime route 只附加服务端产生的规划 ID及脱敏调用摘要。trace.py 据此产生 model_called 事件和实际 generation_calls；TaskTrace.model_called 仍为空，因为模型调用发生在规划阶段，不能复制成每个执行任务都调用了模型。没有 Planner 摘要的原运行继续零生成调用。

## 7. 文件计划

| 文件 | 新增/修改 | 职责 |
| --- | --- | --- |
| backend/app/planner/__init__.py | 新增 | 独立包，不自动启动 |
| backend/app/planner/interface.py | 新增 | TaskPlanner / PlannerTraceSink 协议 |
| backend/app/planner/schemas.py | 新增 | 输入、上下文、候选、验证结果、Trace/Snapshot |
| backend/app/planner/context.py | 新增 | 原 Router 与明确输入范围快照 |
| backend/app/planner/registry.py | 新增 | 五种业务类型、原工具白名单及最低要求 |
| backend/app/planner/validator.py | 新增 | 类型/范围/依赖/权限验证与 Runtime 转换 |
| backend/app/planner/llm_planner.py | 新增 | Gateway 结构化调用、受控重试与失败 |
| backend/app/planner/prompts/task_plan_v1.txt | 新增 | 可审计的固定 Prompt 版本 |
| backend/app/planner/trace.py | 新增 | PlannerRun 原表持久化、所有者、幂等和脱敏摘要 |
| backend/app/planner/service.py | 新增 | 显式规划→原 Runtime 接入 |
| backend/app/llm/diagnostics.py | 新增 | 有界可选输出诊断协议 |
| backend/app/llm/gateway.py:122/139 | 最小修改 | 可选 observer；原接口调用默认行为保持 |
| backend/app/runtime/trace.py:9/34 | 最小修改 | 规划模型摘要及真实计数，原规则路径保持 |
| backend/tests/planner/ | 新增 | 6 个测试模块及专用 fixture/辅助数据 |
| work/planner/ | 实施后新增 | 哈希基线、执行账本、测试运行器与独立日志 |
| PHASE_10B_RESULT.md | 验收后新增 | 按用户八项标题输出结果 |

正式源码的已有文件修改仅上表两处；不修改 Runtime contracts/graph/service/scheduler/executor/store、Provider Adapter、Tool Gateway、检索/资产业务、数据库结构、配置或前端。测试使用显式 Mock fixtures 或回环 HTTP，不在生产 Provider 塞入固定答案。

## 8. 实施步骤

确认后逐项执行 RED→GREEN。每个 Task 的验证命令从项目根目录运行 `backend/.venv/Scripts/python.exe work/planner/run_tests.py <证据名> <下述测试选择> -q`。新运行器仅调用 pytest、输出独立 JSON/XML/log，并恢复旧 database_test_report.json / database_migration_result.json；不覆盖上一阶段证据。

### Task 1：规划协议、上下文与 Registry

**Files:** Create planner/__init__.py、interface.py、schemas.py、context.py、registry.py，以及 tests/planner/__init__.py / fixtures.py；Test tests/planner/test_schemas_registry.py。fixtures.py 提供有明确合成标签的 valid_plan、PlannerInput/Context 和受控模型响应构造器，不调用数据库或模型。

**Interfaces:** 消费 QueryRequest、Runtime TaskContract/Policy、ResolutionInput、原 route/REGISTRY；产出 ModelIdentity、PlannerInput、PlannerContext、PlannerTaskContract、PlannerPlan、ValidatedPlan、PlanningOutcome、PlannerSnapshot、ValidationIssue、PlannerAttempt、PlannerRunTrace 和固定 Registry。ValidatedPlan 含 runtime_plan_json、业务类型映射、validator_version、plan_hash；PlannerAttempt 含脱敏 ModelResult 元数据、诊断、ValidationIssue 和 attempt_index（1或2）。

示例测试的共用构造器由 fixtures.py 定义：valid_plan() 返回完整合成候选字典；cve_input() 返回带唯一 request_key 的 PlannerInput；context_for(target) 返回对应输入范围的服务器 Context。gateway_with_text / structured_request 在任务 3 引入；planner_with_responses 与内存 sink 在任务 4 引入；真实数据库 service/count 辅助函数在任务 5–6 引入，均只属于测试。

- [ ] 定义失败测试：未知 type、额外授权字段、非法 confidence/UUID/大 JSON、原 TaskContract 预算违规拒绝；五类类型可生成 Schema，Context 不含凭据，Registry 工具必须全部来自原注册表。

```python
def test_unknown_type_and_nonfinite_confidence_are_rejected():
    bad = valid_plan()
    bad['tasks'][0]['type'] = 'unknown'
    with pytest.raises(ValidationError): PlannerPlan.model_validate(bad)
    with pytest.raises(ValidationError):
        PlannerPlan.model_validate({**valid_plan(), 'confidence': float('nan')})
```

- [ ] 运行 `tests/planner/test_schemas_registry.py`，预期缺少 planner 实现而失败。
- [ ] 实现以上协议与 `build_context(input: PlannerInput, actor: str, policy: RuntimePolicy, planner_run_id: UUID, trace_id: UUID) -> PlannerContext`；上下文使用独立 JSON 快照。
- [ ] 重跑同一测试，预期全部通过。记录命令/结果及新增文件哈希；无 Git 提交。

### Task 2：Validator 与 Runtime 转换

**Files:** Create planner/validator.py；Test tests/planner/test_validation.py。

**Interfaces:** 消费 Task 1；产出 `validate_plan(plan: PlannerPlan, context: PlannerContext) -> ValidatedPlan`；失败通过受控 PlanValidationError.issues 返回，无模型/工具调用。

- [ ] 定义失败测试：未知工具、越类型白名单、擅自 WRITE/refresh、替换 CVE/资产/组件/版本、移除最低验收、遗漏版本依赖、环/缺依赖/重复/超预算、表达式参数、伪造缺项均拒绝。

```python
def test_schema_valid_target_substitution_is_rejected():
    plan = valid_plan()
    plan['tasks'][0]['input_data']['steps'][0]['arguments']['target'] = 'CVE-2099-8888002'
    with pytest.raises(PlanValidationError):
        validate_plan(PlannerPlan.model_validate(plan), context_for('CVE-2099-9999001'))
```

- [ ] 运行 `tests/planner/test_validation.py`，预期缺少 Validator 而失败。
- [ ] 实现固定验证顺序，复用原 ToolSpec.input 和 compile_graph；合法计划转为原协议，保留 semantic type 映射、不可变快照。
- [ ] 重跑同一测试，预期全部通过；验证缺组件计划得到 input_required，不能被解析成功的 resolve_component 冒充已匹配。

### Task 3：可选 Gateway 输出诊断

**Files:** Create llm/diagnostics.py；Modify llm/gateway.py；Test tests/planner/test_gateway_diagnostics.py。

**Interfaces:** 产出 StructuredOutputDiagnostic / observer 协议；generate_structured 新增可选 output_observer，其他返回类型与接口保持。

- [ ] 定义失败测试：非法 JSON、Schema 错误、截断输出仍有真实诊断；无响应明确 null；超长/已知 Key 脱敏标记；observer 异常失败；默认返回/日志不包含原文。

```python
def test_invalid_json_remains_failed_but_has_private_diagnostic():
    captured = []
    result = gateway_with_text('{bad').generate_structured(
        structured_request(), output_model=PlannerPlan, output_observer=captured.append)
    assert result.status == 'failed' and result.error.code == 'INVALID_JSON'
    assert len(captured) == 1 and captured[0].raw_output == '{bad'
    assert '{bad' not in result.model_dump_json()
```

- [ ] 运行 `tests/planner/test_gateway_diagnostics.py`，预期新参数/诊断缺失而失败。
- [ ] 实现只在结构化生成显式传入时启用的回调；不改 Provider Adapter、不扩大默认日志。
- [ ] 运行 `tests/planner/test_gateway_diagnostics.py tests/model_gateway`，预期新测试与既有 89 项均通过。

### Task 4：LLM Planner、Prompt 与受控重试

**Files:** Create planner/llm_planner.py、prompts/task_plan_v1.txt；Test tests/planner/test_llm_planner.py。

**Interfaces:** `TaskPlanner.plan(input: PlannerInput, context: PlannerContext) -> PlanningOutcome`；只读属性 model_identity: ModelIdentity、prompt_version: str、registry_version: str；`LLMTaskPlanner(gateway: ModelGateway, trace_sink: PlannerTraceSink)`；sink 的 `record_attempt(context: PlannerContext, attempt: PlannerAttempt) -> None` 由 Task 5 持久化。

- [ ] 定义失败测试：简单 CVE 返回 vulnerability_lookup；复杂问题产生规定的依赖链或明确缺项；首错次对恰好两次调用；连续非法返回 PLANNING_FAILED/retry_count=1；模型异常受控降级；永久错误不重试。

```python
def test_two_invalid_attempts_stop_before_tool_execution():
    planner, gateway_calls, sink = planner_with_responses(['{bad', '{bad'])
    outcome = planner.plan(cve_input(), context_for('CVE-2099-9999001'))
    assert outcome.status == 'PLANNING_FAILED' and outcome.validated_plan is None
    assert len(gateway_calls) == 2 and len(sink.attempts) == 2
```

- [ ] 运行 `tests/planner/test_llm_planner.py`，预期 Planner 缺失而失败。
- [ ] 通过 generate_structured(output_model=PlannerPlan, output_observer=...) 实现；记录每次真实调用，用 Gateway 返回的实际元数据形成新的 Context 快照再执行 validate_plan；Prompt 含版本/白名单/Schema/缺项/预算规则；不调用工具。
- [ ] 重跑同一测试，预期通过；断言修复提示只含固定错误摘要、不回灌恶意原文、不超过两个 Gateway 调用、审计失败零工具。

### Task 5：Planner Trace、幂等及显式 Runtime 接入

**Files:** Create planner/trace.py、service.py；Modify runtime/trace.py；Test tests/planner/test_trace_service.py。

**Interfaces:** `PlannerTraceStore(engine).create(input: PlannerInput, actor: str, policy: RuntimePolicy, *, model_identity: ModelIdentity, prompt_version: str, registry_version: str) -> tuple[PlannerSnapshot, bool]`；record_attempt 同 Task 4；`complete(planner_id: UUID, actor: str, outcome: PlanningOutcome) -> PlannerSnapshot`、`link_runtime(planner_id: UUID, actor: str, runtime: RunSnapshot) -> PlannerSnapshot`、`read(planner_id: UUID, actor: str) -> PlannerRunTrace`。`PlannerService(engine, planner: TaskPlanner, runtime: RuntimeService, policy: RuntimePolicy)` 提供 `plan_and_run(input: PlannerInput, actor: str) -> PlannerSnapshot`、`read_trace(planner_id: UUID, actor: str) -> PlannerRunTrace`。策略必须与传入 Runtime 一致；创建成功后用返回 ID建立 Context；缓存的 VALIDATED 计划仍须重新验证，然后用派生运行键调用原 Runtime。

- [ ] 定义失败测试：真实持久化全部规定字段、并发同键仅一个 fresh、异主读取拒绝、旧 Agent 同键不碰撞、审计保存失败不执行、缓存计划重新验权、既有无 Planner 投影保持零调用。

```python
def test_other_owner_cannot_read_planner_diagnostics(engine):
    service = planner_service_with_mock(engine)
    saved = service.plan_and_run(cve_input(), actor='planner-synthetic-owner')
    with pytest.raises(LookupError):
        service.read_trace(saved.planner_run_id, actor='other-owner')
```

- [ ] 运行 `tests/planner/test_trace_service.py`，预期新 Store/Service 缺失而失败。
- [ ] 复用 AgentRun/transaction/lock，原表版本化命名空间；显式调用原 RuntimeService.run_plan，固定服务端派生键，保存运行关联。投影只包含脱敏模型摘要及真实调用数。
- [ ] 重跑同一测试，预期通过；工具执行失败不能抹掉先前规划记录，重复请求不能重新规划或执行；模型计数与 ModelResult 记录一致。

### Task 6：端到端验收、完整回归与结果报告

**Files:** Create tests/planner/test_end_to_end.py、专用 conftest/fixture、work/planner/run_tests.py、PHASE_10B_RESULT.md。

**Interfaces:** 消费 Task 1–5，使用真实 Gateway/Runtime/数据库，受控 Mock 或回环 HTTP 仅替代模型响应。

- [ ] 定义并先运行五种用户要求场景的失败断言：单 CVE；有合法输入和授权的版本链；unknown task；越权工具；模型失败。扩展真实原文失败审计、版本缺项阻塞、重复请求与原认证 GET 兼容。

```python
def test_planning_failure_creates_no_runtime_or_tool_calls(engine):
    service = planner_service_with_invalid_responses(engine)
    before = runtime_and_tool_counts(engine)
    saved = service.plan_and_run(cve_input(), actor='planner-synthetic-owner')
    assert saved.planning_status == 'PLANNING_FAILED' and saved.runtime_run_id is None
    assert runtime_and_tool_counts(engine) == before
```

- [ ] 运行 `tests/planner`，预期未完成连接时明确失败；不把已有绿色单测伪装成端到端 RED。
- [ ] 完成仅限计划的连接和测试夹具。复用 Runtime 的隔离 fixture；Runtime/Planner 提交型记录与旧空库迁移测试使用不同 test cluster，库名均为 aegis_phase5_test。
- [ ] 运行 `tests/planner tests/runtime tests/model_gateway`，预期全部通过、零跳过；随后完整 `pytest -q`，预期既有 548 项全部保留，新测试通过。实际数目与耗时写入报告，不预填通过数字。
- [ ] 一次新上下文只读最终审查，修正重要问题用复现 RED→GREEN，再完整回归；不追加实现 Agent/Integration Gate/前端。
- [ ] 生成 PHASE_10B_RESULT.md：实现内容、Planner架构、Task Schema、Validation机制、修改文件、测试结果、当前限制、下一阶段建议；核对旧文件只有两处计划修改，其余一致。

## 9. 风险与验收

1. 本机检查为 Mock 配置，现有默认 Mock 不提供任意 Planner 答案。测试/固定示例需显式 fixture；真实 LLM 语义规划质量必须在配置真实服务后另验，回环或 Mock 不能计入准确率 Benchmark。
2. prompt_json 只意味着供应商通过提示词接收 Schema；本地 Gateway/Planner 验证始终执行。json_schema 模式取决于实际供应商支持，不自动更改配置。
3. 可选诊断是本阶段必要的 Gateway 小改动，重点回归原 89 项；原文有界且私有，默认审计仍只保留元数据。
4. 匹配组件与风险快照读取的输入/权限不能省略；缺项与 UNKNOWN 不变成“安全”。首期无动态参数绑定、风险重算、Planner 自动续跑。
5. 规划供应商 I/O 超时不等于严格总墙钟期限；执行进程树期限继续由 Phase 10-A 保证。模型费用和耗时由实际 usage/latency 记录，不猜测价格。

验收必须同时满足：五类 Schema 与白名单、模型通过 Gateway、所有验证先于工具、两次调用上限、失败 PLANNING_FAILED、真实 Planner Trace、旧路径稳定、实际测试通过、没有范围外开发。

## 10. 本轮状态与确认边界

已读取用户指令及相关源码，确认上述两个必要已有文件修改点，并完成本计划自检。当前没有 Phase 10-B 功能代码、依赖安装、数据库变更、模型调用或新增测试运行。

自检覆盖：用户第五至九节 Schema/Registry/Gateway/Validation 对应任务 1–4；第十节失败处理对应任务 4；第十一节 PlannerRun 对应任务 5；第十二节五个实际测试及第十三节报告对应任务 6；停止条件进入任务 6 验收及全局约束。接口、字段名称、类型转换、缺项、原文诊断和重试上限已经统一，无待定实施项。

**等待用户确认本计划后实施。** 这是用户指令第四节的明确要求：“输出 PHASE_10B_PLAN.md……等待确认后实施。” 确认后按本计划逐项开发，完成 Phase 10-B 后停止。

# AegisAI Phase 11-D 实施计划：自主调查编排与可信答案交付

审查日期：2026-10-09（Asia/Shanghai）。状态：**规划完成，等待“确认实施 Phase 11-D”；未修改生产代码，未新增 API，未执行本阶段测试。**

**Goal：** 一次受约束的后端调查请求，自动驱动现有 Planner、Investigation / Verification / Security Analysis 三个真实专业 Agent、Integration Gate，生成并保存可回读的证据化 AnswerEnvelope。

**Architecture：** 增加确定性的上层 `InvestigationOrchestrator`，组合已有同步服务及多个真实 Run；增加字段投影、生命周期和审计适配，不重写基础设施。首版 Answer Composer 不调用模型。

**Tech Stack：** 现有 Python 3.12、Pydantic、SQLAlchemy、PostgreSQL、Runtime / Tool Gateway / Model Gateway；pytest 与原测试环境。无新增 Agent 框架、消息队列、数据库或依赖。

**Spec：** 用户附件 `C:/Users/X/.codex/attachments/25f2d22c-2999-4f99-8946-ec9967d9ff0d/Pasted text.txt`；接口事实以本文列出的当前源码为准，历史验收证据见 `PHASE_11C_RESULT.md` 和 `work/integration/`。

**全局约束：** 只实施获批的 11-D 范围；不切换网页、不新增正式 HTTP API；不改风险/核验/Gate 算法、不替换 Scheduler、Executor、Planner、Task Contract；不伪造 SUCCESS，不自动重规划，不付费测模型。保留原始 Artifact、Claim ID、Evidence ID、真实 Run ID 和归属。

**五项重点复查：** ①请求键与跨请求并发隔离；②原始目标、资产、版本、时间范围不被缩窄；③PARTIAL 与可选任务不能绕过依赖；④取消在模型调用、Run 启动和 Gate/答案提交之间的传播；⑤历史答案与 Gate 固定快照绑定，不能引用实时变化的数据冒充历史事实。

## 1. 当前代码状态

### 1.1 本轮审查证据与真实性边界

本轮读取实际源码、协议和历史报告，并对 `work/integration/final_source_hashes.json` 的 **352 个文件**作只读 SHA-256 比对：缺失 0、变化 0。项目根没有 `.git`，也没有已有 `PHASE_11D_PLAN.md`。本轮没有启动测试数据库、执行 pytest、调用模型或安装依赖。

`work/integration/full_suite_final.json` 记录上一阶段 exit_code=0、tests=1169、failed=0、errors=0、skipped=0；这是**历史证据，不是本轮重新验证**。原 Windows 进程测试的时序敏感性、失败审计增长、商业模型与公网准确率未评测等限制继续保留。

### 1.2 已有接口及复用位置

以下路径均相对项目根；“已有”表示源码存在，不代表本轮再次运行通过。

| 层 | 实际文件/接口 | 审查结论与复用方式 |
|---|---|---|
| 原网页入口 | `backend/app/api/assistant.py`；`AssistantService.start(QueryRequest, actor)` | POST `/api/v1/assistant/query` 返回 202；读取 Run / tasks / trace。保留不动。 |
| 旧 Orchestrator | `backend/app/assistant/orchestrator.py` | 旧确定性角色链和旧 Gate，不等于三个专业 Agent + Phase 11-C Integration Gate。不能改名冒充复用。 |
| 网页状态读取 | `frontend/public/modules/pages/assistant.js`、`frontend/public/modules/services.js` | 当前轮询 Run，间隔 2 秒、最多 90 次；该入口未发现 SSE 实现。本阶段不改前端。 |
| 查询/规划输入 | `backend/app/assistant/contracts.py`；`backend/app/planner/schemas.py` | `QueryRequest` 和 `PlannerInput` 可复用；原输入没有独立 typed time_scope。 |
| Query Router | `backend/app/assistant/router.py::route()` | 确定性范围解析、Fast/Deep 与阻断规则已有；不是另一个 LLM Router。时间天数截断不能作为 Gate 权威时间范围。 |
| 基础 Planner | `backend/app/planner/service.py`、`validator.py`、`registry.py` | 五任务白名单已有；资产分析仍有 lookup → version_match → patch_analysis → risk_analysis 四段依赖要求。不能直接塞入 B1 调查链。 |
| B1 调查 Planner | `backend/app/agents/investigation/planner.py`、`validation.py`、`roles.py` | 复用 Model Gateway 的结构化调用、审计及 DAG 验证；只支持 vulnerability_lookup / evidence_search / asset_lookup 三类。版本检查通过 inspect_component_version。无上述固定四段业务依赖。 |
| 原始输入审计 | `backend/app/planner/trace.py::PlannerTraceStore` | 私有 `planner_input_v1` 与 `planner_input_sha256` 已保存。其哈希方式沿用原实现，不能与其他 fingerprint 实现混用。 |
| Runtime | `backend/app/runtime/service.py::RuntimeService.run_plan(plan, actor, request_key)` | 同步执行；返回真实 RunSnapshot。已有 run_key 幂等、DAG、预算、审计。 |
| Scheduler | `backend/app/runtime/scheduler.py::Scheduler` | 只有 TaskState.SUCCESS 解锁依赖；PARTIAL / WAITING_REVIEW / FAILED 阻塞依赖。执行池会等待清理。 |
| 专业 Executor | `backend/app/agents/executor.py::AgentExecutor` | 有 run-local `cancel_all()` 和子进程清理；上层当前没有统一活动 Run/Executor 控制句柄。 |
| Investigation | `backend/app/agents/investigation/service.py::IntelligenceInvestigationService` | `plan_and_run(input, actor)` 已自动完成 Query → Planner → Validation → Runtime → Investigation；`read_results(run_id, actor)` 的 actor 为位置参数。 |
| Verification | `backend/app/agents/verification/service.py::EvidenceVerificationService` | `run(VerificationRequest, actor=actor)`；`read_results(run_id, actor=actor)`。复用 ContextStore、固定来源快照、正式工具回执与 Reader。 |
| Security Analysis | `backend/app/agents/analysis/service.py::SecurityAnalysisService` | `run(AnalysisRequest, actor=actor)`；`read_results(run_id, actor=actor)`。复用资产归属、版本与风险引擎。 |
| 三 Agent 注册 | 各 `backend/app/agents/{investigation,verification,analysis}/registry.py` | 现有真实 Agent 注册工厂，含协议、工具白名单、运行实例隔离；不新建第四个 Agent。 |
| Gate | `backend/app/integration/service.py::IntegrationService` | `evaluate(request, actor=actor, control=GateControl(...))`；`read` / `read_trace`。已支持跨 Run、六类检查和五种结果。 |
| Gate 固定快照 | `backend/app/integration/store.py::decode(row, actor)`；`reader.py` | 存储 IntegrationContext / Result / Trace 与哈希；历史读取检查绑定并在固定上下文上复核纯规则，不重新采集/写审计。 |
| 数据持久化 | `backend/app/db/models/application.py::AgentRun` | 可复用 JSONB 审计命名空间，无需新表。数据库状态仅允许 queued/running/succeeded/partial/failed/timeout/cancelled。 |
| 模型入口 | `backend/app/llm/gateway.py`、现有 Provider/配置 | Planner 统一通过 Model Gateway；Mock 不等于通用规划模型。实际集成测试需配置 InvestigationPlan 的受控响应。 |

### 1.3 当前已具备与尚缺能力

已具备两段真实基础：①用户问题 → B1 Planner → 实际 Investigation Run；②准确选定的 I/V/R Artifact → 跨 Run Gate → 保存与回读。已有 `backend/tests/integration/conftest.py::build_chain()` 手动调用三个服务，是兼容性证据，**不是统一用户请求驱动的上层编排证明**。

尚缺统一逻辑调查身份、自动选择/交接 Artifact、请求生命周期与总预算、统一取消传播、上层幂等与并发隔离、受 Gate 控制的 AnswerEnvelope、历史答案 Reader。

原网页返回的是旧结构化字典及旧引用，没有覆盖完整新协议的可直接复用 AnswerEnvelope。`AgentCitation` 的外键要求现有 UUID Claim 与数据库核验修订，不能容纳所有专业 Agent 派生字符串 Claim ID，也不能代替历史固定快照引用。

## 2. 阶段目标

正式实施后提供内部同步调用入口，一次受认证 actor 约束的请求自动完成正常三 Agent 流程，返回终态调查快照及 AnswerEnvelope；重复调用和历史回读不重新启动 Agent。

首版支持**单个明确 CVE**，可附本人资产/组件 ID、组件及版本、受支持时间条件。正常场景输出可核验结论；不完整/冲突/UNKNOWN 场景输出真实状态、证据和补充调查建议。缺少必要输入不伪造资产或版本。

不扩展批量漏洞、自由网络爬取、自动修改资产、自动处置、跨多次重规划、精确利用验证。单纯事实查询继续走旧 Fast Path；本阶段内部接口明确 opt-in Deep Investigation。商业模型、公网情报质量、比赛 Benchmark 不属于本阶段验收。

## 3. Investigation Orchestrator 架构

### 3.1 推荐集成位置

推荐新增 `backend/app/orchestration/`，与既有 `agents/`、`integration/` 的业务边界一致。这里负责确定性跨阶段控制和交付；不覆盖 `assistant/orchestrator.py`，不往 Scheduler 中塞业务阶段，也不再建 Runtime。

直接扩展旧 Assistant Orchestrator 会混淆旧角色 Artifact、旧 Gate、旧网页响应；在 Scheduler 内加入三个专业阶段则改变已验收的 DAG 语义。新增薄上层组合服务是风险最小且可单独验收的选择。

```text
InvestigationRequest + authenticated actor
  → Store.claim_request / 冻结原始范围 / 生命周期 CREATED
  → Scope Adapter（复用 QueryRequest、PlannerInput、Router）
  → IntelligenceInvestigationService.plan_and_run
      → 已有 Model Gateway / B1 Planner / Validation / Runtime
      → Investigation Reader → 实际 InvestigationArtifact
  → Handoff Adapter → EvidenceVerificationService.run / Reader
  → Handoff Adapter → SecurityAnalysisService.run / Reader
  → IntegrationService.evaluate / 固定 IntegrationContext
  → Answer Source Projection → Deterministic AnswerComposer
  → Store.seal_result → Reader 校验回读
```

### 3.2 上层入口与调用方式（拟新增接口）

```python
class InvestigationOrchestrator:
    def __init__(self, engine, model_gateway, *, policy=None): ...
    def investigate(self, request: InvestigationRequest, *, actor: str) -> InvestigationResult: ...
    def get_status(self, logical_id: UUID, *, actor: str) -> InvestigationStatus: ...
    def get_result(self, logical_id: UUID, *, actor: str) -> InvestigationResult: ...
    def get_trace(self, logical_id: UUID, *, actor: str) -> InvestigationTrace: ...
    def cancel(self, logical_id: UUID, *, actor: str) -> InvestigationStatus: ...
```

`investigate()` 为同步入口。新请求在调用线程内执行；同 actor 同键正在运行则返回已有状态、answer=None，不创建第二条流水线；终态重复请求回读已封存答案。状态/取消可由其他调用线程读取和提交，不新增 HTTP 路由，不新增后台任务平台。Engine / Model Gateway 由调用者提供且借用，Orchestrator 不关闭它们。

每次实际流水线创建独立三个服务实例、Control、Run 引用和事件列表；不复用可变 service.control 跨请求。先形成内部可运行闭环，Phase 12 再设计公开 API/网页适配。

## 4. 三 Agent 调用与依赖关系

### 4.1 实际调用顺序

| 步骤 | 输入 | 现有调用 | 必须检查的真实输出 |
|---|---|---|---|
| I | 规范化但保留原问句的 PlannerInput | `investigator.plan_and_run(input, actor)` | PlannerSnapshot 的 planning_status、runtime_run_id；随后 Reader 的完整结果、Task Trace、回执与 Artifact。 |
| V | I 的精确 run/task/artifact 三元组 | `verifier.run(VerificationRequest(...), actor=actor)` | 真实 V Run；Reader 的 execution_status、verification_status、partial_result、固定来源快照。 |
| R | 同一个 I 引用 + 所选 V 引用 + 原请求资产/组件 | `analyzer.run(AnalysisRequest(...), actor=actor)` | 真实 R Run；风险 Artifact、资产快照、覆盖与 execution_status。 |
| Gate | 三个 ArtifactRef + I 根 Run + Planner ID + 原始目标 | `gate.evaluate(IntegrationRequest(...), actor=actor, control=...)` | 五态、persistence、输入/目标哈希、引用、各项检查和历史快照。 |

I/V/R 默认是**三个不同实际 Run**，Planner 审计与 Gate 审计另计。上层 logical_id 只是关联身份，不覆盖子 Run。V/R 继续使用原有 RuntimeAdapter 的单任务受约束计划，工具、核验和风险业务逻辑保持原实现。

### 4.2 选取 Investigation 主 Artifact

依据服务器验证后的 B1 计划、真实 Task 类型、目标 CVE 和 Reader 回读结果选取；候选须是精确目标的 vulnerability_lookup Artifact，规范化 CVE 匹配。若恰有一个有效候选才交接；零个返回缺失原因，多个返回选择歧义，不用“列表第一个”或最高 confidence 猜测。

evidence_search / asset_lookup 仍在 I 的同一个受约束 Run 中执行，所有任务状态交给 Gate 审查；选取主 Artifact 不意味着忽略其他必要任务。B2 可从其正式回执捕获相关 Claims/Evidence，不能在上层重新合成业务 Artifact。

### 4.3 必要任务、可选任务及领域弃权

必要集合覆盖目标查找、请求明确要求的版本/资产/证据任务，以及其依赖祖先。只有独立叶子 evidence_search、工具为服务器允许的补充 semantic_search、不是已选 Artifact/祖先、也不是用户必答证据，才可作为可选补充源；分类存入固定上下文并由 Gate 再验证。客户端不能传 optional_tasks 或任务权限。

I 必要任务非 SUCCESS、INPUT_REQUIRED、BLOCKED、关键 PARTIAL 时不启动 V/R。可选叶子失败且必要任务确实 SUCCESS，可继续 V/R并向 Gate 传明确 OptionalTask。任何被旧 Scheduler 阻塞的下游任务都不在上层补造成功。

V 的 CONFLICT / PENDING / INSUFFICIENT_EVIDENCE 属于业务结论，不能等同进程失败。若 V Reader 确认有正式输出、完整固定上下文、无执行错误、partial_result=False，即使对应任务 WAITING_REVIEW，也可启动**另一个 Run**的 R 做保守 UNKNOWN 观察；这不是解锁同一 DAG 中的失败依赖。V 程序错误、取消、超时或不完整执行则停止 R。

最终是否可交付由原 Gate 决定：资产影响目标的 WAITING_REVIEW 不能在上层变成 PASS；冲突转人工复核；合法 UNKNOWN 如实保留。

## 5. InvestigationRequest / InvestigationContext

### 5.1 输入 Schema（拟定）

使用现有 FrozenModel / Pydantic、extra=forbid、有限 JSON 和尺寸检查；复用 PlannerInput，不重复建立 Query 协议。

| 字段 | 类型/限制 | 来源与约束 |
|---|---|---|
| schema_version | Literal[`investigation-request-v1`] | 固定版本。 |
| request_id | UUID | 调用关联号；不作权限、工具或实际 Run ID。 |
| planner_input | 现有 PlannerInput | 包含 QueryRequest.question / target / asset_id / request_key，以及 component_id / snapshot_id / component。 |
| time_scope | TimeScope 或 None | window_days=1..365、requires_current；首版不支持任意起止区间。 |
| user_context | 小型受约束 UserContext | display_language 首版 zh-CN；可选说明最多 1000 字，作为数据，不能授予权限/修改提示词。 |
| investigation_options | InvestigationOptions | 总时长可在服务器上限内减小；profile 为现有三种 Profile。拒绝弱化原问句的 profile。 |

逻辑 user_query / vulnerability_scope / asset_scope 分别投影自 planner_input.query.question、target+问句的单 CVE、资产/组件字段；不再维护两份可能互相矛盾的字段。请求整体不超过 64 KiB，question 延续 2000 字，request_key 延续 150 字。

request_key 为必要幂等键；语义请求哈希包含问句、目标、资产/组件/版本、时间条件、options 和 user_context，排除仅追踪用途的 request_id。重复键但语义内容不同返回 IdempotencyConflict。重复键内容相同即使 request_id 不同，也返回首次记录，不替换首次身份。

### 5.2 范围解析与保留

复用 Router 做基础阻断和目标解析；LLM 生成的 plan.objective 不作用户授权范围。单 CVE 规范化且保留原问句；文本目标与 typed target 冲突则拒绝。模板不能追加一句话替代原问句或截断“最近 N 天”条件。

组件名/版本若从问题识别，在调用 I 前显式生成现有 ResolutionInput，存入派生 PlannerInput；记录 `scope_origin=EXPLICIT / QUESTION_EXTRACTED` 及原输入哈希。多版本、与 typed component 不同、解析歧义时要求补充，不猜测。资产 ID 不能从“我的”二字编造；组件 ID 必须由既有资产归属校验确认，跨 actor 不可继续。

snapshot_id 原字段可保留，但当前 R 不接收这一资产快照选择语义；首版遇到该约束记 `SNAPSHOT_SCOPE_NOT_SUPPORTED`，不宣称当前资产分析满足用户指定历史快照。新自由文本范围、批量目标、未知时间格式也记录 scope_gaps，交由 Gate 生成 REPLAN，而非默默缩小范围。

### 5.3 固定上下文与身份

InvestigationContext 至少含 schema_version、logical_investigation_id、owner、original_request/request_hash、resolved_scope/scope_hash、policy_version、current_stage、overall_status、planner_run_id、I/V/R Run ID、ArtifactRef、integration_result_id、**gate_logical_investigation_id**、warnings、cancel_requested_at、deadline_at、lease/revision、stage_keys 和 trace_reference。

上层 logical_id 在创建请求时分配 UUID；Gate 的 logical_id 由 actor + I 根 Run + objective_hash 派生，**两者通常不同**。保存明确映射并在读取时核对 Gate input_hash/objective_hash；不覆盖 Gate ID、子 Run ID 或伪造同一 Run。

已批准的范围与 policy 创建后不可变；生命周期和引用以检查过的 revision 更新。上层状态与数据库 AgentRun.status、TaskState、领域核验/风险状态分开保存。

### 5.4 上层预算

| 项目 | 首版服务器约束 |
|---|---|
| 权限 | READ_ONLY，客户端不能升级 WRITE。 |
| 总时长 | 默认/最大 300 秒；单调时钟控制当前进程，持久化 UTC deadline 供审计/恢复判断。 |
| Planner | 复用原最多 2 次结构化尝试；不增加第三次，不自动 replan。 |
| 模型 | 复用 Gateway 超时配置（默认 30 秒、可配上限 60 秒）及每次最多 4096 输出 token；不声称能精确限制供应商输入计费。 |
| I Runtime | 原 RuntimePolicy 上限 16 tasks、depth 8、32 个授权工具步骤、parallel 3、Run timeout 120 秒。 |
| V/R | 原各 1 task、1 个核验/分析工具步骤、task timeout 30 秒；不得重试创建新 Run。 |
| 实际 Run | 最多 I/V/R 三个 Runtime Run；不把 Planner/Gate/root 审计记录计作 Agent 执行 Run。 |
| 总工具 | 最多 34 个授权工具步骤；不是底层网络重试/HTTP 请求次数，后者受原工具限制。 |
| Gate | 最多一次本流水线调用；使用剩余总 deadline，不因 FAILED 循环提交。 |
| 流水线并发 | 单个服务进程最多 2 个活动调查，超出返回 BUSY；单个调查阶段顺序执行，内部仍遵守原 Runtime parallel。 |

总预算是跨阶段上限，不扩大原 Run/Task/Tool 预算；deadline 取 min。无法立即取消的模型 HTTP、数据库操作可能等待自身超时，300 秒不是操作系统强杀所有调用的精确墙钟保证。测试必须证明超时后不再启动后续 Agent，并记录清理完成时间。

## 6. Artifact 自动交接

### 6.1 精确字段映射

| 来源 | 目标字段 | 规则 |
|---|---|---|
| I.artifact.run_id/task_id/artifact_id | VerificationRequest.source_run_id/source_task_id/source_artifact_id | 原值，必须与 Reader、任务回执一致。 |
| I 主 Artifact | VerificationRequest.task_type | 首版 evidence_verification；claim_ids 默认全范围捕获，禁止 LLM任意删减必答 Claim。 |
| I 三元组 | AnalysisRequest.investigation_* | 与 V 固定快照的 source_* 完全相同。 |
| V.artifact.run_id/task_id/artifact_id | AnalysisRequest.verification_* | 实际 V Reader 回读，不人工创建 V 回执。 |
| 原请求 asset_id/component_id | AnalysisRequest.asset_id/component_id | 传原有 ID，不从 LLM、来源文章或其他请求取值。 |
| I/V/R 原三元组和版本 | IntegrationRequest.investigation/verification/analysis | 复用既有 ArtifactRef；Schema 分别为 investigation-artifact-v1 / verification-artifact-v1 / risk-analysis-artifact-v1。 |
| I.runtime_run_id / planner_run_id | IntegrationRequest.run_id / planner_run_id | 根 Run 与 Planner 审计真实关联，禁止覆盖下游 Run。 |
| 固定 V Claims/Evidence | 答案 Claims/Citations | 原始字符串 ID及作用域；不强转 UUID，不给同一证据重新分配身份。 |
| R.priority | 答案 risk_assessment.priority | 原源码叫 priority，用户逻辑名 remediation_priority 只作说明，不增添第二套独立值。 |

每阶段 request_key 由 upper logical_id + 固定 stage 名生成，长度不超过 150；同阶段唯一。每个下游 Request 序列化后重新 Pydantic 验证，存 hash/引用再提交。B2/B3 的 ContextStore、SnapshotReader、正式回执验证继续是业务输入事实来源。

### 6.2 不可信数据隔离

安全公告、CVE 描述、GitHub/博客内容只能留在原 Tool Receipt / 证据数据中，不拼成系统指令、不触发工具、不改 actor/任务权限/范围/Gate 状态。编排代码只消费白名单字段。Planner 仅接收原请求及受约束 scope；首版 Composer 不用 LLM，所以证据正文不会再次成为生成指令。

注入文本、超长内容、伪造 evidence_id、跨请求 Run 引用都列为负向测试。公共 Trace 不直接返回私有完整提示词、数据库 URL、API Key 或供应商原异常。

## 7. Integration Gate 接入

### 7.1 正常输入与调用时间

正常链：I/V/R Reader 校验完成后创建 IntegrationRequest，调用原 IntegrationService；复用 completion / integrity / evidence / consistency / objective / freshness 六类检查。上层不复制其判决算法，不把“函数返回成功”作为 PASS。

缺少关键结果：在未取消且有安全审计条件时，最多调用一次 Gate，传真实已有引用及缺失 None，由它产生非 PASS；没有实际 Run 也不造引用。取消已生效则停止，允许 integration_status=None、gate_not_run_reason=CANCELLED；这是未执行 Gate，不是假 FAILED Gate 回执。

`persistence=NOT_STORED` 时不能把 Gate 结果当作可历史交付的成功，转上层 FAILED，保留错误码与已完成 Run 引用，禁止重复自动调用。Gate 自身不成功时仍可保存安全失败答案；root 存储也不可用时返回明确未持久化错误，不能宣称可回读。

### 7.2 原始目标、时间和已知覆盖限制

默认 `objective_source=stored_planner_request`：使用原 B1 私有输入与哈希、原 profile，避免模型缩小目标。typed component 在规划前补入派生 PlannerInput，才能被 Gate 正确读取版本范围。

原 Query 没有独立 time_scope；如果上层显式时间条件/范围缺口不能由原 PlannerInput 完整表达，使用 Gate **已有** `new_structured_request` + ObjectiveContract。该目标由冻结原请求与既有 `from_planner_input` / `minimum_outcomes` 派生，不从模型摘要派生；保留全部原始 outcomes/gaps，再增加条件。保留 Gate 固有 NEW_EXPLICIT_OBJECTIVE 警告，不冒称恢复了历史意图。typed/text 时间冲突拒绝，近 0 / 366 天、多个冲突窗口等不截断成支持范围。

Gate 当前无“公开 POC 存在性的穷尽检索完成”这一 Outcome；verified_exploitation 也固定弃权，静态关联不等于有效利用。首版不扩展 Gate：问句明确要求穷尽回答 POC 是否存在时，向显式 ObjectiveContract 添加 `POC_COMPLETENESS_NOT_SUPPORTED` scope_gap，接受 REPLAN_REQUIRED，同时可展示有原始引用的候选发现。对“实际可利用/已验证 PoC”保留既有 verified_exploitation 要求。不得因已有 CVE 概览 PASS，就把未覆盖的 PoC 问题说成完整回答。

### 7.3 五态交付映射

| Gate 实际状态 | 上层终态 | answer_status | 交付约束 |
|---|---|---|---|
| PASS | COMPLETED / SUCCEEDED | COMPLETE | 只交付 final_result_references 对应且引用验证通过的内容。 |
| PASS_WITH_WARNINGS | COMPLETED / SUCCEEDED_WITH_WARNINGS | COMPLETE_WITH_WARNINGS | 相同约束，同时保留所有警告与弃权。 |
| REPLAN_REQUIRED | COMPLETED / INCOMPLETE | INCOMPLETE | 只给安全部分事实、未知和结构化补充建议，自动重规划次数=0。 |
| HUMAN_REVIEW_REQUIRED | WAITING_REVIEW / REVIEW_REQUIRED | REVIEW_REQUIRED | 展示冲突两侧和人工判断事项，不选边、不给确定性风险总结。 |
| FAILED | FAILED / FAILED | FAILED | 无确定性安全结论，只给错误码、已有审计引用和恢复说明。 |

生命周期的 COMPLETED 表示本次处理结束，不自动表示调查目标完整；必须同时读取 overall_status / answer_status / integration_status。

## 8. AnswerEnvelope

### 8.1 新协议与复用

拟新增 `answer-envelope-v1`，复用现有 FrozenModel、ArtifactRef、Gate Status、风险枚举、VerificationStatus 及字符串 Evidence/Claim ID。旧网页返回字典不能直接复用；需要新协议并保留旧入口，后续可另做 UI 适配。

| 字段 | 类型/来源 | 约束 |
|---|---|---|
| answer_id | UUID | root 首次封存分配；重复请求/回读不变。 |
| logical_investigation_id | UUID | 上层 ID；与 Gate ID分开。 |
| schema_version / composer_version | 固定版本 | 用于历史兼容，拒绝未知版本，不能静默按最新格式解读。 |
| question / resolved_scope | 原始问题 / 冻结范围投影 | 不用模型改写的目标替换问题。 |
| answer_status | 六态：COMPLETE / COMPLETE_WITH_WARNINGS / INCOMPLETE / REVIEW_REQUIRED / FAILED / CANCELLED | 按第 7、10 节，不能升级 Gate 结论。 |
| summary | 确定性简要文字，最多 8000 字 | 根据 status 和已准入字段生成，不直接复制来源文章。 |
| key_findings | 结构化 AnswerFinding，最多 32 项 | level=CONFIRMED/CANDIDATE/CONFLICT/UNKNOWN；含原 Claim/Evidence ID、artifact_ref、适用范围。 |
| affected_assets | 范围与资产快照投影 | 原 asset_id/component_id；未知字段明确 None，不拼其他用户资产。 |
| risk_assessment | RiskDecisionProjection 或 None | artifact_ref、risk_level、priority、affected、verification_status、asset/version_match_status 等逐值继承 R。 |
| recommended_actions | 原动作的公共投影，最多 32 项 | 精确 fixed_version/patch_reference 须有 Gate 准入 Claim/Evidence；一般加固与待调查动作明确分类。 |
| claims | 受约束 Claim 公共投影，最多 32 | 原 claim_id、claim_type、status、scope 与证据引用，不引入新业务 Claim。 |
| citations | AnswerCitation，最多 128 | citation_id 为显示锚点；原 evidence_id/claim_id、verification_artifact_ref、哈希与脱敏来源指针。 |
| evidence_references | 原证据引用投影 | Gate.evidence_references 子集；明确 supporting/conflicting/候选用途，不等同全部可信事实。 |
| warnings / unresolved_items | Gate + 实际生命周期/数据不足 | 去重但保留语义，不删除阻塞原因。 |
| follow_up_suggestions | 受约束枚举、缺失字段/任务类型 | 仅建议，不执行；如补版本、补官方证据、人工复核。 |
| integration_status / integration_result_id | 既有 Gate 值，可 None | None 仅用于未进入 Gate/未持久化等明确失败路径，不伪造。 |
| gate_logical_investigation_id / gate_input_hash / objective_hash | Gate 原值 | root 与 Gate 历史绑定。 |
| agent_run_references | 实际 I/V/R、Planner 引用 | 含阶段/真实状态，不把缺失 Agent 写成成功。 |
| trace_reference / generated_at / historical_snapshot | root Trace ID / 首次生成 UTC / True | 回读不刷新时间，不暗示实时结论。 |

Envelope 总量不超过 512 KiB；超出时不得截断必要引用让原结论失去依据，而应拒绝完整交付、保存安全失败说明，完整资料留在既有审计。空安全事实可以是合法未知/失败答案，不能标 COMPLETE 冒充成功调查。

### 8.2 引用与字段一致性校验

每条已确认安全 Finding 必须有对应固定 V ClaimVerification、原 Evidence ID、有效引用，并通过复用的 `integration.rules_common.grounded()` 检查；CVE 目标身份/状态等元信息可以引用实际 I 回执，但不能冒充核验后的受影响结论。

引用锚点仅是展示编号，绝不替代原 Evidence/Claim ID。风险决策源指向固定 R Artifact；断言受影响时还绑定其版本匹配、固定 V核验和 supporting_evidence_ids。冲突 Finding 保留正反证据。UNKNOWN 不自动补引用、不推出安全/无 POC/无补丁。

R 当前字段为 **priority**，不是 remediation_priority；新答案继承 priority，不维护两个可能分歧的决策值。若未来对外别名为 remediation_priority，仅做序列化别名并测试同值。

## 9. Answer Composer

### 9.1 确定性内容生成

拟定 `AnswerComposer.compose(context: InvestigationContext, sources: AnswerSources) -> AnswerEnvelope`，无工具、模型、数据库写入、领域评分。AnswerSources 必须由受归属约束的固定 Gate 审计解码得到，不能接受客户端或任意调用者直接上传业务 Artifact 替代。

流水线：验证 Gate绑定 → 选择允许的 final/partial 引用 → 投影固定 Claim/证据/风险 → 按状态套用简洁模板 → 校验引用图与风险字段逐值相等 → 封存。

PASS/WARN 使用 final refs；REPLAN/REVIEW 使用 partial refs，但这**不是全部 partial 内容可信**：只展示既有 grounded 判定允许的独立确认事实、原候选/冲突/未知，禁止给缺失整体目标的完整结论。FAILED/CANCELLED 不复制可疑业务内容，不给确定性安全判断。

精确修复版本/补丁只从固定 R 动作和已核验 Claim 投影；不从模型记忆、文章中相似字符串或另一个目标漏洞推断。POC_CANDIDATE 只显示候选；VERIFIED_POC_ASSOCIATION 只能显示已核验关联，usability=NOT_EVALUATED 不变；KNOWN_EXPLOITED 也不表示执行过本系统利用测试。

### 9.2 公共内容与敏感信息

复用 `integration.redaction.public_reference/public_lineage` 处理 URL凭据、query/fragment 和敏感键。仅输出白名单字段，不整段复制任意 source details、Prompt、模型原输出或私有异常；Citation 首版不直接输出原始证据正文。Action 的外链也经过相同处理，原私有哈希/原始引用不变。

R 决策字段保持原值，动作公共文本用 action_type/category 与合法字段模板生成，避免任意来源文字穿透交付层。原问句是本人历史输入，不转发给其他 actor。

### 9.3 模型辅助边界

首版**不实现 LLM润色 Composer**。已有 Planner仍通过真实 Model Gateway调用受控Provider，不能因此把整个调查称作无模型系统。后续获批可加可选语言润色，但必须 Gateway 调用、封闭事实/引用检查、超时确定性回退，且不能修改风险/Gate。它不属于本计划的生产文件与测试数量。

## 10. 异常处理与生命周期

### 10.1 状态协议

current_stage 为 CREATED / PLANNING / INVESTIGATING / VERIFYING / ANALYZING / INTEGRATING / COMPOSING / COMPLETED / WAITING_REVIEW / FAILED / CANCELLED。overall_status 独立为 RUNNING / SUCCEEDED / SUCCEEDED_WITH_WARNINGS / INCOMPLETE / REVIEW_REQUIRED / FAILED / CANCELLED；超时体现 FAILED + DEADLINE_EXCEEDED，数据库 root.status 映射 timeout。

| 阶段 | 进入条件、实际关联 | 正常退出 | 失败/停止与重试 | Artifact/Trace |
|---|---|---|---|---|
| CREATED | 通过 Schema、actor 与幂等 claim | 冻结范围、获得执行配额 | 非法请求拒绝；相同请求返回已有；无自动重试 | root ID / 请求哈希 / lease。 |
| PLANNING | 范围已冻结、剩余预算、未取消 | B1 Planner VALIDATED | PLANNING_FAILED 停止；最多原 2 次；PLANNING未终态不能视为成功 | Planner 实际 ID与状态、模型/尝试引用。 |
| INVESTIGATING | 原 Runtime 真正创建 I Run | Reader 验证主 Artifact与必要任务 | 关键 PARTIAL/阻塞停止 V/R；可选失败保留；无新 Run 重试 | I Run/Task/Artifact/Tool 回执关联。 |
| VERIFYING | 满足第 4 节交接门槛 | V Reader完整输出 | 业务冲突/弃权可做保守 R；程序失败停止 R；无重试 | V Run / 固定来源 hash / 领域状态。 |
| ANALYZING | 真实 I/V 绑定、未取消、预算足 | R Reader完整输出 | UNKNOWN 为业务状态；程序错误不假造风险 | R Run / 资产快照 / 规则版本。 |
| INTEGRATING | 正常或受限已有引用 | Gate 返回并可存储读取 | 失败/NOT_STORED不能 PASS；同流水线不二次提交 | Gate ID / 五态 / 双逻辑 ID绑定。 |
| COMPOSING | Gate固定快照验证通过，或安全失败路径 | Envelope验证、原子封存 | 引用/决策不一致→FAILED，不静默删字段升级 | answer_id / 版本 / hash / 内容来源。 |
| COMPLETED | COMPLETE/WARN/INCOMPLETE答案封存 | 终态只读 | 不自动 replan | 答案/Gate/Run固定引用。 |
| WAITING_REVIEW | HUMAN_REVIEW_REQUIRED | 保留人工待办 | 本阶段不执行人工决策/重新调查 | 双方证据与争议。 |
| FAILED | 规划/执行/持久化/超时失败 | 安全失败说明可保存则封存 | 恢复需显式新请求；保留原记录 | 错误码、已完成/未完成子状态。 |
| CANCELLED | 请求已生效且停止后续启动 | 控制与执行清理确认 | 不把在途调用假标已终止 | cancel_requested/observed/completed 时间和实际子状态。 |

### 10.2 取消/总 deadline 的最小兼容扩展

**当前缺口：** RuntimeService 没有向上层暴露活动 Run/Executor，I 服务只在 plan_and_run 完成后返回 PlannerSnapshot。若不补这一接口，无法诚实承诺运行中取消及启动前后的审计联结。

拟新增 `backend/app/runtime/control.py` 中的可选内部 Protocol，以及两个原生产文件的兼容 hook：

```python
class RuntimeExecutionControl(Protocol):
    def check_start(self) -> None: ...
    def effective_deadline(self, runtime_deadline: float) -> float: ...
    def run_started(self, snapshot: RunSnapshot) -> None: ...
    def attach_executor(self, executor) -> None: ...
    def run_finished(self, snapshot: RunSnapshot) -> None: ...
    def detach_executor(self) -> None: ...

class PlannerExecutionObserver(Protocol):
    def planner_created(self, snapshot: PlannerSnapshot) -> None: ...
    def planner_completed(self, snapshot: PlannerSnapshot) -> None: ...
    def before_runtime(self) -> None: ...
```

仅修改 `RuntimeService` 增加 `bind_execution_control(control)` 与 `_run` 的可选 hook：默认 None行为不变；开 Run 前 check_start；deadline=min旧预算与上层预算；真实 create_run 后通知并绑定本次 Scheduler.executor；取消走已有 cancel_all；scheduler按原逻辑产生正式 Task/Run结果，finally解除绑定。禁止改 Scheduler状态、写假 Task或将取消强改为成功。cached Run 不重新执行。

仅修改 `IntelligenceInvestigationService.__init__(..., observer=None)` / `plan_and_run`，在 Planner创建、规划保存和 Runtime开始前通知/检查；不改 Planner业务或验证。V/R服务无需修改业务代码，在本请求实例的 `.runtime` 上绑定同一受约束控制协议。

hook 本身的持久化失败不能忽略：禁止后续阶段、尽可能取消当前 Executor，记录已创建真实 Run；数据库不可用造成子 Run 未终态时如实标恢复待办，不造 finish_run。控制对象必须 request-local，不能在共享服务/全局 Executor 设置别人的取消事件。

上层 bounded monitor 同时检查持久化 cancel flag、deadline 与执行 lease；只绑定当前调查活动 Executor，使用现有 cancel_all。每进程最多两个活动调查 monitor，finally 停止/join，不产生永久线程。跨进程 cancel 通过 DB 标志被当前 worker 感知；数据库不可达时本地 deadline仍生效，不能继续启动新阶段。

Model Gateway当前无中断已发出HTTP请求的接口，也无每调用 deadline字段。使用借用 Gateway 的控制代理在**每次** generate_structured前检查预算/取消；在途请求等待原超时/完成。I的 before_runtime阻止取消后开 Run。不新增模型错误代码冒充原Gateway错误；取消中断原规划时 Planner可能仍 PLANNING，root记录真实未完成子状态，不能伪写 PLANNING_FAILED来“补齐”审计。

取消与封存使用同一 root 行锁/revision：取消先提交则禁封 COMPLETE；完整封存先提交则取消返回 ALREADY_TERMINAL，不把已完成结果改成取消。Gate有自身 late-cancellation事务检查，root仍须再次检查，防止 Gate已经完成但取消先于答案提交的窗口。

### 10.3 进程退出/数据库故障

同一 root 执行持有唯一 worker token，lease/heartbeat只用于检测，不自动抢占重跑。服务重启后 Reader报告 recovery_required 与原存储状态、已链接子 Run，不声称断点续跑。重复请求面对过期活动 lease 也不新启流水线。

人工恢复可在确认旧 worker/子进程停止后按新的 request_key发起新调查，并保留 replaces_logical_id审计关联；这只是恢复建议，本阶段不自动执行。数据库断开时禁止报告已保存答案；重连后可读取实际已提交记录。旧服务已完成但 root引用尚未保存的极小崩溃窗口需要恢复核对 stage_key / owner / agent_type，不能随机寻找或重新执行。

## 11. 历史结果和 Trace

### 11.1 复用存储与幂等隔离

用现有 `app.agent_runs` 存一条 root审计，`agent_type='investigation-orchestrator-v1'`；`details['orchestration_v1']` 存请求键/语义哈希、固定请求/范围、lease/revision、真实阶段引用、Trace、封存答案和哈希。不建表，不改 Claim/Asset/Review，不再建日志库。

**重要兼容点：** 旧 assistant.storage.create_run 会按 actor + `context.request_key` 查找，并未限定 agent_type；旧 owned_run 也仅检查 actor。新 root不写这个通用 context.request_key，也不调用旧create_run/owned_run构造与读取新协议；使用私有命名空间、固定 agent_type + actor + ID限定查询。否则可能把新旧同键请求互相认领。

复用既有数据库 advisory lock辅助函数，以 type+actor+request_key 序列化 claim；持有锁的短事务创建/验证 root并分配worker token，**不持数据库事务等待模型/子进程**。相同请求一次claim；进行中返回相同root；终态返回相同answer；键内容冲突显式报错。

Stage写入采用 root行锁、expected_revision和worker token，保证调用顺序/取消/封存原子性。原上下游 ContextStore的幂等仍保留，不能把它们当作上层并发控制替代品。每个stage_key创建后固定；同次失败Gate不循环提交，以约束原“失败审计每次追加”的已知增长问题。

### 11.2 固定结果与 Reader

`AnswerSourcesLoader.load(integration_id, actor=actor)` 查询 type+owner限定 Gate行，并复用 `integration.store.decode`获得**封存的**Context/Result/Trace。该私有适配只在服务内部使用，不把完整GateContext公开。不用再次调用 Gate.evaluate，也不用历史回读时重读当前情报/资产/再核验。

root不复制一份完整4MiB GateContext；保存 Gate ID/input_hash/objective_hash、来源projection hash、答案与有界Trace。固定业务资料继续留在原Gate/Agent审计。root JSON上限2MiB，低于原 METADATA_LIMIT=8MiB；事件最多128条，stage引用固定，错误重复只计次数而非无界追加正文。

Reader校验 root归属/type/version、请求/范围/答案/Trace哈希、Gate身份与原input/objective哈希，并从固定GateContext重建允许的答案projection，比较原决策、引用与composer版本。修改当前源数据后仍回读历史答案；损坏绑定、未知Schema、悬空Gate引用明确报错，不返回当前资料拼接的“替代历史答案”。哈希不抵抗拥有全部数据库写权限者的任意重签，也不是数字签名或完整版本控制。

### 11.3 Trace和读取协议

Trace保留：root/request_hash、scope来源、Planner ID与尝试状态、每阶段起止/真实Run/task/artifact、源hash与receipt指针、Gate检查/结果/双ID绑定、answer生成/封存版本、取消/预算/失败事件。通过这些指针可重建每条答案依据。

公共Trace仅投影安全字段，私有Planner原输出/Prompt/源码引用仍受原权限限制。`get_status` / `get_result` / `get_trace` 必须传认证 actor；跨用户ID、错误agent_type和未知ID统一不可读取，不泄漏“是否存在”。重复读取零模型调用、零新Agent Run、零Gate审计写入。

未终态get_result返回真实状态及answer=None；失败/取消如果安全说明已封存则可回读。历史支持本阶段固定v1；未来新增版本需显式Reader分支，不原地迁移旧快照。

## 12. 代码修改清单

以下是**正式实施预计范围**，本轮只新增当前计划文件。不存在的路径均标为拟新增，不能当作现已完成。

### 12.1 生产文件：预计新增15，修改2

| 拟新增路径 | 单一职责 |
|---|---|
| `backend/app/orchestration/__init__.py` | 最小包入口，无启动副作用。 |
| `backend/app/orchestration/contracts.py` | Request、Scope、Context、Status、Result、Policy。 |
| `backend/app/orchestration/scope.py` | 复用Router/Input的范围适配与scope_gaps。 |
| `backend/app/orchestration/lifecycle.py` | 上层状态转换、终态映射。 |
| `backend/app/orchestration/control.py` | request-local取消、总预算、monitor与控制代理。 |
| `backend/app/orchestration/adapters.py` | 原同步I/V/R/Gate签名适配、实际Run通知。 |
| `backend/app/orchestration/handoff.py` | Artifact精确选择、下游Request、可选任务限定。 |
| `backend/app/orchestration/service.py` | 确定性调查顺序；不含业务核验/风险/工具实现。 |
| `backend/app/orchestration/store.py` | root claim、CAS更新、lease、取消与结果原子封存。 |
| `backend/app/orchestration/reader.py` | owner/type/version限定历史结果校验。 |
| `backend/app/orchestration/trace.py` | 有界阶段Trace及公共投影。 |
| `backend/app/orchestration/answer_contracts.py` | AnswerEnvelope、Finding、Citation、Risk公共协议。 |
| `backend/app/orchestration/answer_sources.py` | 既有sealed Gate解码及固定来源投影。 |
| `backend/app/orchestration/composer.py` | 确定性模板与引用/决策保持校验。 |
| `backend/app/runtime/control.py` | RuntimeExecutionControl / PlannerExecutionObserver内部可选Protocol。 |

| 拟修改的既有生产路径 | 最小修改 |
|---|---|
| `backend/app/runtime/service.py` | 可选control绑定、实际Run/Executor通知、min deadline、finally解绑；旧默认行为不变。 |
| `backend/app/agents/investigation/service.py` | 可选observer，Planner创建/完成通知、Runtime前检查；不改调查业务。 |

Scheduler、Executor、Tool/Model Gateway、Planner Validator、三个业务Agent、风险/核验规则、Gate算法、API、前端、数据库Model/Migration均不在修改清单。若实现发现必须改它们，先定位接口原因并停在可审查的范围差异，不能暗自扩张计划。

### 12.2 测试文件：预计新增13

1. `backend/tests/orchestration/__init__.py`
2. `backend/tests/orchestration/conftest.py`（原test engine/合成源seed复用，禁止预先跑三Agent）
3. `backend/tests/orchestration/fixtures.py`（受控InvestigationPlan响应与异常注入；标SYNTHETIC）
4. `backend/tests/orchestration/test_contracts_scope.py`
5. `backend/tests/orchestration/test_lifecycle.py`
6. `backend/tests/orchestration/test_runtime_control.py`
7. `backend/tests/orchestration/test_handoff.py`
8. `backend/tests/orchestration/test_store_idempotency.py`
9. `backend/tests/orchestration/test_answer_composer.py`
10. `backend/tests/orchestration/test_reader_trace.py`
11. `backend/tests/orchestration/test_actual_chain.py`
12. `backend/tests/orchestration/test_failure_cancel.py`
13. `backend/tests/orchestration/test_legacy_compat.py`

### 12.3 文档及证据文件

正式实施新增2个交付文档：`docs/INVESTIGATION_ORCHESTRATOR_IMPLEMENTATION.md`、`PHASE_11D_RESULT.md`。当前计划 `PHASE_11D_PLAN.md` 另计1个。本计划不预造结果报告。

预计另有2个非生产验收辅助文件：`work/orchestration/run_tests.py`（沿原runner模式，输出到新目录，不覆盖旧报告）、`work/orchestration/pytest_order.py`（保留原Windows顺序记录方式）。按未来实际需要生成备份、JSON/XML/log、审查证据和hash清单，数量不冒充固定新增源码数。

合计未来源码/测试/交付文档：新增30个（15生产+13测试+2文档），修改2个生产文件；另2个work验收辅助脚本和自动证据。文件可在保持职责/接口不变时减少，但增加生产范围必须在结果报告列出理由。

## 13. 实施顺序

以下未勾选任务只在收到“确认实施 Phase 11-D”后执行。采用本会话内顺序实施；一次完整实现后独立终审，不为每个小任务创建新Agent。独立审查安排在11-D4，不在规划轮启动。

每组先写有实际行为断言的失败测试，确认失败原因，再实现最小适配，再运行通过；无Git提交改为备份/哈希检查点与可回读审计证据，不初始化仓库。

测试命令统一在 `backend/` 中使用 `./.venv/Scripts/python.exe -m pytest`。DB场景先按第16节准备受隔离test DB及变量；单元场景不启动外部模型。下列命令为未来执行命令，**本轮没有运行**。

### 11-D1：Orchestrator与调查上下文

**文件：** contracts/scope/lifecycle/control/store/trace、runtime/control；修改runtime/service与investigation/service；对应test_contracts_scope、test_lifecycle、test_runtime_control、test_store_idempotency。

**输入：** 现有QueryRequest、PlannerInput、RuntimePolicy、AgentRun及原锁；**输出接口：**

```python
resolve_scope(request: InvestigationRequest, *, actor: str) -> ResolvedScope
transition(context: InvestigationContext, event: StageEvent) -> InvestigationContext
PostgresInvestigationStore.claim(request, *, actor: str) -> ClaimReceipt
PostgresInvestigationStore.advance(logical_id, *, actor, worker_token, expected_revision, event) -> InvestigationContext
PostgresInvestigationStore.request_cancel(logical_id, *, actor: str) -> InvestigationStatus
InvestigationControl.check_start() -> None
InvestigationControl.effective_deadline(runtime_deadline: float) -> float
```

ClaimReceipt明确 logical_id、fresh、现有snapshot、worker_token（仅内部，不出公共结果）；读写进行小事务，不持锁运行模型。

- [ ] 写并运行RED：`test_same_key_same_scope_reuses_root`断言两次claim同logical_id、第二次fresh=False；`test_same_key_changed_version_conflicts`断言同键版本变化拒绝；`test_question_and_typed_scope_conflict`断言不缩窄目标。
- [ ] RED命令：`./.venv/Scripts/python.exe -m pytest tests/orchestration/test_contracts_scope.py tests/orchestration/test_lifecycle.py tests/orchestration/test_store_idempotency.py -q`。确认因为新行为/接口缺失失败，不能以DB错误/fixture缺失当有效RED。
- [ ] 实现上述协议、owner/type命名空间、短锁claim、CAS状态、有限Trace；记录创建时request/scope hash。
- [ ] 写并运行控制RED：`test_default_runtime_has_unchanged_behavior`、`test_control_receives_actual_run_and_executor`、`test_cancel_after_planning_prevents_runtime_creation`、`test_shared_engine_does_not_share_cancel_state`；验证默认路径、真实ID、无新增Run、另一请求不受影响。
- [ ] 实现两个最小hook及request-local控制，复用executor.cancel_all、旧timeout/状态；不修改Scheduler。
- [ ] GREEN命令：同上加 `tests/orchestration/test_runtime_control.py`；再运行 `tests/runtime tests/planner tests/agents/investigation` 的受影响回归，核对旧默认调用不变。
- [ ] 形成D1检查点：新增/修改路径、基线/当前hash、测试输出、控制清理记录；未通过不进入D2。

### 11-D2：三Agent串联和Gate接入

**文件：** adapters/handoff/service；补scope/control/trace必要组合；test_handoff、test_actual_chain、test_failure_cancel。

**输入：** D1冻结Context/Control/Store和已有三个service；**输出接口：**

```python
select_investigation(result: InvestigationRunResult, scope: ResolvedScope, plan: TaskPlan) -> ArtifactSelection
build_verification_request(selection: ArtifactSelection, stage_key: str) -> VerificationRequest
build_analysis_request(selection: ArtifactSelection, verification: VerificationArtifact,
                       scope: ResolvedScope, stage_key: str) -> AnalysisRequest
build_integration_request(context: InvestigationContext, refs: StageReferences) -> IntegrationRequest
InvestigationOrchestrator.investigate(request: InvestigationRequest, *, actor: str) -> InvestigationResult
```

StageReferences只保留Reader验证过的实际引用；StageAdmission枚举CONTINUE/STOP/DOMAIN_ABSTENTION，明确执行状态与业务弃权分离，不篡改原Artifact。

- [ ] 写并运行RED：`test_handoff_preserves_original_ids`、`test_ambiguous_lookup_does_not_select_first`、`test_required_partial_does_not_start_verification`、`test_conflict_domain_result_allows_only_conservative_analysis`。
- [ ] RED命令：`./.venv/Scripts/python.exe -m pytest tests/orchestration/test_handoff.py tests/orchestration/test_failure_cancel.py -q`；断言下游服务调用次数和实际Run数量，而不仅检查返回字典。
- [ ] 实现精确交接、保守Admission、server-only可选叶子分类；调用原I/V/R，逐阶段保存真实ID；不能用fake Artifact填补Reader缺失。
- [ ] 接入原Gate、stored/explicit objective选择、双logical ID映射、NOT_STORED处理；replan次数固定0。
- [ ] GREEN核心链测试：`test_one_request_drives_three_actual_agent_runs_to_gate`，单次调用触发Planner与三个真实Runtime；断言实际三个run_id互异、Actor一致、正式receipt存在、Gate绑定同一I/V/R，normal Gate=PASS。
- [ ] GREEN命令：`./.venv/Scripts/python.exe -m pytest tests/orchestration/test_handoff.py tests/orchestration/test_actual_chain.py tests/orchestration/test_failure_cancel.py -q`；D2可先返回含Gate结果的InvestigationResult，D3补答案，不伪报最终完成。
- [ ] D2检查点保存actual-chain引用、Task/Tool状态、六类Gate结果、原业务表写入差异、资源清理；未通过不进入D3。

### 11-D3：AnswerEnvelope与答案生成

**文件：** answer_contracts/answer_sources/composer/reader；补Store封存和service结果组合；test_answer_composer、test_reader_trace。

**输入：** D2真实Gate固定快照和root上下文；**输出接口：**

```python
AnswerSourcesLoader.load(integration_id: UUID, *, actor: str) -> AnswerSources
AnswerComposer.compose(context: InvestigationContext, sources: AnswerSources) -> AnswerEnvelope
AnswerComposer.compose_failure(context: InvestigationContext, failure: FailureInfo) -> AnswerEnvelope
PostgresInvestigationStore.seal_result(logical_id, *, actor, worker_token, expected_revision, answer) -> InvestigationResult
InvestigationReader.read_result(logical_id: UUID, *, actor: str) -> InvestigationResult
InvestigationReader.read_trace(logical_id: UUID, *, actor: str) -> InvestigationTrace
```

- [ ] 写并运行RED：`test_unknown_risk_is_not_safe`断言风险四字段与源完全相等；`test_candidate_poc_is_not_effective_exploit`断言候选/NOT_EVALUATED不升级；`test_unbound_patch_and_citation_are_rejected`断言虚假链接/修复版本拒绝。
- [ ] RED命令：`./.venv/Scripts/python.exe -m pytest tests/orchestration/test_answer_composer.py tests/orchestration/test_reader_trace.py -q`。
- [ ] 实现固定Gate解码、引用白名单、五态模板、typed Envelope，复用grounded和redaction；不调用模型、不重算风险。
- [ ] 实现原子封存、历史Reader、版本与hash/引用绑定检查；不借用AgentCitation的实时外键查询替代历史证据。
- [ ] GREEN：`test_history_is_stable_after_live_sources_change`断言修改当前源后answer/hash/time仍不变；`test_reader_rejects_rehashed_answer_risk_tampering`断言即使局部hash重算也不能改变固定Gate/R决策；`test_repeated_read_has_zero_new_runs`断言无模型/审计副作用。
- [ ] GREEN命令：同上；再运行核心链测试，验证answer保存、owner/type限定回读、引用覆盖真实evidence IDs。
- [ ] D3检查点保存固定Answer、Gateinput/objective hash、逐字段风险对照、历史回读证据和public脱敏检查。

### 11-D4：端到端验证与独立审查

**文件：** 测试包13文件补齐；test_legacy_compat；2个交付文档；2个work验收脚本及独立证据输出。生产改动只允许修复已发现且属于本计划的问题。

**输入：** D1-D3候选实现、全部旧测试与hash基线；**输出：** 实际验收矩阵、原始测试记录、完整回归结果、独立审查与关闭证据、资源清理、`PHASE_11D_RESULT.md`。

- [ ] 完成A-F场景和第14节负向测试；E2E的fixture只预置合成数据库资料和Mock Planner响应，不能调用build_chain先生成I/V/R再塞给上层。
- [ ] 新增测试命令：`./.venv/Scripts/python.exe -m pytest tests/orchestration -q`；实际失败/跳过全部披露。
- [ ] 完整回归使用新work runner保留命令/env/exit code/XML/log/顺序；覆盖历史1169个nodeid，不能仅声称“总数增加”。
- [ ] 自检后做一次独立终审，按第15节18项检查；只读源/证据，不能把开发者自评称为独立审查。记录reviewer、源码hash、Critical/Important/Minor与证据。
- [ ] 修复全部Critical/Important，针对性复验；若影响先前结果，再跑必要回归。旧Windows失败保留首轮和复跑原始记录，不删测试、不只呈现最好一轮。
- [ ] 最终无新增未验证改动后封存source hash，清理本阶段test DB/进程/临时权限；不停止他人服务、不删除业务数据。
- [ ] 写2份交付文档：实际内容/文件/接口/调用示例/Schema/测试/审查/限制/验收与下一阶段边界。阶段结果严格按第17节PASS/PARTIAL/FAIL；完成即停止。

## 14. 测试计划

### 14.1 六类必测验收场景

所有“实际链”使用现有服务、Runtime/进程、数据库与Tool Gateway代码，Planner用明确标注Mock Provider的结构化响应，资料为SYNTHETIC。不会自动转为商业模型/实时情报评测。

| 场景 | 合成输入与故障 | 要断言的实际链路/结果 |
|---|---|---|
| A 正常完整调查 | 单CVE + 本actor拥有的精确组件/0.6.0库存，合成官方影响/修复/严重度证据；问“部署是否受影响，如何修复” | 一次investigate产生真实I/V/R三个Run，Gate=PASS；答案有原Claim/Evidence引用和风险字段原值；同键回读不再执行。测试CVE-2099-*、example.invalid不是真实漏洞结论。 |
| B 来源部分失败 | 在A基础上增加独立补充semantic_search叶子失败；主证据充足，叶子非用户必答、非任何依赖祖先 | 原Runtime保持失败原态；服务器和Gate均确认optional；V/R执行，Gate=PASS_WITH_WARNINGS，答案警告保留。另测该源有依赖子任务时绝不能Optional/PASS。 |
| C 关键证据不足 | 缺关键Claim/有效来源或必要任务PARTIAL | 无伪SUCCESS；必要I失败则V/R调用数=0；领域证据不足可形成保守后续观察；Gate=REPLAN_REQUIRED；答案明确缺失、建议且不重规划。 |
| D 关键证据冲突 | 两个合成有效来源影响版本不同 | V真实CONFLICT，保守R不定性；Gate=HUMAN_REVIEW_REQUIRED；正反证据均保留，答案不选边。 |
| E 资产版本未知 | 精确owned component的库存version=None；问句也不指定版本，仅问该部署影响；Planner实际查询CVE/资产，不伪造version工具输入 | I仍可正常取事实、V核验；R实际UNKNOWN/affected=None/priority=REVIEW_REQUIRED；资产影响Gate不完整，不报告LOW/NOT_AFFECTED。若Planner生成input_required则另测按原依赖停止，不用此分支冒充R已运行。 |
| F 取消/执行失败 | 规划在途、I执行中、V后R前、Gate/封存竞态及程序异常 | cancel请求和实际停止分别记录；不再启动后续Agent；已有真实审计可读；无假PASS；独立请求不被取消；model在途等待原超时的边界明确。 |

### 14.2 单元与协议测试

请求extra字段/目标冲突/超长/NaN/Inf、typed/text版本冲突、时间0/366/多窗口、scope_origin；Lifecycle非法逆转；I候选0/1/多、Schema版本不匹配、ID保留；五态与risk字段保持；候选POC、不存在结论弃权、修复精度约束；public URLuserinfo/query/fragment/敏感键脱敏，正文注入不作指令；不存在/跨actor/错误type/未知schema读取拒绝。

### 14.3 存储、并发与取消测试

相同owner/键多线程同时请求只创建一个root和一套三个Run；同键不同内容冲突；不同owner同键隔离；旧Assistant和新root同键不碰撞；不同请求Control/Trace无污染；取消与封存两种提交顺序；有效lease重复返回进行中、过期lease标恢复而不抢占；DB失败不报告STORED；工具/模型在途取消后无新调用、无遗留monitor/子进程。

总预算小于单Run预算时取min；最多两次Model请求、最多三实际Run、不自动replan；Gate失败重复读无额外记录；有界events/metadata；既有Runtime取消/进程清理保持回归覆盖。必要task PARTIAL、WAITING_REVIEW业务弃权与程序错误分别测，不只测试return值。

### 14.4 固定快照与端到端真实性

真实单入口完整链必须同时验证：Planner原输入hash、实际专业Agent注册/绑定、真实ToolCallRecord、V固定source三元组、R固定I/V/资产context、Gate三个真实Run与六类检查、Envelope原Evidence/Claim IDs、保存后另一个service实例回读、历史源变更不刷新答案、局部数据损坏不通过。

单元测试允许内存fake做局部错误注入；核心E2E不替换I/V/R/Runtime/Gate为fake，不手工传三个成品Artifact。测试Mock响应只是受控规划，合成source seed可以复用原 verification_seed与资料字段，不能复用build_chain的已运行结果。

### 14.5 回归与结果登记

保存baseline collect nodeids和新最终nodeids，核对历史1169覆盖、实际新增数量、失败/错误/跳过、命令和退出码。正式实施先验证原测试环境；任何skip需披露且缺核心场景则不能PASS。原旧API/网页路由与响应兼容测试保留，不启动网页自动切换。

本轮“计划审查通过”不等于这些测试已通过；结果报告不得预填成功数量或准确率。

## 15. 独立审查标准

### 15.1 Critical / Important 判定

**Critical：** 越权读取或串用他人资产/Run；伪造SUCCESS/跨Run关联；绕过Verification/Gate生成确定安全判断；UNKNOWN转安全；候选POC升级有效利用；虚假精确修复版本；证据/请求注入能改变权限；凭据泄漏；取消后无约束启动Agent；同请求并发无限重复执行。任一未解决则阶段FAIL，停止完整交付。

**Important：** 目标/版本/时间弱化、必要PARTIAL可选化、Gate/答案状态不一致、局部篡改仍回读、历史结果随当前资料变动、幂等/lease竞态、取消审计缺实际状态、临界deadline未约束后续、读写失败伪报已保存、原入口行为回归、测试不能证明单请求自动链、无法清理本阶段资源。有任一未解决不能PASS。

Minor指不影响安全与核心交付的呈现/可维护性问题，逐项列出。来源精度/覆盖/商业模型未实测属于明确限制，不能拿“框架测试多”掩盖。

### 15.2 18项审查矩阵

1. 未复制Runtime/DAG/Scheduler；只含可选兼容hook。
2. 未复制Gate六类判决算法，最终值来自原Gate。
3. 三Run链及双logical ID关联真实、可回读。
4. 确定性Finding均有固定核验/证据，partial refs未全量升级。
5. UNKNOWN/affected=None与Risk原值保持。
6. PARTIAL/WAITING_REVIEW未冒充SUCCESS解锁依赖。
7. 自动replan=0、模型尝试/Run/事件有界。
8. Agent继续走Tool Gateway，上层不新增业务工具/API直调。
9. 读写actor/type/ID约束一致。
10. 每请求服务/Control/Trace隔离。
11. 规划在途、Run启动、阶段间和封存取消无后续越界。
12. Evidence/Claim原ID、作用域、hash不丢失。
13. fixed_version/patch_reference有原合法证据。
14. 公共答案/Trace无密钥、私有Prompt、数据库URL泄漏。
15. 同键审计不重复，Gate失败不循环，Trace不无界增长。
16. 原API/网页Fast Path未改默认入口。
17. 未引入异步平台/消息队列/第四Agent。
18. Trace能重建每项关键答案的固定依据。

审查输入包括完整新增/改动文件、基线hash、实际链receipt、回归XML/log和错误记录；不能只读摘要报告判通过。修复后复验必须与最终源码hash相同。

## 16. 风险与工程保护

### 16.1 实施前备份、范围保护与隔离

1. 记录基线352文件当前hash，与C最终证据比对；额外记录两个拟改文件原文备份、测试nodeid、配置文件只读hash。备份位于 `work/orchestration/backup/`，保留目录相对路径。
2. 写入新文件前检测路径不存在；修改旧文件前再次比较hash，发现并发改动停止覆盖。每检查点记录变化路径；不改/删除用户其他成果。
3. 不初始化远程仓库、不自动commit/push。hash只能检出变化，备份只支持已备文件恢复；不能声称完整仓库回滚。失败恢复只还原本阶段确认拥有的两个修改及本阶段新增文件，并先检查无他人后续修改，不递归删除计算路径。
4. 测试使用任务拥有的隔离PostgreSQL cluster与**既有测试所要求的数据库名 aegis_phase5_test**；cluster/端口与生产分开，不擅改fixture数据库名称。实施时先核对占用进程/目录归属；本轮不启动。
5. 设置test URL和Runtime test URL指向受控cluster；Alembic使用的应用DATABASE_URL也指向同一test环境，禁止继承生产地址。使用现有运行库，不下载大量依赖。
6. 复用现有测试准备流程时先检查其固定work路径/报告覆盖行为，所有新日志输出 `work/orchestration/`；保存旧报告原文，不覆盖PhaseC证据。
7. 每轮记录本阶段进程/端口/cluster，结束停止并确认仅本阶段资源已清理。数据库引擎/Model Gateway借用关系明确，不关闭用户已有服务。

### 16.2 风险与应对

| 风险 | 保护与不可夸大之处 |
|---|---|
| 跨Run串错 | 精确三元组、owner/type、Schema、固定V/R上下文、双logical ID与Gateinput hash；不手填成功。 |
| PARTIAL/冲突 | 原依赖门禁保留，optional仅独立补充叶子，业务弃权只进入保守R新Run，最终Gate约束。 |
| 运行中取消缺控制接口 | 先实施两个最小hook；原Executor清理复用；模型不可立刻打断如实记录。缺hook不得宣称完整取消。 |
| 上层幂等/并发 | root命名空间避免旧Assistant碰撞，短advisory lock + worker token + CAS +不可自动接管lease；stage键固定。 |
| 时间/资产范围缺失 | 不用Router截断替代用户目标；typed/Text冲突拒绝；新显式目标保留警告；不造库存版本/拥有者。 |
| POC目标未覆盖 | 通过existing scope_gap产生REPLAN，候选明确；不改Gate Outcome混淆利用验证。 |
| 原Mock不能通用规划 | 使用受控InvestigationPlan fixtures、报告明确Mock；真实Provider兼容延续，不声称真实模型能力。 |
| 历史资料被更新/损坏 | Gate固定快照+版本+哈希+确定性projection校验；未知版本拒绝，回读不发起调查。 |
| 失败审计增长 | 上层同键最多一次Gate调用，不自动重试；root事件/体积上限，旧全局审计保留问题另阶段解决。 |
| Windows进程时序 | 原用例保留；新控制与清理验证；失败和复跑均留证据，不靠删除/弱化断言。 |
| 无Git | 真备份+变化检查+受限恢复；不把hash说成版本管理。 |
| 模型/公网/生产质量未实测 | 本阶段只证明受控内部链可靠；准确率、覆盖、真实模型质量待AegisBench。 |

## 17. 阶段验收标准

### PASS

- 一次内部自然语言调查请求驱动真实Planner、三个专业Agent实际Run、原Gate，场景A=PASS，并保存/另实例回读完整证据化Envelope。
- A-F全部按实际状态通过；B不能绕过依赖；C/D/E/F不伪报完整/安全；取消及预算可验证，重复请求/读历史无额外执行。
- 原Evidence/Claim ID与风险字段保持，owner/type/范围/快照绑定成立，公共资料脱敏，Trace可重建依据。
- 历史1169用例覆盖、新增实际测试数量和原始结果可核对；未隐藏失败/错误/skip；Critical/Important未解决数=0。
- 改动范围和备份可审查，测试资源清理，2份结果文档真实记录限制；网页默认入口不变。

### PARTIAL

只有局部上下文/交接/答案能力完成，或缺真实单入口E2E、取消传播、历史/并发安全验证、完整回归/独立审查时，报告阶段PARTIAL并明确尚缺工作；不能以“各Agent已有测试通过”代替本阶段闭环。业务请求的REPLAN/UNKNOWN不自动等同工程阶段PARTIAL：若预期保护行为被真实验证，工程阶段仍可PASS。

### FAIL

存在未解决Critical、关键Important导致安全/核心验收失败，或引用/状态伪造、事实升级、越权、无法阻止无界执行、原入口明显回归、验收证据编造，则FAIL。不得对外宣布完成，保留失败证据与受限恢复记录。

结果报告区分：生产代码真实调用、Mock规划、合成资料、公网实时采集、商业模型实测五类；后两类未做就写未做。本计划不保证比赛名次，不把工程测试数称为情报准确率。

## 18. 下一阶段边界与本轮停止点

Phase11-D正式完成后仍不自动进入：Phase12公开API/前端问答入口/Agent链与证据展示/用户取消交互；AegisBench真实数据准确率、召回率、多跳任务效果与商业模型对比；公网实时采集扩展；生产部署/域名/服务器/运维；自动replan、多调查并行批处理、长期学习、断点续跑或审计保留策略。这些需要后续明确指令。

**本轮结论：** 正常三Agent自动串联可复用既有服务，不需改核心业务；完整取消与状态审计需要先增加两个可选兼容hook。新AnswerEnvelope只复用基础/领域Schema，不能直接拿旧网页字典代替。推荐新增薄上层orchestration模块；预计15个生产新文件、2个既有生产修改、13个测试和2个交付文档。没有要求先重构基础设施的阻塞问题，但控制hook、目标覆盖与root幂等隔离必须在对应步骤完成，不能留到“演示后再补”。

最小验收就是场景A：**一个单CVE、本人精确资产/版本调查请求 → Mock Planner（明确受控）→ 真实I/V/R三个Run → 原Gate PASS → 带原Claim/Evidence引用的答案 → 保存并回读 → 同键重复零新增执行**。不手传三个成品Artifact，不宣称合成数据是真实漏洞。

### 规划自审记录

已对照用户18项计划章节、A-F场景、8项最终汇报要求检查；已核对真实类名、同步签名、I actor位置参数、R.priority字段、两套logical ID、旧Assistant request_key碰撞、原预算、固定四段Planner依赖与B1三类任务的差异。所有拟新增接口与文件均标为未来实现；测试命令及PASS条件均为未来验收，不预填通过数字。

当前只生成本文件；**停止开发，等待用户回复：“确认实施 Phase 11-D”。**

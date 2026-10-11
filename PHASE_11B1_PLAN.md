# AegisAI Phase 11-B1：Intelligence Investigation Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现唯一的 IntelligenceInvestigationAgent，连接现有受约束 Planner、专业 Runtime、Tool Gateway 和混合检索，输出具有来源、版本结果、候选关联及不确定性的结构化调查 Artifact。

**Architecture:** 增加显式启用的 investigation-v1 规划能力配置，复用原规划、验证、调度、回执与存储流程。调查 Agent 按已授权的固定步骤复用 ProcessSupervisor 和 Tool Gateway；业务结果由工具回执及已接受依赖确定性标准化，原 TaskArtifact 保持可验收。专业调查 Artifact 是上述持久化记录的类型化投影，可以在新服务实例中重建。

**Tech Stack:** 项目现有 Python、Pydantic v2、SQLAlchemy、PostgreSQL、pytest、packaging；不增加模型 SDK、Agent 框架或数据库依赖。

**Spec:** 本会话用户《AegisAI Phase 11-B1：Intelligence Investigation Agent 实现 Prompt》。本文件同时记录适配设计、范围解释、实施步骤及验收，作为本次确认的完整对象。前置结果：[PHASE_11A_RESULT.md](C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/PHASE_11A_RESULT.md)。

日期：2026-10-08。**状态：源码检查与计划编写已完成，待用户确认，尚未实施。** 用户第四节明确要求“输出 PHASE_11B1_PLAN.md”“等待确认后实施”；本轮仅新增本计划。没有修改产品代码、编写测试实现、启动数据库、安装依赖或调用模型。确认后沿用本会话由主代理顺序实施的方式。

## Global Constraints

- 只实现 IntelligenceInvestigationAgent，agent_id 固定为 investigation_agent；支持 vulnerability_lookup、evidence_search、asset_lookup。
- 不实现 VerificationAgent、SecurityAnalysisAgent、Integration Gate、风险评分、PoC 执行、人工复核自动决策、前端展示或部署。
- 不重新实现采集、CVE API、混合检索、版本比较算法、工具调用通道、Planner 重试、DAG 或 Scheduler；通过现有兼容注入点增量接入。
- Agent 只读取已授权的 Task 步骤与已接受的同运行依赖，不直接访问 SQL Session、外部 API、任意 URL、文件、Shell 或模型 SDK。
- SQL/Relation/Vector 检索通过现有 get_vulnerability、get_evidence、get_claims、relation_query、semantic_search 等工具取得，不增加另一套检索。
- 默认 READ_ONLY、refresh=false；不得自动授予 WRITE、EXTERNAL_NETWORK 或 REVIEW_ACTION，不创建资产、不重算风险、不验证 Claim。
- 保留原预算：16任务、8层、32次预留调用、3并行、每任务最多8次调用、1–60秒、运行最多120秒；不通过子步骤扩大预算。
- 原 TaskContract、TaskArtifact、ToolReceipt、执行回执验证、DAG 和 Scheduler 核心保持不变；业务状态与 Runtime 终态分开表达。
- 只有原验收允许的 SUCCESS 解锁依赖；部分结果、来源冲突和证据不足不能被重新标记为 SUCCESS。
- 原 Artifact 512 KiB、worker 4 MiB、元数据8 MiB上限保持；包括持久化回执引用的字节开销，超限明确引用完整回执，不静默截断。
- 外部文章、代码仓库文字、公告及论文均是数据，不能改变任务、工具、权限或控制流程。
- 716项通过是 Phase 11-A 已保存的基线，本轮尚未运行测试；实施后的数量及结果按真实执行记录填写。
- 完成批准范围、实际测试及 PHASE_11B1_RESULT.md 后停止，等待新的阶段指令。

## Review Focus

1. 资产/组件问题被旧 Planner 自动扩为四类分析任务、进而调用未实现 Agent：调查配置限制三种任务，默认配置仍按旧规则；任务2、5测试。
2. 子调用改变参数、漏报已执行回执、扩大期限或跨运行取消：固定已授权步骤、连续回执编号、总截止时间及运行独立实例；任务4测试。
3. 字段没有证据对应、历史源覆盖当前源、模型规划置信度变成安全置信度：按执行时快照标准化，保留范围/来源/状态，confidence不猜测；任务1、3测试。
4. 一项工具失败被包装成成功，或者失败使已有证据不可读：业务 partial_result 与原 FAILED/WAITING_REVIEW分开，持久化后仍可读；任务4、5测试。
5. 标准化投影超限、重启后变化、跨所有者读取或同请求键切换配置：固定投影版本与快照、回执引用、同所有者读取和幂等配置标识；任务1、5测试。

## 1. 已检查的现状

| 位置 | 源码实际情况 | 本阶段复用方式 |
| --- | --- | --- |
| app/agents/interfaces.py | InvestigationAgent.investigate 返回 ExecutionOutcome；for_run/cancel_all规定运行生命周期 | 实现一个具体子类，返回原执行协议 |
| app/agents/registry.py | 默认调查负责漏洞/版本/补丁；evidence_search归 verification_agent；任务负责者不能重叠 | 新建显式调查注册工厂，不修改原默认注册表，不同时注册同一任务 |
| app/agents/contracts.py、router.py | Contract工具最多8种；语义类型来自 Planner；Router同时校验 Agent、Task Registry、工具与预算 | 新配置恰好8种工具；扩展语义类型支持asset_lookup，默认路由仍使用旧五类白名单 |
| app/agents/executor.py | SUCCESS结果必须精确等于回执outputs和依赖ID；检查持久化AgentArtifact大小 | 保留精确结果校验；不把任意调查JSON塞进SUCCESS result |
| app/planner/schemas.py、registry.py | 只有五种任务，没有asset_lookup | 独立调查候选Schema和能力配置，不放宽旧PlannerPlan |
| app/planner/context.py、validator.py、prompts/task_plan_v1.txt | 组件或资产问题必须包含漏洞→版本→补丁→风险；version_match要求component_id和WRITE | 默认规则保留；调查配置使用三类只读任务及版本观察工具，不伪造component_id或授权 |
| app/planner/llm_planner.py、service.py、trace.py | 统一Model Gateway、最多两次规划、保存原输出和验证结果、同所有者重验计划后运行 | 增加服务端配置注入点，复用整个循环和持久化；配置版本纳入幂等摘要 |
| app/runtime/process.py、executor.py | ProcessSupervisor已有进程隔离、取消和回执；原Worker首次工具失败停止 | 每个授权步骤调用原Supervisor，Agent在期限内继续独立只读步骤，父级汇总并重新验收 |
| app/tooling/contracts.py、adapters.py | 已有查询/候选/证据/资产工具；get_vulnerability含CVSS、CWE、版本、来源及intelligence聚合 | 复用现有数据；PoC/补丁候选无需新增爬虫或新候选检索系统 |
| app/knowledge/retrieval.py | semantic_search复用本地Embedding及最多1000块的有界精确向量搜索 | 保持原实现和限制，不宣称新增ANN/pgvector性能能力 |
| app/assets/identity.py、versions.py、matching.py | 身份消歧和compare_version已有；match_component_vulnerabilities会写入，不能默认只读使用 | 增加薄只读工具包装，复用resolve_component与compare_version，不调用写入匹配器 |
| app/db/models/*、repositories/queries.py、enrichment/queries.py | 已有Source/RawDocument/版本/CVSS/CWE/PoC/Patch/Claim/Evidence/Conflict/Asset | 不建表、不迁移；记录字段来自现有查询回执 |

Phase 11-A基线证据：work/agents/reviewed_full_suite.json与.xml记录716项通过、零失败/错误/跳过；不是本阶段新增成果。

## 2. 方案选择及需要确认的适配

推荐采用**显式调查配置＋原始回执协议＋类型化业务投影**。

| 方案 | 影响 | 结论 |
| --- | --- | --- |
| 显式investigation-v1，旧默认配置保持 | 增加有限兼容参数和调查配置，满足三类任务，原流程继续复用 | 推荐；新增配置必须进入审计、幂等及Router校验 |
| 直接修改全局五类Planner和默认注册表 | evidence_search改归属、资产四步流程和旧缓存都会受影响 | 不采用，兼容风险更大 |
| 沿用旧类型，暂不支持asset_lookup或只执行get_vulnerability | 文件较少，但不能兑现资产、版本、证据调查要求 | 不采用 |

确认本计划即确认以下适配：

1. 调查注册表只注册一个IntelligenceInvestigationAgent，evidence_search在该配置中归属调查Agent；原默认verification_agent接口及原归属不变。
2. 添加调查专用asset_lookup Schema/白名单及服务端配置注入，旧PlannerPlan、五类TASK_REGISTRY和默认task-plan-v1保持原意义。
3. 新增inspect_component_version只读工具包装已有身份/版本算法，以支持“vLLM 0.6.0是否落入来源声明范围”；不执行原WRITE匹配工具。
4. 对部分调查结果保留原Runtime失败/阻塞规则；结构化Artifact仍能返回已获取数据和partial_result，而不是把失败伪装成成功。
5. 本阶段提供可运行的内部调查服务和端到端验证，原七页网页入口不切换。网页展示与公开接口集成需要后续明确范围。

## 3. 输入、Planner配置与注册

原TaskContract不增加task_type/target/context字段。用户示例中的业务含义映射到Planner语义type、ToolStep.arguments和已验证输入scope。运行输入仍为AgentExecutionRequest(task, context, input_artifacts)。

新增固定服务端PlannerProfile：legacy-v1沿用原Plan Schema/角色/提示/验证；investigation-v1使用InvestigationPlannerPlan和三类角色。配置不能由模型或工具响应改变。LLMTaskPlanner、PlannerService、build_context和validate_plan只增加默认值为旧配置的参数，复用原重试、来源范围、权限、DAG验证和记录机制。

| investigation-v1类型 | 允许工具 | 最低验收 |
| --- | --- | --- |
| vulnerability_lookup | get_vulnerability、search_vulnerabilities、inspect_component_version | tools_succeeded、output_nonempty |
| evidence_search | get_evidence、get_claims、relation_query、semantic_search | tools_succeeded、output_nonempty、evidence_present |
| asset_lookup | get_asset | tools_succeeded、output_nonempty |

三类工具并集恰好8项，保持AgentContract上限。默认READ_ONLY。find_poc_candidates/find_patch_candidates已经存在，本阶段从get_vulnerability.intelligence及relation_query取得相同候选记录，不额外扩大工具集。

- 单一显式CVE必须实际调用get_vulnerability，检索列表不能替代精确目标查询。多个CVE按任务拆开，保持总预算，不在一个单对象中混合不同漏洞。
- 有明确组件/版本及目标时，漏洞任务可包含inspect_component_version步骤；参数逐字段匹配scope.component和原targets。缺少版本时input_required，不从公告补造用户版本。
- 查询资产只能使用明确且同所有者asset_id；缺少ID时input_required，不自动list_assets选择或伪造UUID。get_asset只返回已录入组件/部署字段，不代表实时服务器扫描。
- evidence_search允许依赖已接受的漏洞/资产查询；参数必须在原用户scope内，semantic_search.query必须等于原问题。
- 调查配置不生成version_match/patch_analysis/risk_analysis任务；资产四步约束仅在旧配置生效。调查配置不能用于宣称已完成资产风险分析。
- Planner配置、候选Schema、prompt_version和registry_version必须在规划审计中保存，并纳入请求幂等摘要；cached candidate重验与Runtime绑定必须使用同一配置。旧记录默认解释为legacy-v1，不重新绑定。
- ProfessionalRuntimeService、AgentRouter和AgentExecutor的内部再路由均使用同一可注入、固定的角色表；默认不变。从同所有者Planner审计检查配置标识，不能信任调用方自行填route或工具返回的profile字段。仅增加配置传递，不修改执行验收。
- 新注册工厂create_investigation_registry(implementation: InvestigationAgent | None=None)只注册agent_id=investigation_agent；实施前半段可用None验证接口/路由，正式调查服务必须显式注入IntelligenceInvestigationAgent，其implementation_key=intelligence-investigation-v1。create_default_registry()保持三个interface_only注册。

## 4. InvestigationArtifact

新增冻结、extra=forbid、禁止NaN的Pydantic业务模型。它引用原Runtime Artifact身份而不覆盖原协议；执行时构建并用于判断不确定性，读取时从执行快照重建，不重新查询最新情报，不依赖内存缓存。

| 字段 | 定义 |
| --- | --- |
| artifact_id、task_id、agent_id、run_id | 原Artifact/绑定身份；agent_id固定investigation_agent |
| schema_version | investigation-artifact-v1，用于固定历史投影解释 |
| status | COMPLETE / PARTIAL / INSUFFICIENT_EVIDENCE / CONFLICT，表示调查数据状态 |
| runtime_status | 原SUCCESS / FAILED / WAITING_REVIEW / BLOCKED，不覆盖原终态 |
| partial_result | 有工具失败、返回partial、范围不完整或投影引用时为true，独立于冲突/不足状态 |
| vulnerability_id、canonical_id | 真实数据库UUID/CVE；没有取得时为null，不从模型生成 |
| component | 用户/资产提供的组件身份、原版本、消歧状态；缺少时为null |
| affected_versions、fixed_versions | 来源逐条声明，保留package/range/source/observation与当前性；不合并成唯一可信范围 |
| version_match | 工具返回的IN_RANGE / OUT_OF_RANGE / UNKNOWN、范围比较记录、来源和verified=false；缺失时明确未执行 |
| cvss、cwe | CVSS保留全部版本/来源/向量/分数；CWE保留原标识，不擅选单一CVSS |
| poc_candidates | 原候选关联及来源、observed_status；新调查分类只为CANDIDATE，不推断可用性、不执行代码 |
| patch_information | 原提交/PR/公告/修复版本记录及观察状态，不宣称适用于用户部署 |
| evidence | 工具原evidence_refs，保留原verified/claim_revision、raw/source ID、URL、定位、时间与信任标记 |
| uncertainties、conflicts | 明确字段/原因/来源；冲突保留双方及同范围，不执行核验或采纳 |
| confidence | 保留原安全置信度；目前一般为null，不使用Planner confidence，不生成主观0.8等分数 |
| tool_calls、dependency_artifact_ids | 原回执引用、状态、起止时间及已接受依赖身份；可追溯来源 |
| evidence_storage、receipt_references | 大结果明确指向完整持久化回执，带数量/摘要及可查询记录ID |
| findings | 列表查询的逐漏洞结构化结果；精确单目标查询不把其他漏洞混入同一结果 |

工具返回中的source_variants、affected_versions、cvss_assessments、intelligence.pocs/patches/claims/conflicts是字段来源。列表查询产生逐目标findings，不把首条结果冒充唯一命中；列表根对象的单漏洞字段为null。

业务状态优先级：存在当前同范围冲突→CONFLICT；针对漏洞调查缺少可追溯的可信来源或关键目标数据→INSUFFICIENT_EVIDENCE；其他非完整获取→PARTIAL；数据满足当前调查任务所需字段且无上述问题→COMPLETE。COMPLETE只表示本地调查步骤和数据完整，不表示安全事实已核验。

可信来源门槛仅描述可调查性：source_id/raw_document_id/URL/定位可追溯，来源authority_level为official或authoritative，并有执行时当前性依据。未知authority/current、仅GitHub提及、仅向量相似度不能满足。该门槛不创建VerificationResult，不升级Claim，也不证明多源独立性；authority_scope和lineage保留给后续核验。

冲突优先使用已有未解决Conflict记录；若当前同scope_key的结构化来源声明存在差异，复用enrichment.rules.compare_claims纯比较函数生成待核验标记，不调用会写库的ConflictDetectionService。不同package/branch/时间范围不直接判冲突，历史记录不覆盖当前声明。

所有字段只能源于当前任务回执及实际接受的依赖Artifact；归一化不创建CVE、补丁、版本、来源或verified=true。超限返回明确的有界引用结果及不确定性，完整证据保留于ToolCallRecord，不能悄悄裁掉尾部数据。

## 5. 调查执行、部分失败与Trace

```text
IntelligenceInvestigationService.plan_and_run(PlannerInput, actor)
  → 原LLMTaskPlanner + ModelGateway（investigation-v1配置）
  → 原计划验证 + 固定三类白名单
  → 原ProfessionalRuntimeService + 调查Registry
  → 原DAG/Scheduler + AgentExecutor
  → IntelligenceInvestigationAgent.investigate
  → 原ProcessSupervisor（逐个已授权只读步骤）
  → 原worker → ToolGateway → 原情报/关系/向量/资产服务
  → 原ToolReceipt + 精确outputs/dependencies + 原验收
  → InvestigationArtifact标准化 / 不确定性判定
  → 原Store保存回执和TaskArtifact
  → read_results从同所有者快照重建业务Artifact与Trace
```

执行方法仍返回ExecutionOutcome。业务Artifact不会作为未验收的任意字段写进SUCCESS result；不修改原AgentExecutor成功结果比较规则。标准化只可增加不确定性或把SUCCESS降为WAITING_REVIEW，不能升级FAILED/WAITING_REVIEW/BLOCKED。

为满足工具失败后的部分结果，Agent复用原ProcessSupervisor执行固定单步TaskContract：原目标、参数、task_id、trace/run/actor均保持；子步骤不含依赖、不生成新计划，最终依赖ID仍是原Task的准确列表。子步骤的ToolReceipt按原授权顺序重编号1…N，原时间/参数/Envelope不变；父级重新调用validate_receipts/validate_outcome。总调用次数等于授权步骤数，每次期限取原deadline，max_tool_calls没有被放大。

工具failed/no_result/partial时保留回执，若期限和取消状态允许，继续后续独立只读步骤；不会重试、换工具、刷新或用前一步结果拼新参数。遇到取消、总超时、隔离/协议/cleanup失败时停止，保留已完成回执，未执行步骤明确记录。原进程监管负责所有子进程清理，for_run提供独立Supervisor。

| 情况 | 调查Artifact | Runtime行为 |
| --- | --- | --- |
| 数据完整且满足原验收 | COMPLETE | 原验收SUCCESS，依赖可继续 |
| 一项工具failed、其他数据已取得 | partial_result=true；有可信数据为PARTIAL，否则INSUFFICIENT_EVIDENCE | 保留FAILED和失败码；下游依赖BLOCKED |
| no_result/partial或可信证据不足 | INSUFFICIENT_EVIDENCE或PARTIAL，说明覆盖范围 | WAITING_REVIEW或保留更严格的FAILED；不推断安全 |
| 同范围来源冲突 | CONFLICT，保留两侧证据 | SUCCESS降为WAITING_REVIEW；交给未来Verification Agent |
| asset_id/版本缺少 | 说明Required Input | 原input_required→WAITING_REVIEW |
| 超时/取消/隔离异常 | 记录partial_result及中断原因 | 保留原失败和cleanup判定，不再调用工具 |

注意：本阶段默认查询本地已采集情报；NVD实时采集故障不由本Agent重新联网恢复。工具失败测试覆盖Gateway/已注册服务失败；如数据库中有采集失败/覆盖缺口，按来源时间和查询结果表达，不编造实时NVD调用。

新增IntelligenceInvestigationService组合原PlannerService与ProfessionalRuntimeService，提供plan_and_run(input, actor)、read_results(run_id, actor)。read_results返回InvestigationRunResult（run_id、原运行状态、逐任务InvestigationArtifact、工具引用、未执行/阻塞节点说明），只读同所有者记录。旧read_trace/read_agent_trace结构保持。

专业AgentRun→ToolCallRecord→TaskArtifact关系已存在，继续沿用，不新增表或第二套审计。业务Reader校验绑定fingerprint、原Task和回执身份、依赖是否真正接受、工具实际记录ID及投影版本；新Reader得到相同结果。所有来源快照来自当次Envelope；不会以当前数据库值替换历史调查。

投影Schema版本由已保存的implementation_key映射为investigation-artifact-v1；未知实现/投影版本明确拒绝，不能用最新版归一化规则悄悄重新解释历史记录。执行时记录call_index，持久化Reader增加原Store生成的正式record_id，不伪造尚未分配的记录ID。

## 6. 修改文件与职责

新增正式文件：

- backend/app/agents/investigation/__init__.py：最小包入口。
- backend/app/agents/investigation/schemas.py：InvestigationArtifact、字段子模型、InvestigationRunResult。
- backend/app/agents/investigation/normalize.py：仅从回执/已接受依赖做确定性字段映射及不确定性/冲突标记。
- backend/app/agents/investigation/agent.py：唯一具体Agent、逐步骤原Supervisor委托、回执合并、for_run/cancel_all。
- backend/app/agents/investigation/registry.py：create_investigation_registry，仅一个实现。
- backend/app/agents/investigation/service.py：显式服务组合及读取入口。
- backend/app/agents/investigation/reader.py：同所有者持久化业务投影及工具引用读取。
- backend/app/planner/profiles.py：冻结legacy/investigation能力配置、角色表、Schema/提示版本选择。
- backend/app/planner/investigation_schemas.py：三类调查候选Schema及asset_lookup类型，原PlannerPlan不变。
- backend/app/planner/prompts/investigation_plan_v1.txt：固定调查范围/版本只读步骤/证据候选/权限预算。
- backend/app/tooling/investigation.py：inspect_component_version的薄只读业务包装。

既有文件仅增量适配：

| 文件 | 必要变化 |
| --- | --- |
| backend/app/agents/contracts.py | 专业语义类型允许asset_lookup；原工具/预算限制不变 |
| backend/app/agents/router.py | 可注入角色表，默认原TASK_REGISTRY；不修改绑定和图验证算法 |
| backend/app/agents/executor.py | 可选角色表传入内部AgentRouter，使绑定与执行再路由一致；原SUCCESS结果比较和验收完全保留 |
| backend/app/agents/service.py | 可注入固定Planner配置/候选Schema；核对审计配置；默认旧行为 |
| backend/app/planner/schemas.py | PlannerContext记录服务端profile_id，默认legacy-v1；原PlannerPlan任务类型不变 |
| backend/app/planner/context.py | 可选配置参数，完整保留原用户scope；不删除asset_analysis事实 |
| backend/app/planner/llm_planner.py | 构造注入配置、选择固定Schema/角色/提示；原Gateway调用、两次重试及Trace逻辑复用 |
| backend/app/planner/validator.py | 可选配置决定候选解析/角色/调查覆盖规则；公共scope/权限/refresh/DAG校验不削弱 |
| backend/app/planner/service.py | 构造注入固定配置，初次规划与缓存重验使用同配置；默认旧行为 |
| backend/app/planner/trace.py | 记录配置版本；核对缓存解释，保留旧记录兼容及原所有者/幂等规则 |
| backend/app/tooling/contracts.py | 注册inspect_component_version和严格输入Schema，READ_ONLY |
| backend/app/tooling/adapters.py | 分派薄包装；给证据引用增加已有Source authority_scope/level、lineage、当前性元数据，不升级verified |

不修改Runtime/DAG/Scheduler/ProcessSupervisor/原Executor/Store、AgentExecutor验收、Model/Tool Gateway核心、旧业务算法、Embedding、数据库模型/Migration、前端或Dify。

新增测试在backend/tests/agents/investigation/；实施证据在work/investigation/；最终报告PHASE_11B1_RESULT.md。实施前记录旧文件哈希，结束核对批准变化和零删除。当前无Git，不初始化仓库、编造提交或覆盖前一阶段证据。

## 7. 实施步骤

### Task 1：业务Schema与回执标准化

**Files:** 新增investigation/schemas.py、normalize.py；测试test_artifact.py、test_normalize.py。

**Interfaces:** 消费TaskContract、ExecutionOutcome、tuple[AgentArtifact,...]；产出normalize_investigation(task: TaskContract, outcome: ExecutionOutcome, dependencies: tuple[AgentArtifact,...]) -> InvestigationArtifact。该函数不访问数据库、不调用工具/模型。

- [ ] 写test_cve_artifact_preserves_provenance：断言原身份、CVSS全部来源、CWE、版本、raw/source定位保持，confidence=None。
- [ ] 写test_poc_is_candidate、test_no_authoritative_source_is_insufficient、test_same_scope_conflict、test_historical_source_not_current、test_cross_target_dependency_rejected、test_projection_size_reference：分别固定候选不升级、无可信源状态、双方冲突、历史/异范围区分、身份拒绝、超限明确引用。
- [ ] 实际运行新测试，确认因缺失实现失败；保存RED日志。
- [ ] 实现上述Schema/映射，复用compare_claims，不调用核验Service；保留原证据值和候选observed_status。
- [ ] 运行并确认该组全部通过，保存GREEN；记录文件哈希及完成项。

### Task 2：调查Planner配置与Registry/Router接入

**Files:** 新增profiles.py、investigation_schemas.py、调查prompt、investigation/registry.py；修改第6节对应Planner/Agent兼容文件；测试test_profile.py、test_registration.py。

**Interfaces:** 产出get_profile(profile_id: str) -> PlannerProfile、create_investigation_registry(implementation: InvestigationAgent | None=None) -> AgentRegistry；现有LLMTaskPlanner/PlannerService/ProfessionalRuntimeService构造增加profile可选参数，默认legacy-v1；build_context/validate_plan使用同一固定配置。AgentRouter及AgentExecutor构造增加task_registry可选参数，默认原TASK_REGISTRY；ProfessionalRuntimeService在_make_scheduler中传入同一角色表。

- [ ] 写test_profile_has_exact_three_roles、test_evidence_routes_to_investigation、test_asset_lookup_registered、test_legacy_schema_unchanged、test_profile_switch_requires_new_key、test_unknown_profile_and_write_rejected：断言三类/8工具、唯一负责者、旧五类拒绝asset_lookup、审计/幂等一致、禁止WRITE/refresh/伪造route。
- [ ] 写test_component_question_does_not_spawn_risk_agent、test_missing_asset_id_requires_input：调查配置只产生实际调查节点，原资产四步要求在legacy配置仍生效。
- [ ] 运行RED并保存；按最小可选配置钩子实现，保留原循环和公共验证。
- [ ] 运行新组＋原Planner/Agents回归，确认旧默认流程不变；保存GREEN。此时具体Agent若尚未安装保持明确未实现，不假装完成调用。

### Task 3：只读版本观察工具与来源元数据

**Files:** 新增tooling/investigation.py；修改tooling/contracts.py、adapters.py；测试test_version_tool.py、test_evidence_metadata.py。

**Interfaces:** 产出inspect_component_version(session, arguments: dict, actor: str) -> dict；输入target与现有ResolutionInput字段，其中version必填。从原工具入口invoke取得结果，Agent不能调用该函数。输出identity_resolution、source_range_results、coverage、uncertainties和provenance。

- [ ] 写test_vllm_060_range_result、test_exact_package_and_boundaries、test_ambiguous_identity_unknown、test_unsupported_version_unknown、test_fixed_version_is_source_assertion：复用已保存的合成范围，断言精确边界、身份消歧、未知弃权与来源修复版本。
- [ ] 写test_version_tool_read_only_no_model_mutations：比较业务表前后记录/修订，不创建Claim、Evidence、Asset、风险快照或VerificationResult。
- [ ] 写test_authority_metadata_does_not_verify、test_source_currentness_and_lineage：仅增加已有Source/观察元数据，保持原verified及source assertions。
- [ ] 运行RED；薄包装复用resolve_component、vulnerability_detail和compare_version；按包/当前观察过滤，结果不猜安全性。
- [ ] 运行GREEN及原工具/版本/资产测试；保存SQL写入检查与结果。

### Task 4：唯一调查Agent、独立运行实例与部分失败

**Files:** 新增investigation/agent.py，完成调查注册工厂；测试test_agent.py、test_process.py。

**Interfaces:** IntelligenceInvestigationAgent(InvestigationAgent)实现investigate(request: AgentExecutionRequest, *, database_url: str | None=None) -> ExecutionOutcome、for_run(run_id: UUID) -> IntelligenceInvestigationAgent、cancel_all() -> None。每次运行独立Supervisor；固定implementation_key=intelligence-investigation-v1。

- [ ] 写test_agent_executes_only_authorized_steps、test_gateway_failure_retains_partial_and_later_receipts、test_unknown_tool_no_call、test_original_result_exact：失败继续独立只读步骤，顺序/参数/编号原样，返回回执精确outputs/dependencies。
- [ ] 写test_conflict_and_insufficient_do_not_unlock、test_timeout_cancel_cleanup、test_parallel_runs_do_not_cross_cancel、test_failure_without_receipt_stops、test_total_budget_not_multiplied：Runtime状态不升级，不能绕过期限/隔离或扩大子步骤预算。
- [ ] 运行RED；委托原Supervisor，重新执行原回执/结果验收，构建调查Artifact并仅收紧终态。
- [ ] 运行GREEN及原Runtime进程/回执/AgentExecutor测试；实际覆盖进程超时/取消。测试里的故障注入与生产实现清晰区分。

### Task 5：持久化读取、完整业务链路与交付

**Files:** 新增investigation/service.py、reader.py；测试test_reader.py、test_end_to_end.py；新增work/investigation运行器及PHASE_11B1_RESULT.md。

**Interfaces:** IntelligenceInvestigationService(engine, model_gateway, *, policy=None).plan_and_run(input: PlannerInput, actor: str) -> PlannerSnapshot；read_results(run_id: UUID, actor: str) -> InvestigationRunResult。Reader只读取原Run/Task/ToolCallRecord的同所有者快照，不访问外部源、不重新调用工具或模型。

- [ ] 写test_query_planner_runtime_investigation_chain：问题→真实ModelGateway结构化调用（受控模型响应）→原Planner审计/验证→原Runtime/Agent→真实PostgreSQL与Tool Gateway→业务Artifact；不得绕过Planner直接提交预制Task冒充链路。
- [ ] 写用户要求的五项场景：CVE信息、vLLM 0.6.0版本观察、PoC候选、Gateway失败部分结果、无可信证据。增加asset_lookup、来源冲突、不同package/历史源、向量检索来源、跨所有者拒绝、同键不重执行及新Reader重建。
- [ ] 写test_projection_uses_execution_snapshot、test_canonical_receipt_id_and_size_limit、test_blocked_node_not_investigated：更新业务表不能改变历史调查；512 KiB边界与正式回执ID一致；阻塞节点没有虚构工具调用。
- [ ] 运行RED；实现固定配置组合与Reader，保持旧API/Trace返回结构。
- [ ] 新组GREEN后运行全部后端测试，包含原716项，保存命令、退出码、JUnit、日志及真实数量。CI模型仅Mock/受控Provider，不要求外部API或额度。
- [ ] 进行一次全范围独立只读审查；重要问题先复现失败再修复并完整回归。按本会话已有实施方式执行，不逐任务派发实现代理。
- [ ] 核对文件基线、只读业务表、进程清理；只停止本轮拥有的专用测试集群，保留全部失败/通过证据。
- [ ] 写PHASE_11B1_RESULT.md，包含用户要求的九个标题：Agent设计、调查流程、Artifact设计、工具调用、Trace变化、修改文件、测试结果、当前限制、下一阶段建议；如有未达到的验收项明确说明。
- [ ] 停止，不进入Verification Agent、Security Analysis Agent或Integration Gate。

实施测试命令由项目现有虚拟环境运行，不下载依赖。每组使用同一证据运行器：

```powershell
& 'backend/.venv/Scripts/python.exe' 'work/investigation/run_tests.py' task1_red -q tests/agents/investigation/test_artifact.py tests/agents/investigation/test_normalize.py
& 'backend/.venv/Scripts/python.exe' 'work/investigation/run_tests.py' focused_green -q tests/agents/investigation tests/agents tests/planner tests/runtime
& 'backend/.venv/Scripts/python.exe' 'work/investigation/run_tests.py' reviewed_full_suite -q
```

Expected：RED必须为本轮缺失实现/真实缺陷而失败；GREEN退出码0，全部选中测试通过。完整回归零失败、零错误、零跳过，新增数量以JUnit为准。数据库准备复用已有专用测试集群和fixture：迁移/空库测试与提交型Runtime数据使用独立数据库地址，业务主库不得作为测试目标。运行器保留既有阶段证据，不覆盖work/agents历史。

## 8. 验收与当前风险

| 验收项 | 必须取得的证据 |
| --- | --- |
| 只有一个具体专业Agent | 正式Registry仅investigation_agent，其他能力没有新增实现 |
| 三类Task接入 | vulnerability_lookup/evidence_search/asset_lookup均经过Schema、Validator、Router与Agent |
| 工具与混合检索复用 | Trace中有实际Tool Gateway回执，SQL/Relation/Vector按问题使用既有工具；无需每个问题强制三路都执行 |
| 结构化业务输出 | InvestigationArtifact通过Schema，来源/版本/PoC/补丁/不确定性有数据或明确空值原因 |
| 失败和不足 | partial_result与原失败状态同时保留；INSUFFICIENT_EVIDENCE、CONFLICT无伪造成功 |
| Trace持久化 | 新实例读取当次证据快照和正式ToolCallRecord ID，所有者隔离生效 |
| 稳定性 | 原716项回归与新增业务测试实际通过；批准文件范围外无产品变化 |

材料限制与风险：

- 调查配置是必要的新入口适配，不能简单复用旧资产四步计划，否则会调到尚未实现的风险Agent；兼容参数必须全部默认旧行为。
- 子步骤监管要保存完整回执并满足总预算，不能通过单步拆分规避调用上限；失败结果必须留在Trace，不能被业务PARTIAL掩盖。
- READ_ONLY版本工具只观察现有来源范围；本阶段不宣称资产风险判定、部署安全、补丁适用或PoC可用。
- 来源权威元数据不等于独立核验；博客/论文/仓库召回可能不足、旧向量集合有既定容量限制，必须报告覆盖范围。
- COMPLETE不等于Verified；confidence可为null。真实模型规划质量、实时采集时延和比赛Benchmark不能用受控测试代替。
- 旧取消测试曾有瞬时失败，实施时关注并保留记录；不在无根因情况下重写原进程监管。
- 内部服务完成不等于网页已展示；本阶段不接入公网或前端，不提前开发另外两个Agent。

## 9. 自查与交接

计划已对照用户要求覆盖：接口/注册/三类Task、四类工具能力、版本观察、结构化Artifact、证据候选、Trace、部分失败、信息不足、冲突、五项必需测试及最终报告。版本观察只新增现有算法的只读包装；采集/混合检索/工具调用通道不重复开发。

设计选择已明确写入第2节；本轮只生成此计划。**根据用户要求等待确认实施Phase 11-B1，确认前不修改产品代码。**

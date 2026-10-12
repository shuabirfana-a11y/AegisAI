# Phase12D.1 Planner稳定化实施计划

> For agentic workers: use superpowers:executing-plans inline, task-by-task, with TDD and one final independent review.

**Goal:** 让现有真实模型经实际HTTP专用Planner产出合法、可审计的计划，统计每种已有模型至少20次，并验收一次三Agent/Gate/Answer真实闭环。

**Architecture:** 修正现有Investigation Planner的模型输入契约与小范围提示，不改通用五任务Planner、Runtime、验证器或Gate。最外层tasks是DAG任务，input_data.steps是工具调用，禁止把两者自动重命名或补齐任务。错误仍明确失败，不自动切Mock。

**Tech stack:** 已有FastAPI/Pydantic、Model/Tool Gateway、Windows Ollama、PostgreSQL；不安装依赖或新模型。

**Spec:** 用户本轮Phase12D.1指令，以及本计划“已查明事实/边界”。本轮已明确授权实施，不重复索取整个阶段的实施许可。

## 已查明事实与边界

1. 旧探测使用LLMTaskPlanner五任务，而HTTP使用InvestigationPlannerAdapter三种既有任务与8个只读工具。
2. InvestigationTaskCandidate直接继承TaskContract，没有Phase12D的TaskInput schema描述：当前Schema接受input_data.target，但原Pydantic拒绝。实际最终HTTP两个候选均SCHEMA_VALIDATION_FAILED。
3. 通用五任务规划的FALSE_MISSING_INPUT不能当作HTTP专用Planner的失败统计。新样本只调用后者。
4. 专用版本观察使用已注册inspect_component_version，不新增version_match/risk_analysis任务；Risk Agent是后续独立阶段。三个专用任务白名单不变。
5. 两种模型只使用已安装Qwen2.5 7B和Qwen3.5 4B；模型请求串行、固定参数。每种20逻辑调查，允许原有最多两次规划尝试，分母同时记录请求与尝试。
6. 三类固定问题：CVE事实、明确版本条件、同一CVE的多步骤证据调查。资产库存如需建立仅为明确标注的本机演示输入，不伪造来源/答案/安全结论、不修改已有库存。
7. 结构化失败不删除Validation或自动修补任务，不改白名单、权限、Runtime、Agent安全规则或Gate；无需修复层时不引入。
8. 协议/计划稳定性不是安全准确率，不进入正式AegisBench、部署或更多模型接入。

## Review Focus

- 任务层级混淆、未知任务或工具必须被拒绝。
- 缺失库存/版本不能发明ID、伪造影响结论或隐式降级。
- 同一CVE重复get_vulnerability导致交接歧义：模型须生成一个包含必要观察的调查任务。
- 统计中区分JSON、Schema、语义合法、完整阶段执行及Gate验收；缺失证据不可算安全通过。
- 中断/超时记录失败并终止自己的探测进程；不遗留旧成功报告，不停止其他服务。

### Task 1: 修正实际HTTP Planner契约

Files: backend/app/agents/investigation/planning.py；必要时planner.py、roles.py和新增investigation_plan_v2.txt；新增tests/agents/investigation/test_model_schema.py。既有prompt v1、两种Validation、Runtime及Agent业务源码保持。

Interfaces: InvestigationPlannerAdapter.plan(input, context) -> PlanningOutcome；InvestigationPlan的tasks/type/input_data.steps与既有TaskContract兼容；调用原Gateway.generate_structured。

- [ ] 先写Schema错误结构拒绝、正常steps/asset类型兼容、三个任务白名单和非法工具拒绝测试；确认当前错误结构测试失败。
- [ ] 最小复用既有TaskInput Schema/TaskContract描述，不添加任务或执行逻辑；跑原13项规划测试与新Schema测试。
- [ ] 对同一个真实CVE调用实际Adapter，记录原始失败位置。若需要，只增加明确嵌套结构、工具白名单/作用和角色相关缺失输入的小范围v2提示；固定输出参数与工具Schema排序。
- [ ] 先写提示版本、合法/非法输出、无自动修复/隐式Mock、重试上限测试，再实施提示元数据。
- [ ] 真实小样本达到合法计划后提交Task1；保留失败回执，不以合成回执替代。

### Task 2: 固定问题集、20次实跑与HTTP闭环

Files: demo/phase12d1/cases.json；backend/scripts/probe_planner_stability.py；tests/investigation_api/test_planner_stability.py；忽略的work/phase12d1保存本机绑定和私有诊断。

Interfaces: run_stability_case(client, case, deadline_seconds) -> sanitized run receipt；summarize(receipts) -> denominated JSON/schema/task/chain metrics。用原创建/状态/Trace/Artifact/Integration/Answer接口，保存真实Run/Artifact/Integration IDs；原调查状态无改写。

- [ ] 用受控协议写统计分母、错误/缺失结果、非法模拟、模式拒绝、冻结读取和中断失败测试，观察缺少实现而失败。
- [ ] 实现有限轮询与每逻辑调用分母统计；公开回执无Key/提示/原始输出，真实模型与合成协议测试分开。
- [ ] 固定3种问题按7/7/6顺序，每种已有模型20次；不随机筛除失败。JSON/Schema按实际捕获输出计算，Task按原验证结果，Gate通过只认PASS/PASS_WITH_WARNINGS。
- [ ] 记录完整阶段执行率与完整验收成功率，不把HUMAN_REVIEW/REPLAN_REQUIRED当Gate通过。推荐配置至少19/20合法计划、三类均有合法样本；一次真实模型+真实来源的完整Gate通过是必须项。
- [ ] 重复读取成功Answer确认额外模型调用0，记录PERSISTED_PLANNER_CALL/REAL与所有运行引用；未满足则继续定位，不篡改结果。
- [ ] 提交Runner/问题集及脱敏实跑证据。

### Task 3: 回归、审查与交付

Files: PHASE_12D1_RESULT.md；CURRENT_STATUS.md；docs/phase12d1/验证摘要与精确源码例外；必要的交接状态说明。

- [ ] 跑新增测试、既有Planner/调查/Orchestrator/API/TCP回归、基础CI与契约。历史1261与本轮实跑分别记录，已通过集不无故重跑。
- [ ] 对本轮获授权Planner文件建立独立版本化哈希记录；原基线及Phase12D摘要不改写；其他业务文件继续保护。
- [ ] 一次独立全分支代码审查，发现重要问题先复现测试再修复。
- [ ] 生成结果报告：模型/提示/Schema版本、20次分母与失败、实际完整链IDs、限制。秘密/包校验后按已有GitHub授权提交草稿PR，不自动合并main。
- [ ] 满足稳定计划、原验证有效、真实三Agent/Gate/Answer闭环后停止，不进入Benchmark/部署。

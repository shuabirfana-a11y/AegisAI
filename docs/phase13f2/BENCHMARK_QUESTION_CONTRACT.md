# Benchmark 输入契约

适用项目：AegisAI（ICT 命题九）。这是 evaluation 侧的输入适配说明，不是新 HTTP API。

## 输入来自哪里

只允许原始 `Question.question`、`Question.input_context` 和调用者实际拥有的资产登记绑定。`expected_answer`、人工证据、标注/复核状态、类别提示名称均不能进入调查请求。题号可以用于离线关联记录，不能用作资产名称或模型上下文。

`BenchmarkQuestionContract.from_input()` 对输入执行本地检查，产生 READY 或 INPUT_REQUIRED。它不会生成版本、资产、证据或任务，也不进入模型 Prompt。HTTP 请求仍由已有 `build_request()` 生成并通过真实 InvestigationCreateRequest 验证。

## 各题型要求

| 题型 | 原题输入 | 实际绑定 | 现有 objective_profile |
|---|---|---|---|
| facts | 精确 vulnerability_id（现有字段 target） | 无资产要求 | overview_v1 |
| poc_patch | 精确 target；问题说明需要哪类候选信息 | 无资产要求 | overview_v1 |
| version | target、component、version | asset_id、component_id | asset_risk_v1 |
| risk | 资产中的 component/version、target；环境与暴露条件来自真实登记 | asset_id、component_id | asset_risk_v1 |
| multihop | 原问题提供 objective，原 context 提供 target/scope；涉及部署资产时提供 component/version | 涉及资产时必须有实际绑定 | 按真实输入选择既有 profile |

现有 HTTP 适配只支持一目标、一资产。多目标不是新的 Benchmark 支持承诺；模型侧仍按原 Runtime 已支持的多目标 Schema 校验。

## 字段映射

| Benchmark | HTTP | 约束 |
|---|---|---|
| question | user_query | 原文，不含标准答案 |
| input_context.target / 单元素 targets | asset_scope.target | 不从标准答案提取 |
| component + ecosystem + version | asset_scope.component | 已提供的字段原样传递；缺版本保持缺失 |
| input_context.asset 或单元素 assets | 本地展平读取 | 和外层相同字段不同值时拒绝，不静默覆盖 |
| 实际资产绑定 | asset_scope.asset_id / component_id | 原题的演示名称不能充当数据库资产 ID |
| category | 本地选择既有 objective_profile | category 本身不作为模型/工具输入 |

精确漏洞总览中的 component 是公告对象提示，不是部署资产，不触发凭空补版本。没有 target 的组件检索仍保留组件查询范围。API 参数和公开 TypeScript/OpenAPI 契约未变化。

## 缺失与错误

无版本：INPUT_REQUIRED，version=null，missing_fields 包含 version。可调查已有漏洞信息，但不得把不完整资产风险题当已回答。

未绑定资产：现有 ASSET_BINDING_REQUIRED；未知、数字、字典类型的 targets：受控 ValueError，适配器报告 REQUEST_BINDING_INVALID。多资产、多目标、输入互相冲突继续拒绝。禁止自动生成或猜测。

## Planner 的模型侧限制

复用原角色、工具、Tool Input Schema，把 target、component/version、asset_id、语义检索 query 绑定到实际输入。只在确有版本时提供版本工具参数；缺版本保留原 input_required 类型。共享 `$defs/ScopedToolStep` 避免重复膨胀。

Gateway 的 JSON/Schema 验证、原 Planner Validator、角色权限、Runtime 预算均继续执行。模型侧 Schema 不是权限边界的替代，也不能保证小模型稳定生成合法计划。v5 的 5 题实跑仍有重复 JSON 键、角色/工具错误和重复调查任务，详见结果报告；不得宣称已恢复正式评测准入。

# 真实模型联调发现：Planner 输入 Schema 缺少既有结构

2026-10-12，Phase 12-D。用户已明确批准仅补齐 Planner 输入 Schema；已执行的变动仅为Schema元数据，Runtime、提示词和验证器保持原实现。

## 已验证事实

- 本机 Ollama v0.40.3 + Qwen2.5 7B Q4_K_M 已安装。
- 通过原 Model Gateway 的模型健康检查与文本调用成功；初次冷启动有一条60秒 TIMEOUT，随后预热调用成功。
- 5次小型结构化输出均通过本地验证。这只是本轮格式检查，不是安全准确率。
- 两种真实 Planner 输入、每种最多两次尝试，均为 PLANNING_FAILED / SCHEMA_VALIDATION_FAILED。
- 另一次只读诊断复现同一问题：JSON Schema检查通过，但原 Pydantic Runtime约束拒绝 input_data.target。

## 原因

现有 PlannerTaskContract 继承的 input_data 声明为任意JSON对象。生成给模型的JSON Schema允许任意字段。

实际 TaskContract.valid_payload() 会把同一个对象交给既有 TaskInput 验证。TaskInput只允许 steps 和 required_fields；工具调用应为 steps[].name/arguments，不能直接将 target 放在 input_data 下。

模型返回 input_data.target 可以通过目前展示的JSON Schema，却不能通过原Runtime验证。原系统正确拒绝了它，没有执行非法计划。

## 已批准的Schema修复

只在 backend/app/planner/schemas.py 的 PlannerTaskContract.input_data 增加JSON Schema元数据，复用既有 TaskInput.model_json_schema()，把嵌套 ToolStep引用就地展开。保留Python字段为字典，保留全部既有验证器和执行逻辑。

不改任务白名单、权限、预算、DAG、Runtime、Agent、Gate、风险评分或提示词。不补写/修复模型返回的计划。

先用测试证明当前Schema接受的错误结构应被拒绝，再执行这个元数据修复并跑Planner/Runtime回归和真实模型联调。初始建议差异保存于本机 work/phase12d/planner-schema-proposal.diff。结构修复已实施并通过回归；真实服务对组合Schema的解码表现另行记录。

## 为什么需要单独确认

用户本阶段明确禁止“修改 Planner”。虽然建议只补齐接口Schema，不涉及规划业务规则，但文件属于Planner。本阶段先完成Provider、模式隔离、公共Trace和前端契约等已授权工作；这个额外文件修改已经取得用户的明确确认。

在批准且实际复测通过前，不宣称完整真实调查链路已经成功。

后续诊断发现：工具任务必须有非空steps和工具白名单，input_required必须零工具并列出缺失字段。这些都是原TaskContract的既有约束，已在模型Schema中描述，未调整验证器。Ollama在anyOf与公共字段并列时会生成缺少task_id/type/description的对象；现用完整分支表达同一约束。最终模型是否通过，以实际Provider/HTTP报告为准。

# Phase 13-F.3 实施范围

直接执行用户给定的归一化/模板/5题验证设计；不新增 Agent，不扩大修复范围。基线为 Phase13-F.2 68efb25a9f09a1facd2ac254505d1a21011b9e0d，复用独立工作树，分支 codex/phase13f3-normalization-templates。

原始证据：F.2 保存的计划存在重复 JSON type 键、证据工具放入漏洞角色，以及重复同目标 get_vulnerability 导致根 Artifact 歧义。版本漏传是 F.1 已修的历史问题，不能把本次剩余失败全部归因于评测输入缺失。

范围：

1. 不调用模型的 literal QuestionNormalizer，复用已有 DTO/字段；明确输入缺失/歧义/冲突，保留 provenance。CVSS、公告版本范围不能变成部署观察。
2. Evaluation Request Builder 使用它读取原问题/原上下文/实际绑定；Backend Planner adapter 使用同一模块描述其冻结输入，不改变 Validator 作用域或字段。
3. 四类通用 intent 任务模板只提供角色/工具指导，不生成实际 Runtime TaskContract。模型仍必须通过 Gateway 自己生成结构化计划。
4. 模型侧 Schema 展示每个字段一次，保留原输入工具绑定，补齐角色工具约束和同目标根查询唯一要求。strict_json、原 Validator、Task白名单、Runtime、Agent/Risk/Gate规则不改。
5. 控制测试先 RED，再 GREEN；既有 portable、evaluation 和 OpenAPI 契约回归。固定原五题新隔离库各创建一次调查，不调用评分器，不运行39题。

数据/模型/代码/提示冻结及 5 题请求与结果全部保存。未知题允许 Gate REPLAN_REQUIRED；进入完整链路不等于正确回答或 Gate 必须通过。若五题仍不能全部规划/进入链路，报告未恢复，不追加无限调试或模型调用。

不把人工答案、review 标记、题号中的分类、原资料的冲突标签加入 Model Prompt/Context。来源冲突场景使用原问题，冲突须由执行后的源数据发现。

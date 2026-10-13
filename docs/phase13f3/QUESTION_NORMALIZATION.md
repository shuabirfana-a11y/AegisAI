# 问题归一化与任务模板

本层把已有输入变成模型能读懂的调查目标。它不产生计划、不查库、不调用模型、不补答案。模型仍通过 Model Gateway 生成 Task Plan，再经过原 Validation、Runtime、专业 Agent 和 Gate。

## 输入与来源

输入只有原问题、原 `input_context` 和已经创建且受权限控制的资产绑定。`expected_answer`、`ground_truth`、`review_status`、标注/复核身份等标签字段递归拒绝。原问题不重写，题号和题目分类不进入请求。

字段优先使用原上下文；缺失时只读取字面 CVE、已识别组件名称，以及明确部署/版本适用性问题中的单一版本。CVSS 3.1、官方受影响范围、修复版本、多个候选版本都不能当成当前部署版本。未知版本仍为 null，显式互相矛盾的输入拒绝。

资产 ID 只能来自真实绑定。模型不能创造企业资产；本轮用中性随机名称的受控演示库存，不是企业扫描数据。归一化只保留已有 environment/exposure/criticality，不推算这些属性。

输出 `NormalizedQuestion`：objective、vulnerability_id、targets、component、version、asset_context、task_type、input_status、missing_fields、warnings、provenance。状态 READY 表示字面输入完整，不表示证据可信；INPUT_REQUIRED 保留缺失；AMBIGUOUS 阻止多义输入悄悄选值。

## 两个接入位置

Evaluation Request Builder 可从原问题提取显式字面字段，填入既有 InvestigationRequest。Backend Planner adapter 使用同一模块描述已经冻结的 Scope，设置 `extract_literals=False`，不能重新解释出 Scope 外的组件或版本。未修改公共 DTO、PlannerService、旧 build_context 或 Validator。

## 四类模板

| 意图 | 模板 | 指导 |
|---|---|---|
| vulnerability_fact | vulnerability-fact-v1 | 一个漏洞根查询；需要 Claim/Evidence 时建立独立 evidence_search 角色任务 |
| version_impact | version-impact-v1 | 当前版本观察和漏洞查询放在同一个根任务；独立读取真实绑定资产 |
| asset_risk | asset-risk-v1 | 查询资产、漏洞和版本证据；最终 Verification/Risk/Gate 由后续服务器阶段执行 |
| evidence_conflict | evidence-conflict-v1 | 保存来源分歧，交后续核验；Planner 不能裁定哪个来源正确 |

模板只有说明和现有角色列表，没有具体 tasks、无确定性备用计划。问题没有写明“冲突”时不能从题号或人工标签选择冲突模板；来源冲突须在实际取证后发现。

## 模型侧约束

提示 v6 使用四个通用 wire-format 示例；所有占位符来自冻结输入。每个 JSON 字段只出现一次，role `type` 和执行类型 `task_type` 区分。动态 Schema 将完整 Task 字段定义一次，并引用角色可用工具；每个目标只允许一个 get_vulnerability 根查询。仅真正需要且缺失的输入可成为 input_required，事实查询不能误要求部署版本。

动态约束是生成侧限制，后续仍经过 strict_json、原 Pydantic/Validator、角色/工具白名单、DAG/预算检查。没有更改 Runtime、Agent 权限、Risk 或 Gate 规则。

## 当前边界

只支持有限组件字面表，不是任意软件名称/版本的完整实体识别器；无法确定的别名和多组件保持未知/歧义。单次 5 题诊断不能证明模型长期稳定、答案准确或全 39 题成功。任何 Gate 阻断必须保留。

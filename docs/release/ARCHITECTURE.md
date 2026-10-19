# 架构与源码入口

系统由情报监测、情报富化和资产上下文问答组成。Planner产生候选计划，服务端检查Schema、任务目录、权限、必需节点和依赖，Runtime再执行正式计划。角色产物以Artifact交接，Evidence关联来源与原文，Claim保存待核验命题，Verification记录支持、冲突和不足。资产分析比较固定版本和适用范围，Integration Gate检查当前调查交付，AnswerEnvelope封存已接受的结果及警告。

|机制|源码|
|---|---|
|服务入口与接口|backend/app/main.py、backend/app/investigation_api/|
|任务需求、补齐和复验|backend/app/agents/investigation/task_invariants.py、planning.py、validation.py|
|字段反馈与被拒计划上下文|backend/app/agents/investigation/schema_feedback.py、retry_context.py|
|来源独立性|backend/app/enrichment/evidence.py|
|包身份与版本范围|backend/app/enrichment/package_registry.py、version_scope.py|
|Evidence/Claim核验|backend/app/enrichment/rules.py、backend/app/agents/verification/|
|资产适用性与风险|backend/app/agents/analysis/、backend/app/assets/|
|统一验收和答案封存|backend/app/integration/、backend/app/orchestration/|
|工作台与代理|frontend/public/modules/pages/assistant.js、frontend/server.mjs|

来源转载和镜像按实际关系核对，多个URL不能自动算作多个独立事实依据。包发布元数据可支持身份与发布版本，但不能单独支持漏洞影响。公告范围、资产应用补丁和实际利用状态分别表达；缺少依据时保留未知或人工复核。

完整设计与源码节选见同目录上一级 submission 技术报告。企业资产发现、利用验证及补丁落地不是本次公开交付的已验证能力。

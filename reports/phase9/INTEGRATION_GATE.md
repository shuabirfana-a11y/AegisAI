# Phase9 INTEGRATION_GATE

状态：PASS / 保守策略

门禁区分PASS/PASS_WITH_WARNINGS/REPLAN_REQUIRED/HUMAN_REVIEW_REQUIRED/FAILED。CONFIRMED必须是当前受信Claim，匹配当前修订与支持证据；来源冲突/资产不确定进入人工复核。保守策略可使单个范围冲突阻止同漏洞其他事实的自然语言答案，需后续字段级裁决设计。

证据：backend/app/assistant/gate.py；storage.py；real_agent_cases.json

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

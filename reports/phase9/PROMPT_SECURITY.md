# Phase9 PROMPT_SECURITY

状态：PASS / 确定性执行边界

README/公告/PoC说明中的指令只作为外部数据。用户越权Shell请求真实运行0次工具；测试包括恶意来源文本、未知工具、额外字段、权限、owner隔离、假确认、缺证据、超时和调用预算。没有已激活LLM，不把这些结果表述为所有生成模型的提示注入防御保证。

证据：prompts/；backend/tests/test_phase9*；real_agent_cases.json

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。


## 本次续作更新

明确POC执行请求在调用工具前拒绝；真实运行0工具。未配置生成模型，未对LLM提示注入能力作认证。

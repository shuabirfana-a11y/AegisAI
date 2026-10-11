# Phase9 TOOL_GATEWAY

状态：PASS / 受限规模

30个具名工具，按QUERY/INVESTIGATION/VERIFICATION/ASSET/SYSTEM分类。HTTP仅READ_ONLY，服务端许可的编排才能WRITE/REVIEW_ACTION/EXTERNAL_NETWORK。严格Pydantic schema拒绝额外字段。固定Python worker，不接收SQL/URL/Shell/可执行POC；子进程超时终止，审计不包含凭证。

证据：backend/app/tooling/；docs/tooling/TOOL_CONTRACTS_V3.json；test_phase9_tools_knowledge.py

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

# Phase9 AGENT_ARCHITECTURE

状态：PARTIAL

Investigation收集来源陈述；Verification读取现有确定性核验；SecurityAnalysis合并已接受Artifact。角色只调用Gateway，不直接ORM查库，不重新实现版本/POC/Patch匹配。三个Python角色不等同于三个LLM Agent；实际模型辅助角色需后续Dify和模型服务验收。

证据：backend/app/assistant/roles.py；prompts/；integrations/dify/prompts/roles.v1.json

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

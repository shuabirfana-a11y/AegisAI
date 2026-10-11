# Phase9 FAST_PATH

状态：PARTIAL

单CVE路径最多get_vulnerability+get_claims两次工具。来源不足时弃答；存在来源冲突时进入WAITING_REVIEW。真实例子在real_agent_cases.json，未将一次延迟当作P50/P95。当前答案主要为结构化结果，未接生成模型，字段级自然语言表达仍受限。

证据：backend/app/assistant/orchestrator.py；real_agent_cases.json

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

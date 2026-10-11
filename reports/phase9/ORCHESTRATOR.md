# Phase9 ORCHESTRATOR

状态：PARTIAL

协调器管理路由、任务契约、依赖、进度、结构化handoff与门禁；业务能力来自Phase6–8工具。最多16任务、深度8、并发3、32工具、重试2、运行120秒。动态展开根据真实候选数据；没有LLM自主规划、模型切换或复杂自由重规划。

证据：backend/app/assistant/orchestrator.py；service.py

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

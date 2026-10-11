# Phase9 DEPENDENCY_GRAPH

状态：PASS

拒绝重复ID、未知依赖、环和超深图。独立调查层最多并行3个；只接受成功/部分且通过handoff的依赖。Task/Run到期标记blocked并取消未开始的任务；实际生产工具在固定子进程内执行，按更短任务/运行剩余时限终止。任意测试函数的线程不具备强制终止保证，不向调用方开放任意执行函数。

证据：backend/app/assistant/graph.py；test_scheduler_parallelizes_ready_tasks_and_waits_for_dependency_acceptance

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

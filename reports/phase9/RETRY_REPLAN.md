# Phase9 RETRY_REPLAN

状态：PARTIAL

仅retryable失败重试，最多2次；不可重试错误立即停止。Live刷新失败可切换同一白名单工具的缓存数据，保存原请求、原失败、替代参数和原因。测试为明确标记的故障注入，不称真实来源故障；不等同于LLM生成任意新调查策略或切换无限备用源。

证据：backend/app/assistant/roles.py；test_live_failure_replans_to_cached_tool_and_preserves_original_failure

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

# Phase9 QUERY_ROUTER

状态：PARTIAL

Fast/Deep、CVE、资产、有限产品名、语义话题和时间窗由受限规则识别。产品查询复用既有关系服务，不通过向量猜数据库事实。此版本不是开放域LLM理解器；未识别的问题保留局部覆盖/不确定性，不保证完整召回。

证据：backend/app/assistant/router.py；test_phase9_hardening.py

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。


## 本次续作更新

新增明确POC/exploit执行意图拒绝，中英文用例已测；合法POC证据查询仍可用。实际“执行这个POC看看”FAILED，0工具。规则路由仍有界，不宣称覆盖所有自然语言。

# Phase9 HANDOFF_PROTOCOL

状态：PASS / 内部边界

检查Task/Agent/Trace对应关系、依赖状态、带时区的时间、必要证据和可追溯来源结构。Artifact仅由服务端受信角色生成，不接受外部任意Artifact导入。字段形状验证不能单独证明来源真实；确认事实还需现有数据库核验与门禁。

证据：backend/app/assistant/handoff.py；gate.py；test_phase9_orchestration.py

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

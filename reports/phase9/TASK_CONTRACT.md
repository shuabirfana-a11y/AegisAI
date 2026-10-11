# Phase9 TASK_CONTRACT

状态：PASS

TaskContract包含goal/type/inputs/constraints/dependencies/allowed_tools/expected_output/evidence_required/acceptance_criteria/timeout/retry_policy/failure_policy；Artifact包含result/claims/evidence/unresolved/warnings/errors/trace/timing。身份、schema、依赖、次数与时限均受约束。

证据：backend/app/assistant/contracts.py；test_phase9_orchestration.py；test_phase9_hardening.py

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

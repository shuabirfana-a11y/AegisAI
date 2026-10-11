# Phase9 DEEP_PATH

状态：PARTIAL

主范围检索后最多展开3个候选漏洞；调查→核验→分析形成DAG，调查分支可并行，证据冲突阻止事实合并。实际复杂资产/产品问题使用11次工具，输出来源与Demo标记。候选覆盖是有界集合，不能宣称全量资产/全网情报完整性。

证据：real_agent_cases.json；backend/app/assistant/graph.py

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

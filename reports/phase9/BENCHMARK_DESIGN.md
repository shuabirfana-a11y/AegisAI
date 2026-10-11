# Phase9 BENCHMARK_DESIGN

状态：PARTIAL / 准备

AegisBench-v0.1有24个A–K候选题，问题与gold分离；人工复核gold当前0条。GroundTruth必须有人类annotator/审核状态/支持来源；代理或LLM草稿不能直接纳入正式指标。Runner与分类、FalseSafe、弃答、unsupported、Recall@K/MRR、延迟和错误明细基础设施可复用。RAG-only与无核验消融明确BLOCKED；尚未做Phase10正式实验，没有虚构准确率/F1或Agent优越性。

证据：evaluation/README.md；evaluation/datasets/；evaluation/ground_truth/；test_phase9_evaluation.py

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

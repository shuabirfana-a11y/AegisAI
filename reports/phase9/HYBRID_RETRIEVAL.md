# Phase9 HYBRID_RETRIEVAL

状态：PARTIAL

结构化数据查询、语义检索和关系查询已经实际组合。20份真实来源文档、98个片段、384维本地向量，原文/来源URL/raw SHA/抽取JSON路径/Unicode片段定位均保留。当前没有pgvector，使用最多1000片段的精确cosine，超限失败，未声明ANN性能。实时采集受服务端开关、来源限流及运行预算控制；没有Dify生成层。

证据：real_knowledge_index.json；backend/app/knowledge/；backend/app/tooling/adapters.py

验证范围：本机真实 PostgreSQL、已采集来源和显式 Demo 资产。角色执行器为确定性代码；本地 ONNX 仅负责语义向量。生成模型由用户选择稍后配置。Dify未运行，不计入真实LLM/Agent验收。

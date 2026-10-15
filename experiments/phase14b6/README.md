# Phase 14-B6 结果复现

实际49题 ONLINE_EVALUATION 已完成，运行代码 b8182eac1153e08bd9323b949f1b56af162360c8。数据/评分规则未改；缺上下文与范围不支持题全部保留。主报告是根目录 PHASE_14B6_RESULT.md。

机器记录在 evaluation/reports/phase14b6-human49-20261016：逐题字段链、各variant原预测（未实现Baseline仅记录状态）、原指标、冻结配置/来源哈希、历史6题分析与相同回答重处理。原敏感日志、服务完整启动证明和10MB原生HTTP采集留在本地work/phase14b6；实际复核包另以文件夹+zip交付，不上传密钥、私有提示或数据库。

从仓库根运行：

```text
python experiments/phase14b6/reproduce_metrics.py
```

入口校验记录哈希、49条批准数据和Risk原集合，使用既有score_variant重算完整AegisAI variant，断言全部指标与已保存结果一致。只读、离线，不请求HTTP或模型。Evidence Coverage/Hallucination保持null/PENDING_HUMAN。源配置和Prompt依旧B5当前配置；跨历史轮次不能作公平因果对照。

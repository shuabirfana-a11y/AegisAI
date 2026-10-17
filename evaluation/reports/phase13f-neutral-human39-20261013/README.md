# 首轮实验归档

入口：[Phase 13-F结果](../../../PHASE_13F_RESULT.md)。

- report.json / report.md：从冻结真实HTTP输出离线评分，不是Mock实验。
- experiment.json：评分回执及文件哈希；collection/：原始39题记录（含全部失败）。
- freeze/：运行前冻结的来源、模型、Prompt与中性库存。
- verification.json：原预测不变/类别兼容差异/工程测试记录。
- outcome-audit-pending.jsonl：未签署的2份实际输出复核表单。

既有CLI可在新目录离线复现（不用模型或服务，不覆盖本归档）：

~~~powershell
python evaluate.py --mode offline --manifest evaluation/datasets/AegisBench-v0.3-human39-20261013/manifest.json --rescore-report evaluation/reports/phase13f-neutral-human39-20261013/report.json --output work/phase13f-replay-new
~~~

复核表单真实完成后，用同一命令增加 --outcome-audit 表单文件路径。未经人工完整审计不得声明证据覆盖率或幻觉率。

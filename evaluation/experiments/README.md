# 实验登记与复现

每次 `python evaluate.py` 生成新 run_id，并拒绝覆盖已有非空结果目录。`experiment.json` 记录问题/标注/源 SHA-256、语料指纹、评测器及复用函数逐文件哈希、Git commit/dirty 状态、Python、UTC 时间、模型与 prompt 身份、参数、结果哈希。API 凭据与数据库地址不进入登记。

已保存一次真实 offline pilot：

- 数据：`AegisBench-v0.2-pilot`，49 问题，5 个公告 cluster，人工 gold=0。
- 模型：NONE，外部调用=0；RAG 与 AegisAI 没有模型结果。
- 路径：`../reports/phase13b-pilot-20261011/`，每例预测、运行状态、pending outcome audit、JSON/Markdown 报告与 receipt。
- 结论：框架和两个基线确实运行；没有正式准确率、证据支持率、幻觉率或相对提高结论。

复现到新目录：

```powershell
& backend/.venv/Scripts/python.exe evaluate.py --output evaluation/reports/my-repeat
```

逐例 answer/status、来源哈希和分类结果应相同；UUID、时间、Git 位置和延迟可以不同。标注数据变更要另建 dataset version，保留旧文件，不覆盖历史输出。

结果审核应针对已保存的输出，使用重新计分模式，**不再调用模型**：

```powershell
& backend/.venv/Scripts/python.exe evaluate.py --rescore-report evaluation/reports/my-live-run/report.json --outcome-audit evaluation/experiments/local/reviewed.jsonl --output evaluation/reports/my-reviewed-run
```

这会验证原实验 receipt/report SHA、问题与来源指纹，保持原预测和原延迟，记录 rescore_of。人审后的 gold 可以使用新的 `--manifest`，但问题与来源必须一致。OutcomeAudit 的 prediction_sha256 必须匹配实际输出，不能直接批准机器 pending 包或把旧模型输出的审核套到新回答上。

原生请求映射是敏感的本机准备材料，请放 ignored `evaluation/experiments/local/`，不提交真实账号/资产秘密。示例只写测试 question ID 与本机专用测试资源标识，不添加密码。此目录不提供伪造的“已实测四基线”参数或未经运行的结果。

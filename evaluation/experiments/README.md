# 实验登记与复现

每次 `python evaluate.py` 生成新 run_id，并拒绝覆盖已有非空结果目录。`experiment.json` 记录问题/标注/源 SHA-256、语料指纹、评测器及复用函数逐文件哈希、Git commit/dirty 状态、Python、UTC 时间、模型与 prompt 身份、参数、结果哈希。白名单记录有效生成超时、输出 Token 上限、结构化模式和 Token 参数名；显式 native 准备的请求映射仅记录 SHA-256 与未准入状态。API 凭据、actor、原映射和数据库/模型地址不进入登记。

已保存历史真实 offline pilot，保留原字节：

- 数据：`AegisBench-v0.2-pilot`，49 问题，5 个公告 cluster，人工 gold=0。
- 模型：NONE，外部调用=0；RAG 与 AegisAI 没有模型结果。
- 路径：`../reports/phase13b-pilot-20261011/`，每例预测、运行状态、pending outcome audit、JSON/Markdown 报告与 receipt。
- 结论：框架和两个基线确实运行；没有正式准确率、证据支持率、幻觉率或相对提高结论。

当前候选修订为 AegisBench-v0.2.1-pilot，仅纠正 cross-advisory-priorities 的部分弃答标签；问题和来源哈希保持不变，仍为 0 人审 gold。最终实跑及新版审核包见 `../reports/phase13b-final-20261011/`；历史包缺 claim_inventory_complete 时默认不完整，不能据此给整体 Evidence Coverage。

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

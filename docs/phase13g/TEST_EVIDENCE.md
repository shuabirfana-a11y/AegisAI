# 本轮真实验证

日期：2026-10-14（北京时间）。历史1261/1426等工程计数未作为本轮执行结果使用。

## 实际测试

命令：`python -m pytest tests/aegisbench -q`

真实输出末尾：

```text
........................................................................ [ 55%]
.........................................................                [100%]
129 passed in 26.60s
```

本地执行129项，0失败、0跳过；覆盖Dataset、Evaluation、Metrics、Runner、Report、HTTP Adapter、Need Context和隔离控制。没有为了无业务代码变更而再次运行全部后端测试。

## 在线实验

- 49题均有持久化记录；42题调用HTTP，37次真实Planner/Runtime调查，5题HTTP返回NEED_CONTEXT且没有模型调用，7题因多资产范围不支持而未进入HTTP。
- 37个Planner最终VALIDATED，共38次模型调用；1题在原Planner预算内重试一次，没有人工重答或重跑样本。
- 原模型调用记录汇总：input_tokens=241644、output_tokens=21806、total_tokens=263450。它们是Provider返回的usage，非费用或准确率。
- Gate真实结果：PASS_WITH_WARNINGS=6、REPLAN_REQUIRED=15、HUMAN_REVIEW_REQUIRED=16；12题未到Gate。
- 调用后只做原HTTP终态查询和数据库只读审计；没有直接调用Agent生成可评分结果。

## 冻结与隔离

- 634个受保护文件逐一复算SHA256一致，含业务源码、Schema、原评分器和Gold、旧实验文件。当前版本签核原件亦在保护列表。
- 12份运行时原始来源哈希不变；库存资产为随机中性名称，Planner输入不含评测题号/类别提示、expected_answer、reviewer或Ground Truth字段。
- 49条通过现有Loader准入；来源URL、哈希及JSON Pointer原文与原数据源一一校验。
- `PROTECTED_FILES_RESULT.json`记录changed=[]，`PROTECTED_HASHES.json`提供逐文件摘要。

## 原评分器离线复算

命令：`python experiments/phase13g/reproduce_metrics.py`

真实结果：

```json
{"offline_reproduction":"PASS","samples":49,"accuracy":0.0,"risk_accuracy":0.0,"evidence_coverage":null,"hallucination_rate":null,"new_model_calls":0}
```

复算前核对原报告、预测和原生HTTP记录回执哈希，所有metric字段与原保存值逐项相等。没有重新询问模型，没有改变计分标准。

Evidence Coverage与Hallucination仍等待独立人审37份输出、235个Claim；0条实际输出批准，不会把Gold的49条批准当成输出人审。

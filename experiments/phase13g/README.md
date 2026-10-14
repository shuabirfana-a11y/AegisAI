# Phase13-G：49题冻结在线基线

本轮按用户确认改为最新49条人工批准记录。执行一次在线采集，结束后停止；没有调整核心系统、人工答案或原指标。

冻结配置和全量结果在 `evaluation/reports/phase13g-human49-20261014/`。实验代码提交为 `ba92879c364411c8fa10642f3950c9f78370b468`，Provider是原本机Qwen2.5，Planner Prompt为v6。

## 输入与执行边界

1. 原Question/input_context与原问题哈希保持；签核原件只用于导出已声明计分字段和最后比较。
2. 新隔离数据库只复制旧原始来源图谱。原件中的人审证据、答案和题号不注入运行时检索数据库。27个受控库存按原输入创建，名称为随机中性名，没有类别/影响标签；不是企业扫描。
3. 原HTTP Adapter执行所有49个样本。42题实际调用HTTP，37次实际调查经过真实Planner；5题缺版本由原Context Check返回NEED_CONTEXT。7道多资产题在原Adapter被拒绝，没有改写或拆题。
4. 原Planner、Runtime、专业Agent、Gate及AnswerEnvelope执行原逻辑。235个输出Claim待独立人审；未从Gate状态推定语义支持。
5. 使用原 `evaluate_http` / `score_variant` 生成报告。所有49题仍在评分分母，原严格JSON匹配和拒答公式保持。

不能把技术适配SUCCEEDED当答案正确，不能把NEED_CONTEXT假装调用了模型，不能把7道未支持输入排除后宣称覆盖全部49题HTTP闭环。

## 离线复现（不会调用模型）

在这个Git仓库安装现有Python依赖后，运行：

```powershell
python experiments/phase13g/reproduce_metrics.py
```

检查结果回执哈希，按原冻结Gold、原Question、原来源和原预测重新计算全部metrics，并逐项断言等于保存值。输出仍为Strict Match=0/49、Risk=0/10；这不是自然语言语义准确率或生产安全效果。

独立人审完成后，使用现有入口另建输出目录进行离线评分，例如：

```powershell
python -m evaluation.bench.e2e --mode offline --manifest evaluation/datasets/AegisBench-v0.4-human49-20261014/manifest.json --rescore-report evaluation/reports/phase13g-human49-20261014/collection/report.json --outcome-audit <已完成人审的输出表单.jsonl> --output <新目录>
```

这只是说明后续入口，本阶段没有批准表单或执行二次实验。

## 重跑不是本阶段动作

在线重跑需要后续授权。应使用新隔离库存和新输出目录，保留原记录，沿用冻结问题和上下文。使用已有HTTP入口，不直接调Agent；把私有Token留在环境变量/本机私有目录中。

```powershell
python -m evaluation.bench.e2e --mode online --manifest evaluation/datasets/AegisBench-v0.4-human49-20261014/manifest.json --base-url http://127.0.0.1:<隔离端口> --bindings <私有库存绑定.json> --timeout 180 --output <新目录>
```

Qwen/Ollama完整制品未包含在交付包中，模型摘要已冻结；不同运行的时间、UUID、模型输出及样本相关性均保留，不能承诺重跑逐字节相同。RAG-only与No Verification公平对照仍NOT_IMPLEMENTED。

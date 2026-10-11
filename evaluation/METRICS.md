# AegisBench 指标规范 v0.2

计分使用 `bench/quality.py`，复用旧 `evaluation.metrics` 数学函数；输入由 Pydantic 严格验证。源、问题和答案分别冻结。机器草稿/TEST_FIXTURE 不准入正式成绩。工程测试通过数不代表情报准确率。

| 指标 | 分子 / 分母 | 前置条件与限制 |
|---|---|---|
| Accuracy | 所有期望字段均匹配的问题 / 所有准入问题 | 失败、缺预测和执行过的变体中的未执行案例均留在分母；全部不可用变体为 null |
| Field Accuracy | 匹配字段 / 有此标准字段的问题 | 规范 JSON 精确比较；缺字段为错。对 summary 是严格字段匹配，不能冒充语义回答正确率 |
| Precision / Recall / F1 | TP/(TP+FP)、TP/(TP+FN)、2TP/(2TP+FP+FN) | AFFECTED/NOT_AFFECTED/UNKNOWN 三类；非法预测记 NO_PREDICTION，统计非法数 |
| False Safe | 受影响却报安全 / 真实受影响样本 | 从分类矩阵计算；失败/弃答不算误报安全，但仍损失召回 |
| POC/Patch Classification | 匹配分类 / 对应准入问题 | 公告确认修复 release、仅被引用的 commit 候选、独立利用验证严格区分 |
| Risk / Priority Accuracy | 对应字段匹配 / 有该标准字段的问题 | 本批参考风险为显式分诊政策符合性，尚不是生产风险真实标签；不能跨不同政策强行比较 |
| Evidence Coverage | 人审确认 SUPPORTED 的 Claim / 所有实际输出 Claim | 所有输出 Claim 完成人审后才给整体比率；引用存在和哈希匹配只证明 provenance |
| Hallucination Rate | 人审确认 HALLUCINATED 的 Claim / 所有实际输出 Claim | 无完整审核为 null；CONTRADICTED、UNRESOLVED 分开，不把查不到事实当虚构 |
| Abstention Precision / Recall | 正确弃答 / 实际弃答；正确弃答 / 应弃答 | 字段未知可部分弃答；失败不是正确弃答。缺预测保留在 recall 分母 |
| Abstention Quality | 正确回答/弃答行为 / 所有准入问题 | 缺预测为错；同时给错误弃答、错误自信和缺预测数量 |
| Reasoning Completeness | 命中的必要流程步骤 / 必要步骤，按问题平均 | 当前测的是记录的流程步骤覆盖，**不证明推理正确或多跳语义正确**；RAG 不把模型自述步骤当 Trace |
| Observed Latency | 实际执行 wall-clock，含失败 | p50/p95 线性插值；不可用变体无延迟成绩；本地 Python 子毫秒处理不代表网络/模型速度 |

分母为 0 一律 JSON null；不得格式化为 0%/100%。分类缺失类别显示 support=0、recall=null，宏 F1 同时公布有定义类别数。逐类别与逐例输出保留，避免只报总体成功率。

人工结果审核逐回答覆盖全部 claim_id，明确证据源与定位。未审核的输出不能从分母移除后宣传全局 Evidence Coverage。仅公布 `reviewed_subset_*` 时须注明覆盖比例，整体指标保持 null。Claim 应按可独立核对的事实划分；人工需检查遗漏、过度合并和引用的直接性。

机器参考对照记录为 `MACHINE_REFERENCE_AGREEMENT_NOT_FORMAL_ACCURACY`。直接从同一公告抽字段并与抽出的参考答案比较，只检查管线，不证明产品质量。当前没有真实模型和 human gold，四基线公平效果比较为 NOT_COMPARABLE。

正式评测前：补齐人审 gold 与结果审核；按漏洞分组切分训练/开发/holdout；加入真实安全负例、冲突来源、弱来源、PoC 候选/已验证利用正例、不同语言/生态和多跳问题。预先登记样本、政策、模型、prompt、参数、失败规则，禁止看结果后挑题或改标签。至少按 advisory cluster 汇报，当前样本不适合给独立样本置信区间。

# 首轮采集后评分标签兼容问题（待确认，不实施）

39个批准题均已完成独立HTTP调用；原始checkpoint完整保存。评分时原score_variant遇到5条人审poc_status=NO_EVIDENCE，抛出Unrecognized gold class label。原POC_LABELS只有POC_CANDIDATE、VERIFIED_EXPLOIT、UNKNOWN，而人审规范及原件明确使用NO_EVIDENCE。

当前未改金标、指标、Gate或系统业务；未生成正式准确率。该遗漏来自运行前未检查评分器类别白名单，而不是人审原件被改动。

## 建议的最小修复（用户确认后才改）

只在evaluation/bench/quality.py的POC_LABELS增加原人审类别NO_EVIDENCE；不将它映射成UNKNOWN，不更改字段匹配、分母39、失败处理、风险/优先级或Gate。配套负向控制先复现当前异常，再验证原5条金标可加载评分、缺失答案仍不匹配，并实际回归。

```diff
-POC_LABELS = ["POC_CANDIDATE", "VERIFIED_EXPLOIT", "UNKNOWN"]
+POC_LABELS = ["POC_CANDIDATE", "VERIFIED_EXPLOIT", "UNKNOWN", "NO_EVIDENCE"]
```

评分类别覆盖从3类变4类，应作为独立评测器兼容版本记录，不能假装运行前就具备；不宣称指标提高。当前投影不产出NO_EVIDENCE，增加合法金标类别不会给缺失PoC字段或失败样本自动加分。

39份已保存输出只需离线重评分，无须重新调用调查API或模型。Evidence Coverage/Hallucination仍等待原复核人员对本次输出的独立审核。若不授权此变更，则交付完整采集及评分阻断报告，正式指标保持未计算。

## 授权与实际执行补记（2026-10-13）

以上为审批前原方案，保留历史。用户已明确回复‘允许补齐类别并离线评分’。已仅增加NO_EVIDENCE类别，先复现原错误、后运行108项评测测试通过；39题离线评分完成，无新模型/调查调用、无金标或公式/分母变动。结果及源码哈希见PHASE_13F_RESULT.md与归档verification.json。

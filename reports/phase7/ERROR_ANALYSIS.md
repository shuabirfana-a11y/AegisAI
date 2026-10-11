# 错误分类

ENTITY_ERROR：标识/产品关联错误；VERSION_ERROR：范围/修复版本错误；POC_FALSE_POSITIVE/POC_FALSE_NEGATIVE：候选误判/漏判；PATCH_FALSE_POSITIVE：补丁错误关联；SOURCE_CONFLICT：同 scope 明确矛盾；STALE_DATA：超出新鲜度；MISSING_EVIDENCE：缺少原始佐证；PARSER_ERROR：格式不支持/非法字段；UNKNOWN：未判定。

实际 GitHub 限流/外部连接错误为来源可用性问题，不能直接计为 PoC 假阴性。EPSS模型未报告属于缺失字段；无 KEV条目不等于未被利用。人工样本未完成，暂不公布分类错误率。回归用合成案例覆盖错误边界，单测通过不等于真实识别准确率。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

# EPSS

只使用 https://api.first.org/data/v1/epss?cve=目标CVE 。严格匹配 CVE、ISO 日期、有限数字与 [0,1] 概率范围。保存 score、percentile、score_date、observed_at、source、raw_document_id、model_version 的不可变 Snapshot；多日期保留历史，不覆盖。

API `version=1.0` 不代表模型版本。响应未报告模型时记录 `unknown_api_not_reported`，并输出 warning。无该 CVE 是 NO_RESULT，不写零概率。EPSS_CHANGED 表示首次观察到日期快照，可据历史比较，不声称每个新日期的分数都不同。EPSS 是概率评估，不能证明已被利用。

来源文档：https://api.first.org/epss/ 。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

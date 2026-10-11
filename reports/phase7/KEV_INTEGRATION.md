# KEV 整合

复用 Phase6 的 CISA_KEV 完整目录 RawDocument，核对 count 和唯一 CVE 后精确查找，不重复 Collector，也不改动 Phase6 的采集 pending/checkpoint。目标条目复用原始完整目录产生关联 Observation 和 Evidence。

命中写 KNOWN_EXPLOITED=true 与 KnownExploitation 的 date_added、required_action、due_date、catalog_version；可触发 KEV_ADDED。目录未列出写 not_listed_as_of 和 unknown/null，绝不 known_exploited=false。检查时间、目录发布时间及取回时间分开返回。无完整目录为失败，不能以残缺目录证明未收录。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

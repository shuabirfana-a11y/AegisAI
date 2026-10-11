# PoC 发现

PocDiscoveryService 使用 GitHub 官方 Repository Search API，以精确 CVE 及 in:name,description,readme 查询，返回上限5；README 静态检查上限3。保留完整搜索响应、时间、total_count、incomplete_results、检查范围与候选。

候选保留 repository、owner、description、上游创建/更新时间、first_seen/last_seen、原文与 README 引用。空的完整搜索为 NO_RESULT；不完整搜索、未全部检查与 README 获取失败为 PARTIAL。没有永久 has_poc=false。后续调查允许新候选与真实事件进入。

不 clone、不安装、不运行、不访问攻击目标。来源：https://docs.github.com/en/rest/search/search 。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

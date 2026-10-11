# 版本富化

只消费当前 Phase6 来源修订与厂商结构化字段。PyPI 使用 PEP440，保留 raw_expression/events/parse_status，固定版本仅从 explicit fixed event 或 Vendor patched_versions 提取。不会把 affected upper bound 推算成 fixed release。

同一包同一来源的分段范围形成 union，合并相邻/重叠区间后比较语义集合，包含开闭端点、精确版本、预发行版规则。不同生态/分支/范围 scope 不混用；unsupported 保留且弃判，不伪造冲突。CVE 中未映射为现有 PyPI package 的通用版本仍通过旧 affected_versions 暴露，未硬凑成支持的 Claim。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

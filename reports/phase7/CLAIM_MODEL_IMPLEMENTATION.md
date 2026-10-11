# Claim 实现

复用 intel.claims。明确类型枚举含 AFFECTS_PRODUCT、AFFECTS_VERSION、FIXED_VERSION、POC_EXISTS、POC_ASSOCIATION、PATCH_EXISTS、FIX_COMMIT、KNOWN_EXPLOITED、VENDOR_CONFIRMED、EXPLOIT_CONDITION、REMEDIATION、CVSS_SCORE；不把所有数据塞入 claim_text。

确定性 claim_key 由 target/type/scope/语义值组成；相同来源重复执行不会新增同语义 Claim。Subject 关联现有 package/PoC/Patch。verification_status 与 adopted 分开。不是所有枚举都会在三个真实案例出现，EXPLOIT_CONDITION/REMEDIATION/CVSS 未做自然语言自动抽取，原始描述/评分保持来源字段可查。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

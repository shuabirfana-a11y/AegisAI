# 冲突检测

ConflictDetectionService 对当前且新鲜的同 scope Claim 作确定性比较：Affected Version、Fixed Version、Severity、PoC/Patch 状态、Known Exploitation、Vendor/third-party。固定版本落在受影响范围内产生 VERSION_CONFLICT；语义等价区间不冲突，CVSS 不同版本及生态/分支 scope 共存。

新增 intel.conflicts，保存 target、两 Claim、scope、类型、检测时间、状态、review 和 resolution/actor/time。自动生成 ReviewTask 和双方 CONTRADICT Evidence，历史不覆盖。相同已解决冲突不会每次调查重新创建任务。真实库不人为制造冲突；冲突闭环在明确标注 TEST SCENARIO 的真库 fixture 中验证。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

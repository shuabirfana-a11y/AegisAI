# Patch / Fix Commit / Release

PatchDiscoveryService 从官方公告明确引用和现有来源 reference 发现，严格限定注册官方仓库，区分 commit、pull_request、release。Commit 必须完整40/64位十六进制 SHA；查询官方 metadata 必须返回同一 SHA、PR number 或 release tag。

官方公告直接关联并成功检查 metadata 才形成强 Patch Evidence；仅模糊 security 文本或第三方引用不直接 Confirmed。固定版本来自明确上游字段，不通过代码猜测。保留 patch 关联理由、source observation、raw locator 和候选状态。网络失败不能证明不存在补丁。没有执行补丁或 PoC。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

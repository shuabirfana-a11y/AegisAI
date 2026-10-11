# 实际测试

最新完整回归 218 passed / 0 failed / 0 skipped，exit_status=0，时间 2026-10-03T11:30:41.432522+00:00。真实 PostgreSQL；原Phase5/6测试与新增Phase7测试均执行。网络 MockTransport 只用于可重复来源测试，真实案例另有记录。

迁移实际 upgrade→downgrade→upgrade 到 0002，45 表、22 历史保护，ORM drift空。三组案例的回环 HTTP 检查 27 次全部成功；耗时及完整路径见 api_validation.json。

红绿证据保存在 work/phase7_task*_red.log 与后续完整日志，包含候选拒绝/无结果/限流、Patch明确引用、版本逻辑、证据来源、同源相关性、冲突复核、人工决定保护、API与排程。一个已知 Starlette/AnyIO BlockingPortal 弃用警告保留，未计测试失败。不是最终Benchmark。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

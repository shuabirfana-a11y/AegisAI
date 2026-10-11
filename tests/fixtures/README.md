# 离线公开源响应

每个CVE有cve.json、osv.json，两份literal HTTP响应字节；源URL、时间、sha256和别名核对见evaluation/seed_set。均为真实数据，禁止执行原文中的脚本/PoC。测试不必联网；源返回错误另用HTTP MockTransport模拟。

# Phase 14-B3 验证记录

日期：2026-10-14。所有测试为工程验证，不是安全任务准确率。

| 检查 | 实际命令 | 结果 |
| --- | --- | --- |
| 新增知识关联 SQL/HTTP 和既有调查联动 | `python -m pytest -q backend/tests/test_phase14b3_graph.py backend/tests/orchestration/test_knowledge_graph.py` | 30 passed |
| 相关 PostgreSQL 回归 | `python -m pytest -q backend/tests/test_phase14_api.py backend/tests/test_phase14b1_poc.py backend/tests/test_phase14b2_pipeline.py backend/tests/test_phase9_tools_knowledge.py backend/tests/test_phase14b3_graph.py backend/tests/orchestration/test_knowledge_graph.py` | 120 passed；包含上述 30 项，不能重复累加 |
| 便携后端 CI 套件 | `python scripts/ci/run_backend_tests.py` | 675 passed，1 deselected；排除既有真实缓存 embedding 测试 |
| 前端 | `node --test frontend/tests/*.test.mjs` | 68 passed，0 failed，0 skipped；原 67 + 新增代理认证测试 1 |
| JS 语法 | `node scripts/ci/check_frontend.mjs` | 24 文件通过；原生 JS 无应用 build 脚本，NOT_APPLICABLE |
| TS 契约 | `node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json` | 通过 |
| 情报导出 | `python scripts/export_intelligence_api.py --check` | 8 文件、10 HTTP 操作一致 |
| 调查导出 | `python scripts/export_investigation_api.py --check` | 10 文件一致 |
| 总契约 | `python scripts/ci/check_contracts.py` | 52 HTTP 操作、40 合成对象验证通过 |
| 工程门禁 | `python -m unittest discover -s tests/engineering -q` | 18 通过 |

PostgreSQL 测试只用本阶段自建的临时合成集群和 aegis_phase5_test，按测试依赖顺序执行，未使用开发/演示数据库做破坏性测试。部分既有编排 fixture 提交持久化合成行，会影响全库计数断言；一次探索性混合运行出现 2 失败、108 通过，定位后仅重置自有临时测试库并按独立目录顺序运行，最终上述 120 项通过，没有削弱断言。

TDD：最初知识图不存在时 16 项失败；独立审查指出的三类关系/预算问题先用回归重现；最后证据交集用例先 2 失败、1 正向通过，修复后全部通过。审查修正包括：范围不能借用修复 Claim；Risk 不能借用无关 verified_claim；证据和嵌套值预算；同一组完整性/当前性/新鲜度/值匹配/核验引用证据交集。

独立只读复查结论：原四项及残余 P2 均关闭，未发现剩余 P1/P2。审查者未访问数据库、凭据、服务或修改文件。

只读演示接口实际输出 19 节点、23 边，Gate PASS，三个专业 Agent Artifact 引用；SQL 只读事务中无记录变化、无新模型调用。演示响应与回执见 demo/。

这些是相关回归与便携基线；没有声称整个后端数据库集成套件全绿。历史其他数据库测试问题不属于本次改动。Starlette/AnyIO 的既有弃用警告不影响结果，未修改依赖。

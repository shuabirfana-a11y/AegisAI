# 本次真实验证记录

历史1261/1426项结果不代替本次执行。自动测试均为工程验证，不输出准确率。

| 验证 | 实际结果 | 解释 |
| --- | --- | --- |
| 首次全后端，未分离测试库 | 1496通过，41失败 | Runtime持久化夹具污染事务隔离库、工作目录/环境和旧断言；原日志保留 |
| 分离库并使用backend工作目录，全后端 | 1546通过，3失败 | 一项新来源配置回归；另两项既有缺失上下文断言 |
| 修复来源配置后相关测试 | 70通过 | 包括本阶段48项、既有来源格式21项和历史兼容守卫1项 |
| 基线8294f55只读代码复现 | 3通过，2失败 | 厂商三种repo用例原来通过；unknown_version/ambiguous两项在基线同样失败 |
| 前端测试 | 23通过，0失败 | 原页面逻辑没有重构 |
| 工程维护测试 | 18通过 | 现有部署/安全门禁的合成工程测试 |
| TypeScript契约检查 | 退出码0 | 原契约加新监测客户端，无新增UI |
| JavaScript语法 | 17文件通过 | 当前原生JS前端没有build脚本，不虚构build结果 |
| OpenAPI/Pydantic契约一致性 | 47操作，5组Schema，40个合成对象通过 | 原八调查API不变，新增五监测API |
| 受保护文件 | 652个，0变更 | Agent/Planner/Runtime/Gate/LLM、迁移、Benchmark/金标/历史实验 |

最终便携CI基线的数量与唯一排除项由 `verification-summary.json` 保存。排除的是需要缓存实际Embedding的旧测试；本次真实论文入库另实际使用了已有MiniLM缓存模型，不能把排除项报成已执行。

## 执行命令

两套测试库预先设置为独立的专用 `aegis_phase5_test`：事务库与已提交Runtime夹具库分别配置 `AEGIS_TEST_DATABASE_URL` / `AEGIS_RUNTIME_TEST_DATABASE_URL`。迁移核验时 `AEGIS_DATABASE_URL` 仅指向事务测试库，不指向开发或评测数据。

```text
cd backend
python -m pytest tests -q
python -m pytest tests/test_phase14_sources.py tests/test_phase14_storage.py tests/test_phase14_api.py tests/test_phase14_cli.py tests/agents/verification/test_source_formats.py tests/orchestration/test_legacy_compat.py::test_old_api_and_business_source_hashes_are_unchanged -q
cd ..
python scripts/ci/run_backend_tests.py
python scripts/ci/check_contracts.py
python scripts/export_investigation_api.py --check
python scripts/export_intelligence_api.py --check
python -m unittest discover -s tests/engineering -v
node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json
node scripts/ci/check_frontend.mjs
cd frontend
node --test tests/*.test.mjs
```

## 两项保留的旧失败

- `tests/investigation_api/test_bench_http.py::test_evaluation_adapter_reaches_full_original_http_chain[unknown_version]`：预期SUCCEEDED，实际缺失上下文返回NOT_EVALUATED。
- `tests/orchestration/test_failure_cancel.py::test_essential_partial_blocked_or_ambiguous_stops_downstream[ambiguous]`：旧断言预期REPLAN_REQUIRED，实际在上下文准入阶段停止，尚无Integration状态。

两项在Phase14-A之前的只读代码上均可复现。未修改Benchmark、上下文业务或保护测试迎合它们。完整后端套件不能声称全绿；本阶段相关验收与便携CI另列，不合并重复测试数量。

原始执行日志在本机私有 `work/phase14a/`，不会提交包含机器路径/运行配置的完整日志。Starlette/AnyIO弃用警告及旧合成Enum序列化警告仍可见，未屏蔽。

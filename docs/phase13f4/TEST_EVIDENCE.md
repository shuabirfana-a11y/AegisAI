# 实际验证与复审

本阶段遵守用户要求，未重新执行全量本地测试或正式评分。

TDD 控制：首次 13 个缺失上下文控制失败；空白 UNKNOWN/overview 语义、来源证明、Scope 一致性、幂等冲突均先保存失败控制，再补齐新检查层。没有通过调整断言、业务 Validator 或评分获得通过。

实际命令：

```text
python -m pytest -q backend/tests/investigation_api/test_missing_context.py tests/aegisbench/test_need_context.py backend/tests/investigation_api/test_contract.py backend/tests/investigation_api/test_service.py backend/tests/agents/investigation/test_normalization.py backend/tests/agents/investigation/test_task_templates.py tests/aegisbench/test_http_investigation.py tests/aegisbench/test_http_integrity.py
python scripts/export_investigation_api.py --check
python scripts/export_bench_http_schema.py --check
python scripts/ci/check_contracts.py
node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json
```

结果：103 passed，1 个既有 AnyIO 弃用 warning；其中新增后端 29 个、评测适配器 1 个控制。HTTP 10 个导出文件、评测 11 个 Schema 组与代码一致；42 个 HTTP 操作保持原数量，TypeScript 检查退出码 0。契约导出没有连接数据库或模型。

独立只读复审验证 30 个新控制通过，已处理 profile 绕过、公告/null 版本误归因、冻结 Scope 不一致、并发幂等键冲突、必填 TypeScript 判别字段、空白组件及纯风险意图。复审没有编辑文件或调用真实模型/API/数据库，结论为可进行本阶段限定验证。

真实五题诊断单独冻结/保存，不用这些 Mock/合成控制声明准确率。历史 1426/1261 等工程测试数量不作为本次实跑结果。

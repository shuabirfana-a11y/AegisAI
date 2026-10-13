# Phase 13-F.3 自动回归凭据

以下是本阶段在冻结实现前实际执行的结果，不是历史 1426 项验收，也不是 Benchmark 准确率。

| 命令 | 实际结果 |
|---|---|
| `python -m pytest -q tests/agents/investigation/test_task_templates.py -k fact_template`（backend 中，修复前） | 1 failed, 5 deselected：事实题不应请求缺失部署版本，但模型侧 Schema 当时允许 |
| `python -m pytest -q tests/agents/investigation/test_task_templates.py tests/agents/investigation/test_normalization.py tests/agents/investigation/test_scope_schema.py tests/agents/investigation/test_model_schema.py tests/agents/investigation/test_planning.py`（backend 中，修复后） | 67 passed |
| `python scripts/ci/run_backend_tests.py` | 583 passed, 1 deselected, 1 warning；排除既有缓存真实 Embedding 测试，警告为 AnyIO 弃用提示 |
| `python -m pytest -q tests/aegisbench` | 128 passed |
| `python scripts/ci/check_contracts.py` | PASS：42 HTTP operations、5 Schema groups、40 个合成契约对象；无数据库连接、无导出修改 |
| `python scripts/export_investigation_api.py --check` | PASS：10 个导出文件与代码一致 |

新增自动用例：归一化 28 项、任务模板/模型 Schema 6 项、Evaluation Request Builder 2 项。67 项针对性回归与 583 项 portable 有重叠，不相加为独立用例总数。

测试用 Mock Gateway 检查调用契约；5 题真实 HTTP 诊断另行冻结记录。没有为了通过测试安装新依赖、改变模型或放宽运行时 Validation。

独立复审指出公告范围/修复版本可能误作部署版本、句末标点解析、跨句范围影响下一句、Backend 描述越过冻结 Scope；这些边界已修复并通过限定复核。最后的最小 Schema 补充限制 input_required 只请求冻结 Scope 需要的字段，原 Validator 未修改。

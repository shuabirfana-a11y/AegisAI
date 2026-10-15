# 数据库回归的正确入口

Runtime / Agent / 调查 HTTP 测试为跨连接、子进程读取而真实提交合成数据；早期采集、富化和 ORM 测试用外层事务回滚，并假设测试库没有其他题的数据。两类 fixture 共用同一库，会污染全量回归。不能通过删除断言、清理生产数据或把业务调用改成成功 Mock 解决。

## 前提

准备两个独立、空的本地 PostgreSQL 17 实例，均只创建 `aegis_phase5_test`。实例端口必须不同；用户名、密码、localhost 别名不同不构成隔离。迁移使用已有 0001–0004；当前向量存储为 FLOAT[]，本测试入口不额外安装图数据库或 pgvector。

Windows PowerShell，在项目根目录，按自己 provision 的测试端口配置：

```powershell
$env:AEGIS_TEST_DATABASE_URL='postgresql+psycopg://aegis_test@127.0.0.1:55447/aegis_phase5_test'
$env:AEGIS_RUNTIME_TEST_DATABASE_URL='postgresql+psycopg://aegis_test@127.0.0.1:55448/aegis_phase5_test'
python scripts/ci/run_database_tests.py --full
```

使用安装 `backend/requirements.txt` 的明确解释器；本机还需既有 embedding 缓存才能跑全量中的真实 embedding 测试。该缓存不使用标准答案。新机器缺缓存必须报告未完成，不能把全量改成便携结果。

脚本仅执行迁移并读检查初始空库，不创建、删除数据库或清除已有行。两个实例同库、缺配置、外部主机、非专用库、有残留数据均拒绝。重复运行前由开发者只重新 provision 自己的可丢弃测试实例，保留前一次日志；不要指向开发库或比赛演示库。脚本为迁移测试显式设置 AEGIS_DATABASE_URL，不依赖开发默认连接。

## 范围与结果

- `--full`：执行整个 `backend/tests`，不使用 -k、skip 或新增 deselection。
- 默认模式：执行脚本 `CRITICAL_TESTS` 清单的数据库/HTTP关键回归，用于 CI；不是全量。覆盖引起本次51项失败的各模块，以及前一题真实提交、后一题回滚检查的组合。
- 数据库记录使用受控外部传输和 Mock 模型；真实模型 HTTP 验证独立记录，不计作 Benchmark。
- 输出目录默认 `work/database-regression`，包含 entry.json 和 results.xml。保存原始标准输出和实际退出码；pytest 的 collection/setup/call/teardown 错误不会被吞掉。

CI 四项名称分别说明范围。PostgreSQL job 用两个仅绑定 loopback 的临时服务，不使用真实 API Key。便携 job 仍显式排除一项真实缓存 embedding 测试；不得把排除算作通过。

## 两项历史契约断言

Phase13-F.4 已批准：缺部署版本在 API preflight 返回 NEED_CONTEXT / NOT_STARTED，不创建 Planner/调查/Gate。测试保留“不猜版本、不声称安全、无模型调用”的负向检查。

Phase13-F.3 已批准：同目标重复 get_vulnerability 根查询被模型面对的 scoped Schema 拒绝。测试检查 PLANNING_FAILED、无 Runtime/Agent/Gate、无确定结论；旧的 Artifact 歧义选择检查 `test_ambiguous_lookup_does_not_select_first` 仍保留，继续拒绝读取第一个结果。

# 后端联调与本地演示检查

本说明对应已合入 main 的 Phase 12-B，以及后续本地启动修复。联调时分别检查 HTTP 可用、受控闭环可执行、真实模型可规划，不能用其中一项代替另外两项。

## 三种数据与执行模式

| 模式 | 可以验证或展示 | 限制 |
|---|---|---|
| 本地数据库 + 旧确定性 Assistant | 漏洞查询、现有证据、工具 Trace、保留冲突/未知的结果 | 不经过 Phase 10-B LLM Planner，不是新的 AnswerEnvelope 调查链 |
| 专用测试库 + 显式 PlannerPlan 合成回执 | 真实 HTTP 适配层、Planner 验证、三 Agent、Gate、冻结答案、取消 | 资料和模型回执均为 SYNTHETIC_TEST，只证明工程闭环，不能作为安全标准答案 |
| 本地数据库 + 配置的规划模型 | 新调查真实业务联调 | 本机尚未配置；供应商能返回 JSON 仍须通过任务/权限/DAG 验证，不保证成功 |

默认 `MODEL_PROVIDER=mock` 的健康状态是 healthy，但默认 Mock **没有 PlannerPlan 回执**，不是能回答任意问题的离线模型。新调查受理后会停在 PLANNING_FAILED，未发生的三个 Agent、Gate 和 Artifact 保持缺失；失败 AnswerEnvelope 是可读取的诊断交付，不能显示为成功答案。本轮保留了该失败记录，没有添加猜测计划或补造证据。

## 本机启动

以下命令在本项目根目录运行，要求已有 `backend/.venv`、Node 和 `work/postgresql_runtime.json` 指向的本机 PostgreSQL/pgvector 缓存。新队友电脑按 [开发指南](DEVELOPMENT_GUIDE.md) 自备环境，不能直接复制数据库目录。

```powershell
# 明确免费离线协议测试配置；不调用外部模型。
$env:MODEL_PROVIDER='mock'
$env:MODEL_EMBEDDING_PROVIDER='mock'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
& './scripts/start-local-demo.ps1'
```

脚本只启动本项目开发库 55436、API 8000 和代理 8769，执行已有 Alembic 迁移，并将临时鉴权凭据留在服务进程内。迁移不是数据清空。启动前端口被占用会报错，不启动第二套服务。

- 页面：`http://127.0.0.1:8769/dashboard`。
- API 文档：`http://127.0.0.1:8000/docs`；受保护调用需要服务端配置的凭据。浏览器页面通过同源代理访问，临时凭据不显示在页面或文档。
- `http://127.0.0.1:8000/health`：仅数据库/应用连通性。
- `http://127.0.0.1:8769/client-config`：仅本地代理模式；不含 token。

启动脚本明确提示 Mock 规划限制；显示“HTTP services are ready”不等于新调查成功。

## 重启后的数据库恢复

旧脚本只看 `postmaster.pid` 是否存在。机器重启后文件可能还在而服务已退出，于是跳过启动并等待连接。本轮改为使用 `pg_ctl status` 的实际退出码：0 为运行，3 为停止，其他状态报错；原生 PostgreSQL 负责处理失效标记，脚本不手动删除 PID 文件。

状态探测限时 10 秒；启动等待参数 30 秒、子进程限时 40 秒；数据库连接限时 5 秒。保留已有 PG_VERSION、数据库目录、库名和端口。停止已退出的开发库是安全空操作。退出码定义见 [PostgreSQL pg_ctl 官方说明](https://www.postgresql.org/docs/17/app-pg-ctl.html)。

## 前端联调步骤

1. 从接口导出包复用 `investigation-client.ts` 和 DTO；完整字段、枚举、幂等与取消语义见 [调查 API 契约](PHASE12B_INVESTIGATION_API.md)。
2. POST `/api/investigations` 使用同源 JSON 请求和唯一幂等键；202 代表受理。相同键/内容重复提交返回同一根调查；内容变化返回 409 IDEMPOTENCY_CONFLICT。
3. 约每秒读取 status。仅在 revision 变化时刷新 trace/artifacts；可空的 Artifact 要显示“尚未产生”，不能填 Mock 到真实结果区域。
4. RUNNING 时收到 RESULT_NOT_READY，遵守 Retry-After。终态没有 Gate 时收到 RESULT_UNAVAILABLE，停止无意义重试。FAILED/CANCELLED/REVIEW_REQUIRED 不呈现为成功。
5. Answer GET 读取已保存的 AnswerEnvelope，不生成第二份答案。取消是协作式请求；完成后的取消不能倒转终态。
6. 记录请求路径、HTTP 状态、业务状态、request_id 和调查 ID；不要提交 token、原始数据库 URL 或日志里的敏感内容。

现有 `/assistant` 页面仍接旧 `/api/v1/assistant/query`。该接口返回 run_id 和旧结果结构，不能转称为新的 Investigation API 或 AnswerEnvelope。实际新工作台由前端队友继续实现。

## 受控离线闭环验收

只在专用 `aegis_phase5_test` 测试库运行。测试插入合成资料并真实执行各服务，不能把测试 URL 指向保存真实采集数据的 `aegis_phase6`。

当前开发者机器已经准备好 55435 测试库，可在根目录执行：

```powershell
$env:AEGIS_TEST_DATABASE_URL='postgresql+psycopg://aegis_test@127.0.0.1:55435/aegis_phase5_test'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
Push-Location './backend'
try {
    & './.venv/Scripts/python.exe' -m pytest tests/investigation_api/test_live_chain.py -q
} finally { Pop-Location }
```

在其他机器上换成自己已迁移至 head 的同名专用测试库和解释器。两项测试分别验证：完整链输出三份 Artifact、Gate PASS、冻结答案重读不调用模型、跨调查引用拒绝；规划中取消、并发重复键复用及容量限制。它们采用现有显式注入 ModelGateway 的接口，不改默认模型行为，也不向开发库加入合成资料。

## 演示前与结束后

演示前确认页面、health、数据更新时间、正确的模型标签和现有失败记录。默认 Mock 环境先演示真实数据库查询与旧确定性 Assistant；受控完整链展示必须持续标记“合成工程测试”。真实新调查成功演示需要先配置并实跑规划模型。

服务停止使用现有 `scripts/stop-local-demo.ps1`，它依据本机记录停止两个应用进程，开发数据库继续运行。需要停止开发数据库时单独运行：

```powershell
& './backend/.venv/Scripts/python.exe' backend/scripts/local_database.py stop
```

不手动删除 work 下数据库目录，不关闭其他项目的进程或 55435 测试库。强制终止进程时，在途调查可能留下 recovery_required；当前没有持久工作队列或自动续跑功能。

## 本轮实际结果与待办

本轮实测：本地开发库恢复约 5 秒，迁移 0004；漏洞列表返回 278 条已存在记录。新调查 API 经实际 8769 代理验证了鉴权、幂等、状态、Trace、Artifact、历史和终态取消；默认 Mock 规划失败，Gate 未产生。旧确定性 Assistant 在同一数据库上完成一次查询，Gate 为 PASS_WITH_WARNINGS，记录了 5 次工具调用。

受控专用库闭环 2 项通过；portable 后端 423 项通过、真实缓存 embedding 1 项显式排除。完整验收及新的 GitHub 状态见 [本轮结果](BACKEND_INTEGRATION_STABILITY_RESULT.md)。这些数量不代表安全准确率；人工批准标准答案仍为 0。

下一步是配置规划模型并验证真实数据闭环、队友完成工作台联调，以及人工标准答案复核。公网部署、产品 Replay 模式和正式 Benchmark 属于后续阶段。

# 前端监测进度契约

新增接口共两个，均只读；原八个调查接口和 PoC 接口保持兼容。

| 接口 | 响应 | 页面用途 |
|---|---|---|
| GET /api/v1/intelligence/records | RecordPage | 最新漏洞、博客、论文与富化进度 |
| GET /api/v1/intelligence/monitoring/runs | PipelineRunPage | 来源运行、失败和积压状态 |

`records` 的 type 可为 vulnerability/blog/paper，q 为标题/规范编号筛选；两个接口 offset≥0，limit 为1..100。
`monitoring/runs` 的 source 使用注册 Source key；响应 total 是分页前总量。

TypeScript 使用 frontend/contracts/monitoring.ts 及 intelligence.ts 的 records/monitoringRuns 方法。
交接包镜像位于 AegisAI_FRONTEND_HANDOFF_PACKAGE/contracts/，响应类型由真实 Pydantic/OpenAPI 导出。

## 页面显示

- status 展示情报生命周期；verification_status 另外展示核验结论，不互相覆盖。
- execution_mode 为 LIVE/MOCK/UNSPECIFIED。已有未标识或混合历史显示 UNSPECIFIED，不能加“实时”标。
- enrichment_progress 按真实 job 的 queued/running/success/partial/no_result/failed/conflict/cancelled 展示。
- observed_at 来自保存的来源观测或实体创建时间，刷新页面不改变时间。
- pending_jobs 表示未完成任务；processed_jobs 与 failed_jobs 是该捕获批次累计根任务进度。
- collection_status 是原采集状态，不能把 NOT_DUE 或后续续跑解释成来源失败已修复。
- errors 是受控错误类型，warnings 解释可查但未确认、失败和混合模式等限制。

建议页面可见时每 15–30 秒轮询这两个 GET，离开页面后停止，失败保留上一份数据并显示错误。
不把 AVAILABLE、HTTP 200 或进度100%直接映射成 CONFIRMED/VERIFIED_EXPLOIT。
没有配置后台 worker 时，接口只显示历史；刷新页面不会启动流水线。

未修改队友工作台、页面布局和调查状态。全量 HTTP 契约现有50项操作，情报相关8项；
旧接口响应类型尚缺失的限制没有在本阶段补造。

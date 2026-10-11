# 尚未开放的产品能力与历史建议

Phase 12-B 已实现 `/api/investigations` 的 8 个操作，详见 [实际调查 API](INVESTIGATION_API.md)。下表是被取代的历史 `/api/v1/investigations` 建议，不能作为实际调用 URL；公开 DTO 已在 `reference/investigation-http.d.ts` 冻结。旧内部请求仍接受，但内部输出不是公共响应。

历史 Phase12-A.5/早期12-B 计划采用的路径如下，仅保留用于辨认旧材料；新增 `/api/investigations` 已完成提交、状态、Trace、Artifact、Gate、Answer、取消、历史及代理/鉴权/错误适配。

| 能力 | 建议方法与路径（未实现） | 最小适配及输出约束 |
|---|---|---|
| 提交智能调查 | POST `/api/v1/investigations` | 校验 InvestigationRequest 与鉴权；委托已有 Orchestrator，实际根领取提交成功后才能返回 202/root ID；确认 DTO 待冻结 |
| 历史调查列表 | GET `/api/v1/investigations/history` | 当前 principal 隔离、分页、必要筛选；列表 DTO 待冻结，不暴露内部 Context |
| 当前进度 | GET `/api/v1/investigations/{id}/status` | 公开 InvestigationStatus，阶段/总体状态/revision/取消请求/恢复待确认 |
| 调查过程 | GET `/api/v1/investigations/{id}/trace` | InvestigationTrace，受控事件和摘要，禁止私有 Prompt/控制字段 |
| 专业 Artifact | GET `/api/v1/investigations/{id}/artifacts` | 调查、核验、风险 Artifact 或引用；未产出阶段与失败阶段要明确，聚合 DTO 待冻结 |
| Gate 结果 | GET `/api/v1/investigations/{id}/integration` | 已保存的 IntegrationResult；根 ID 与 Gate ID 空间不能混用 |
| 最终答案 | GET `/api/v1/investigations/{id}/answer` | 已保存 AnswerEnvelope，运行中不能造完整答案 |
| 取消调查 | POST `/api/v1/investigations/{id}/cancel` | 持久化 cancel_requested；不承诺立刻杀死调用或立即成为 CANCELLED |

完整请求和内部结果模型已有 TypeScript 映射，但公开提交确认、历史列表、Artifact 聚合、统一错误等 HTTP DTO 仍应在实施时明确。当前不能凭空生成或假定 `{job_id,status:'queued'}` 已存在。

## 最小实现原则

Router 与适配服务复用既有 Planner、DAG、专业 Agent、Gate 和 AnswerComposer；不重写业务。后台任务执行与根领取应复用已有幂等控制。不得先在 API 层制造假的根 ID 或重复领取同一任务。

保留 actor 归属、相同 key/语义请求去重、修订控制、调用预算、取消和恢复语义。`202` 必须表示实际根创建/领取已确认，不能只表示线程启动。提交结果不明时保留相同 request_key 恢复，不重新生成 key 以制造重复任务。

同步内部调查预算可达 300 秒，而现有代理上游超时 30 秒，所以需要提交与查询生命周期适配，不能把完整同步调用直接塞进页面长请求。本计划不是本包实现内容。

## 历史联调检查单（接口适配已完成，UI 由前端团队接入）

- 放行新路由的方法和必要请求头，明确同源、Host、CSP/CORS 与真实部署方式。
- 对每次状态/历史/Artifact 读取检查 principal，不根据客户端 Body 的 owner 认定权限。
- 冻结公开 HTTP 错误映射；内部 PLANNING_FAILED 等不能直接当作已实现的 HTTP 响应格式。
- 定义运行中答案/Gate 未就绪、提交确认不明、线程容量满、重启后恢复待确认的返回与 UI。
- 增加请求/响应模型并重新导出 OpenAPI、类型和浏览器实测回执。

## 额外产品缺口

全局新增/趋势统计、CPU/内存/模型用量遥测、SSE/WebSocket、完整账户登录与多租户、自动任务恢复等没有在当前公开 API 中。单独记录需求，不在 UI 里暗示已实现。现有复核/资产写入是代理受限而非新业务缺口，分别处理。

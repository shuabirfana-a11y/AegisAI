> 当前更新：Phase 12-B 已提供 `/api/investigations` 的 8 个 HTTP 操作。以下 `/api/v1/investigations` 是 Phase 12-A.5 历史提案，仍不可调用；当前实现见 `investigation-http.openapi.json` 和仓库 `docs/PHASE12B_INVESTIGATION_API.md`。

# Phase 11-D API 缺口（仅建议，未实施）

所有条目状态均为 **API_NOT_EXPOSED**，建议地址均为 **PROPOSED**；没有新增 Router、HTTP API、队列或业务算法。内部模型名称不构成浏览器接口。

## 创建调查

状态：API_NOT_EXPOSED。

已有能力：InvestigationOrchestrator.investigate(request, *, actor)。

代码位置：backend/app/orchestration/service.py。

建议新增接口：POST /api/v1/investigations（PROPOSED，当前不可调用）。

请求：InvestigationRequest（现有内部输入）；公开DTO及队列领取边界BACKEND_REQUIRED。

响应建议：建议202根调查ID/InvestigationStatus；未实现异步HTTP适配。

原因：现有方法同步运行，需可靠幂等领取与后台执行，不能伪造202。

## 调查状态

状态：API_NOT_EXPOSED。

已有能力：InvestigationOrchestrator.get_status(id, *, actor)。

代码位置：backend/app/orchestration/contracts.py。

建议新增接口：GET /api/v1/investigations/{id}/status（PROPOSED，当前不可调用）。

请求：root logical_investigation_id。

响应建议：InvestigationStatus。

原因：只有Python Reader，没有FastAPI Router。

## 调查结果

状态：API_NOT_EXPOSED。

已有能力：InvestigationOrchestrator.get_result(id, *, actor)。

代码位置：backend/app/orchestration/reader.py。

建议新增接口：GET /api/v1/investigations/{id}（PROPOSED，当前不可调用）。

请求：root logical_investigation_id。

响应建议：BACKEND_REQUIRED：status/answer/persistence/delivery_error白名单公开视图。

原因：内部InvestigationResult.context包含owner/stage_keys，不能原样暴露。

## Agent Trace

状态：API_NOT_EXPOSED。

已有能力：InvestigationOrchestrator.get_trace(id, *, actor)。

代码位置：backend/app/orchestration/trace.py。

建议新增接口：GET /api/v1/investigations/{id}/trace（PROPOSED，当前不可调用）。

请求：root logical_investigation_id。

响应建议：InvestigationTrace安全投影。

原因：旧HTTP /assistant/runs/{id}/trace使用不同协议。

## Artifact读取

状态：API_NOT_EXPOSED。

已有能力：Context.artifact_references + Runtime/专业Agent内部Reader。

代码位置：backend/app/runtime/contracts.py。

建议新增接口：GET /api/v1/investigations/{id}/artifacts（PROPOSED，当前不可调用）。

请求：root logical_investigation_id；不接受任意外部ArtifactID。

响应建议：BACKEND_REQUIRED：三个专业Artifact的有序、授权响应包装。

原因：需验证root绑定、owner、哈希/Schema及存储回执关联。

## Integration Gate结果

状态：API_NOT_EXPOSED。

已有能力：Context.integration_result_id + IntegrationService.read(id, *, actor)。

代码位置：backend/app/integration/service.py。

建议新增接口：GET /api/v1/investigations/{id}/integration（PROPOSED，当前不可调用）。

请求：root logical_investigation_id映射到Gate integration_id。

响应建议：IntegrationResult。

原因：Gate logical ID与root logical ID不相同，必须绑定校验；GET不得重评。

## 可信答案

状态：API_NOT_EXPOSED。

已有能力：InvestigationResult.answer。

代码位置：backend/app/orchestration/answer_contracts.py。

建议新增接口：GET /api/v1/investigations/{id}/answer（PROPOSED，当前不可调用）。

请求：root logical_investigation_id。

响应建议：建议未就绪202状态，终态200 AnswerEnvelope；这些HTTP语义尚待确认。

原因：只有内部冻结交付，没有浏览器HTTP入口。

## 取消调查

状态：API_NOT_EXPOSED。

已有能力：InvestigationOrchestrator.cancel(id, *, actor)。

代码位置：backend/app/orchestration/store.py。

建议新增接口：POST /api/v1/investigations/{id}/cancel（PROPOSED，当前不可调用）。

请求：root logical_investigation_id；actor由认证上下文提供。

响应建议：建议202 InvestigationStatus（cancel_requested不等于CANCELLED）。

原因：只有内部持久化取消请求；浏览器Abort不取消任务。

## 历史调查

状态：API_NOT_EXPOSED。

已有能力：已持久化AgentRun；历史list服务尚未实现。

代码位置：backend/app/db/models/application.py。

建议新增接口：GET /api/v1/investigations（PROPOSED，当前不可调用）。

请求：建议offset/limit及明确筛选，owner+agent_type服务器过滤。

响应建议：BACKEND_REQUIRED：分页公开调查摘要DTO。

原因：现有get_result仅单条Reader，没有history HTTP或list方法。

## 共同约束

认证owner来自服务器；保留request_key幂等；状态/Trace只读；Gate不自动重跑；禁止暴露worker_token、stage_keys、数据库配置、原始Prompt；异步提交需要原子领取和去重入队，当前同步服务不具备HTTP队列。完善前端代理、域名Host配置和认证，之后再联调。

全局情报趋势与CPU/内存/模型健康也属于BACKEND_REQUIRED，当前只有列表total、资产统计、数据库health、来源及sync-runs。

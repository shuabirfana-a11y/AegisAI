# API 状态总览

Phase 12-B 已新增 `/api/investigations` 的 8 个实际 HTTP 操作，创建、状态、Trace、Artifact、Gate、答案、取消、历史可以接入；8769 同源代理已放行创建/取消。详见 [调查 API](INVESTIGATION_API.md)。下方历史缺口表中相应调查项目已被此更新取代；其他缺口继续有效。完整 OpenAPI 现有 42 个操作。

状态分两维：后端 HTTP 是否存在、当前前端代理是否放行。页面有设计稿或 TypeScript 类型不表示 API 存在。

| 标记 | 含义 |
|---|---|
| AVAILABLE | FastAPI 已有该操作；需要实际服务、同源和鉴权，才能调用 |
| PROXY_BLOCKED | HTTP 已有，但当前 8769 代理阻止该方法；不是 API_NOT_EXPOSED |
| API_NOT_EXPOSED | 内部服务存在或产品需要此能力，但当前没有相应 HTTP |
| PROPOSED | 尚未实现的建议；不能直接写进真实 API Client |
| MOCK_ONLY | 演示/测试 fixture；不是真实 API 可用性或情报证据 |
| BACKEND_REQUIRED | 页面所需字段/统计/能力目前没有可用公共协议 |

## 当前可接与待补

| 前端能力 | 当前状态 |
|---|---|
| 漏洞分页/详情/富化子资源、证据、复核读取 | AVAILABLE |
| 资产风险与快照/变更读取 | AVAILABLE，需要资产权限 |
| 复核提交、资产新增/组件修改/SBOM/重算、工具 invoke | AVAILABLE + PROXY_BLOCKED，共 7 个操作 |
| 旧问答提交与 run/tasks/trace | AVAILABLE，独立旧协议 |
| 完整智能调查的提交/状态/Trace/Artifact/Gate/Answer/取消/历史 | API_NOT_EXPOSED；Phase 12-B 计划 8 个操作 |
| 数据源、同步历史、health | AVAILABLE |
| 全局情报趋势、CPU/内存/模型实时遥测、SSE/WebSocket | BACKEND_REQUIRED，不声称已实现 |

真实 HTTP：34 个操作，其中 GET 26、POST 7、PATCH 1；代理放行 27 个、拦截 7 个。精确列表见 [AVAILABLE_API](AVAILABLE_API.md)，参数/错误见 [逐项 API 参考](reference/HTTP_API_REFERENCE.md)，机器列表见 [http-apis.json](reference/http-apis.json)。

OpenAPI 的成功响应 Schema 都是 `{}`，因为当前没有声明 response_model。请求定义可用，但生成的空响应不能替代 [HttpContracts](../contracts/HttpContracts.ts) 与人工审查的响应类型。

不要把旧问答 run_id、根 logical_investigation_id、Gate integration_id 和 Gate 自身 logical ID 混用；也不要通过猜测 URL 暴露内部 Python 服务。

# 当前已实现 HTTP API

Phase 12-B 已新增 8 个调查操作，见 [调查 API](INVESTIGATION_API.md)，总数为 42。以下是原有 34 个操作；AVAILABLE 表示接口存在，不承诺当前服务在线。PROXY_BLOCKED 的 7 个旧写操作仍不能从本地前端代理提交。

完整参数、权限、请求示例与错误见 [逐项接口参考](reference/HTTP_API_REFERENCE.md)。旧成功响应的 OpenAPI 描述已经补齐，序列化行为保留；新调查响应使用严格 Pydantic 模型。

| 方法 | 真实完整路径 | 当前浏览器代理 | 返回 TypeScript 类型 | Body 类型 |
|---|---|---|---|---|
| GET | `/health` | AVAILABLE | `Health` | `无 Body` |
| GET | `/api/v1/sources` | AVAILABLE | `SourcesResponse` | `无 Body` |
| GET | `/api/v1/sync-runs` | AVAILABLE | `SyncRunsResponse` | `无 Body` |
| GET | `/api/v1/vulnerabilities` | AVAILABLE | `VulnerabilityListResponse` | `无 Body` |
| GET | `/api/v1/vulnerabilities/{id}` | AVAILABLE | `VulnerabilityDetail` | `无 Body` |
| GET | `/api/v1/vulnerabilities/{id}/enrichment` | AVAILABLE | `EnrichedPage<EnrichmentJob>` | `无 Body` |
| GET | `/api/v1/vulnerabilities/{id}/claims` | AVAILABLE | `EnrichedPage<ClaimRow>` | `无 Body` |
| GET | `/api/v1/vulnerabilities/{id}/evidence` | AVAILABLE | `EnrichedPage<EvidenceRow>` | `无 Body` |
| GET | `/api/v1/vulnerabilities/{id}/pocs` | AVAILABLE | `EnrichedPage<PocCandidate>` | `无 Body` |
| GET | `/api/v1/vulnerabilities/{id}/patches` | AVAILABLE | `EnrichedPage<PatchCandidate>` | `无 Body` |
| GET | `/api/v1/vulnerabilities/{id}/timeline` | AVAILABLE | `EnrichedPage<IntelligenceEvent>` | `无 Body` |
| GET | `/api/v1/evidence/{id}` | AVAILABLE | `EvidenceRow` | `无 Body` |
| GET | `/api/v1/reviews` | AVAILABLE | `Page<ReviewRow>` | `无 Body` |
| GET | `/api/v1/reviews/{id}` | AVAILABLE | `ReviewDetail` | `无 Body` |
| POST | `/api/v1/reviews/{id}/resolve` | PROXY_BLOCKED | `AuditRow` | `Decision` |
| GET | `/api/v1/assets` | AVAILABLE | `Page<AssetRow>` | `无 Body` |
| GET | `/api/v1/assets/overview` | AVAILABLE | `AssetOverview` | `无 Body` |
| POST | `/api/v1/assets` | PROXY_BLOCKED | `AssetRow` | `NewAsset` |
| GET | `/api/v1/assets/{id}` | AVAILABLE | `AssetDetail` | `无 Body` |
| POST | `/api/v1/assets/{id}/components` | PROXY_BLOCKED | `ComponentRow` | `NewComponent` |
| PATCH | `/api/v1/assets/{id}/components/{component_id}` | PROXY_BLOCKED | `ComponentRow` | `UpdateVersion` |
| POST | `/api/v1/assets/{id}/sbom` | PROXY_BLOCKED | `SbomImportResponse` | `原始 JSON + x-request-key` |
| GET | `/api/v1/assets/{id}/risks` | AVAILABLE | `AssetRisksResponse` | `无 Body` |
| GET | `/api/v1/assets/{id}/risks/{snapshot_id}` | AVAILABLE | `HistoricalAssetRisk` | `无 Body` |
| POST | `/api/v1/assets/{id}/recompute` | PROXY_BLOCKED | `{items: LegacyAssetRiskPayload[]}` | `无 Body` |
| GET | `/api/v1/assets/{id}/risk-changes` | AVAILABLE | `RiskChangeResponse` | `无 Body` |
| GET | `/api/v1/assets/{id}/inventory-history` | AVAILABLE | `InventoryHistoryResponse` | `无 Body` |
| GET | `/api/v1/assets/{id}/reviews` | AVAILABLE | `Page<ReviewDetail>` | `无 Body` |
| POST | `/api/v1/assistant/query` | AVAILABLE | `LegacyAssistantRun` | `QueryRequest` |
| GET | `/api/v1/assistant/runs/{id}` | AVAILABLE | `LegacyAssistantRun` | `无 Body` |
| GET | `/api/v1/assistant/runs/{id}/tasks` | AVAILABLE | `{items: LegacyTaskRun[]}` | `无 Body` |
| GET | `/api/v1/assistant/runs/{id}/trace` | AVAILABLE | `LegacyAssistantTrace` | `无 Body` |
| GET | `/api/v1/tools/contracts` | AVAILABLE | `ToolContractsResponse` | `无 Body` |
| POST | `/api/v1/tools/{name}` | PROXY_BLOCKED | `ToolEnvelope` | `按工具 input_schema` |

## 权限与错误

- 漏洞/证据/公开复核读取、sources、sync-runs 和 health 没有资产令牌要求；资产、旧问答、工具入口需要 AEGIS_ASSET_TOKEN。复核 resolve 需要 AEGIS_REVIEW_TOKEN。真实凭据不包含在本包。
- 未配置令牌通常为 503，缺少/无效 Bearer 为 401。资产与问答归属由服务器 principal 控制，不允许客户端冒充 owner。
- 404 可表示不存在或无权访问；422 是参数/业务输入错误；409 是幂等/修订冲突；旧问答容量满为 429。代理可返回 403/405/413/415/502。具体逐项说明以接口参考为准。
- 后端尚无统一错误 Envelope，HTTPException 通常为 `{detail:string}`；FastAPI 校验为 `{detail:[...]}`。工具 HTTP 200 仍需检查 ToolEnvelope.status/errors。

## 字段和读取约束

- 漏洞 q 只搜索 canonical_id；分页 offset>=0、limit=1..100，默认 0/20；来源筛选 CVE_LIST/OSV/CISA_KEV。sources 不是同样的分页协议。
- 漏洞详情已有 conflicts、epss、verification_results、reviews 等聚合数组；没有对应独立子资源 URL，也没有 GET /claims/{id}。
- GET /api/v1/evidence/{id} 要求数据库 UUID。专业快照的派生 evidence_id/claim_id 不能假设可调用这条接口。
- /tools/contracts 公开注册工具类型不表示所有工具可 invoke；外部入口只允许 READ_ONLY，写工具和 refresh=true 被拒绝。
- 旧 assistant/query 返回旧 LegacyAssistantRun，不是 InvestigationStatus 或 AnswerEnvelope。没有现成的旧问答 HTTP cancel/history-list/SSE。

Node 的 `/client-config` 是前端本地配置入口，不属于上述 34 个 FastAPI 操作。后端 `/docs`、`/redoc`、`/openapi.json` 是文档入口，当前前端代理不代理。

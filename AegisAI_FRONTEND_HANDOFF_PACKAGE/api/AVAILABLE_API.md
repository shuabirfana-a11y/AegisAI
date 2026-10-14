# 当前真实 API 清单

2026-10-14增量：当前46路径/47操作，原调查8操作保留，另有5个 `/api/v1/intelligence` 只读接口。见仓库 `docs/phase14a/FRONTEND_ADAPTER_NOTES.md` 与本包 `api/reference/intelligence-http.openapi.json`。监测客户端为 `contracts/intelligence.ts`。下表为旧代理范围快照，新接口请按配置直接连接后端URL，不假定旧8769代理已经接线。

2026-10-11：42个HTTP操作、41条路径，代理可接35个，7个旧写操作仍受限。AVAILABLE不保证服务在线。

| 方法 | 真实路径 | 响应类型 | 8769代理 |
|---|---|---|---|
| GET | `/health` | `Health` | AVAILABLE |
| GET | `/api/v1/sources` | `SourcesResponse` | AVAILABLE |
| GET | `/api/v1/sync-runs` | `SyncRunsResponse` | AVAILABLE |
| GET | `/api/v1/vulnerabilities` | `VulnerabilityListResponse` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}` | `VulnerabilityDetail` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/enrichment` | `EnrichedPage<EnrichmentJob>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/claims` | `EnrichedPage<ClaimRow>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/evidence` | `EnrichedPage<EvidenceRow>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/pocs` | `EnrichedPage<PocCandidate>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/patches` | `EnrichedPage<PatchCandidate>` | AVAILABLE |
| GET | `/api/v1/vulnerabilities/{id}/timeline` | `EnrichedPage<IntelligenceEvent>` | AVAILABLE |
| GET | `/api/v1/evidence/{id}` | `EvidenceRow` | AVAILABLE |
| GET | `/api/v1/reviews` | `Page<ReviewRow>` | AVAILABLE |
| GET | `/api/v1/reviews/{id}` | `ReviewDetail` | AVAILABLE |
| POST | `/api/v1/reviews/{id}/resolve` | `AuditRow` | PROXY_BLOCKED |
| GET | `/api/v1/assets` | `Page<AssetRow>` | AVAILABLE |
| POST | `/api/v1/assets` | `AssetRow` | PROXY_BLOCKED |
| GET | `/api/v1/assets/overview` | `AssetOverview` | AVAILABLE |
| GET | `/api/v1/assets/{id}` | `AssetDetail` | AVAILABLE |
| POST | `/api/v1/assets/{id}/components` | `ComponentRow` | PROXY_BLOCKED |
| PATCH | `/api/v1/assets/{id}/components/{component_id}` | `ComponentRow` | PROXY_BLOCKED |
| POST | `/api/v1/assets/{id}/sbom` | `SbomImportResponse` | PROXY_BLOCKED |
| GET | `/api/v1/assets/{id}/risks` | `AssetRisksResponse` | AVAILABLE |
| GET | `/api/v1/assets/{id}/risks/{snapshot_id}` | `HistoricalAssetRisk` | AVAILABLE |
| POST | `/api/v1/assets/{id}/recompute` | `{items: LegacyAssetRiskPayload[]}` | PROXY_BLOCKED |
| GET | `/api/v1/assets/{id}/risk-changes` | `RiskChangeResponse` | AVAILABLE |
| GET | `/api/v1/assets/{id}/inventory-history` | `InventoryHistoryResponse` | AVAILABLE |
| GET | `/api/v1/assets/{id}/reviews` | `Page<ReviewDetail>` | AVAILABLE |
| POST | `/api/v1/assistant/query` | `LegacyAssistantRun` | AVAILABLE |
| GET | `/api/v1/assistant/runs/{id}` | `LegacyAssistantRun` | AVAILABLE |
| GET | `/api/v1/assistant/runs/{id}/tasks` | `{items: LegacyTaskRun[]}` | AVAILABLE |
| GET | `/api/v1/assistant/runs/{id}/trace` | `LegacyAssistantTrace` | AVAILABLE |
| GET | `/api/v1/tools/contracts` | `ToolContractsResponse` | AVAILABLE |
| POST | `/api/v1/tools/{name}` | `ToolEnvelope` | PROXY_BLOCKED |
| POST | `/api/investigations` | `InvestigationCreateResponse` | AVAILABLE |
| GET | `/api/investigations/history` | `HistoryResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/status` | `InvestigationStatusResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/trace` | `TraceResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/artifacts` | `ArtifactResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/integration` | `IntegrationResponse` | AVAILABLE |
| GET | `/api/investigations/{id}/answer` | `AnswerResponse` | AVAILABLE |
| POST | `/api/investigations/{id}/cancel` | `InvestigationStatusResponse` | AVAILABLE |

完整参数见 [OpenAPI](reference/openapi.json)、[调查说明](INVESTIGATION_API.md) 与 [机器清单](reference/http-apis.json)。

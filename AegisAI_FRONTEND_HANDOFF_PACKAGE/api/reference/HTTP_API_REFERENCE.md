# 现有 HTTP 操作逐项参考

本文件记录旧 34 个操作。Phase 12-B 已新增 8 个调查操作，完整 OpenAPI 共 42 个操作，新入口见 [调查 API 对接](../INVESTIGATION_API.md)。旧响应 OpenAPI 描述已补齐，序列化与旧错误格式保留。

AVAILABLE表示现有HTTP已实现，在正确同源/鉴权条件下调用；PROXY_BLOCKED行不能从当前8769页面直接提交。此标记不是API_NOT_EXPOSED。

所有示例是MOCK，不含令牌值。错误码是处理分支清单，不是已经实现的统一ErrorEnvelope。

## GET /health

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/routes.py:13。

请求Body：无。

无额外业务参数。

成功：HTTP 200；响应类型 Health（手工源码映射，OpenAPI Schema={}）。

已识别失败：503: Database down; response still uses Health fields。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/health",
  "body": null
}
~~~

## GET /api/v1/sources

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/routes.py:21。

请求Body：无。

无额外业务参数。

成功：HTTP 200；响应类型 SourcesResponse（手工源码映射，OpenAPI Schema={}）。

已识别失败：未显式定义专用业务错误；公共网络/服务器错误仍需处理。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/sources",
  "body": null
}
~~~

## GET /api/v1/sync-runs

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/routes.py:24。

请求Body：无。

- query source（可省略）：{"anyOf": [{"enum": ["CVE_LIST", "OSV", "CISA_KEV"], "type": "string"}, {"type": "null"}], "title": "Source"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 SyncRunsResponse（手工源码映射，OpenAPI Schema={}）。

已识别失败：422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/sync-runs",
  "body": null
}
~~~

## GET /api/v1/vulnerabilities

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/routes.py:28。

请求Body：无。

- query q（可省略）：{"anyOf": [{"type": "string", "maxLength": 150}, {"type": "null"}], "title": "Q"}
- query source（可省略）：{"anyOf": [{"enum": ["CVE_LIST", "OSV", "CISA_KEV"], "type": "string"}, {"type": "null"}], "title": "Source"}
- query ai_relevance（可省略）：{"anyOf": [{"enum": ["relevant", "irrelevant", "uncertain"], "type": "string"}, {"type": "null"}], "title": "Ai Relevance"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}
- query sort（可省略）：{"enum": ["modified_desc", "published_desc"], "type": "string", "default": "modified_desc", "title": "Sort"}

成功：HTTP 200；响应类型 VulnerabilityListResponse（手工源码映射，OpenAPI Schema={}）。

已识别失败：422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/vulnerabilities",
  "body": null
}
~~~

## GET /api/v1/vulnerabilities/{id}

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/routes.py:34。

请求Body：无。

- path id（必填）：{"type": "string", "title": "Id"}

成功：HTTP 200；响应类型 VulnerabilityDetail（手工源码映射，OpenAPI Schema={}）。

已识别失败：404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/vulnerabilities/CVE-2099-0001",
  "body": null
}
~~~

## GET /api/v1/vulnerabilities/{id}/enrichment

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/enrichment.py:18。

请求Body：无。

- path id（必填）：{"type": "string", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 EnrichedPage<EnrichmentJob>（手工源码映射，OpenAPI Schema={}）。

已识别失败：404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/vulnerabilities/CVE-2099-0001/enrichment",
  "body": null
}
~~~

## GET /api/v1/vulnerabilities/{id}/claims

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/enrichment.py:18。

请求Body：无。

- path id（必填）：{"type": "string", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 EnrichedPage<ClaimRow>（手工源码映射，OpenAPI Schema={}）。

已识别失败：404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/vulnerabilities/CVE-2099-0001/claims",
  "body": null
}
~~~

## GET /api/v1/vulnerabilities/{id}/evidence

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/enrichment.py:18。

请求Body：无。

- path id（必填）：{"type": "string", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 EnrichedPage<EvidenceRow>（手工源码映射，OpenAPI Schema={}）。

已识别失败：404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/vulnerabilities/CVE-2099-0001/evidence",
  "body": null
}
~~~

## GET /api/v1/vulnerabilities/{id}/pocs

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/enrichment.py:18。

请求Body：无。

- path id（必填）：{"type": "string", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 EnrichedPage<PocCandidate>（手工源码映射，OpenAPI Schema={}）。

已识别失败：404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/vulnerabilities/CVE-2099-0001/pocs",
  "body": null
}
~~~

## GET /api/v1/vulnerabilities/{id}/patches

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/enrichment.py:18。

请求Body：无。

- path id（必填）：{"type": "string", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 EnrichedPage<PatchCandidate>（手工源码映射，OpenAPI Schema={}）。

已识别失败：404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/vulnerabilities/CVE-2099-0001/patches",
  "body": null
}
~~~

## GET /api/v1/vulnerabilities/{id}/timeline

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/enrichment.py:18。

请求Body：无。

- path id（必填）：{"type": "string", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 EnrichedPage<IntelligenceEvent>（手工源码映射，OpenAPI Schema={}）。

已识别失败：404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/vulnerabilities/CVE-2099-0001/timeline",
  "body": null
}
~~~

## GET /api/v1/evidence/{id}

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/enrichment.py:27。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}

成功：HTTP 200；响应类型 EvidenceRow（手工源码映射，OpenAPI Schema={}）。

已识别失败：404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/evidence/00000000-0000-4000-8000-000000000001",
  "body": null
}
~~~

## GET /api/v1/reviews

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/enrichment.py:33。

请求Body：无。

- query status（可省略）：{"anyOf": [{"enum": ["open", "assigned", "resolved", "deferred", "cancelled"], "type": "string"}, {"type": "null"}], "title": "Status"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 Page<ReviewRow>（手工源码映射，OpenAPI Schema={}）。

已识别失败：422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/reviews",
  "body": null
}
~~~

## GET /api/v1/reviews/{id}

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：none。源码：backend/app/api/enrichment.py:41。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}

成功：HTTP 200；响应类型 ReviewDetail（手工源码映射，OpenAPI Schema={}）。

已识别失败：404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/reviews/00000000-0000-4000-8000-000000000001",
  "body": null
}
~~~

## POST /api/v1/reviews/{id}/resolve

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**PROXY_BLOCKED**。

权限：AEGIS_REVIEW_TOKEN (server principal)。源码：backend/app/api/enrichment.py:58。

请求Body：Decision，精确约束见 http-input.schemas.json。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}

成功：HTTP 200；响应类型 AuditRow（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Asset review requires protected context；409: Idempotency or revision conflict；422: Invalid request or business input；503: Local token not configured。
代理层失败：405: 当前代理未放行此提交。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "POST",
  "url": "/api/v1/reviews/00000000-0000-4000-8000-000000000001/resolve",
  "body": {
    "expected_revision": 1,
    "expected_claim_revision": 1,
    "request_key": "mock-review-001",
    "status": "PENDING",
    "reason": "MOCK: evidence requires review",
    "evidence_ids": []
  },
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assets

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:43。

请求Body：无。

- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 Page<AssetRow>（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assets",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assets/overview

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:49。

请求Body：无。

无额外业务参数。

成功：HTTP 200；响应类型 AssetOverview（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assets/overview",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## POST /api/v1/assets

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**PROXY_BLOCKED**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:52。

请求Body：NewAsset，精确约束见 http-input.schemas.json。

无额外业务参数。

成功：HTTP 201；响应类型 AssetRow（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Asset or component unavailable；409: Idempotency or revision conflict；422: Invalid request or business input；503: Local token not configured。
代理层失败：405: 当前代理未放行此提交。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "POST",
  "url": "/api/v1/assets",
  "body": {
    "name": "MOCK asset",
    "request_key": "mock-asset-001",
    "is_demo": true
  },
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assets/{id}

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:57。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}

成功：HTTP 200；响应类型 AssetDetail（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## POST /api/v1/assets/{id}/components

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**PROXY_BLOCKED**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:62。

请求Body：NewComponent，精确约束见 http-input.schemas.json。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}

成功：HTTP 201；响应类型 ComponentRow（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Asset or component unavailable；409: Idempotency or revision conflict；422: Invalid request or business input；503: Local token not configured。
代理层失败：405: 当前代理未放行此提交。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "POST",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001/components",
  "body": {
    "name": "vllm",
    "version": "0.6.0",
    "request_key": "mock-component-001"
  },
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## PATCH /api/v1/assets/{id}/components/{component_id}

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**PROXY_BLOCKED**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:67。

请求Body：UpdateVersion，精确约束见 http-input.schemas.json。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}
- path component_id（必填）：{"type": "string", "format": "uuid", "title": "Component Id"}

成功：HTTP 200；响应类型 ComponentRow（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Asset or component unavailable；409: Idempotency or revision conflict；422: Invalid request or business input；503: Local token not configured。
代理层失败：405: 当前代理未放行此提交。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "PATCH",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001/components/00000000-0000-4000-8000-000000000001",
  "body": {
    "version": "0.6.1",
    "expected_revision": 1,
    "request_key": "mock-version-001"
  },
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## POST /api/v1/assets/{id}/sbom

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**PROXY_BLOCKED**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:71。

请求Body：原始SBOM JSON；不是multipart。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}
- header x-request-key（必填）：{"type": "string", "minLength": 1, "maxLength": 150, "title": "X-Request-Key"}

成功：HTTP 200；响应类型 SbomImportResponse（手工源码映射，OpenAPI Schema={}）。

已识别失败：400: Invalid Content-Length；401: Authentication required；404: Asset or component unavailable；409: Idempotency or revision conflict；413: Exceeds 2 MiB；422: Invalid request or business input；503: Local token not configured。
代理层失败：405: 当前代理未放行此提交。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "POST",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001/sbom",
  "body": {
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "version": 1,
    "components": [
      {
        "type": "library",
        "name": "vllm",
        "version": "0.6.0",
        "purl": "pkg:pypi/vllm@0.6.0"
      }
    ]
  },
  "auth": "configured server token required; value intentionally omitted",
  "headers": {
    "x-request-key": "mock-sbom-001",
    "Content-Type": "application/json"
  }
}
~~~

## GET /api/v1/assets/{id}/risks

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:86。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 AssetRisksResponse（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001/risks",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assets/{id}/risks/{snapshot_id}

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:91。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}
- path snapshot_id（必填）：{"type": "string", "format": "uuid", "title": "Snapshot Id"}

成功：HTTP 200；响应类型 HistoricalAssetRisk（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001/risks/00000000-0000-4000-8000-000000000001",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## POST /api/v1/assets/{id}/recompute

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**PROXY_BLOCKED**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:96。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}

成功：HTTP 200；响应类型 {items: LegacyAssetRiskPayload[]}（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Asset or component unavailable；409: Idempotency or revision conflict；422: Invalid request or business input；503: Local token not configured。
代理层失败：405: 当前代理未放行此提交。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "POST",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001/recompute",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assets/{id}/risk-changes

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:102。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 RiskChangeResponse（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001/risk-changes",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assets/{id}/inventory-history

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:107。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 InventoryHistoryResponse（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001/inventory-history",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assets/{id}/reviews

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assets.py:115。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}
- query offset（可省略）：{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}
- query limit（可省略）：{"type": "integer", "maximum": 100, "minimum": 1, "default": 20, "title": "Limit"}

成功：HTTP 200；响应类型 Page<ReviewDetail>（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assets/00000000-0000-4000-8000-000000000001/reviews",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## POST /api/v1/assistant/query

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assistant.py:9。

请求Body：QueryRequest，精确约束见 http-input.schemas.json。

无额外业务参数。

成功：HTTP 202；响应类型 LegacyAssistantRun（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；403: Realtime tools disabled by server policy；409: Same request key with different content；422: FastAPI validation; mutation may also return controlled ValueError；429: Assistant queue full；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "POST",
  "url": "/api/v1/assistant/query",
  "body": {
    "question": "查询 CVE-2099-0001（MOCK）",
    "request_key": "mock-query-001",
    "target": "CVE-2099-0001",
    "realtime": false
  },
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assistant/runs/{id}

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assistant.py:16。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}

成功：HTTP 200；响应类型 LegacyAssistantRun（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assistant/runs/00000000-0000-4000-8000-000000000001",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assistant/runs/{id}/tasks

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assistant.py:21。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}

成功：HTTP 200；响应类型 {items: LegacyTaskRun[]}（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assistant/runs/00000000-0000-4000-8000-000000000001/tasks",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/assistant/runs/{id}/trace

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/assistant.py:26。

请求Body：无。

- path id（必填）：{"type": "string", "format": "uuid", "title": "Id"}

成功：HTTP 200；响应类型 LegacyAssistantTrace（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；404: Resource missing or not owned; protected review context may be excluded；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/assistant/runs/00000000-0000-4000-8000-000000000001/trace",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## GET /api/v1/tools/contracts

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**AVAILABLE**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/tools.py:13。

请求Body：无。

无额外业务参数。

成功：HTTP 200；响应类型 ToolContractsResponse（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：问答POST另有同源/JSON类型/2MiB检查；网络超时502。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "GET",
  "url": "/api/v1/tools/contracts",
  "body": null,
  "auth": "configured server token required; value intentionally omitted"
}
~~~

## POST /api/v1/tools/{name}

状态：**AVAILABLE（现有 HTTP）**；当前8769浏览器入口：**PROXY_BLOCKED**。

权限：AEGIS_ASSET_TOKEN (server principal)。源码：backend/app/api/tools.py:19。

请求Body：注册工具 input_schema，见 tools.registry.json。

- path name（必填）：{"type": "string", "title": "Name"}

成功：HTTP 200；响应类型 ToolEnvelope（手工源码映射，OpenAPI Schema={}）。

已识别失败：401: Authentication required；403: Tool not READ_ONLY, or refresh requested；404: Unknown tool；422: FastAPI validation; mutation may also return controlled ValueError；503: Local token not configured。
代理层失败：405: 当前代理未放行此提交。

请求示例仅为MOCK，不是实际HTTP抓包：

~~~json
{
  "api_status": "MOCK_ONLY",
  "fixture_label": "MOCK",
  "production_data": false,
  "method": "POST",
  "url": "/api/v1/tools/search_vulnerabilities",
  "body": {
    "q": "CVE-2099-0001",
    "limit": 20
  },
  "auth": "configured server token required; value intentionally omitted"
}
~~~

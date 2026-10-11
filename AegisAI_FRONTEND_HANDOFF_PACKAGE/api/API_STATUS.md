# 当前 API 状态

更新：2026-10-11，Phase12-C。42个HTTP操作、41条路径；8769可接35个，另7个旧写操作受限。完整清单见 [AVAILABLE_API](AVAILABLE_API.md)。

| 标签 | 含义 |
|---|---|
| AVAILABLE | 当前HTTP操作已实现；服务、Origin与权限须满足 |
| PROXY_BLOCKED | 后端已实现，但8769未放行 |
| API_NOT_EXPOSED | 当前无对应HTTP；内部模型不代表已经开放 |
| BACKEND_REQUIRED | 产品需要，但尚无公共字段/实现 |
| MOCK_ONLY | 明确的合成演示资料，不能冒充真实结果 |

智能调查提交、状态、Trace、Artifact、Gate、Answer、取消、历史八操作均AVAILABLE，统一前缀 `/api/investigations`，无需再等API开放。原 `/api/v1/investigations` 是历史提案，不可调用。

旧34操作保留兼容响应，OpenAPI描述为LEGACY_DESCRIPTION_ONLY；新八操作使用严格Pydantic，类型见 `reference/investigation-http.d.ts`，Client见 `reference/investigation-client.ts`。

当前默认Mock缺少PlannerPlan，普通调查实测PLANNING_FAILED。显式合成测试规划回执已通过真实TCP闭环，不能据此声称真实模型演示可用。详见 [联调结果](../docs/PHASE12C_INTEGRATION.md)。

尚未开放的能力见 [API_NOT_EXPOSED](API_NOT_EXPOSED.md)；已有7个受限写操作是PROXY_BLOCKED，不能误报为无API。

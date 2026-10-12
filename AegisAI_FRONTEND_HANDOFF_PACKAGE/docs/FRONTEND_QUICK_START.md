# 前端联调快速开始

更新：2026-10-11。先读取 [API状态](../api/API_STATUS.md) 与 [实际联调结果](PHASE12C_INTEGRATION.md)。

1. **取得运行环境。** 后端由负责人准备；本机8769同源代理可直接调用，队友电脑的127.0.0.1不是负责人的电脑。本轮没有公网网址。
2. **复制当前公共契约。** 将 `api/reference/investigation-client.ts` 和 `investigation-http.d.ts` 放在同一目录；由队友自己的TypeScript构建工具处理。旧 `contracts/generated/internal-output.ts` 仅作内部/历史fixture参考。
3. **创建调查。** 使用公共 user_query / asset_scope / options，并保留一个稳定幂等键。用 `new InvestigationApiClient()` 接8769同源代理；自建前端则配置已获授权的baseUrl与运行时token回调，勿保存模型Key。
4. **读实际状态。** 每1–2秒查询status，revision变更才刷新trace/artifacts；终态读取answer/integration。202不是成功，null Artifact不是零风险；取消要等CANCELLED。
5. **处理失败。** HTTP异常看ApiError/Retry-After；默认Mock规划会PLANNING_FAILED。允许展示明确Mock，但真实失败不得静默改成Mock成功。

## 对接检查

- 新八操作路径以 `/api/investigations` 开头，**没有 `/api/v1/investigations`**。
- 旧 `/api/v1/assistant/query` 使用旧问答协议；不要将其answer字符串当AnswerEnvelope。
- 当前42操作、代理可接35个、7个旧写操作仍受限。列表/详情/证据/资产读取可继续按原协议接入。
- 七个现有路由：dashboard、vulnerabilities、vulnerabilities/{id}、assets、reviews、assistant、system。
- 当前TypeScript语义检查已由项目CI实际执行；Client本轮通过真实TCP八操作，但没有浏览器运行时Schema验证或自动重试。
- `mock/` 是历史合成演示资料，不能直接将外层fixture对象作为公共提交请求。

完整字段、状态、证据及错误见 [完整交接](FRONTEND_TEAM_HANDOFF.md)，调用约束见 [调查API](../api/INVESTIGATION_API.md)。本包只有契约/文档/模拟资料，无法单独启动后端。

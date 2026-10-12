# AegisAI 前端团队交接包

**先读本页，再读快速入门和页面需求。此包可以独立转交，不包含后端程序、数据库、账号或密钥。**

项目：AegisAI——面向 AI 生态的可信安全情报与自主调查智能体系统。目标：赛题九的安全情报调查、证据核验和可信答案展示。

更新日期：2026-10-12。Phase12B调查闭环8个HTTP操作可对接；Phase12D新增可选Trace模型身份字段，真实模型调查仍未就绪。请优先阅读 [调查 API](api/INVESTIGATION_API.md)、[模型联调状态](docs/PHASE12D_MODEL_STATUS.md)和 `api/reference/investigation-http.d.ts`；Phase12A.5内部协议仍为历史参考。

## 三个先记住的事实

1. 后端现有 **42 个 HTTP 操作**；新增 8 个调查操作已放行代理，原有 7 个其他写操作继续受限。鉴权和运行环境仍需满足，不能据此认定服务当前在线。
2. `/api/v1/assistant/query` 是旧问答入口。新调查入口是 `/api/investigations`，能够调用 Phase 11-D 闭环并读取存储结果；两者不混用。
3. `mock/` 全部是演示资料。历史测试回执使用合成漏洞和资产；不是实际漏洞情报、线上 HTTP 抓包或比赛 Benchmark 成绩。

## 阅读顺序

| 次序 | 文件 | 用途 |
|---|---|---|
| 1 | [快速入门](docs/FRONTEND_QUICK_START.md) | 先把类型和 Mock 接进自己的前端 |
| 2 | [页面需求](docs/UI_REQUIREMENTS.md) | 七页内容、数据口径和验收条件 |
| 3 | [API 状态](api/API_STATUS.md) | 区分真实接口、代理阻断和缺失接口 |
| 4 | [完整项目交接](docs/FRONTEND_TEAM_HANDOFF.md) | 字段、状态、错误、幂等、取消、类型映射 |
| 5 | [页面结构](design/PAGE_STRUCTURE.md)、[组件计划](design/COMPONENT_PLAN.md)、[用户流程](design/USER_FLOW.md) | 页面组织与实现分工 |
| 6 | [比赛演示流程](docs/DEMO_FLOW.md)、[示例场景](examples/demo-scenario.md) | 展示顺序和边界说明 |
| 7 | [后端状态](docs/BACKEND_STATUS.md) | 已有能力与 Phase 12-B API 边界 |

## 文件用途

- `contracts/`：九个指定的类型入口、现有 HTTP 类型和 `generated/` 依赖。**请整目录复制**，不要只复制九个入口文件。
- `mock/`：五个展示入口以及独立 Gate 示例。五个入口使用同一批历史场景 ID，方便联动；完整专业 Artifact 的弃权示例单独标记，不能混入成功场景。
- `api/`：当前 API 清单、缺失 API 和离线 OpenAPI/JSON Schema。完整请求、响应、权限和错误请查 [逐项接口参考](api/reference/HTTP_API_REFERENCE.md)。
- `design/`：沿用现有 UX/UI 方向的实施需求，不表示新页面已经开发完成。
- [VALIDATION.json](VALIDATION.json)：本次实际验证范围与结果。
- [MANIFEST.json](MANIFEST.json)：包内文件、字节数和 SHA-256。

## 前端当前可以开始什么

可以接入现有漏洞列表/详情、证据、复核读取、资产风险读取、数据源和系统健康；可以用明确标记的 Mock 开发完整调查界面。旧问答可单独联调。完整调查的提交、状态、Trace、Artifact、Gate、答案、取消和历史列表已有 HTTP 入口，请按调查 API 文档接入配置好的后端环境。

现有前端采用原生 JavaScript ESM 和 Node 本地代理，七页已经存在。此包提供 TypeScript 契约供团队使用，不等于项目已经改成 React/Vue 或建立了 TypeScript 构建系统。

本包不含可部署网站，也不含服务地址或登录凭据。收到 ZIP 后可以立即进行离线 Mock 页面开发；真实联调需取得完整项目或由后端负责人提供可访问环境。历史测试与本轮实跑结果分别记录；当前验证见 PHASE12B_VERIFICATION.json，原 VALIDATION.json 仅保留历史交接检查。

## Phase 12-C 当前联调

八个HTTP操作和现有TypeScript Client已通过本机TCP闭环；成功输入/模型回执明确为SYNTHETIC_TEST。默认Mock真实来源查询仍PLANNING_FAILED，不能声明真实模型演示已就绪。参见 [当前联调结果](docs/PHASE12C_INTEGRATION.md) 与 [当前验证](PHASE12C_VERIFICATION.json)。历史VALIDATION.json与PHASE12B_VERIFICATION.json保留原时间和范围，不替代当前记录。

## Phase 12-D 模型标识

调查Trace公共投影新增可选 model_execution：execution_mode、provider、model、source、attempt_count。null表示尚无确认调用记录；不要从当前服务配置推断历史模式。MOCK/REAL与执行成功/失败分别展示。只用 api/reference/investigation-http.d.ts 的公共类型；不向浏览器传模型Key或11434地址。模型/业务实跑状态见本阶段交接记录，不将历史Mock示例当成实时调查。

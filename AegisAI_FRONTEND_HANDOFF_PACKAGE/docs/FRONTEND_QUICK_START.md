> Phase 12-B 更新：先复制 `api/reference/investigation-client.ts` 和 `investigation-http.d.ts` 到前端同一目录。用客户端调用 8 个调查接口；HTTP 响应以这份生成类型为准。下文旧 `contracts/` 继续描述内部模型和历史演示，不应替代新的公共响应 DTO。

# 前端快速入门

## 先选择工作模式

| 模式 | 需要什么 | 能做什么 |
|---|---|---|
| 离线 Mock | 本交接包 + 团队现有前端工程 | 页面布局、字段展示、状态和跨组件联动 |
| 当前真实 API | 完整项目或可访问后端；正确同源代理及权限 | 漏洞、证据、资产、复核读取、旧问答、系统状态 |
| 完整自主调查 | Phase 12-B 后端分支或合并后版本；已配置权限/同源代理 | 8 个调查 API 已实现，按 api/INVESTIGATION_API.md 联调 |

本包本身不能启动后端或数据库。`127.0.0.1` 指当前使用者自己的电脑；队友在自己的电脑输入开发者的本地地址，无法访问开发者的服务。现有代理只接受本地 Host，云端或远程联调需另行部署适配。

## 第一步：复制类型与示例

把 `contracts/` 整目录复制到自己的前端类型目录，把 `mock/` 放到自己的开发用 fixture 目录。不要把私有密钥写进页面、静态 JSON 或前端环境变量。

```ts
import type { InvestigationRequest, InvestigationStatus, AnswerEnvelope } from './contracts/index.js';
import type { RiskView } from './contracts/generated/internal-output.js';
import type { VulnerabilityListResponse } from './contracts/HttpContracts.js';
```

这些是类型导出，没有执行模型、调用服务或发起请求的代码。`.js` 是 ESM 导入写法，文件实际为 `.ts`，由团队 TypeScript 构建工具解析；请按自己的 `tsconfig` 进行语义检查。当前项目未安装 TypeScript 编译器，本次只做原生 TypeScript 语法与引用校验。

读取 Mock 时先选同一个场景：

```ts
// JSON 导入或 fetch 静态 JSON 的方式由现有前端构建工具决定。
const scenario = 'PASS';
const request = investigationFixture.scenarios[scenario].request;
const status = investigationFixture.scenarios[scenario].status;
const trace = traceFixture.scenarios[scenario];
const answer = answerFixture.scenarios[scenario];
const evidenceView = evidenceFixture.scenarios[scenario];
const riskView = riskFixture.scenarios[scenario];
```

上面只是读取位置示意，未提供运行中的 API Client。Mock 外层含 `api_status`、`fixture_label`、`production_data` 等标签；**不能把整个包装对象作为 InvestigationRequest 提交**。字段映射见 [Mock 说明](../mock/README.md)。

## 第二步：先做一个正确的结果页

先用 `PASS` 展示问题范围、调查阶段、核验结论、风险、修复建议及引用。然后用 `REPLAN_REQUIRED`、`HUMAN_REVIEW_REQUIRED`、`CANCELLED`、`DEADLINE_EXCEEDED` 验证结果状态。不要把任何终态都渲染成“调查成功”。

`risk-demo.json` 的场景数据是 **AnswerEnvelope 风险展示投影**，其中 `risk_assessment` 类型为 `RiskView | null`，不是完整 `RiskAnalysisArtifact`。`artifact_examples` 的专业 Artifact 是独立弃权示例，不属于 PASS 场景。

## 第三步：接当前真实接口

先读 [现有接口清单](../api/AVAILABLE_API.md)，复用完整项目中的 `frontend/public/modules/services.js`。现有 API 没有统一错误 Envelope，HTTP 失败先读取 `detail`，成功再检查业务状态和字段。

常用读取示例：

```text
GET /api/v1/vulnerabilities?offset=0&limit=20&sort=modified_desc
GET /api/v1/vulnerabilities/{CVE编号或内部UUID}
GET /api/v1/vulnerabilities/{id}/claims?offset=0&limit=20
GET /api/v1/vulnerabilities/{id}/evidence?offset=0&limit=20
GET /api/v1/assets/overview                  （需要资产权限）
GET /api/v1/reviews?offset=0&limit=20
GET /api/v1/sources
GET /health
```

`q` 目前只搜索漏洞 `canonical_id`，不支持把它当产品全文搜索。分页 `limit=1..100`，`offset>=0`；sources 的返回没有 offset/limit。总览图表只使用已有统计口径，缺少趋势 API 时显示“未提供”或明确 Mock。

## 完整项目的本地入口

如果队友已经拿到完整项目，并且后端和数据库已由负责人准备好，可在项目的 `frontend/` 目录运行 `npm start`，打开 `http://127.0.0.1:8769/dashboard`。前端默认转发到本机 8000 端口；此命令不启动后端。

`8768/#/overview` 是静态原型；`8769/dashboard` 是实际 API 前端。两者不同。`/openapi.json` 和 `/docs` 位于后端 8000，当前前端代理不代理这些地址；可直接离线查阅 [OpenAPI 文件](../api/reference/openapi.json)。

资产、旧问答和工具需要后端环境中的 `AEGIS_ASSET_TOKEN`；复核写入需要 `AEGIS_REVIEW_TOKEN`。凭据只在联调环境本机配置，不随交接包发送。现有 `AEGIS_LOCAL_DEMO=1` 可由 Node 注入资产/问答令牌，但不是用户注册登录或云端多租户方案。具体要求见完整交接中的鉴权说明。

不要通过跨端口 fetch 绕过代理：后端尚无 CORS 配置，页面 CSP 限制同源连接。7 个现有写操作仍被当前代理阻断，按钮应禁用并注明原因。

## 第四步：给后端的联调反馈

记录页面、方法、路径、请求字段、HTTP 状态、业务状态、根调查 ID（如有）和安全摘要。不要发送令牌、原始 Prompt、私有上下文或数据库信息。缺字段按 `BACKEND_REQUIRED` 反馈，缺 API 按 `API_NOT_EXPOSED` 反馈。

Phase 12-B 完成后，先取得新的 OpenAPI、成功响应 DTO、公开错误映射和代理说明，再把 Mock 适配器切换到真实服务。当前包中的建议 URL 不应直接投入调用。

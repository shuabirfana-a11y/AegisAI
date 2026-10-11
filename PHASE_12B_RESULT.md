# Phase 12-B 完成报告

验证时间：2026-10-11T11:18:47.043020+00:00。分支：feature/investigation-api，基线：c32b147。仅完成调查 HTTP 暴露、契约导出和前端传输接线，没有进入 Phase 12-C。

## 完成内容

- 复用原 InvestigationOrchestrator、三专业 Agent、Runtime、Planner、Gate、Artifact Readers 和 AnswerEnvelope。
- 创建响应等待原 claim 提交后才返回 202 和真实根 ID；同键同内容复用，不同内容返回 409。最多 2 个后台工作线程，满载返回 429。
- status、trace、artifacts、integration、answer、cancel、history 均为真实 FastAPI 路由；读结果不重新调用模型或计算 Gate。
- 新响应采用 Pydantic。认证主体来自服务端，不接收请求指定 owner；跨主体读取统一不可访问。
- 原 34 个 HTTP 操作的 URL、处理器和序列化行为保留，只补齐 OpenAPI 描述。原 7 个其他写操作仍被代理阻断。

## API 列表

| 方法 | 路径 | 内容 |
|---|---|---|
| POST | /api/investigations | 创建 / 幂等复用，202 |
| GET | /api/investigations/history | 所有者历史、分页、Overall 过滤、时间排序 |
| GET | /api/investigations/{id}/status | 真实 Stage / Overall、revision、取消与恢复标志 |
| GET | /api/investigations/{id}/trace | 已发生事件、Agent run、脱敏工具摘要 |
| GET | /api/investigations/{id}/artifacts | Investigation / Verification / Risk 公共投影 |
| GET | /api/investigations/{id}/integration | 原冻结 Gate 结果，保留全部 5 种状态 |
| GET | /api/investigations/{id}/answer | 已保存 AnswerEnvelope 的公共投影 |
| POST | /api/investigations/{id}/cancel | 原协作式取消；已完成状态不逆转 |

旧 `/api/v1/investigations` 仍只是历史提案，没有新建第二套接口。前端完整说明见 docs/PHASE12B_INVESTIGATION_API.md。

## Schema 与 OpenAPI

真实 OpenAPI 为 42 个 HTTP 操作。新增请求支持简化 InvestigationCreateRequest 和原 InvestigationRequest 两种互斥形状，映射原输入，不迁移业务协议。新响应和错误严格使用 Pydantic；旧响应标记 LEGACY_DESCRIPTION_ONLY，动态 JSON 字段仍为扩展对象。

全量 openapi.json、新 8 操作的完整独立 OpenAPI、调查 TypeScript 类型、客户端及 API inventory 已同步到 docs/frontend-contracts 和前端交接包 api/reference。独立 OpenAPI 含 info 和 HTTPBearer 定义，生成检查与 TypeScript 语义检查通过。历史提案/验证文件已注明适用基线，文件清单哈希已刷新。

## 安全与一致性

- 新接口统一 ApiError：error_code / message / request_id / retryable；不回显验证输入、堆栈或数据库信息。
- CORS 只允许显式 Origin；凭据不写入前端源码或构建变量。Artifact 移除原始工具/模型记录、内部配置，过滤嵌套凭据、带凭据 URL、Basic/Bearer 字符串及本机路径。
- Gate 前引用绑定根阶段 run、漏洞目标和 Artifact 交接；Gate 后读取原冻结输入。稳定的损坏引用报错，不修复或重新裁决。
- Trace 仅在根 revision 改变时进行有界重读；正常推进不被误报成稳定损坏，持续推进返回 SNAPSHOT_BUSY。
- 正常关闭保留未 ACK claim 的取消意图，晚到提交先取消，再交回 Orchestrator；沿用原协作控制。
- 使用校验官方归档摘要的 Gitleaks v8.30.1 扫描。新增代码阶段暂存改动扫描为 0 个候选；交付文件复扫的 2 个命中分别为旧/新 OpenAPI 文件 SHA256，已核对摘要，不是凭据。提交后按准确历史指纹处理该误报，并在推送前重扫。索引安全检查拒绝密钥、数据库、日志、依赖和临时 work 文件。

## 测试结果

| 检查 | 本次实跑结果 |
|---|---|
| 完整后端回归 | 1288 passed，0 failed / errors / skipped |
| 新增调查 API 用例 | 27，包含 11 个独立审查回归用例 |
| 可移植 CI 基线 | 423 passed；1 个真实缓存 Embedding 用例在该基线明确排除，完整回归已包含 |
| 前端现有测试 | 23 passed |
| 工程门禁测试 | 6 passed |
| TypeScript / JavaScript | tsc 通过；17 个 JS 文件语法检查通过 |
| Schema / 导出 | 42 操作、5 个原 Schema 组、40 个合成对象及 10 个导出文件检查通过 |

历史 1261 只是既有成绩；本轮完整回归重新执行了这 1261 项和新增 27 项。测试使用两个隔离的专用 PostgreSQL 库、离线 Embedding 缓存；B2 时间敏感用例仅调整执行顺序，没有改断言或删减用例。初次复跑的数据库隔离和历史用例导出目录前置条件问题已修正并复跑。

HTTP 闭环实际使用原 Orchestrator、数据库、工具、三专业 Agent 和 Gate，仅 Planner 模型使用受控 Mock。五种 Gate HTTP 枚举测试为受控 DTO 映射；没有编造五条完整 Agent 成功链，也没有生成业务准确率。合成 CVE / 资产明确为 SYNTHETIC_NOT_BENCHMARK。

## 修改文件

- 新增 backend/app/investigation_api/ 适配层、backend/app/api/investigations.py、openapi_contracts.py 和对应 API 测试。
- 增量接线 backend/app/main.py、frontend/server.mjs；增加 frontend/contracts/investigations.ts 和代理测试。
- 调整旧源码保护用例，仅放行 main.py 接线，原哈希基线未改变；增加旧 34 路由处理器一致性断言。
- 新增 scripts/export_investigation_api.py；CI 增加新 API 单元用例和导出一致性检查。
- 更新前端契约、交接文档、历史标识及 MANIFEST；原 258 个源码文件中仅 main.py 和 server.mjs 变更，其余 256 个原样保留。

## 当前限制

默认模型是 Mock，本轮不包括真实模型费用/质量评测。后台执行为单进程有界工作者，没有持久队列、跨实例自动恢复或多用户登录。旧响应只有 OpenAPI 描述增强；公共 Artifact 不是可重新执行的内部快照。数据库永久阻塞或进程强杀不能保证正常关闭。没有部署云端、开发 UI、SSE 或 WebSocket。

## 交付与停止

本分支提交 PR 到 main，保持人工审查，不自动合并队友代码。前端可按新 8 个 HTTP 契约开发和联调；本阶段完成后停止，等待下一阶段指令。

# AegisAI 队友接入与文档交接

仓库用于团队源码协作；前端交接包在 `AegisAI_FRONTEND_HANDOFF_PACKAGE/`，ZIP 在仓库根目录。这里没有线上网站或共享开发数据库。

## 仓库负责人：添加队友

1. 打开本仓库 GitHub 页面，进入 **Settings → Collaborators / Manage access**。
2. 选择 **Add people**，输入队友的 GitHub 用户名并发送邀请。
3. 队友接受邀请后，用自己的 GitHub 账号访问、下载或克隆私有仓库。
4. 将仓库链接和下面的交接入口发给队友，不需要分享自己的 GitHub 密码。

GitHub 邀请需要队友用户名；本次上传不代替邀请，也没有向未知用户发送通知。

## 队友先读什么

1. [交接包 README](../AegisAI_FRONTEND_HANDOFF_PACKAGE/README.md)
2. [前端快速入门](../AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/FRONTEND_QUICK_START.md)
3. [页面需求](../AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/UI_REQUIREMENTS.md)
4. [当前 API 状态](../AegisAI_FRONTEND_HANDOFF_PACKAGE/api/API_STATUS.md)
5. [完整前后端契约](../AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/FRONTEND_TEAM_HANDOFF.md)
6. [组件计划](../AegisAI_FRONTEND_HANDOFF_PACKAGE/design/COMPONENT_PLAN.md) 与 [演示流程](../AegisAI_FRONTEND_HANDOFF_PACKAGE/docs/DEMO_FLOW.md)

建议先整目录复制交接包的 `contracts/`，然后用 `mock/` 同一个 scenario 做结果视图。示例都是合成测试回执或 Schema Mock，界面要持续保留标签。

## 获取源码与分支协作

接受邀请后，在 GitHub 点 **Code** 获取 HTTPS 克隆地址，或用 GitHub Desktop 克隆。命令行示例中地址必须替换为页面实际地址：

```text
git clone <仓库页面的HTTPS地址>
cd AegisAI
git switch -c frontend/你的功能名称
```

每次开始工作先同步主分支；每人使用自己的功能分支，通过 Pull Request 说明改动、界面效果和验证结果，再由团队审查合并。不要把队友的未提交修改直接覆盖。

不需要重新建后端、重写 Agent 或另造 DTO。当前前端是原生 JavaScript ESM；团队如采用 TypeScript/其他框架，先讨论迁移范围，协议继续复用。

## 现在能开发和联调什么

- 可以直接做明确 Mock 模式下的完整调查 UI，以及七页布局、字段和异常状态。
- 有可用后端环境和权限时，可接漏洞/证据/资产风险/复核读取、旧问答及系统状态 API。
- 完整 Phase 11-D 调查的提交、状态、Trace、Artifact、Gate、Answer、取消和历史 API 尚未开放；Phase 12-B 仍是待实施计划。
- 旧 `/api/v1/assistant/query` 与新调查协议分开，不能把旧答案强制转换成 AnswerEnvelope。
- 7 个现有写操作被当前前端代理阻断；新调查 URL 是提案，不是可以立即调用的接口。

## 本地环境的边界

仓库包含代码、配置模板、迁移、测试、设计与文档，不包含现有开发数据库、虚拟环境、下载模型、Git/CVE 缓存和本机日志。安装依赖或恢复数据库需要队友自己的环境；下载 ZIP 不会取得开发者电脑上的数据。

历史报告文档保留；原始 HTTP 抓包/运行 JSON、云账号与短信截图、聊天原始 Word 附件保留在开发者本机，不作为协作输入上传。交接包中的脱敏 JSON、Schema 和 Mock 示例仍完整提供。

只看前端源码时，可在自己的 Node 环境进入 `frontend/` 执行 `npm start`，页面默认在 `http://127.0.0.1:8769/dashboard`，需要另有本机 8000 后端；这个命令不启动数据库或后端。离线 Mock 页面可先在队友自己的工程开发。

需要完整后端时，使用 Python 3.12 和 PostgreSQL + pgvector。配置模板在 [backend/.env.example](../backend/.env.example)，应用从环境变量读取，不自动加载 `.env`。先设置自己的数据库 URL，再运行 Alembic 迁移和 API。已有 Compose 是开发配置，不能据此声称生产部署或 Docker 构建已经验收。

原 `backend/scripts/local_database.py`、`test_postgres.py` 和 `scripts/start-local-demo.ps1` 依赖开发者本机 `work/postgresql_runtime.json` 与便携 PostgreSQL 缓存，**不能在新电脑直接当通用一键启动脚本**。队友使用自己安装的 PostgreSQL/受控开发环境，按契约联调，不复制数据库目录。

单元/接口测试如涉及数据库，必须配置专用测试库；不要把测试 URL 指向实际开发数据。历史兼容测试需要的纯文件哈希基线 `work/orchestration/baseline_hashes.json` 已纳入仓库，其他 work 内容保持本地。

凭据由负责人在必要的本机环境配置，不通过仓库、截图或交接 JSON 传递。`.gitignore` 已排除相关本机文件。

## 团队反馈格式

联调问题记录：页面、方法/路径、范围、字段、HTTP 状态、业务状态、复现步骤和脱敏截图。缺 API 标 `API_NOT_EXPOSED`，缺字段/统计标 `BACKEND_REQUIRED`，代理阻断标 `PROXY_BLOCKED`。复用真实状态和原引用，不靠前端补造安全结论。

本仓库上传属于协作准备；没有实施新功能、部署公开网站或重跑历史 1261 项全量测试。

# 本地开发与基础 CI

推荐 Python 3.12 和 Node 24。正式后端是 FastAPI/Pydantic/SQLAlchemy + PostgreSQL/pgvector；现有前端是原生 JavaScript ESM，不是 React/Vue/TypeScript 应用。具体页面及接口先读 [交接入口](../AegisAI_FRONTEND_HANDOFF_PACKAGE/README.md)。

## 先跑不依赖数据库的检查

以下 Windows PowerShell 命令在仓库根目录运行；创建环境后始终明确使用其中的解释器，避免把依赖装入系统 Python。

~~~text
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .github/requirements-ci.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests/engineering -v
.\.venv\Scripts\python.exe scripts/ci/check_repository.py
.\.venv\Scripts\python.exe scripts/ci/run_backend_tests.py
.\.venv\Scripts\python.exe scripts/ci/check_contracts.py
node scripts/ci/check_frontend.mjs
npm ci --prefix .github --ignore-scripts --no-audit --no-fund
node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json
npm --prefix frontend test
~~~

Linux/macOS 将上述 Python 路径替换为 .venv/bin/python。现有前端没有依赖安装或 build 脚本；独立 .github 工具只安装契约编译器，不改变应用。

## CI 究竟检查什么

| 检查 | 范围 | 不能证明 |
|---|---|---|
| Repository safety | Git 索引敏感路径、工程失败门禁、Gitleaks 历史扫描 | 没有任何类型的潜在风险 |
| Backend unit and contracts | scripts/ci/run_backend_tests.py 明确列出的便携测试；Pydantic/OpenAPI/导出副本；AegisBench 离线框架检查 | 全量历史回归、数据库集成、真实模型准确率 |
| Backend PostgreSQL critical regression | 两个独立 PostgreSQL 17 测试服务；迁移、采集富化、单/多资产 HTTP、冲突、取消和缺上下文的受控测试 | 全量后端、真实模型效果、生产数据验证 |
| Frontend tests and types | 当前 JS 语法、前端测试及导出契约 TS 编译（数量以该次日志为准） | 七页视觉/E2E 验收、应用 build、线上部署 |

http-data-columns 是手工 ORM 列形状映射：本 CI 验证其 JSON Schema 合法及两个副本一致，**没有把它当作 Pydantic HTTP 响应或数据库迁移一致性验收**。

portable baseline 的明确选择在 scripts/ci/run_backend_tests.py。真实缓存 embedding 测试 test_cached_real_local_embedding_through_gateway 被显式排除，因为新机器没有该模型；不将其算作通过。数据库测试不在该集合。收集阶段遇到已知数据库 fixture 会直接拒绝，防止误连测试或开发库。

CI 的最小 Python 依赖保存在 .github/requirements-ci.txt，版本与已有后端依赖一致，省去模型推理包；运行完整后端时使用 backend/requirements.txt。依赖变更须同时审查安装和 Schema 兼容性。

本阶段实际 TypeScript 编译发现旧 JsonValue 使用递归 Record 导致 TS2456；四份类型文档改用等价索引签名，字段/API 不变。独立 contracts-smoke.ts 还验证嵌套 JSON 可接受，undefined、函数和 Date 对象不能直接成为 JSON 字段；交接 ZIP 和校验清单同步更新。历史“仅 Node 类型语法检查”记录保留，新 TypeScript 编译记录单独标注。

## 运行应用

前端目录 npm start 默认启动 8769，需要另行启动本机 8000 后端。8768 是历史 Mock 原型。

后端环境必须自己准备 PostgreSQL + pgvector，安装完整后端依赖，设置本机 AEGIS_DATABASE_URL 后执行已授权迁移，再从 backend 启动 uvicorn app.main:app。配置示例 .env.example 不会自动加载。已有便携 PostgreSQL 脚本依赖开发者本机 work/postgresql_runtime.json，不能作为新电脑一键安装方案。

PostgreSQL CI 已执行关键迁移和数据库回归。完整后端验收使用 [DATABASE_REGRESSION.md](DATABASE_REGRESSION.md) 的 --full 入口，只允许两个独立、空的 aegis_phase5_test 实例；不可将测试配置指向开发或演示数据。本机启动、重启检查和受控调查闭环命令见 [BACKEND_DEMO_STABILITY.md](BACKEND_DEMO_STABILITY.md)。

## API 与下一阶段

PR #6 已把 Phase 12-B 的 8 个调查 API 合入 main，现在共 42 个 HTTP 操作，现有代理放行 35、阻断 7 个原有写操作。公共 DTO、OpenAPI、TypeScript Client 及说明已导出；先读 [调查 HTTP API](PHASE12B_INVESTIGATION_API.md)。

默认 Mock 不支持 PlannerPlan，服务健康不能证明自主调查可完成。真实模型调用、受控合成闭环和 AegisBench 正式评测分别记录；不把内部 Context 当公共响应，不把 Mock 结果当标准答案。AegisBench 框架和 49 题已存在，人工 APPROVED 仍为 0；真实模型评测和正式 Live/Replay 演示产品仍待后续阶段。

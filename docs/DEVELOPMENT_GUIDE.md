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
| Backend unit and contracts | 当前 398 项无数据库测试；OpenAPI 和五组 Pydantic Schema 的两个副本一致；40 个合成请求/状态/Trace/答案验证 | 全量 1261 项重跑、数据库集成、真实模型准确率 |
| Frontend tests and types | 17 个 JS 文件语法、21 项现有测试、两个契约 TS 目录及原 d.ts 编译 | 七页视觉/E2E 验收、应用 build、线上部署 |

http-data-columns 是手工 ORM 列形状映射：本 CI 验证其 JSON Schema 合法及两个副本一致，**没有把它当作 Pydantic HTTP 响应或数据库迁移一致性验收**。

portable baseline 的明确选择在 scripts/ci/run_backend_tests.py。真实缓存 embedding 测试 test_cached_real_local_embedding_through_gateway 被显式排除，因为新机器没有该模型；不将其算作通过。数据库测试不在该集合。收集阶段遇到已知数据库 fixture 会直接拒绝，防止误连测试或开发库。

CI 的最小 Python 依赖保存在 .github/requirements-ci.txt，版本与已有后端依赖一致，省去模型推理包；运行完整后端时使用 backend/requirements.txt。依赖变更须同时审查安装和 Schema 兼容性。

本阶段实际 TypeScript 编译发现旧 JsonValue 使用递归 Record 导致 TS2456；四份类型文档改用等价索引签名，字段/API 不变。独立 contracts-smoke.ts 还验证嵌套 JSON 可接受，undefined、函数和 Date 对象不能直接成为 JSON 字段；交接 ZIP 和校验清单同步更新。历史“仅 Node 类型语法检查”记录保留，新 TypeScript 编译记录单独标注。

## 运行应用

前端目录 npm start 默认启动 8769，需要另行启动本机 8000 后端。8768 是历史 Mock 原型。

后端环境必须自己准备 PostgreSQL + pgvector，安装完整后端依赖，设置本机 AEGIS_DATABASE_URL 后执行已授权迁移，再从 backend 启动 uvicorn app.main:app。配置示例 .env.example 不会自动加载。已有便携 PostgreSQL 脚本依赖开发者本机 work/postgresql_runtime.json，不能作为新电脑一键安装方案。

本阶段不执行迁移或数据库测试。需要集成验收时只允许专用 aegis_phase5_test 数据库，并使用对应测试脚本/fixture；不可将测试配置指向开发数据。

## API 与下一阶段

现在是 34 个真实 HTTP 操作，现有前端代理放行 27、阻断 7 个写操作。Phase 11-D 的提交调查、状态、Trace、Artifact、Gate、Answer、取消、历史接口仍为 API_NOT_EXPOSED；Phase 12-B 尚待实施。前端先按已冻结 Mock/契约开发，新 API 开放后同步公共 DTO 与对接说明。

真正开展 Phase 12-B 时，受影响冻结文件和契约需要显式审查；不能为了过 CI 删除旧兼容检查或把内部 Context 当公共响应。AegisBench、真实模型评测和 Live/Replay 仍为后续单独阶段。

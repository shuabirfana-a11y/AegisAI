# Phase 12-C 联调实施计划

> 执行方式：使用 writing-plans / executing-plans，在当前工作树内顺序实施；完成后做一次独立审查。

**目标：** 验证现有八个调查 HTTP 操作、真实内部执行链和前端契约；明确模拟模型与真实来源数据的边界。

**基线：** AegisAI / origin/main `8e0bfe6bd398d26fc7270e5f0b5aeb6d03d354fd`，工作分支 `feature/phase12c-http-integration`。

**架构：** 只增加联调检查工具、固定场景、测试与文档。HTTP 检查复用现有 Pydantic 公共响应 Schema；成功闭环复用现有测试场景和实际服务，并通过本机 TCP 端口执行。

**技术：** Python、httpx、Uvicorn、Pydantic、现有 TypeScript API Client。

## 范围与约束

- 不修改 `backend/app/`、Planner、Runtime、三个 Agent、Gate 或前端页面。
- 不将模拟答案、测试库证据或模型配置检查计为真实模型效果或正式 Benchmark。
- 只在专用 `aegis_phase5_test` 库使用合成测试输入；开发库只读取真实数据并创建调查记录。
- 不写标准答案，不改 49 题，不推送密钥，不部署公网。
- main 合并仍遵循负责人确认规则。

## 审查重点

- 请求 REAL 但服务实际为 Mock 时必须明确失败，不自动降级。
- 失败链路不应被包装成八个成功结果或完整调查成功。
- 轮询有期限；未完成时不得假冒终态或自动取消用户调查。
- 检查工具只允许显式本机 HTTP 地址，不跟随重定向或输出令牌。
- Answer 读取不重新调用模型；取消和错误响应保持现有语义。

## 任务 1：固定场景与 HTTP 检查

- [x] 先添加检查工具的模式、地址和固定场景测试，运行并确认缺少工具时失败。
- [x] 新增 `backend/scripts/probe_investigation_http.py`，读取固定请求，有限轮询并验证八个操作的实际响应 Schema。
- [x] 新增 `demo/phase12c/real-source-case.json` 和说明；使用已在本地来源数据中存在的 CVE-2025-32434 / torch 2.5.1，不预填答案。
- [x] 运行纯检查测试；记录真实来源 + 默认 Mock 的实际失败。

## 任务 2：TCP 闭环与模型配置准备

- [x] 新增 `backend/tests/investigation_api/test_tcp_chain.py`，复用既有合成输入和 Model Gateway，启动独立临时端口。
- [x] 实际验证 Planner、三个 Agent、工具记录、Artifact、Gate、冻结 Answer 和八个 HTTP 操作。
- [x] 验证失败、模式不匹配和运行中取消；不改业务执行逻辑。
- [x] 补充已有 `backend/.env.example` 的兼容远程 / 国产 / 本地配置说明；仅验证配置，不调用外部模型。

## 任务 3：当前交接契约与交付

- [x] 更新 `docs/FRONTEND_HANDOFF.md`，移除当前规范中已过期的调查 API_NOT_EXPOSED 描述，保留尚未实现的缺口。
- [x] 同步队友交接包当前文档、清单与 ZIP，保留历史验证记录并明确历史含义。
- [x] 更新 `CURRENT_STATUS.md`，生成 `PHASE_12C_RESULT.md`，区分历史 1261 与本次实际测试。
- [ ] 运行回归、OpenAPI/TypeScript 一致性检查、敏感信息检查；完成独立审查后提交 PR。

验收后停止，不进入真实模型效果评测、正式 AegisBench 或公网部署。

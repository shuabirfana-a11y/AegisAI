# AegisBench HTTP 评测准备 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 用户已提供实施设计及授权，本轮采用当前会话内执行与一次最终独立审查。

**Goal:** Question → Investigation API → 冻结 AnswerEnvelope → 原人工准入/指标，支持 Online 和 Offline。

**Architecture:** 新 HTTP Adapter 负责正向输入与真实响应采集、引用验证、原生结果投影。现有 bench runner、Metric、记录回放复用，新增模式及批准准入包装。核心后端及已有标注数据不变。

**Tech Stack:** 现有 Python/Pydantic/httpx/FastAPI；现有 PostgreSQL 仅用于隔离工程控制。

**Spec:** docs/superpowers/specs/2026-10-12-aegisbench-http-evaluation.md

## Global Constraints

- 基线 main 59ea2a239556e70514ce19bba52141121a98d570；不合并队友分支，不改 Agent/Runtime/Gate。
- 不改49题/标准答案/人工状态；未批准样本不执行线上调查或正式打分。
- 只通过公开 API，不直接 Orchestrator、数据库或模型 SDK。
- 失败、缺失、未知、冲突保留；NoVerification 控制不作为生产绕过开关。
- 既有默认 CLI/CI、严格人工 gold/OutcomeAudit、哈希回放规则保留。

## Review Focus

1. 响应 ID、模型模式和事实来源错配时不得接受为完整链。
2. 嵌套标注字段、问题 ID 标签、操作者版本覆盖不得污染模型输入。
3. 非批准和合成材料不得产生正式质量；有效引用不能冒充人工语义复核。
4. 网络超时、重定向、失败取消、无风险结果不能被改成正确 UNKNOWN 或丢掉。
5. 回放记录被篡改、数据范围变化、多资产范围不适配必须明确拒绝。

### Task 1：HTTP 输入/输出适配

Files: evaluation/bench/http_investigation.py（新增）；tests/aegisbench/test_http_investigation.py（新增）。

Interfaces: build_request(question: Question, binding: dict|None) -> dict；InvestigationHTTPAdapter.run(question,sources) -> Prediction，records 保存脱敏公开响应，不持有 Annotation。

- [ ] 写失败测试：新接口缺失、问题/资产版本、禁止字段/标签、未知/失败输出。
- [ ] 实跑失败，确认因缺功能。
- [ ] 正向请求投影、HTTP生命周期、真实 Schema/引用验证、原生风险/版本观察投影、有限超时与取消。
- [ ] 测试响应 ID 错配、被阻断的风险不变确定答案、过长问题/多资产拒绝。
- [ ] 目标测试通过，提交；不触碰 Metrics 或业务模块。

### Task 2：两模式与人工准入/报告

Files: evaluation/bench/e2e.py（新增）；evaluate.py（小范围模式分发）；tests/aegisbench/test_e2e.py（新增）。

Interfaces: evaluate_http(data, adapter, run_id) -> report，批准 ID 包装再调用原 evaluate_dataset；main(argv) 与旧 CLI 独立。离线使用 recorded_adapters 校验完整链报告和 experiment hash。

- [ ] 写失败测试：0 approved 无网络、单条获准控制、hash回放、模式分发。
- [ ] 实跑失败。
- [ ] 人工准入包装/不可用 Baseline、实际 Trace 模型/Prompt 配置、原报告和风险/拒答列。
- [ ] 标签仅准入元数据/最后比较；不写标注；原默认入口不变。
- [ ] 测试失败样本/Mock标识/篡改/已有输出保护与敏感信息处理，全部 AegisBench 测试通过。

### Task 3：完整 API 控制与交付

Files: backend/tests/investigation_api/test_bench_http.py（新增）；evaluation/ground_truth/schema.md（仅说明）；docs/phase13d-e2e、PHASE_13D_RESULT.md、CURRENT_STATUS.md。

- [ ] 新完整 HTTP 控制：现有 scenario + 原 create_app + 真实本机 TCP + Mock Planner；断言3 Agent、新观察、Gate、冻结答案与请求隔离。该材料为 SYNTHETIC_NOT_BENCHMARK。
- [ ] 保留原人工模板，说明原生字段与审批/输出语义审核两个门禁；导出 Adapter Schema。
- [ ] 实际49题0 approved 的准备命令，仅输出 NOT_EVALUATED 与缺口；不调用模型。
- [ ] 执行全部 AegisBench、针对性 DB/HTTP、便携后端/契约/前端/工程检查。验证 backend/app 与题目/标注文件字节不变。
- [ ] 一次独立审查，修复实质问题（RED→GREEN）；记录实际结果、限制、Baseline不可用/数据一致性未证明。
- [ ] 上传独立草稿 PR，文件夹交付；停止，不自动合并本轮新 PR。

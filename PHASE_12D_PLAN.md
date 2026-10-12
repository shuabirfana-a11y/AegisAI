# Phase 12-D：真实模型 Provider 联调与前端接入准备 Implementation Plan

> **For agentic workers:** 使用 `superpowers:executing-plans` 在当前会话逐项实施。以下复选项均为待实施事项。本文件只完成审查和规划；用户本阶段明确要求“确认后实施”，未确认前不下载、不安装、不修改运行配置或业务代码。

**Goal:** 利用现有 Model Gateway 接入本机免费模型，验证实际结构化规划和调查 HTTP 链路，同时保持 Mock 测试、确定性答案及既有业务规则稳定。

**Architecture:** Planner 仍经 Model Gateway → OpenAI Compatible Adapter 调用模型。Ollama 仅提供本机兼容 HTTP 服务，不新增模型 SDK 或 Agent 框架。只增加运行辅助、联调检查及读取已保存模型调用身份的 HTTP 投影；核验、风险、Gate 与答案事实仍由已有实现决定。

**Tech Stack:** Windows、PowerShell、现有 Python 环境、FastAPI/Pydantic、httpx 0.28.1、Ollama Windows 独立运行包、Qwen2.5 7B Q4_K_M、现有 PostgreSQL 和 TypeScript 契约导出工具。

**Spec:** 本会话用户《AegisAI Phase 12-D：真实模型 Provider 联调与前端接入准备 Prompt》及选择“本地免费模型（推荐，需要下载）”；已有基线见 `PHASE_12C_RESULT.md`、`docs/FRONTEND_HANDOFF.md`。

## Global Constraints

- 项目仅为 AegisAI / ICT 命题九，不进入 SentinelGraph、恒脑或 Dify。
- 不修改 Agent 业务逻辑、Runtime、Planner 提示词/验证规则、Integration Gate、风险规则或 Evaluation 框架。
- 不迁移既有 Embedding 调用点，不新建数据库表、迁移或 HTTP 路由。
- Mock 保留用于 CI；本机真实模型联调需单独显式运行，不让 CI 下载模型或依赖 GPU。
- 使用现有环境变量，密钥不得进入源码、Git、前端或公开日志。
- 真实调用失败须记录失败；不得悄悄用 Mock、预生成计划或预生成答案替代。
- 不填写或批准 Ground Truth，不运行正式 AegisBench，不输出安全准确率，不进行公网部署。
- 完成本阶段后停止；本阶段没有新的关机指令。

## Review Focus

1. 在工作树没有 `.venv`、已有服务占用端口或启动失败时，应明确失败并保留原服务；Task 1 以启动检查和清理测试覆盖。
2. 切换供应商后历史调查仍显示当时保存的模型调用身份，未产生调用记录时不推断已经运行真实模型；Task 2 覆盖双向切换、待规划和重用。
3. 模型返回合法 JSON 但任务类型、工具权限或 DAG 不合法时仍不能执行；Task 3 复用真实 Planner 验证并检查拒绝与两次尝试上限。
4. 冷启动、超时和中途取消不能被写成成功，旧成功报告不能残留为本轮结果；Task 1/3 覆盖限时、失败覆盖和协作取消语义。
5. 真实文本模型与 Mock Embedding 混合时不得声称全链真实化，模型文本也不能改变冻结事实；Task 3/4 覆盖模式分列、只读答案和契约脱敏。

---

## 1. 当前审查结果

### 仓库与依赖

- Remote：`https://github.com/shuabirfana-a11y/AegisAI.git`，私有仓库。
- 稳定 main：`8e0bfe6bd398d26fc7270e5f0b5aeb6d03d354fd`。
- Phase 12-C 基线：`8198bd8d641604b8ee05f1478952416d3152fb53`。PR #8 本次检查仍为 OPEN，尚未合并；此前 CI 通过不能当作已合并。[PR #8](https://github.com/shuabirfana-a11y/AegisAI/pull/8)
- 当前独立本地分支：`feature/phase12d-model-provider`，基于上述 Phase 12-C 提交。原 main 与 Phase 12-C 分支保持原提交。
- 本计划复用已附加工作树，不重新初始化 Git，不改 remote，不覆盖队友分支。后续 PR 须注明依赖 PR #8，未经授权不自动合并任一 PR。

### Model Gateway 已有能力

| 能力 | 当前实际情况 | 本阶段处理 |
|---|---|---|
| 统一方法 | `generate_text`、`generate_structured`、`embed`、`health_check` 已实现 | 直接复用 |
| Provider | mock、openai_compatible、local_embedding | 不新增 Ollama 专用 Provider |
| 兼容协议 | `/chat/completions`、`/embeddings`、`/models`，httpx 同步调用 | 本机 Ollama 走已有 `/v1` 适配 |
| 结构化输出 | prompt_json/json_object/json_schema 显式配置，严格 JSON + JSON Schema + Pydantic 校验 | 使用 json_schema，验证真实兼容性 |
| 超时 | `MODEL_TIMEOUT_SECONDS` 1–60 秒；连接超时另有上限 | 保留限制，不加大 Runtime 预算 |
| 重试 | Adapter 无自动重试；现有 Planner 总共最多两次尝试 | 不叠加新的重试层 |
| 错误 | 认证、限流、超时、网络、非法 JSON、截断、拒绝等有明确错误码 | 扩充联调覆盖，不掩盖错误 |
| 审计 | request_id/provider/model/function/token/duration/status/error/is_mock | 保留既有调用记录 |
| 内部诊断 | Planner 可保存受限原始输出供内部排障 | 不导出到前端或公开报告 |
| Embedding | 独立 Provider 可配置；既有检索调用点尚未全部迁移 Gateway | 本阶段不迁移，不启用新 Embedding 模型 |

`ModelConfig.from_env()` 只读进程环境，不自动加载 `.env`。实际变量为 `MODEL_TIMEOUT_SECONDS`，不是示例中的 `MODEL_TIMEOUT`。API Key 是 `SecretStr`，配置禁止作为公开对象直接序列化。

API 的创建响应已有 `model_provider` 和 `is_mock`，但当前由服务配置生成；它们不能独立证明历史调查实际用了哪个模型。持久化的 `PlannerRunTrace.model` 与 `attempts[].model_call` 可用于只读确认；公共 Trace 当前未暴露这部分身份。

### Answer Composer 的边界

现有 `AnswerComposer` 是确定性模板；`AnswerEnvelope.explanation_provider=DETERMINISTIC_TEMPLATE`、`fact_origin=FROZEN_GATE_CONTEXT`。它没有模型调用点。本阶段不新建 LLM 答案生成器，不改它的事实、风险或 Gate 状态。用户要求的 Composer 验证落实为：真实 Planner 接入后仍生成/读取已有冻结答案，重复 GET 不增加模型调用。

另通过独立 `generate_text()` 验证模型文本能力；该文本只是联调输出，不进入正式 AnswerEnvelope、不作为安全结论。

### 本机条件与尚未完成事项

- 本次只读检查：约 15.2 GiB RAM，RTX 5060 Laptop GPU，`nvidia-smi` 显示约 8151 MiB 显存，C 盘剩余约 413 GiB。
- 未发现可调用的 Ollama/LM Studio 服务，未发现配置好的模型 Key。本次没有下载模型，也没有真实模型调用。
- 规划前检查实际执行：Model Gateway 测试 **88 passed / 1 deselected**；排除项为缓存真实 Local Embedding 测试。`scripts/export_investigation_api.py --check` 确认 **10 份导出一致**。
- Phase 12-C 的 481 项通过是上一阶段历史结果；本阶段不能写成已经再次全部运行。

## 2. 选型和配置决定

使用 Ollama 的 Windows 独立运行包，模型基础 tag 为 `qwen2.5:7b-instruct-q4_K_M`。官方模型页列出约 4.7 GB 模型体积；运行时、缓存和上下文还需要额外空间/内存。硬件检查支持进行本机试跑，但尚不能保证全 GPU 驻留、响应速度或计划生成成功率。[官方模型页](https://ollama.com/library/qwen2.5:7b-instruct-q4_K_M)

Ollama 官方提供包含 CLI 和 GPU 依赖的 Windows 独立 zip，可在用户目录运行。确认实施后从官方发布源读取具体版本、下载该版本包并记录 URL/SHA-256/版本；不使用第三方安装包，不安装 Linux、WSL 或 Docker。[Windows 官方说明](https://docs.ollama.com/windows)

本机模型别名为 `aegisai-qwen25-planner`，Modelfile 仅包含：

```text
FROM qwen2.5:7b-instruct-q4_K_M
PARAMETER num_ctx 16384
```

16K 上下文用于承载现有完整 Planner 提示、工具 Schema 与输出，仍需实际核对 token 和内存。若 OOM、上下文不足或超时，记录阻塞与实际运行条件，不自行下载更大模型、改验证规则或上云。Ollama 的 OpenAI 兼容 API 不提供统一的每请求上下文设置，因此通过本地别名设置上下文。[兼容接口说明](https://docs.ollama.com/api/openai-compatibility)

运行目录在 `%LOCALAPPDATA%/AegisAI/ollama-runtime/`，模型在 `%LOCALAPPDATA%/AegisAI/models/`，不进入 Git。模型进程仅监听 `127.0.0.1:11434`；设置 `OLLAMA_NO_CLOUD=1`、`OLLAMA_NUM_PARALLEL=1`、`OLLAMA_MAX_LOADED_MODELS=1`。只在专用子进程环境中设置，启动后不修改机器/用户永久环境。[Ollama FAQ](https://docs.ollama.com/faq)

REAL 配置精确采用：

```ini
MODEL_PROVIDER=openai_compatible
MODEL_NAME=aegisai-qwen25-planner
MODEL_API_BASE=http://127.0.0.1:11434/v1
MODEL_API_KEY=
MODEL_ALLOW_KEYLESS_LOCAL=true
MODEL_TIMEOUT_SECONDS=60
MODEL_MAX_OUTPUT_TOKENS=4096
MODEL_STRUCTURED_MODE=json_schema
MODEL_TOKEN_PARAMETER=max_tokens
MODEL_EMBEDDING_PROVIDER=mock
MODEL_EMBEDDING_NAME=mock-embedding-v1
MODEL_EMBEDDING_DIMENSION=384
```

本机无 Key 是既有 Adapter 显式允许的 loopback 分支，不填假 Key。REAL 表示实际使用非 Mock 文本 Provider，不表示检索/Embedding 全真实，也不表示回答准确。

MOCK 配置使用 `mock / mock-text-v1` 与 `mock / mock-embedding-v1 / 384`，不继承 REAL 的地址或 Key。默认 Mock 没有合法 PlannerPlan 回执；此前会 `PLANNING_FAILED`。本阶段保留这个诚实行为，不为普通调查注入隐藏成功 fixture。

如果 Ollama 对现有 Schema 的 json_schema 模式不兼容，先保存兼容失败结果；只允许显式改变运行配置并重新记录实验，不偷偷切模式。本计划不修改 Provider/Gateway 核心实现，发现真实协议缺口时须先给出最小修订范围。

## 3. 文件范围

| 文件 | 动作/职责 |
|---|---|
| `scripts/setup-local-model.ps1` | 新增：官方独立运行包获取、模型拉取/别名、有限准备检查；下载/进程证明写到忽略目录 |
| `scripts/start-model-demo.ps1` | 新增：显式 MOCK/REAL 进程配置，复用已有启动脚本；不自动关闭未知进程 |
| `scripts/start-local-demo.ps1` | 最小扩展：可选 `PythonPath` 参数，默认路径不变，解决工作树没有 `.venv`；其他启动行为不重写 |
| `demo/phase12d/README.md`、`mock-profile.json`、`local-real-profile.json`、`Modelfile` | 新增：不含秘密的固定配置；说明配置文件不会被 ModelConfig 自动加载 |
| `backend/app/investigation_api/model_execution.py` | 新增：读取已持久化 Planner 调用身份，检查所有权和一致性 |
| `backend/app/investigation_api/schemas.py`、`service.py` | 增量：公共 Trace 的可选模型执行元数据；不改创建、调度或业务结论 |
| `backend/scripts/probe_model_provider.py` | 新增：只经 Gateway 的结构化/文本联调和现有 Planner 独立验证，白名单报告 |
| `backend/scripts/probe_investigation_http.py` | 最小扩展：在可用时按保存的 Trace 调用身份检查模式，保留原 CLI 和失败语义 |
| `backend/tests/model_gateway/test_local_profile.py`、`test_provider_probe.py` | 新增：配置、限时、错误、日志、Gateway 调用和报告测试 |
| `backend/tests/investigation_api/test_model_execution.py` | 新增：所有权、历史模式、待规划、失败调用、字段脱敏 |
| `tests/engineering/test_local_model_scripts.py` | 新增：路径/进程/配置恢复等启动辅助检查；不下载模型 |
| `scripts/ci/run_backend_tests.py` | 仅加入本次不依赖真实模型/DB的检查；DB测试单独本机运行 |
| `docs/FRONTEND_HANDOFF.md`、`docs/MODEL_PROVIDER_TEST.md`、`docs/phase12d/verification.json` | 同步契约、实际模型试跑和脱敏验收记录 |
| `PHASE_12D_RESULT.md`、`CURRENT_STATUS.md` | 实施后写实际成果、未完成项和本次实跑结果 |
| 契约导出及队友包 | 使用已有导出器生成的 10 份文件；对应 README、契约说明、MANIFEST 与交接 ZIP 同步 |

不修改 `backend/app/planner/`、`runtime/`、`agents/`、`integration/`、`orchestration/`、`llm/` 的业务实现或前端页面。测试和运行辅助按现有目录增量增加，不搬迁目录。

## 4. 实施任务

### Task 1：可复现的本机模型准备与双模式启动

**Interfaces:**
- `setup-local-model.ps1` 参数 `RuntimeRoot`、`ModelsRoot`、`PythonPath`；路径均解析为绝对路径，运行时/模型默认在上述 LOCALAPPDATA 目录。
- `start-model-demo.ps1` 参数 `Mode`（MOCK/REAL）、`PythonPath`；消费 `demo/phase12d/*-profile.json`，只传递已列出的模型变量。
- `start-local-demo.ps1` 增加可选 `PythonPath`，未指定时仍查原项目 `backend/.venv/Scripts/python.exe`。
- 产出忽略目录 `work/phase12d/runtime-receipt.json`：安装来源、版本、包哈希、模型 tag/摘要、GPU、配置摘要、准备状态；不含 Key 或永久环境快照。

- [ ] **Step 1 — 测试：** 新增 `test_missing_python_does_not_start_services`、`test_occupied_port_does_not_stop_existing_process`、`test_local_profiles_are_valid_and_embedding_stays_mock`、`test_environment_is_restored_after_start_failure`；断言退出失败时没有新遗留进程、原服务仍存在、配置通过现有 `ModelConfig.from_env()`。
- [ ] **Step 2 — RED：** 运行 `python -m unittest discover -s tests/engineering -p test_local_model_scripts.py -v` 及 `python -m pytest tests/model_gateway/test_local_profile.py -q`（第二条在 backend 目录）；确认失败来自尚未实现的新增辅助。
- [ ] **Step 3 — 最小实现：** 下载来源限定官方发布包，保存/核对 SHA-256；zip 成员限制在运行目录，不覆盖其他文件。已有同版本包和模型可复用；不同版本不强删。下载进度不得表示已通过服务健康检查。
- [ ] **Step 4 — 模型准备：** `ollama serve` 用隐藏子进程启动，只监听 loopback。服务已在 11434 时先核对 `/api/version`、模型列表和本机配置，不抢占/杀掉未知服务。拉取基础 tag、创建别名、记录实际版本；准备超时/失败停止本工具创建的子进程，保留可恢复下载缓存。单次拉取操作最多 30 分钟，等待分段不超过 60 秒并可报告进度。
- [ ] **Step 5 — 启动验证：** 模型预热经 Task 3 的 Gateway 文本调用，独立于调查 SLA。脚本拒绝已有 8000/8769 端口，不改变旧服务；确认当前运行实例空闲且 PID/程序/启动时间属于本项目后，才按已有进程记录重启为新模式。不能证明归属时报告占用，不强制结束。
- [ ] **Step 6 — GREEN / Commit：** 同样测试通过，再在本机检查隐藏进程、loopback、模型版本和失败清理。只提交本任务脚本、样例、测试；不提交包、模型或本机运行记录。Commit：`feat: prepare local model profiles and bounded startup`。

### Task 2：公开已保存的模型执行身份

**Interfaces:**
- `ModelExecutionMetadata(PublicModel)`：`execution_mode: Literal['MOCK','REAL']`、`provider: str`、`model: str`、`source: Literal['PERSISTED_PLANNER_CALL']`、`attempt_count: int`（1–2）。
- `TraceResponse.model_execution: ModelExecutionMetadata | None = None`，兼容旧消费者。
- `read_model_execution(engine, context: InvestigationContext, *, actor: str) -> ModelExecutionMetadata | None` 位于 `model_execution.py`；消费 `PlannerTraceStore(engine).read(context.planner_run_id, actor)`。
- `InvestigationApiService.trace()` 只读附加该字段，现有快照重试和状态/Stage逻辑保持原样。

- [ ] **Step 1 — 测试：** `test_mock_history_stays_mock_after_real_switch`、`test_real_history_stays_real_after_mock_switch`；保存实际 Planner 审计后换 service Gateway，断言历史 Trace 模式、provider、model不变。受控协议回执明确 SYNTHETIC_TEST，不能写成真实本机模型实验。
- [ ] **Step 2 — 测试边界：** `test_no_completed_call_means_unknown_metadata`、`test_failed_real_call_is_real_but_not_success`、`test_reused_investigation_uses_persisted_identity`、`test_unowned_planner_trace_cannot_be_read`、`test_identity_mismatch_is_not_repaired`、`test_public_metadata_has_no_secrets_or_raw_output`。
- [ ] **Step 3 — RED：** 在 backend 运行 `python -m pytest tests/investigation_api/test_model_execution.py -q`；DB部分只使用既有专用测试库，禁止修改项目真实调查或标注记录。记录未实现字段引起的失败。
- [ ] **Step 4 — 最小实现：** 缺 planner_run_id 或尚无持久化 attempt 时返回 null。对已有 attempt 用现有 `CallRecord` 检查 provider/model/is_mock 与被冻结 `PlannerRunTrace.model` 一致；不根据当前环境重新推断、不改旧 Trace。所有权/引用损坏沿用明确失败，不吞为 null。投影走 `public_copy`，只输出上述白名单字段。
- [ ] **Step 5 — 文档语义：** 创建响应的旧 `model_provider/is_mock` 保持兼容，文档说明它反映当时服务配置；历史标签以 `trace.model_execution` 为准。该字段证明保存的调用身份，不能证明调用成功、答案质量或全检索链真实化。null 显示“模型调用尚未确认”，不能默认 REAL 或 Mock。
- [ ] **Step 6 — GREEN / Commit：** 上述测试和现有 API 回归通过；Schema可验证新增字段/null；无新数据库迁移。Commit：`feat: expose persisted planner model identity in public trace`。

### Task 3：真实 Provider、实际 Planner 与 HTTP 调查验证

**Interfaces:**
- 复用 `ModelGateway.health_check()`、`generate_text(TextRequest)`、`generate_structured(StructuredRequest, output_model=...)`，不直接调用 Ollama/OpenAI模型接口。
- `probe_model_provider.py` 定义 `ProviderProbeReport(BaseModel)` 与 `run_provider_probe(gateway: ModelGateway, planner_inputs: tuple[PlannerInput, ...]) -> ProviderProbeReport`。
- 规划验证消费 `LLMTaskPlanner(gateway, trace_sink).plan(input, build_context(...))`，实际 `PlannerPlan`、现有 whitelist/DAG/权限验证全部复用。probe的 sink 仅保留本次检查记录；正式调查 Trace 仍由原 Orchestrator 持久化。
- CLI：`--case demo/phase12c/real-source-case.json --mode MOCK|REAL --output work/phase12d/provider-report.json`；Python环境明确指定，不隐式加载 `.env`。
- 产出白名单：provider/model/is_mock、requested/observed mode、request_id、耗时、token使用（未知保留 null）、JSON/规划通过数和分母、错误码、prompt/schema版本、benchmark=false、text/embedding Provider分别标识。

- [ ] **Step 1 — 失败测试：** `test_probe_calls_gateway_not_model_sdk`、`test_invalid_json_does_not_execute_plan`、`test_unknown_task_and_forbidden_tool_are_rejected`、`test_planner_attempts_are_at_most_two`、`test_timeout_empty_and_truncated_response_are_reported`、`test_failed_probe_overwrites_previous_success`、`test_probe_deadline_stops_only_owned_worker`。受控 httpx响应沿用现有Adapter测试，不伪装为真实模型回执。
- [ ] **Step 2 — RED：** 在 backend 运行 `python -m pytest tests/model_gateway/test_provider_probe.py -q`，确认失败点来自缺失的probe行为。
- [ ] **Step 3 — 最小实现：** 先健康检查，再一次固定文本预热、5次固定小型结构化输出检查（CVE/risk/evidence Schema，仅协议检查），再两种实际Planner输入：纯CVE查询、固定torch2.5.1影响/补丁/证据查询。每个规划最多沿用现有2次尝试；Gateway不新增重试。任一次失败如实记录，不能将非法计划补字段后当模型输出。
- [ ] **Step 4 — 限时：** HTTPX现有限时是网络阶段/无活动限时，不声称它等于整个请求的绝对时限。probe的单次规划在本工具持有的Python子进程运行，外层180秒截止；到期终止该probe子进程并记录失败。每次受限调用单独记录，不能对应用的其他调查执行这个强制终止。整个小型probe最多15分钟，不进行无界重试。
- [ ] **Step 5 — 真正本机试跑：** 在确认已准备的Ollama服务上运行上述流程，保留真实模型版本、结构化模式、输入场景版本、调用ID/耗时/token。读取实际GPU驻留信息；运行时间或显存判断以实测为准。5次JSON检查得到的比例只能叫本次接口/格式成功比例，不是安全准确率。
- [ ] **Step 6 — 实际HTTP链：** 新幂等键提交已有固定真实来源 `demo/phase12c/real-source-case.json`，经现有HTTP入口触发原Orchestrator。`probe_investigation_http.py` 增量检查已保存Trace的模式；8个操作均按当前公共Schema验证，轮询最多120秒，超时不自动取消其他人调查。
- [ ] **Step 7 — 业务证据：** 若Planner通过，读取实际三Agent、三Artifact、Gate、Answer状态。PASS/PASS_WITH_WARNINGS、需复核或证据不足都按真实结果记录；仅按既有probe规则判定“完整成功链”，不为通过验收把Gate结果改为PASS。规划失败须记录PLANNING_FAILED，不宣称完整演示可用。
- [ ] **Step 8 — 冻结答案验证：** 重复GET Answer与同键重用不增加模型调用；Answer仍为DETERMINISTIC_TEMPLATE/FROZEN_GATE_CONTEXT，事实/风险/Gate前后一致。补充受控错误与取消测试：接口受理取消不等于即时打断模型，仍等待真实CANCELLED或终态；不改现有Runtime。
- [ ] **Step 9 — GREEN / Commit：** probe单位测试、现有Planner错误/重试测试、现有TCP/API链和冻结答案测试通过。真实服务不可用或合法Planner未通过时保存阻塞报告，不能写“真实模型验收完成”。Commit：`test: validate local provider and real planner through existing gateway`。

### Task 4：契约、交接、完整回归与实跑报告

**Interfaces:**
- 已有 `scripts/export_investigation_api.py` 的生成/check，`frontend/contracts/investigations.ts`仍复用已有类型/Client，不改页面。
- Task 2新增公共字段由现有OpenAPI导出器生成到 `docs/frontend-contracts/` 和 `AegisAI_FRONTEND_HANDOFF_PACKAGE/api/reference/` 的10份文件。
- `MODEL_PROVIDER_TEST.md`消费Task1/3脱敏记录；结果没有发生就写未执行/阻塞，而非填估计数值。

- [ ] **Step 1 — 契约检验：** 新增字段的MOCK、REAL、null响应由当前Pydantic校验，原TypeScript Client读取不出错；基于旧成功报告的模式断言不能掩盖新失败。
- [ ] **Step 2 — 文档与导出：** 运行导出器，再 `--check`确认一致。同步队友包的README、`contracts/README.md`和前端总交接，说明模型徽标从Trace读、模型不直连浏览器、API Key在服务端、Embedding仍Mock、历史身份与配置身份不同；检查实际现有文件名再更新，不创造重复契约。
- [ ] **Step 3 — Python实际回归：** 运行 `python -m unittest discover -s tests/engineering -v`、`python scripts/ci/run_backend_tests.py`；新增不依赖真实模型/DB的probe检查加入portable集合。随后在专用测试库运行 `python -m pytest tests/investigation_api tests/planner/test_llm_planner.py tests/orchestration/test_answer_composer.py -q`（backend目录）。失败、跳过、排除项及命令全部记录。
- [ ] **Step 4 — 前端/类型：** 运行 `npm --prefix frontend test`、`python scripts/ci/check_contracts.py`、`python scripts/export_investigation_api.py --check`、`node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json`、`node scripts/ci/check_frontend.mjs`。当前前端没有应用build命令，报告语法/类型检查，不能写成进行了不存在的build。
- [ ] **Step 5 — 交接封装：** 按现有MANIFEST算法更新队友包/ZIP并验证文件哈希、路径和排除内容；不夹带模型、真实Key、数据库或私有诊断。`python scripts/ci/check_repository.py` 和差异审查确认敏感内容未上传。
- [ ] **Step 6 — 实际报告：** 写 `docs/MODEL_PROVIDER_TEST.md`、`docs/phase12d/verification.json`、`PHASE_12D_RESULT.md`、更新 `CURRENT_STATUS.md`，区分真实Ollama、受控协议测试、Mock、历史测试。记录Provider/实际模型摘要/日期/调用分母/耗时/token/JSON/Planner稳定性，不生成准确率或效果提升。
- [ ] **Step 7 — 审查/Commit：** 回归实际通过后进行本阶段最终差异审查，检查核心业务目录没有改动、API只有可选字段、下载没有入库。Commit：`docs: record local model validation and frontend contract impact`。只有明确发布授权范围内才推送/建PR；合并仍须负责人确认。

## 5. 验收与停止条件

| 条件 | 必须提供的证据 |
|---|---|
| 复用Gateway与真实Provider | 已安装本机服务版本/模型摘要 + 真实Gateway调用记录 |
| 双模式及配置隔离 | Mock/Real配置检查；本机模型仅loopback；进程配置不污染永久环境 |
| 实际Planner | 原LLMTaskPlanner返回合法且经既有Validation通过的计划；失败则仍未验收 |
| HTTP业务链 | 唯一实际调查ID、持久化REAL调用身份、真实Agent/Gate/Answer结果；不以测试fixture替代 |
| 事实不可被模型改写 | 重复冻结答案不触发模型、事实/风险/Gate字段保持既有规则 |
| 前端契约 | Pydantic/OpenAPI/TypeScript/交接包一致，model_execution=null有明确语义 |
| 安全与报告 | 无Key/私有诊断/模型大文件；真实命令和结果，失败及限制明确 |

遇到真实模型未启动、GPU/内存不适配、Schema不兼容、计划持续非法或HTTP业务证据不足时，只完成已验证部分，明确列出尚未满足的验收项。不得为结束阶段宣称已全部完成。

验收后停止，不进入正式评测、公网部署、UI开发或模型大规模优化。未来若需要模型辅助答案表达，应另有阶段设计，仍不得改变冻结事实。

## 6. 风险与待确认的实施边界

1. 7B模型与现有完整Planner Schema的契合度尚未知；可用JSON不等于可执行计划。现有两次重试及验证边界不放宽。
2. 16K上下文、4096输出及当前内存/显存可能造成CPU部分卸载或超过调查时限；先预热并报告实际条件，不修改应用超时上限来掩盖失败。
3. 现有取消是协作机制，不能立即中断同步网络请求；文档和测试保持这一限制。
4. 默认Mock不会生成完整调查；可保留已有显式合成链用于CI，但不能将它说成真实模型业务验证。
5. PR #8未合并；本计划/后续实现基于其已审查提交，发布与合并时保持依赖清楚，不提前改main。

## 7. 计划自审

- 用户要求的Provider/配置/超时/Retry/Error/Logging检查已完成，实际结果见第1节。
- 支持本地免费模型使用已有Compatible Adapter；无新业务SDK、第三方Agent框架或检索迁移。
- Planner、结构化输出、模型异常、文本能力与确定性Composer分别由Task3验证；不假设已有LLM Composer。
- execution_mode由持久化调用身份派生，创建/历史/失败/无回执情况均有任务和测试。
- 所有新增方法、字段、固定模型参数及文件范围已明确；全部实施复选项尚未执行。
- 不将Ground Truth、精度评测、云端部署或关机混入本阶段。
- 本轮唯一新增文件应为本计划；模型下载与应用修改等待用户按本阶段要求确认。

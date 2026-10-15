# Phase 14-B4：多资产影响分析与证据化汇总

日期：2026-10-15。项目：AegisAI（ICT 命题九）。本轮在上层 API 适配中复用单资产调查，实现一个明确 CVE 对多个显式资产的独立调查、持久化与确定性汇总；未新增 UI、Agent、风险分数或总体 Gate。

## 1. 检查结论与最小范围

已有能力：B3 六类实体／候选关系、资产库存、单资产 Investigation API、Planner、Runtime、三专业 Agent、Gate、AnswerEnvelope、认证与审计存储。

实际缺口：B3 仅返回关系，不发起多资产调查；旧 Benchmark 适配器在入调查之前拒绝多资产问题。不能用关系命中代替组件身份、版本范围证据与核验。

复用入口：`InvestigationApiService.create/read/artifacts/answer/cancel`、`build_security_graph`、已有资产 owner 校验、数据库事务和原版本判断规则。

最小修改：新增批次 Schema／Repository／Service／Router，接入原 FastAPI 生命周期，扩展同源代理写入白名单、TypeScript 和生成契约。没有修改 Planner、Runtime、Agent、Gate、评分器、金标或数据库表结构。

验证方式：先写协议与隔离测试，再补实现；PostgreSQL HTTP 集成测试、独立静态审查、真实本地模型 TCP HTTP 双资产演示、全后端回归及便携／前端／契约检查分开记录。

## 2. Git 与依赖

- 远程核验：`shuabirfana-a11y/AegisAI`；未改 remote、未重建仓库、未强推。
- 使用隔离 worktree 的 `codex/phase14b4-multi-asset`，基线为 PR #27 的 `10a445e3ba51a97c6eddac10145be06fbd5689d4`。
- PR #27 为 OPEN draft，base 为 `codex/phase14c1-frontend-integration-fixes`，head 为 `codex/phase14b3-knowledge-relations`，检查时三项 CI 通过。**尚未进入 main**。
- 本轮草稿 PR 以 `codex/phase14b3-knowledge-relations` 为 base，避免把依赖栈重复算成本轮变更；不自动合并任何 PR。
- 保留已有未跟踪的 `PHASE_14C_RESULT.md`、`docs/phase14c/`，不纳入本次提交；未覆盖队友前端分支。

## 3. 执行与证据链

```text
单一已入库 CVE + 显式资产 UUID
  → 整批权限检查、去重、预算和不可混用的库存快照
  → B3 候选关系引用（不是影响证明）
  → 按资产 UUID 稳定顺序串行创建原单资产调查
  → 原 Planner → Runtime → Investigation → Verification → Analysis → Gate
  → 每资产独立 Artifact / Gate / Answer / Claim / Evidence
  → 确定性处置清单、未受影响清单、待解决清单
  → 原审计表持久化、认证回读
```

每资产稳定子键绑定批次、资产和漏洞；组件名称、包身份、生态、purl、版本、原调查 objective、Artifact 与结果引用均校验。风险取原 Answer 已接受字段，不调用额外模型拼接风险。

库存快照固定组件版本／修订及环境／暴露／来源。启动前或执行期间检测到变化，或原风险封存上下文与快照不一致时，不接受该快照的影响／风险结论，保留 UNKNOWN 和补充原因。库存是声明资料，`USER_INVENTORY_NOT_SCANNED`；criticality 没有原始字段，保留 unknown。

历史风险节点只保留为候选引用，不能覆盖本轮子调查。完成后回读始终标记 historical_snapshot=true、current_safety_evaluated=false，不称为读取时最新库存评估。公共漏洞证据可以被两个资产引用，版本判断、风险、Gate 与 Artifact 不共用。

持久化复用 `AgentRun` 的专属类型 `multi-asset-investigation-v1` 和独立命名空间，带摘要校验、请求绑定和 4 MiB 记录预算；没有数据库迁移。摘要用于一致性检查，不是抵抗数据库管理员篡改的数字签名。

## 4. 范围、状态与取消

默认最多 5 个去重资产，配置 `AEGIS_BATCH_MAX_ASSETS=1..20`；传输最多 100 项，超业务上限整体拒绝。仅支持已入库明确 CVE（可用该漏洞 UUID 别名）。不枚举全库存、不扫描、不执行 PoC、不跨多个漏洞。

每批串行；全库最多一个活动批次，继续沿用单资产资源限制。子预算最多 300 秒，总预算默认 900、最多 1500 秒。排序复用 P0–P3，次级按资产 UUID；不新增评分。

执行状态与影响判断分离：COMPLETED 不等于 Gate 全通过。只有完成、快照有效、允许的子 Gate、CONFIRMED、有证据且已接受的影响／风险才能进入处置或明确不受影响列表。UNKNOWN、缺版本、冲突、失败和未执行进入独立待解决列表，保留反证与人工复核要求。

同 owner、同键、规范化同漏洞／资产集合／预算不重复创建；顺序、重复项、CVE 大小写和 UUID 别名归一化。同键换范围／预算返回 409。旧键返回原快照；新库存分析必须用新键。

取消先持久化意图，阻止后续接纳，转发原活动子调查取消，保留完成项。已收到取消不等于底层已停止：宽限后可保留 RUNNING 子项和 recovery_required；GET 只对已接纳子项对账，不发起新调查。子创建 ACK 超时／提交后响应异常也保留稳定键，不因暂时查不到 Run 就启动下一项。

进程重启不自动重放非终态批次；90 秒心跳陈旧提示人工恢复。未确认停止的已接纳子项仍阻止新批次。该实现是有界进程内执行器，不宣称分布式任务调度或自动崩溃恢复。

## 5. API 与前端

新增四个认证接口：POST `/api/investigations/batches`；GET `/{id}`；GET `/{id}/summary`；POST `/{id}/cancel`。后三者均在相同 batches 前缀下。均有 Pydantic 请求／响应契约，summary 保留完整逐资产引用。OpenAPI 共 56 项操作；原接口路径和原 Schema 逐项比对保持一致。

更新生成 OpenAPI、HTTP 清单、TypeScript 和交接包镜像；前端原客户端扩展批次方法、同源代理只放行确切创建／取消路径。未改页面。接入细节见 [MULTI_ASSET_API_HANDOFF.md](MULTI_ASSET_API_HANDOFF.md)。

认证复用服务端 Bearer／owner 边界，不是完整多租户。创建前原子检查整组资产；回读、取消、子 Run 与 Artifact 引用均验证归属。异常仅返回安全错误码，不公开堆栈或模型原始输出。

## 6. 真实模型 HTTP 双资产记录

使用既有 `aegisai-qwen25-planner:latest`，通过 OpenAI Compatible Gateway 调用本地 Ollama，超时 60 秒、json_schema 结构化模式；未换模型、未优化 Prompt。隔离演示数据库、真实 Uvicorn TCP HTTP 请求、两个 `is_demo=true` 库存，非企业扫描、非 Benchmark。

来源为保存的 vLLM 官方公告 `GHSA-hjq4-87xh-g4fv`（CVE-2025-47277），公告发布时间 2025-05-20，快照取得时间 2026-10-12T12:40:38.540828Z；保存原始字节、SHA256、观察记录、Claim 和 JSON 定位证据。它是既有官方来源快照，不冒充本轮实时抓取。

运行：2026-10-15T06:46:32Z–06:47:41Z。批次：`791798cd-06c8-41bc-b247-9ba8f43b2dba`，COMPLETED。

| 演示资产 | 部署版本 | 独立子调查 | 影响／风险／优先级 | 核验／Gate |
|---|---|---|---|---|
| Demo inference A | vLLM 0.6.5 | c1c34106-e080-4038-9e4c-6679ed675460 | AFFECTED / HIGH / P1 | CONFIRMED / PASS |
| Demo inference B | vLLM 0.8.5 | b824f465-6fa8-4d18-9f4d-9de207195183 | NOT_AFFECTED / LOW / DEFER | CONFIRMED / PASS |

A 的 Investigation／Verification／Risk Artifact：`a461a1a6-313d-422b-aca0-9b3a789065f0`、`84199d60-69e5-4e37-8b16-16029d2ad80b`、`f0d79d80-c112-44fd-9089-7bb89b9f0671`；Gate：`f176692c-a0be-4f23-a727-3414e3d542ca`。B 有独立三类 Artifact 和 Gate，见脱敏 [决策及引用记录](docs/phase14b4/real-demo.json)。该文件是节选，不是完整 HTTP 夹具；完整运行记录留在本机隔离数据库，不上传日志或库存库。

## 7. 历史 7 题缺口核对

读取旧 requests-preflight 与原始题目 input_context，不读取答案来构造请求：

- 5 题为单 CVE＋两台显式资产，新的 BatchRequest 可以表达其范围；仍需将题目声明资产映射到实际有权限的库存 UUID。
- 2 题为跨公告、多漏洞优先级／缺版本场景，仍超出本轮单漏洞契约，继续记录不支持。
- 旧 Evaluation Adapter 未修改，仍保留原多资产拒绝；本轮没有将这 5 题重新跑成正式实验，也没有修订旧 49 题分数。

逐题输入范围记录见 [historical-scope-check.json](docs/phase14b4/historical-scope-check.json)。这是开发回归范围核对，不是新的独立泛化评测，不宣称 7 题全部修复。

## 8. 修改文件

- 后端新增：`app/api/multi_asset.py`；`app/investigation_api/multi_asset_{schemas,repository,projection,service}.py`。
- 后端兼容接入：`app/main.py`；原接口契约测试；历史源文件校验只增加经本轮授权的 main.py 精确哈希例外，未改旧基线文件。
- 测试：`tests/investigation_api/test_multi_asset.py`、`test_multi_asset_database.py`、`test_multi_asset_chain.py`。
- 前端：`contracts/investigations.ts`、`server.mjs`、`tests/server.test.mjs`；便携 CI 测试入口。
- 契约：`docs/frontend-contracts/` 与 `AegisAI_FRONTEND_HANDOFF_PACKAGE/api/reference/` 的五种调查契约导出；交接包清单仅同步对应导出文件哈希。
- 交付：本报告、API 接入说明；`docs/phase14b4/` 中的最小哈希授权、真实演示节选和历史范围核对。

## 9. 本轮验证

各组有重叠，**不能相加成新的总数，更不是业务准确率**。数据库测试使用工作区自有集群与专用测试库；真实演示使用另一个隔离数据库。

| 实际命令（项目根目录；backend 测试在 backend 执行） | 本轮结果 |
|---|---|
| `python -m pytest tests/investigation_api/test_multi_asset.py tests/investigation_api/test_multi_asset_database.py tests/investigation_api/test_multi_asset_chain.py -q` | 最终 **28 passed / 0 failed / 0 skipped**，1 AnyIO 弃用警告，167.06 秒 |
| `python -m pytest -q --junitxml=../work/phase14b4/full-backend.xml` | **1644 passed / 51 failed / 0 skipped**，23 warnings，1133.37 秒；此后仅补截止边界修复及对应测试，未重复全量 |
| `python scripts/ci/run_backend_tests.py` | 最终 **687 passed**，1 deselected，1 AnyIO 弃用警告；原便携入口排除真实 embedding 缓存测试，未新增排除 |
| `python scripts/ci/check_contracts.py` | PASS，56 HTTP 操作、40 个合成对象；不连接数据库 |
| `python scripts/export_investigation_api.py --check` | PASS，10 个导出文件一致 |
| `python scripts/export_intelligence_api.py --check` | PASS，8 个文件、10 个情报操作一致 |
| `python -m unittest discover -s tests/engineering -q` | 18 tests，OK |
| `node --test frontend/tests/*.test.mjs` | 69 passed，0 failed，0 skipped |
| `node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json` | exit 0 |
| `node scripts/ci/check_frontend.mjs` | 24 个 JavaScript 文件检查通过；原生前端无构建脚本，build 为 NOT_APPLICABLE |

新增 28 项后端测试（12 便携、3 数据库、13 HTTP 链路）覆盖不同版本、缺版本、候选关系无影响证明、冲突、Planner 失败、同键并发、UUID 别名、快照变化、已封存上下文临时漂移、ACK 超时、提交后响应异常、取消宽限与迟到回读、总截止、创建前输入不兼容／读取异常、越权及缓存引用篡改。升级库存后回读旧 HIGH 的测试明确检查原版本快照和 current_safety_evaluated=false。外部模型在自动化链路测试中被替身隔离；真实模型验证单独记录于第 6 节。

全量失败没有隐藏：两条历史失败分别为 `test_bench_http.py::test_evaluation_adapter_reaches_full_original_http_chain[unknown_version]`（现有入口返回需上下文，而旧断言要求 SUCCEEDED）和 `test_failure_cancel.py::test_essential_partial_blocked_or_ambiguous_stops_downstream[ambiguous]`（原链未产生旧断言要求的 Gate 状态）。在未修改的 PR #27 源码快照、干净测试库中两条也均失败，不能声称已消失。

另外 49 条中，一条迁移用例缺少 AEGIS_DATABASE_URL 环境设置，其余主要涉及持久化夹具污染全库计数／既有内容。将顶层 535 项旧测试按原有序文件列表单独运行，并设置专用库的 AEGIS_DATABASE_URL 后：当前分支 528 passed / 7 failed；未修改基线 527 passed / 8 failed。当前这 7 个失败名称全部也出现在基线，基线额外一项内容回放用例波动不构成改进结论。**这不等于全量通过，也没有通过改测试或旧业务代码来掩盖失败。** 详细失败名称与分组见 `docs/phase14b4/validation-results.json`。

复核命令：顶层组用 PowerShell `$taskFiles = @(Get-ChildItem tests -File -Filter 'test*.py' | Sort-Object Name | ForEach-Object { 'tests/'+$_.Name })` 后执行 `python -m pytest @taskFiles -q`；基线通过 `git archive HEAD` 提取未修改源码并在相同 Python、同一已重置的专用测试库复跑。两个历史失败通过上述完整节点 ID 单独指定复核。没有触碰演示库或开发库。

增加截止边界修复后的批次＋原 API 契约／兼容检查＋历史两项组合实跑为 42 passed / 2 failed（失败正是上述历史两项）；之后补齐前创建异常保护，末轮 28 项批次测试与 687 项便携测试通过。没有把这一局部结果改写成完整后端通过。

独立审查发现的“第二次接纳事务剩余不足一秒”问题已先用单测复现：未调用子创建却留下 RUNNING；现改为 NOT_EXECUTED／DEADLINE_BEFORE_CHILD_CREATION，避免无子 Run 的批次永久占用活动名额。完整回归之后的针对性验证另列，不把全量旧结果当成此修复的验证。

同类前创建异常也已修复：库存合法名称长度可能大于子请求允许长度，或第二次快照读取失败；这些确定尚未调用 create 的异常分别返回 NEED_CONTEXT／CHILD_INPUT_INCOMPATIBLE 或 FAILED／CHILD_PREPARATION_FAILED，不误认为已创建子调查。进入原 create 后的异常仍保留不确定性保护，不能因为响应失败就启动下一项。两类均有红→绿测试。

真实演示还在重启应用后重新 GET 批次、summary、两个子调查的 trace／answer／artifacts／integration，结果与原持久化记录一致；验证时禁止所有 Gateway 模型调用，确认只是回读。

独立审查由只读审查子任务完成，针对串用、权限、持久化、取消、超时和响应完整性；已修复发现项，末轮静态审查无新的 P1/P2 阻断。审查任务未执行测试，实跑由实施任务完成。

安全检查：本轮暂存变更脱敏扫描无发现；提交前全历史 76 个提交扫描无发现；禁止路径检查通过。仅上传演示库存的脱敏引用节选，不上传数据库、模型文件、凭据或完整日志。GitHub 三项基础 CI 与本机全后端测试范围不同，不能互相替代；远端最新状态以本轮草稿 PR 为准。

## 10. 当前限制与停止范围

不支持跨漏洞批次、全库存自动枚举、扫描验证、自动安装修复、完整多租户或崩溃自动恢复。大组件库存和大响应有明确上限。单实例串行调度适合当前演示规模，不宣称生产分布式吞吐能力。

没有改金标、评分规则、Gate 或风险规则；没有执行 49 题实验。本阶段只提交草稿 PR，完成后停止，不合并、不发布、不冻结、不进入页面开发。

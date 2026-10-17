# Phase 14-B4.1：全量回归失败定位与核心业务可靠性修复

项目：AegisAI，ICT 产教融合创新大赛命题九。日期：2026-10-15。

**交付状态：PASS（本轮工程验收范围）。** 原51项已逐项归因并全部复测通过。最终FIX后端完整套件1702项通过，0失败/错误/跳过/xfail，23警告，1080.74秒；四项GitHub CI代码检查通过。修复提交在草稿PR #29，不合并依赖PR或main。

## 1. 直接回答四个问题

**为什么出现51项失败？** 原始 JUnit 有1695个测试节点，1644通过、51失败、0错误、0跳过。51个 nodeid 均唯一，均在 call 阶段失败，不是把同一节点的 setup/teardown 重复计数。48项由真实提交的 Runtime/Agent 测试数据串入假设空库的 rollback 测试引起；1项缺少迁移读取的显式数据库配置；2项旧断言不符合已经批准的缺上下文和重复根查询契约。

**哪些由B4新增？** 在包含B4实际依赖的BASE和最终提交HEAD中，同条件选择原51节点，两个版本均为36失败、15通过，逐项结果一致。清洁环境只运行原49个数据库节点时，两个版本均49通过。本轮没有在原51项中证实B4新增生产回归，也没有把它们当作51个既有生产缺陷。原全量失败时工作区没有冻结精确SHA，不能对那个未恢复快照作绝对因果保证。

**为什么三项CI绿色？** 原检查确实执行了便携后端子集、契约、离线评测设施、前端和仓库检查；没有数据库服务，未跑这些数据库组合。未发现吞退出码、continue-on-error、隐藏失败的包装器。它通过的是自己的有限范围。新增独立 PostgreSQL CI 第一次真实捕获了3项环境相关的语义工具失败，定位并修复后253项通过。

**修复后哪些真实功能仍受影响？** 在本轮已验证的单/多资产、缺上下文、冲突、证据、取消、幂等、持久化和监测富化检查中，没有剩余失败或未定位节点；最终1702项完整后端全部通过。模型或网络不可用、有索引但缺Embedding时仍会明确失败；缺版本仍请求补充，证据不足/冲突仍非PASS。这些没有被改成“安全”。未验证生产部署效果、企业实际扫描或业务准确率。

## 2. 仓库、版本与保护

仓库：`https://github.com/shuabirfana-a11y/AegisAI.git`。

工作目录：`C:/Users/X/.codex/worktrees/phase13a-engineering/files-mentioned-by-the-user-9`。路径有历史阶段名称，但remote、源码和PR均属于AegisAI。

| 对象 | 准确提交 | 含义 |
|---|---|---|
| BASE | `10a445e3ba51a97c6eddac10145be06fbd5689d4` | B4开始前的实际B3依赖，PR #27 head |
| HEAD | `b1ad6824c56e52e7d34cd6f5a531f55846f1fc24` | 最终提交B4，PR #28 head |
| FIX-1 | `fe2a377acd0ad1d8c035c4af8b0328f8eb5bb575` | 数据库隔离、两项契约断言、CI与精确哈希授权 |
| FIX代码 | `d637cb45f208205418807335670258069b292492` | 新CI发现的空索引/Embedding修复及4项回归 |

原51失败报告对应B4提交前的未冻结工作区，精确SHA **NOT_FROZEN_NOT_RECOVERED**。HEAD不能冒称那个原始快照；51项所在测试文件在BASE/HEAD的哈希全部相同。原报告1695节点、最终HEAD1698节点，最终B4另补3项边界检查；保留该差异。

BASE/HEAD用Git archive等效隔离源码副本，未在队友目录来回切分支。BASE、HEAD、FIX各有独立测试PostgreSQL实例。保留了原未跟踪的 `PHASE_14C_RESULT.md`、`docs/phase14c/`；未清理原演示数据库及历史审计。未改remote、未强推、未合并#27/#28、未改main、未创建Release。

修复PR：[PR #29](https://github.com/shuabirfana-a11y/AegisAI/pull/29)，草稿，base为 `codex/phase14b4-multi-asset`；head为 `codex/phase14b4-1-regression-reliability`。

## 3. 原51项台账与根因

逐项机器台账：[`docs/phase14b4_1/failure-ledger.json`](docs/phase14b4_1/failure-ledger.json)。包含原异常和堆栈、失败阶段、测试文件和测试内容哈希、BASE/HEAD两种环境结果、复现条件、主分类、生产影响、修复提交、FIX全量结果及精确旧快照不确定性。敏感连接密码不导出。

| 主分类 | 节点数 | 证据与修复 |
|---|---:|---|
| 测试隔离问题 | 48 | 提交型Agent/Runtime fixtures与回滚型旧tests同库；独立实例、空库检查及同库拒绝 |
| 环境配置 | 1 | `test_actual_upgrade_downgrade_upgrade_matches_orm`未设置迁移读取的`AEGIS_DATABASE_URL`；入口显式指向测试root库 |
| 已批准契约与旧测试不一致 | 1 | HTTP未知版本已应NEED_CONTEXT/NOT_STARTED，旧测试仍要求SUCCEEDED |
| 已批准契约与旧测试不一致 | 1 | scoped Schema早于Runtime拒绝同目标重复lookup，旧测试仍要求Gate REPLAN_REQUIRED |
| 已确认新增生产回归 | 0 | 原51项中未证实 |
| 已确认既有生产缺陷 | 0 | 原51项中未证实，另见新CI发现的真实工具缺陷 |
| 尚未定位节点 | 0 | 所有51项指定一个主要分类，不重复统计 |

48项涉及采集幂等、原文/证据保存、分页、任务数量、监测状态及资产事件，不能因“基线也失败”就忽略。原断言会读到其他题的SYNTHETIC来源、漏洞和任务。最小复现：先运行 `test_phase14b2_agent.py`，再运行pipeline和jobs代表用例，1通过2失败；只读探针确认4个已提交AgentRun和6个任务，后题期望2任务却读到8。不是rollback实现凭猜测“可能没回滚”。

对照：单独运行pipeline/jobs的60项全部通过，teardown后的只读计数为0。说明那些事务回滚本身成立，真正边界是另一些fixture必须跨连接真实commit。特别是顶层 `test_phase14b2_agent.py` 显式导入Runtime engine，仅按目录分组也不足以隔离。

## 4. BASE / HEAD 可比对照

| 检查 | BASE | HEAD | 解释 |
|---|---:|---:|---|
| collected后端节点 | 1670 | 1698 | B4新增28，无删除节点 |
| 原51节点，同样保留原共库/迁移配置缺失条件 | 15通过/36失败 | 15通过/36失败 | 每节点结果一致；缩小集合没有原全量的全部污染前序，不能强行凑51失败 |
| 原49数据库节点，初始空库、显式migration URL | 49通过 | 49通过 | 原测试断言未改 |
| 原两项契约旧测试 | 原先2失败 | 仍旧断言 | 用已批准契约修正，不改安全规则 |

两组共同测试内容在B4变化的只有API操作数契约检查及历史源码哈希检查；台账列出具体nodeid。原51项测试文件BASE/HEAD全相同。FIX后端增加4个空索引节点，collected为1702；另有3个仓库工程测试，不与后端节点相加。

两个隔离副本均验证 `app.__path__` 指向各自源码，无editable install。解释器同为Python3.12.14，pytest9.1.1、SQLAlchemy2.0.54、psycopg3.3.6。依赖使用同一解释器，锁文件差异只涉及本轮CI加入已存在版本的uvicorn；没有修改BASE生产依赖来伪造相同环境。

PostgreSQL均17.11；BASE端口55445、HEAD55446、FIX回滚55447、FIX提交55448，专用库名均 `aegis_phase5_test`。FIX两实例均重新provision为空库，并执行原0001–0004迁移；脚本不增加数据库迁移或扩展。真实向量储存仍FLOAT[]，未宣称本轮启用pgvector。

原“两项历史失败”只跑两节点；之前535项顶层检查分别527通过8失败、528通过7失败，环境还含commit污染。不能计算51−2=49新增问题。BASE那次额外A→B→A检查使用未排序SQL列表作断言，本轮预先限定5次干净重复均通过；保留全部结果，未为它增加skip、重试直到绿或更改业务。原全量51项不含该节点。

## 5. 最小修改

### 数据库隔离与实际退出码

`scripts/ci/run_database_tests.py`使用两个显式、独立、初始空的本地测试实例。缺配置、非loopback、非专用库、共实例共库或残留数据均拒绝。密码/用户名/localhost别名不算隔离。迁移只用显式测试URL，不回退开发库。入口不创建/删除数据库，不清除数据；准确返回pytest非零退出码。

`--full`执行整个 `backend/tests`，不加筛选、skip或deselection。默认清单是CI数据库关键回归，不能冒称全量。`backend/tests/conftest.py`增加共库拒绝，防止错误配置悄悄重现污染。

### 两项旧断言

Phase13-F.4已批准缺版本的HTTP preflight：断言NEED_CONTEXT、NOT_STARTED、NOT_EVALUATED/abstained，不调用模型、不创建调查/Trace/Gate，不把未知判为安全。未修改Evaluator或计分规则。

Phase13-F.3已批准scoped Schema maxContains=1：同目标重复根lookup必须PLANNING_FAILED，断言无Runtime、Verification、Risk、Gate和确定事实。原 `test_ambiguous_lookup_does_not_select_first`仍保留，Artifact歧义不能偷选第一条。

旧源码哈希基线保持不可变；两处授权改动在 `docs/phase14b4_1/source_hash_exceptions.json`登记精确前/后SHA与授权原因，校验白名单仅允许root fixture与语义适配器，不整体排除文件或目录。

### 新CI发现的工具缺陷

新CI首跑246通过、3失败，涉及optional_failure、required_partial、blocked三个编排场景。它们的semantic_search在空知识索引上仍初始化FastEmbed；CI未安装/下载缓存模型，工具返回TOOL_FAILURE，Gate忠实输出FAILED，不能把这个结果降级成warning来凑预期。

根因是空索引情况下提前加载不必要的Embedding。补充反例测试得到3失败/1通过；最小业务修复仅在 `backend/app/tooling/adapters.py` 增加SQL存在性检查，使用与既有检索相同的model、当前document revision、chunker、非deleted及RawDocument关联约束。

无可检索索引时返回真实 `no_result`、空Evidence；有当前索引仍调用原SemanticSearch和模型，模型加载失败照样保留。不制造结果，不认为“无语义结果”等于“没有漏洞”。四项新增测试覆盖空库、过期版本、软删除、有当前索引但模型不可用。相关27项通过；新CI重跑253项通过。

这是本轮另发现并修复的1类既有生产工具缺陷，**不属于原51项，也不把3个CI节点重复算成3个生产缺陷**。没有改Agent、Planner、Runtime、Verification、Risk或Gate规则。

## 6. CI实际覆盖

原PR #28运行：[38703884798](https://github.com/shuabirfana-a11y/AegisAI/actions/runs/38703884798)。API的head是b1ad682，实际checkout为GitHub合成提交 `a8b82b7f35d4dc2813304ef934041db27f96b0e0`，父提交分别为10a445e和b1ad682；没有把PR检查当作本地exact SHA。

| 原检查 | 实际命令/结果 | 未覆盖 |
|---|---|---|
| Backend unit and contracts | `python scripts/ci/run_backend_tests.py`：687通过、1明确deselected；`pytest tests/aegisbench -q`：129通过；契约导出/离线pilot执行 | PostgreSQL组合、真实Planner和模型缓存测试 |
| Frontend tests and types | JavaScript检查、`npm test`69通过、TS contracts编译；当前原生JS前端无build脚本，步骤明确NOT_APPLICABLE | 后端全量和真实浏览器演示 |
| Repository safety | 工程unittest18项，12通过/6因Linux无Windows PowerShell跳过；Git全历史Gitleaks及路径安全 | 生产业务和数据库 |

便携job有NoDatabaseFixtures guard，不是暗中忽略数据库异常；显式排除一项cached-real-embedding。没有发现continue-on-error、`|| true`、非零退出码吞掉或关键步骤被条件跳过。

当前新增第四项：**Backend PostgreSQL critical regression**。两个只绑定loopback的临时PostgreSQL17服务；受控外部传输、Mock模型，执行20个明确路径，253通过、0失败/错误/跳过。新CI代码运行：[38713651482](https://github.com/shuabirfana-a11y/AegisAI/actions/runs/38713651482)，实际checkout为合成提交 `1a12c76`，将FIX d637cb4合入B4 b1ad682；四项SUCCESS。本轮文档提交后的最新CI在交付时再次核对。

CI不接真实Key，不下载本地模型，数据库关键回归与本地完整套件分别报告。Windows工程测试本地21项通过；Linux21项中6个Windows专用检查跳过，不能算作CI通过21项。

## 7. 本轮实跑与失败保留

**最终FIX全量：1702 passed，0 failed，0 errors，0 skipped，0 xfailed，0 deselected，未执行0（backend/tests范围），23 warnings，1080.74秒，退出码0。** 原51失败节点全部在此完整套件中passed。警告是现有依赖弃用和负向测试注入非法枚举产生的序列化告警，未过滤或改成跳过。

| 运行范围 | 真实结果 | 原始记录 |
|---|---|---|
| 原始B4全量 | 1644通过/51失败，1695节点 | `work/phase14b4/full-backend.log/xml` |
| 同条件BASE原51 | 15通过/36失败 | `base-original-51.log/xml` |
| 同条件HEAD原51 | 15通过/36失败 | `head-original-51.log/xml` |
| 干净BASE原49 | 49通过 | `base-clean-common49.log/xml` |
| 干净HEAD原49 | 49通过 | `head-clean-common49.log/xml` |
| 污染最小复现 | 1通过/2失败 | `pollution-red.log/xml` |
| 单独pipeline/jobs与只读rollback探针 | 60通过 | `transaction-probe-2.log`、`transaction-probe.xml` |
| 两项契约及Artifact交接 | 6通过 | `contracts-fix.log/xml` |
| FIX首次全量 | 1697通过/1失败：获准fixture改动尚未登记精确哈希 | `full-fix.log`、`full-fix/results.xml` |
| 精确哈希登记后全量 | 1698通过、0失败/错误/跳过，23警告，1079.97秒 | `full-final.log`、`full-final/results.xml` |
| 新CI首次运行 | 246通过/3失败 | `ci-database-first.log` |
| 空索引回归RED | 1通过/3失败 | `semantic-red.log/xml` |
| 空索引修复及关联GREEN | 27通过、0失败/跳过 | `semantic-green.log/xml` |
| FIX最终本地全量 | 1702通过、0失败/错误/跳过，23警告，1080.74秒 | `full-complete.log`、`full-complete/results.xml` |
| FIX便携子集 | 687通过/1明确deselected | `portable-after-empty-fix.log` |
| FIX数据库CI | 253通过、1警告，275.75秒 | `ci-database-pass.log` |
| 前端既有套件 | 69通过、0失败/跳过 | `frontend.log` |

除特别注明外，记录均在 `work/phase14b4_1/`。初版诊断探针曾因写错表名产生INTERNALERROR，原 `transaction-probe.log`保留，修正辅助查询后重跑；不将它混入原51项。没有删除失败记录、跳过旧失败、非严格xfail、增加sleep/timeout来凑通过或修改金标。

各测试范围重叠，**不得把49、60、27、253、687、1702相加**。工程通过不是Benchmark准确率。

## 8. 真实命令与环境前提

本机明确解释器：`C:/Users/X/Documents/Codex/2026-10-03/files-mentioned-by-the-user-9/backend/.venv/Scripts/python.exe`。项目根目录运行：

```powershell
$env:AEGIS_TEST_DATABASE_URL='postgresql+psycopg://aegis_local@127.0.0.1:55447/aegis_phase5_test'
$env:AEGIS_RUNTIME_TEST_DATABASE_URL='postgresql+psycopg://aegis_local@127.0.0.1:55448/aegis_phase5_test'
& '<明确的Python解释器>' scripts/ci/run_database_tests.py --full --output work/phase14b4_1/full-complete
& '<明确的Python解释器>' scripts/ci/run_backend_tests.py
& '<明确的Python解释器>' scripts/ci/check_contracts.py
& '<明确的Python解释器>' scripts/export_investigation_api.py --check
& '<明确的Python解释器>' scripts/export_intelligence_api.py --check
& '<明确的Python解释器>' -m unittest discover -s tests/engineering -v
```

前端工作目录执行 `node --test tests/*.test.mjs`；TypeScript使用现有 `.github/tsconfig.contracts.json`执行noEmit。契约检查56个API操作和40份合成对象通过；调查导出10个镜像文件、情报导出8文件/10操作一致。没有新增API或改响应Schema。

BASE/HEAD复现保持同Python、同依赖、Mock和offline环境，分别在各自 `backend` 工作目录：`python -m pytest -q <台账51个nodeid> --junitxml=<输出>`；原条件不设置AEGIS_DATABASE_URL、两类fixture在该版本内部同库。清洁对照选择49数据库节点并显式设置migration URL。详细测试内容哈希、各节点结果与日志SHA见机器台账。

只重新provision已经验证归属的可丢弃测试实例。测试入口自身拒绝脏库，不负责自动擦除。原演示库 `aegis_phase14b4_demo`全部保留。当前本机已有FastEmbed缓存，完整套件中的真实Embedding继续真实运行；新机器没有缓存必须明确未完成，不能以便携检查代替。

## 9. 核心业务验收与真实模型HTTP

| 业务行为 | 检查方式 |
|---|---|
| 单资产旧链 | 原Orchestrator、三个Agent、Gate、AnswerEnvelope回读；TCP HTTP契约 |
| 多资产独立判断 | 两版本完整链与数据库保存，不串版本、Artifact/Evidence；原28个B4节点保留 |
| 缺版本及部分失败 | 缺版本为UNKNOWN/NEED_CONTEXT，不进入低风险/安全名单，完整兄弟资产仍运行 |
| 冲突/证据不足 | 保留冲突Artifact、disputed claims、来源与合法非PASS；关系图不当作影响证据 |
| 所有权、取消和幂等 | 原鉴权、并发重复请求、延迟ack/取消确认、停止后不再开兄弟调查、库存漂移拒绝 |
| 监测与富化 | 原采集格式、变更/304/重放、原文与证据、任务持久化、来源失败不污染其他来源、PoC候选不自动Verified |
| 知识关系与历史风险 | 原图owner/target约束、决策所用证据、历史风险不提升为当前部署风险 |

最终FIX代码使用现有本地免费Qwen2.5完成新一组有限真实TCP HTTP验证：

- 单资产调查ID：`879f269b-b008-489e-9bbd-0465af4c1d77`；读取status/trace/artifacts/integration/answer，同幂等键重复POST返回同ID。
- 双资产批次ID：`9dd26078-cbf1-4f3b-b2be-9a182a188ad0`，COMPLETED；vLLM0.6.5得到AFFECTED/HIGH/PASS，0.8.5得到NOT_AFFECTED/LOW/PASS，两条独立子调查及Artifact。
- 模型：OpenAI-compatible、`aegisai-qwen25-planner:latest`，Planner非Mock；Gateway embedding provider明确为mock，此场景风险事实来自结构化工具和缓存证据，不冒称全链所有Embedding调用真实。
- 公告：缓存官方GHSA-hjq4-87xh-g4fv/CVE-2025-47277，发布2025-05-20，获取2026-10-12；原文SHA `5bb7d95bca042809b37e15104a0e0f9d9ac1c20d61e16994fc99770df38714c0`。
- 库存：`is_demo=true`、人工声明版本、没有企业扫描；输出为固定库存及证据快照，`historical_snapshot=true`、`current_safety_evaluated=false`。

脱敏结果见 [`docs/phase14b4_1/real-http-validation.json`](docs/phase14b4_1/real-http-validation.json)。前一组fe2a377真实HTTP记录另存保留；本次不运行Benchmark、不输入Ground Truth、不输出准确率。未实际访问当前所有外部来源或公网生产部署。

## 10. 修改文件

业务仅：`backend/app/tooling/adapters.py`。

测试与入口：`backend/tests/conftest.py`、`backend/tests/investigation_api/test_bench_http.py`、`backend/tests/orchestration/test_failure_cancel.py`、`backend/tests/orchestration/test_legacy_compat.py`、`backend/tests/test_semantic_empty_index.py`、`scripts/ci/run_database_tests.py`、`tests/engineering/test_database_regression_gate.py`。

CI与文档：`.github/workflows/ci.yml`、`.github/requirements-ci.txt`、`CONTRIBUTING.md`、`docs/GITHUB_WORKFLOW.md`、`docs/DEVELOPMENT_GUIDE.md`、`docs/DATABASE_REGRESSION.md`、本报告及 `docs/phase14b4_1/` 三份JSON。

未改Agent、Gate、模型提示词、数据库模型/迁移、前端功能、Ground Truth、评分规则、历史Benchmark结果。

## 11. 范围与剩余限制

原始51运行精确工作区未冻结，因果对照以提交HEAD明确界定，不凭空补齐SHA。虽然所有原节点已解释，本轮不能证明从未发生任何生产缺陷。

本轮是工程可靠性检查，受控数据回归不等于富化准确率或多跳推理准确率。真实HTTP使用缓存公告和演示库存，只证明该固定场景调用、证据和保存链成立。实际企业库存、生产鉴权配置、外部限流/断网及长期并发负载仍需另行验收。

有索引但模型不可用、来源不可用、证据不充分，系统仍允许明确FAILED/UNKNOWN/REPLAN_REQUIRED/HUMAN_REVIEW_REQUIRED；不为了通过率移除这些状态。CI本身仍不是1698/1702全量，它承担253个数据库关键回归；完整本地运行必须单独保存证据。

完成本阶段后停止，不扩功能、不制作材料、不冻结或发布版本，不自动合并依赖PR。

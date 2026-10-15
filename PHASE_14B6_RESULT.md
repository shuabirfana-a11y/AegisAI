# Phase 14-B6：实际答案事实链核对与新版49题复测

本轮完成源码/事实链核对、两项兼容修复、49题完整采集与原规则评分、实际输出复核包及完整后端回归。**工程可运行与业务答对分别验收：新版严格整题匹配仍0/49，风险匹配0/10，不能声称达到赛题准确率档位。**

## 1. 基线与实际执行版本

- 仓库 `shuabirfana-a11y/AegisAI`；分支 `codex/phase14b6-answer-chain-retest`。草稿 [PR #31](https://github.com/shuabirfana-a11y/AegisAI/pull/31) 基于未合并的 #30；依赖 #30 → #29 → #28 → #27。没有合并main、修改remote、强推或Release。
- B5基线 `244dd9a7afceaae615ac9eaf602aa79cf9145b32`；本轮**HTTP实际采集代码** `b8182eac1153e08bd9323b949f1b56af162360c8`。后续提交只交付结果、状态说明和离线复现入口，不冒充重新跑过模型。
- 服务从目标worktree启动，校验实际 `backend/app/main.py`、解释器、提交与业务源码哈希；关闭reload。启动证明在本地 `work/phase14b6/formal-service-proof.json`，评测逐题检查冻结文件哈希，结束复核模型digest。
- 两个独立空库做完整测试；另一个独立实例做正式评测，资料只来自历史公开来源的私有副本，未改原历史库。原开发/其他任务数据库、队友未提交的 `PHASE_14C_RESULT.md` 与 `docs/phase14c/` 保留。

## 2. 历史低分的事实链核对

仅选6题，按题型与历史失败选择，复用历史HTTP原始结果，没有额外6题模型试跑。台账见 [历史六题核对](evaluation/reports/phase14b6-human49-20261016/historical-six-audit.json) 和 [逐题字段链](evaluation/reports/phase14b6-human49-20261016/field-chain-ledger.jsonl)。

| 问题 | 已取得的证据 | 本轮处理 |
|---|---|---|
| CVE字段读取遗漏 | 正式AnswerEnvelope有唯一已确认 `VENDOR_CONFIRMED.value.cve`，旧投影没有读取 | 仅读取该既有正式字段；多个不同确认编号不任选，不从问题补值 |
| 多资产路径不适配 | 5道单漏洞双资产题被旧单资产客户端拒绝，后端已有正式批量接口 | 复用批量API；按原输入绑定中性库存，回读每个既有子调查，保留独立版本与Gate |
| 版本资料存在却无法核验 | 多个Claim带来源范围，但被判不足/冲突；部分 `raw_expression` 是序列化OSV范围，解析为unsupported | 原判断保留，未把资料存在直接升为CONFIRMED |
| 事实契约表达不足 | CWE/原公告摘要没有现有核验Claim类型；CVSS需区分版本/向量，现Composer白名单不透传vector | 记录正式契约缺口；不把调查目录当已确认事实，也不借此变更旧答案内容哈希/契约语义 |
| 缺版本与跨漏洞范围 | 5题没有部署版本；2题跨公告但没有明确漏洞目标 | NEED_CONTEXT/范围不支持保留，不猜版本、目标或资产 |

**不能把历史0/49都归于格式。** 版本影响、风险、修复、PoC等多项仍未取得可交付结论，部分已输出值与金标范围/语义不同，需要人工查源。冲突是否属于真实来源差异或规范化差异，不能仅凭错误文字裁决。

使用完全相同的历史HTTP回答离线重处理，原历史结果不覆盖：CVE字段由0/5变为2/5，严格整题仍0/49、风险仍0/10。记录见 [历史重处理](evaluation/reports/phase14b6-human49-20261016/historical-reprocessing.json)。这是读取修复对照，不是新版能力提升实验。

## 3. 修复与复现依据

1. `evaluation/bench/http_investigation.py`：增加唯一确认CVE的正式字段投影；抽取已有调查结果读取以供正式批次子项复用；保留原Schema、所有权、问题、资产、证据、产物和结果版本校验。
2. `evaluation/bench/http_batch.py`：调用已有 `POST /api/investigations/batches`；不创建另一套编排。原题资产ID只作本地输出对照，发送真实中性库存UUID；不得含金标、分类、预算扩张或资产提示名。每个子调查按批次公布的结果版本回读；整道多资产题仍按全部原字段比较。
3. 新增9项评测测试及1项数据库HTTP集成测试；新DB用例加入既有CI关键套件。先复现CVE遗漏/批量请求不支持，再通过修复验收。初版新批量适配器混淆显示组件名与canonical package_name，先实际失败，再按原输入区别最小修正；没有修改原业务。

没有修改Agent、Planner/Prompt、Runtime、Verification、Risk、Gate、评分公式、大小写/别名策略、金标、题目或B5补查额度。前端、OpenAPI与TypeScript业务契约保持。

## 4. 冻结环境与数据隔离

- 数据集 `AegisBench-v0.4-human49-20261014`：49 APPROVED，0剔除；manifest SHA256 `002f021912a56f629c79a6207d30a91abe126c55f3d5f201adbfc358e8ae13e3`。题目/批准数据与评分源码冻结，输入只使用原题问题及input_context。
- Provider `openai_compatible`；本机 `aegisai-qwen25-planner:latest`；digest `15aaf3fda3b8e9bb6724e5e9911eec3b9cbdb6bd967646b6bf49ee9846b7ec16`；实际temperature=0.0、JSON Schema、模型超时60秒、输出上限4096。
- Planner `investigation-plan-v6`，提示SHA256 `7075cae933bb2eba41504e62248b63119320435689dae60b44e7199d5c32e0ab`；答案仍确定性Composer。Embedding保持Mock384维，不能声称整个模型栈全真实。
- `ONLINE_EVALUATION`：2026-10-15 15:35:32至15:58:46 UTC（北京时间23:35:32至23:58:46）。HTTP客户端180秒；固定输入顺序、独立请求键，不命中旧调查缓存。
- 知识来源为 `FROZEN_PUBLIC_SOURCE_GRAPH_REPLAY_NOT_LIVE_REFRESH`：12份公开资料快照，UUID/哈希与历史Phase13-G一致。未在线刷新、未按金标新增资料。43个中性受控资产仅来自原题明确组件/版本，不是企业扫描。
- Gold仅在最后比较使用；不进入Prompt、Retrieval、Context或Tool输入。原题ID不进入资产名称/HTTP请求。实际服务、评测、测试数据库分离。
- 该数据只有5个公告簇，经过开发排错，非独立保留集。新配置采用B5现有JSON Schema/60秒，历史13-G为JSON Object/40秒；没有公平控制，不能把新版差异归因某单一架构特性。

冻结资料及哈希见 [实验记录](evaluation/reports/phase14b6-human49-20261016/experiment.json)。原始HTTP、执行日志、服务完整启动证明及库存映射在本地 `work/phase14b6/`，不上传凭据或私有模型提示。

## 5. 49题实际结果：三层分开

| 执行覆盖（题） | 数量 | 解释 |
|---|---:|---|
| 技术适配取得正式结果 | 42 | 37单调查+5批量调查；不等于42题答对 |
| 缺部署版本 | 5 | 已调用创建入口，NEED_CONTEXT，没有捏造Run或答案 |
| 范围不支持 | 2 | 跨公告且无明确目标，BATCH_TARGET_REQUIRED；未调用调查API |
| 程序执行失败 / 未处理题 | 0 / 0 | 全部49题保留 |

37个单调查Gate：PASS_WITH_WARNINGS=6、REPLAN_REQUIRED=15、HUMAN_REVIEW_REQUIRED=16。5个批次的10个子调查全部回读，分别6个REPLAN_REQUIRED、4个人工复核。**共47个实际调查：6 / 21 / 20；没有PASS。** 批次没有单一Gate，不与单调查状态强行加成题目成功率。

47次真实Planner调用，均实际VALIDATED，0重试；261次原工具调用记录，0额外补查调用。42题成功投影耗时平均33.059秒、P95 69.603秒；不是所有49题耗时的分母，也没有冷启动控制。

| 原规则评分 | 本轮结果 | 分母/限制 |
|---|---:|---|
| 严格整题字段匹配 | **0/49** | 所有原必需字段同时严格相等；失败/缺信息题不剔除 |
| 风险字段匹配 | **0/10** | 原风险适用集合，非全部49题 |
| CVE字段 | 2/5 | 仅编号字段，不是整题事实准确率 |
| Patch状态 | 1/10 | 部分字段正确，不包装成整题通过 |
| 原拒答质量口径 | 1/49（2.04%） | 原结构化UNKNOWN与标志一致性；NEED_CONTEXT未投影成UNKNOWN，不能擅自加分 |
| 工作流步骤覆盖 | 39.29% | 已记录步骤覆盖，不等于多跳推理正确率 |
| Evidence Coverage / Hallucination / 语义正确性 | **PENDING_HUMAN** | 不能由引用存在代替独立复核，也不填0%/100% |

原评分器原样运行；没有新匹配规则。离线再次复现所有指标完全一致，新增模型调用0。详细 [指标](evaluation/reports/phase14b6-human49-20261016/metrics.json)、[执行汇总](evaluation/reports/phase14b6-human49-20261016/execution-summary.json) 与 [复现入口](experiments/phase14b6/reproduce_metrics.py)。Baseline RAG-only / 无Verification仍NOT_IMPLEMENTED，没有对照优势结论。

## 6. 补查在真实样本中实际做了什么

一次补查开关启用，仍限1轮、最多3次新增采集、批次共享、原deadline/权限。**本轮0次发布v2、0新增证据、0缺口解决、0额外模型/工具调用。**

47个调查的停止原因：GATE_NOT_REPLAN=26、NO_UNREAD_EVIDENCE_ENTRY=18、UNSUPPORTED_GAP=3。弱证据/冲突已经被首次消费，不符合“未读入口缺口”准入，不能因已有资料而假称补查修复成功。B5合成分页场景取得3条证据的历史结果不能充当这49题的表现。所有最终结果v1，首版即最终版，没有新旧版本混读。

## 7. 输出复核与数据疑点

已生成真实文件夹 `outputs/AegisAI_Phase14B6_OutputReview_Package` 及同名zip，位于用户原工作目录。49题均含原题输入、实际HTTP结果（含批次全部子项）、事实链、原资料、可填写表单。42份计量复核表、49份通用表均PENDING；没有代签。

12份来源原文及哈希保存。482个来源引用记录中462个可按原JSON Pointer直接提取；20个使用派生range_id而非原文Pointer，明确未直接解析，保留原资料和引用供人工查源，不默认无效或有支持。Quote只是原文提取，不是支持度结论。

交付副本移除可重放请求键，scope_key使用短范围标签并提供原始非鉴权范围对照；原始本地HTTP及预测哈希保留。扫描初次标记请求键/范围键，逐项确认后仍将公开副本脱敏；最终暂存交付与完整复核文件夹均零发现，没有添加扫描规则例外。机器记录中的范围标签不应直接回放到生产服务。

需人工核对：相同发布主体资料是否独立；影响范围分支/发布时间；CVSS版本、缺值占位与vector；修复版本与提交/部署的区别；PoC缺资料与NO_EVIDENCE的区别；原基准优先级与系统正式Priority语义；拒答是否合理。金标未变。如金标有疑点，另行人工在下一数据版本修订。

## 8. 本轮实际工程验收

| 实际命令/检查 | 结果 | 范围 |
|---|---|---|
| `python scripts/ci/run_database_tests.py --full --output work/phase14b6/full` | **1725 passed，0 failed/errors/skipped，退出0；1924.72秒，175警告** | 全部backend/tests、两个独立空PostgreSQL；无排除，历史1724+新增1 |
| `python -m pytest -q tests/aegisbench` | **138 passed** | 历史129+新增9；不是问答正确率 |
| 正式批量HTTP新增用例 | 1 passed | 已在全量1725中，不能相加 |
| 前端实际测试 | **72 passed，0失败/跳过** | 无本轮新前端功能 |
| JS/TypeScript/OpenAPI契约 | 24个JS语法、类型、56操作/5组/40对象检查通过 | 原生JS项目无应用构建脚本，build=NOT_APPLICABLE |
| `python experiments/phase14b6/reproduce_metrics.py` | 49题评分完全复现 | 离线，只读结果；0模型调用 |

全量警告保留，主要包括既有故障注入枚举序列化与新增HTTP测试的TestClient timeout提示；没有过滤或通过改跳过掩盖。初次TDD失败、适配器新用例失败和修复后的输出均在本地保留。GitHub执行本轮当前提交的四项CI；当前代码CI：portable687（1明确deselected，不替代全量）、数据库关键276、评测138、前端/类型与仓库安全通过。最后交付提交的检查见PR当前Checks，不沿用旧阶段CI。

## 9. 完成度与唯一下一业务优先项

系统已有模型入口、受约束规划、多专业Agent、核验/Gate、资产版本与多资产、补查、七页前端、情报采集/富化和评测框架；本轮完整运行与交付已完成。**业务可靠性未达验收，不能给整个项目100%完成或“问答强”的结论。** 公平Baseline、49题本轮输出的人审、实际企业库存和生产部署效果仍未证明。

下一轮只建议优先修复：**影响范围来源证据 → 规范化版本Claim → 既有核验/资产判断的消费契约。** 本轮版本Claim出现unsupported表达、适用分支冲突和来源作用域/独立性不足，继而资产影响UNKNOWN、Risk不可交付；应保留原文定位与时间/分支范围，区分真正冲突和表达差异，再以既有规则验证。不要降低Gate或把UNKNOWN改安全，也不要先调模型/评分。本轮停止，不自动实施下一阶段。

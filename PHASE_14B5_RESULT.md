# Phase 14-B5：证据缺口驱动的一次受控补充调查

日期：2026-10-15。仓库：shuabirfana-a11y/AegisAI。本文件是本阶段工程交付，不是参赛材料或版本冻结。

## 1. 基线与实际缺口

基线提交：68ea13f24946f536c45f76c1b7a41ddf97ab12bf，包含 Phase 14-B4.1 数据隔离、迁移配置、契约及空知识索引修复。分支：codex/phase14b5-evidence-supplement。[草稿 PR #30](https://github.com/shuabirfana-a11y/AegisAI/pull/30) 依赖 #29，目标为 codex/phase14b4-1-regression-reliability；上游依次依赖 #28、#27。未合并 main、强推或发布 Release。

已核对仓库归属、实际分支及提交，未发现适用 AGENTS.md。原未跟踪 Phase 14-C 文件保留。本轮创建两个独立 PostgreSQL 测试实例；实验另用独立数据库，不复用旧共享测试配置。

原 HTTP worker 实际调用 InvestigationOrchestrator，但原 Gate 后没有针对 Claim 缺口的补查。采集积压续跑和同一工具重试不能替代该功能。本轮复用 Task Contract、专业 Agent 路由/Executor、Runtime、Tool Gateway 和原 Verification/Risk/Gate/Composer。

**首版只解决：已采集知识库存在、首次有界读取未消费的影响范围证据。** 没有联网刷新、新来源、已有弱证据的一般补强或自由重新规划。固定合法动作足够，补查不增加模型调用。

## 2. 实际流程与准入

```text
原调查、Gate、答案 v1 封存
  → 结构化缺口、库存、权限与预算检查
  → 原子获得一次补查资格
  → 固定 evidence_search Task，按 Claim 定向 get_evidence
  → 新采集 Run / Investigation Artifact
  → 原 Verification、Risk、Gate
  → 新答案 v2 完整提交后更新最新引用
```

确定性准入同时检查：

- 原 Gate=REPLAN_REQUIRED；结构化原因限 OBJECTIVE_NOT_COVERED、REQUIRED_TASK_INCOMPLETE、REQUIRED_DETERMINATION_UNAVAILABLE、UNRESOLVED_ANALYSIS，且包含 version_impact 未覆盖。
- 原调查、核验产物有效，没有失败工具、关键冲突或完整性问题。
- 目标漏洞、已授权资产、组件、部署版本及封存 Version Observation 明确；当前库存版本、修订、环境/暴露范围与原快照一致。
- 存储 Claim 最多3条，限 AFFECTS_VERSION、FIXED_VERSION、CVSS_SCORE，必须含影响范围 Claim；处于 PENDING/INSUFFICIENT_EVIDENCE、尚无已消费 Evidence，并且没有查过同一具体入口。
- 原截止时间、总调用预算、批次预算、取消与执行槽检查允许。

不根据错误文字触发。缺用户版本仍 NEED_CONTEXT；关键冲突仍人工复核；已有弱证据、无入口、已查过、库存变化或预算不足明确停止。一次查询未取得资料不能推出资料不存在。

固定任务继续通过原白名单、权限和 DAG 检查；只允许 READ_ONLY 的 get_evidence，绑定原漏洞及 Claim。来源文本请求写入、访问其他用户资产或执行攻击不会成为执行指令。

## 3. 预算、幂等、取消与多资产

每个逻辑调查最多1轮；每个多资产批次最多1个符合条件的子项获得额度。新增采集最多3次，失败和超时尝试也计数；未增加重试层。原总工具上限、已发生调用和截止时间继续生效。

成功场景新增采集3次、重新风险读取1次、Gate读取1次，总额外工具5次；规则核验没有模型调用。采集预算和全部下游预算分别记账，不把“三次采集”说成“全流程只有三次工具”。

稳定身份绑定父调查、原 Gate ID/内容、缺口、资产快照及策略版本。数据库锁与持久化 grant 保证并发只获一次资格；等待工具期间不长时间持有事务。批次统一分配剩余预算，已完成资产不重跑，不同资产部署版本、判断和答案独立。

取消意图与新步骤创建共享锁边界，调用前后均检查。取消、库存漂移、超时和过期回调不能发布；最终再次校验并原子保存完整答案及最新引用。GET状态、Trace、版本及历史不触发新调用。

中断保留未完成记录，过期 heartbeat 标记 recovery_required，需要人工处理。**未实现自动断点恢复，不声称安全自动重放。** 来源暂时故障停止并计数；权限、引用和程序错误保持错误，不包装成证据不足。

## 4. 原结果、新证据与核验

原 Planner、调查 DAG、Task 状态、调查 Run、Artifact、Verification、Risk、Gate 和答案 v1 不覆盖。补查创建独立采集 Run 和新下游产物；附加证据消费前校验所有权、来源、封存引用及指纹。

证据按 Claim、内容哈希、观测值和立场去重；重复转载不是独立支持，损坏引用不能确认。只有真实新 Evidence 被原核验消费，并支持对应 Claim，才记为缺口解决。补查完成不等于 Gate PASS，新资料仍可能不足或冲突。

## 5. API与前端接入

服务端 AEGIS_EVIDENCE_SUPPLEMENT_ENABLED=1 启用，默认严格关闭（0）。不新增客户端预算/权限参数，不新建页面。

- 原创建接口的 worker 自动接入补查。
- Status增加 supplement、processing_complete、result_version；过程状态与 Gate 业务状态分离。
- Trace/Artifacts/Integration/Answer 四个既有 GET 支持 ?version=1|2；默认完整提交的最新版本，v1始终原结果；v2未就绪409，非法版本422。
- 前端在 processing_complete=false 时继续刷新，并把同一 result_version 绑定四次读取；保留请求竞态控制及取消。
- 摘要包含父 Gate、具体 Claim、工具记录、新 Evidence、调用数量和停止原因，不公开参数、原文、密钥或 worker token。
- 批次子项附版本/补查摘要。history 的 status 筛选仍依据首次根调查状态，不能据此推断 v2 Gate。

实际 OpenAPI、TypeScript、Client及既有交接包同步。评测HTTP投影先验证公开 AnswerResponse，剥离 result_version 后验证原领域 AnswerEnvelope；只处理版本元数据，不改变事实或计分。评测等待 processing_complete 并绑定同一版本读取。

## 6. 有限真实模型验证

运行核心代码冻结于99d5c0abaf176e17f53b0622541c52c02a22da03，tracked_dirty=false。随后兼容修复只涉及HTTP评测投影、测试夹具及实际Schema导出；真实验证后应用/前端业务字节未变化。

- 本地真实模型 aegisai-qwen25-planner:latest；digest 15aaf3fda3b8e9bb6724e5e9911eec3b9cbdb6bd967646b6bf49ee9846b7ec16。
- Provider=openai_compatible；JSON Schema；单次模型超时60秒，输出上限4096。原 InvestigationPlannerAdapter 实际显式传 temperature=0.0，未调整。
- Planner=investigation-plan-v6；实际提示文件 backend/app/agents/investigation/investigation_plan_v6.txt，SHA256=7075cae933bb2eba41504e62248b63119320435689dae60b44e7199d5c32e0ab。Answer Composer仍确定性生成。
- Embedding配置仍 Mock，该定向查询未调用 Embedding，不能称整个模型栈全真实。
- OFF库在任一组运行前克隆至ON库，初始资料、Claim/Evidence/来源/库存 UUID及输入相同，Run与业务缓存独立。来源清单SHA256=799cdaadeebab33bc900d9c26936b938feff72eeeecb60ff5c5ef5b633f87b75。

资料是明确标记的**受控合成分页缺口**，不是真实CVE事实、自然线上恢复、企业库存或独立Benchmark。没有把金标/预期答案送入模型。原采集辅助脚本曾把通用Planner提示哈希与默认温度描述记入配置摘要；现已按冻结代码的实际 InvestigationPlannerAdapter 更正脱敏记录，原调用观测不改。

| 对照 | 关闭补查 | 开启补查 |
|---|---|---|
| 原 Gate | REPLAN_REQUIRED | REPLAN_REQUIRED |
| 最终版本/Gate | v1 / REPLAN_REQUIRED | v2 / PASS |
| 新可用 Evidence / 被补齐 Claim | 0 / 0 | 3 / 3 |
| 额外采集 / 全部额外工具 / 额外模型 | 0 / 0 / 0 | 3 / 5 / 0 |
| 总耗时 | 64.953秒 | 83.812秒 |
| 原 Planner | 1次真实调用 | 1次真实调用 |

本地模型服务未做冷启动隔离，可能存在前缀缓存；耗时只记录本次观测，不构成性能改进结论。

ON父调查 e6aee547-d2b4-41f8-8754-4717df5a7e12；原调查Run 4960db3b-b0e6-4080-a192-66311eb39cac 保留；补查Run f00f5b66-a442-44a6-abed-597de86638a8，Artifact c45c1bc4-ecdf-4ca5-a659-3a5fa7ab37df。

原Gate 4e7151e2-9944-4496-a7c2-42b7981bed85，新Gate f8aaf752-c6df-47c4-9ebb-9f5afe67be2a；原答案 e3d6e606-a8ab-5f68-a55d-2537ab61a10a，新答案1ebe9176-7126-5dfb-9991-c8ed11b5cf6d。

三条Claim均由v1的 INSUFFICIENT_EVIDENCE/无支持，变为v2的 CONFIRMED/具体新Evidence：

| 类型 | Claim ID | 新 Evidence ID |
|---|---|---|
| AFFECTS_VERSION | 2e575b30-f246-4a9b-899c-6ffe9a3a1672 | c44639c0-33d8-43dd-82a4-c8e65d3a1cce |
| CVSS_SCORE | fe4b7f42-4e96-428a-9f1a-4ae46456844e | 90574971-4040-4167-85e0-859b9759a026 |
| FIXED_VERSION | ffd3ebb9-ccfd-48c3-88cd-f25fde5dfd23 | a5145309-a735-4969-b9b5-a9e833310684 |

四类最新及v1读取均HTTP200，原产物未覆盖。脱敏证明见 [validation.json](docs/phase14b5/validation.json)。原观测、实验数据库及日志保存在本机 work/phase14b5，不发布大量内部快照。

### 多资产只补一个子项

另一次真实数据库/HTTP功能验证使用明确Mock模型和合成来源，不是上述真实模型对照。批次 f4da27e2-27e7-4a29-9437-156dcda1354c：首资产已完整通过，仍为v1/PASS、零补查，答案与原版完全相同；第二资产因未读依据阻断，执行一次补查成为v2/PASS。两资产独立版本和答案，重复读取无新增调用，模型共2次Mock调用。

该夹具在首子项完成后、第二子项规划前追加合成来源记录，制造仅后者的分页缺口；原Evidence行没有改写。它验证只补合格子项，不属于固定来源OFF/ON比较，不计为自然恢复或准确率。最初两次辅助计划的验收条件/未绑定Claim参数被现有Planner拒绝，原记录保留；最终使用合法原计划，不放宽Schema。

## 7. 实际回归与修复

新增后端21个用例（补查16、HTTP5，含参数化），前端4个。1702是历史基线。

**完整后端实际结果：1723 passed，0 failed，0 errors，0 skipped，退出码0，耗时1701.79秒（28分21秒）。** 其中21项为本轮新增，已有1702项均在本次实际执行；JUnit记录与完整输出保存在 work/phase14b5/full-fixed。23条警告保留，主要来自旧契约故障注入测试的枚举序列化，不将警告隐藏或说成零警告。

| 实际命令/范围 | 本轮结果 | 边界 |
|---|---|---|
| python scripts/ci/run_database_tests.py --full --output work/phase14b5/full-fixed | 1723 passed、0失败/错误/跳过 | 全部backend/tests、两个独立PostgreSQL，无排除 |
| GitHub PostgreSQL关键回归 | 274 passed | 全量子集，不相加 |
| GitHub便携单元/契约 | 687 passed、1 deselected | 明确便携范围，不替代全量 |
| python -m pytest -q tests/aegisbench | 129 passed | 评测框架回归，没有正式实验 |
| 前端测试 | 72 passed、0 failed、0 skipped | 旧68+新增4 |
| TypeScript .github/tsconfig.contracts.json | 通过 | 实际契约类型 |
| scripts/ci/check_frontend.mjs | 24个JS通过 | 原生JS，无build脚本，build不适用 |
| 实际Schema/导出一致性 | 通过 | 56HTTP操作、5组、40合成对象；另11组评测HTTP Schema |
| staged / Git历史秘密扫描 | 通过；最终交付再检查 | 不输出凭据 |

首次完整回归尝试发现4项兼容问题后停止，原日志保留，不算完成的全量结果：2项旧Trace纯测试未配置新增依赖，2项HTTP评测拒绝新增版本元数据。最小修复夹具及公开响应投影后，在空隔离测试库重新全量执行。CI另检出评测Schema导出过期，已按真实代码同步。没有过滤失败测试、降低断言或调整评分。

新增用例覆盖有用新证据、无有用证据、未知版本、关键冲突、重复资料、超时/限流/权限、并发grant、取消/过期发布、预算/中断、恶意来源、多资产共享额度、新旧版本回读和客户端越权预算。独立多资产“仅一子项缺口”补验单列，不计入pytest总数；辅助计划错误与修订记录保留。

## 8. 修改文件范围

- 新增 backend/app/orchestration/supplement/：协议、准入、持久化、控制、固定Runtime及服务。
- Tool get_evidence 输入/适配：可选Claim过滤，权限保持。
- Verification输入/快照及Analysis/Gate来源适配：绑定有效封存引用，可信判定算法未改。
- 既有Investigation API/service/schema、路由、多资产service/schema：补查、版本、状态、取消与共享预算。
- 前端既有Client、assistant轮询及TS契约：版本绑定，无新页面。
- 补查/HTTP/前端测试、旧Trace夹具、数据库CI入口及精确源哈希授权清单。
- HTTP Evaluation适配及真实导出；原Metrics、Gold与历史结果未改。
- 实际OpenAPI/TS/接口导出、交接包镜像、原三份交接说明、当前状态、本报告及一份脱敏验证记录。

没有数据库迁移、新Agent、扫描器、新来源、Planner提示修改或Gate规则修改。精确文件列表见PR。

## 9. 六项验收回答

1. **真正针对缺口补查？** 是，固定Task按具体Claim读取，不重跑原Planner或原调查DAG。
2. **补齐哪些依据？** 受控场景中的影响范围、修复版本、CVSS，三条新Evidence实际进入原核验；不是只看Gate变绿。
3. **哪些仍正确停止？** 缺用户版本、冲突、无有用新证据、重复资料、权限/完整性错误、取消、库存漂移、过期、预算不足。未获得批次额度的子项保留缺口。
4. **新旧产物能分别读取？** 是，原Run/Artifact/Gate/答案保持，v2独立持久化，读取不执行；未完整提交的v2不公开。
5. **单/多资产与完整回归？** 真实模型OFF/ON、批次共享预算、仅补缺口子项及独立版本已验；完整后端1723项本次实际通过，零失败/错误/跳过，前端72项通过。
6. **改善什么，未验证什么？** 主动补齐一种已有权限内的明确证据缺口，然后由原规则再裁决。没有一般自愈、自然恢复成功率、问答准确率提升或竞赛档位结论。

## 10. 当前整体完成情况与改进

| 能力 | 实现情况 | 当前证据边界 |
|---|---|---|
| Gateway/Planner/Runtime/三Agent/Gate/Answer | 已实现，单资产HTTP闭环可运行 | 可执行不等于安全答案准确 |
| 资产/版本、知识关联、多资产汇总 | 已实现，判断及历史快照可追溯 | 受控库存，未做真实企业库存评测 |
| 采集/标准化/富化/PoC/知识检索 | 框架与有界流水线已实现 | 部分网络来源失败，不能说全来源持续在线 |
| 七个前端页面及调查展示 | 已交付并有联调测试，本轮同步版本读取 | 功能PR仍在依赖分支，不等于main或公网已上线 |
| Ground Truth/AegisBench | 49题已批准，正式在线基线已有 | 仅5个公告簇，存在开发样本交叉 |
| 一次受控补查 | 本轮实现与验证 | 默认关闭，只补已采集未读资料，不联网刷新 |

**不提供没有依据的全项目完成百分比。** 工程主链已齐备，业务效果的证明仍明显落后。

历史 Phase13-G 实际49题严格字段匹配为0/49，Risk为0/10；37题技术适配成功，12题未进入有效回答。这不是自然语言语义准确率，也不能删掉或说成尚未评测。Evidence Coverage/Hallucination的系统输出独立人审仍待完成；公平RAG-only/无Verification对照未实现。本轮没有重跑49题或产生新准确率。

建议后续优先级（本轮不自动执行）：

1. 逐条核对49题的缺字段、来源适用性、版本/风险和接口支持，补真实可追溯事实链，保持Gold/指标/Gate不变；分开记录契约失配与语义错误。
2. 完成原复核人员对实际输出的证据/幻觉复核，公平实现两个Baseline，并另建未用于开发的留出问题。
3. 提升现有来源可用性、更新时间及发布者独立性；接入成员实际提供的资产库存，再评估有界联网补查，不能猜库存。
4. 负责人确认后整合依赖PR，再验证前端完整、缺上下文、冲突三类实际展示与复现环境。当前不自动合并或公网部署。

完成本阶段后停止，不开展新功能、Benchmark重跑、PPT、发布或版本冻结。

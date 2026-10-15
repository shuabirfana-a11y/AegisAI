# Phase 14-B5：受控证据补查（实施中）

基线：68ea13f24946f536c45f76c1b7a41ddf97ab12bf，依赖草稿 PR #29 → #28 → #27。仓库身份已检查；未发现适用 AGENTS.md；保留未跟踪的 Phase14-C 文件。

## 实施记录

现有 HTTP worker 调用 InvestigationOrchestrator；首次结果由 Gate 与 AnswerComposer 固化。没有证据缺口补查，采集任务重试与本轮不同。

首版限定：目标、资产版本和原产物完整，Gate 结构化阻塞涉及 version_impact，已有 AFFECTS_VERSION Claim 缺少可用支持时，使用已注册 get_evidence 的新增可选 claim_id 过滤读取此前未消费的资料。权限仍 READ_ONLY，任务类型仍 evidence_search。没有新增来源或网络能力。

复用原 Investigation Artifact、资产观察、Verification、Risk、Gate、Composer；新建一次补查 Runtime 及新 Verification/Risk/Gate/Answer，不重跑原 Planner 或原调查 DAG，不改原任务状态。新旧结果独立存储，默认关闭，服务端开关启用。预算包含原调用及补查下游，原 deadline 不重置。

预计修改：补查策略/持久化/控制与适配文件；已有 Evidence 查询 Schema/过滤；Verification Snapshot 受约束附加来源与 Analysis/Gate 来源绑定；HTTP worker/版本读取、OpenAPI/TS 同步、测试与现有交接说明。可信判断算法不变。

本文件将在实际测试、HTTP 验证与 GitHub 检查完成后更新。1702 是历史基线，业务准确率未测。

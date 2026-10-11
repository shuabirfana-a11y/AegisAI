# Phase 13-B：AegisBench 评测子系统设计

依据用户 Phase 13-B 实施指令，目标是提供可复查的安全样本、标注规范、指标、基线、实验记录及报告。只扩展 evaluation、独立测试、评测 CI 和文档；冻结 Planner/Runtime/专业 Agent/Integration Gate/数据库/API/前端业务文件。

## 当前事实与复用

已有 evaluation/dataset.py 的人工 gold 门槛、classification/abstention/latency 指标、只读 loopback RuntimeAdapter；v0.1 是 24 条候选题和 0 条 gold。它们保持兼容。Phase 11-D 是 Python 内部 Orchestrator，没有新的公共调查 API。本机生成模型默认 mock，因此不能声称真实 LLM 评测通过。

## 数据与标准答案

建立新 AegisBench-v0.2-pilot，覆盖事实查询、版本判断、POC/Patch、资产风险、复杂多跳五类。只采集可重新获取的官方 GitHub Advisory JSON，冻结必要原字段、源 URL、发布/更新时间、获取时间、内容摘要。保留 CVSS 版本、未知字段、多个版本范围。

问题与标签分文件；运行输入不含 expected_answer 或人工判定。新 schema 和 ground_truth/schema.md 包含用户要求的 id/question/input_context/expected_answer/evidence_refs/confidence，同时保留标注人、复核人、类型、状态和注释。自动提取的是待人工复核参考标签，不冒充人工 gold。复用既有 gold_exclusion_reason；正式指标只有人工 APPROVED/REVIEWED 标签才计分。没有 gold 时正式指标为 null/NOT_EVALUATED。

资产为明确标识的受控评测场景，不声称真实用户部署；CVE、组件、版本范围和补丁来源必须可追溯。版本正例、修复边界负例和缺失版本 UNKNOWN 都保留。没有可解释的漏洞利用核验记录时，不能标记 Verified Exploit。

## 指标

复用分类 Precision/Recall/F1、False Safe、延迟与弃答基础。补充字段/答案 Accuracy、Risk/Priority Accuracy、多跳必要步骤覆盖、Abstention Precision/Recall/Quality。

Evidence Coverage 需要支持性判断及可解析的来源定位，不能用 URL 数量代替。开放自然语言 Claim 的幻觉/支持判断依赖独立人工 outcome audit；没有审核记录则保持 null。结构化已标注字段可精确比较，但字段正确率不冒充自然语言语义准确率。缺预测/失败留在可评分分母；未执行基线单列，不能赋 0 分或 100 分。

## 基线与执行

1. keyword_search：冻结来源上的真实关键词检索，输出检索结果；不声称生成答案。
2. rag_only：一次检索后通过现有 ModelGateway.generate_structured 生成，拒绝 Mock 作为正式模型结果；不直接使用供应商 SDK。
3. fixed_workflow：复用现有 normalizer 与版本匹配算法，冻结来源上的确定性流程；能力范围和无生成模型状态单独披露。
4. aegisai：调用现有 Python InvestigationOrchestrator 的可选适配器；要求显式专用评测库、actor、真实 Model Gateway 以及相同数据快照。配置缺失时 NOT_EVALUATED，绝不用旧 assistant 或手工输出冒充 Phase 11-D。

默认 python evaluate.py 离线执行可用检索/固定流程，记录其他基线不可用原因。真实模型/Orchestrator 通过显式选项启用，默认不联网调用模型、不修改数据库。正式比较要求相同问题、资料快照、模型/参数、限额和审核覆盖；不满足时报告不可比较。

## 实验与报告

保存 dataset/ground-truth/source SHA256、Git revision、adapter/model/prompt 版本、参数、UTC 时间、每例原始结构化输出和实际耗时。配置严格允许列表，不输出 API Key、数据库连接串或环境全量。JSON/Markdown 报告区分执行观察、正式指标和阻塞原因。工程测试与正式业务评测不混用。

## 验收及停止

TDD 实跑验证 schema、gold 门槛、证据支持、失败分母、UNKNOWN、幂等数据、报告及基线。冻结业务哈希不变；敏感扫描和当前 CI 通过。交付 PHASE_13B_RESULT.md，明确正式 gold 和模型限制；停止，不进入前端/UI/新 Agent。

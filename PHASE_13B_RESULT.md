# Phase 13-B：AegisBench 完成报告

## 1. 交付范围与当前结论

已建立独立评测框架、真实来源候选集、标注规范、指标、四基线适配、实际离线运行与报告生成。工程基线保持稳定。当前人工标准答案为 **0 条**；用户确认先完成框架和候选数据。没有真实模型的 AegisAI/RAG 质量成绩，不能声称情报准确率或相对提高。

## 2. 架构

```text
官方 API 记录 → 冻结来源投影/哈希/获取时间
                      ↓
问题与资产控制场景 → baseline adapters → 逐例 Prediction
                      ↓                      ↓
独立人审 Ground Truth ───────────→ Metrics → JSON/Markdown Report
独立人审 OutcomeAudit + 输出哈希 ────┘
```

所有运行输入与标准答案分开。旧 v0.1 框架、空 gold、种子与来源示例保持原字节。新代码仅在 evaluation/bench、根 evaluate.py 和评测测试中；Model Gateway、Python Orchestrator、版本算法直接复用。

## 3. 数据集与标注

- AegisBench-v0.2-pilot：49 条问题；facts 5、版本影响 17、POC/Patch 10、资产风险 10、多跳 7。
- 5 份实际获取的官方 GHSA 公告：PyTorch 2、LangChain 1、LangGraph 1、vLLM 1；不是 49 个独立漏洞。
- 每份来源保存 upstream 时间、retrieved_at、API URL、投影哈希、完整 API 输出哈希与 attribution。JSON Pointer/excerpt 精确验证，源路径越界与摘要漂移拒绝。
- 49 条机器参考均为 MACHINE/SOURCE_REFERENCE/PENDING，人工 gold=0；controlled asset 明示演示输入，版本空档场景不声称真实部署。
- 原始 PoC 正文不保存或执行；无独立利用验证正例。release fix 的公告确认和 commit 候选分类分别处理。

## 4. 指标与基线

实现事实/字段准确率、受影响分类 Precision/Recall/F1/False Safe、POC/Patch 分类、风险/优先级字段准确率、弃答精确率/召回率/行为准确率、流程步骤覆盖、实际延迟。Evidence Coverage/Hallucination 需完整人审结果与支持/反证；不能把引用存在当支持。失败/缺预测保留在分母，0 分母为 null。

四基线：keyword_search、rag_only、fixed_workflow、aegisai。原生适配使用真正 Phase11-D Python InvestigationOrchestrator，缺真实模型、匹配资料或请求上下文时记录 NOT_EVALUATED；从未用旧 assistant 或人工 Artifact 冒充执行。

## 5. 实际首轮实验

执行 `python evaluate.py`，生成 196 条逐例记录：

| 基线 | 成功返回 | 失败 | 未评测 | 正式质量 |
|---|---:|---:|---:|---|
| 关键词 | 49 | 0 | 0 | NOT_EVALUATED |
| RAG-only | 0 | 0 | 49 | NOT_EVALUATED：真实模型未配置 |
| 固定流程 | 49 | 0 | 0 | NOT_EVALUATED |
| AegisAI | 0 | 0 | 49 | NOT_EVALUATED：真实 Planner 模型未配置 |

首轮真实记录在 `evaluation/reports/phase13b-pilot-20261011/`。关键词 10/49、固定流程 49/49 与机器参考相符，仅为 extraction/policy wiring diagnostic，**不是正式准确率**。报告明确 PARTIAL / NOT_EVALUATED / NOT_COMPARABLE；没有生成虚假的 uplift、语义问答准确率或多跳效果结论。

## 6. 修改文件

- `evaluation/bench/`：严格协议、来源采集、冻结数据加载、指标、四基线、guarded native factory、Runner。
- `evaluate.py`：默认离线入口与已记录输出的重新计分。
- `evaluation/datasets/AegisBench-v0.2-pilot/`：49 问题、49 待审参考、5 源投影、manifest、演示与许可说明。
- `evaluation/ground_truth/schema.md`、`evaluation/METRICS.md`、`evaluation/BASELINES.md`、`evaluation/experiments/README.md`、README 新阶段入口。
- `evaluation/contracts/`：Pydantic 导出的评测 JSON Schemas；`evaluation/reports/`：真实记录与待审结果包。
- `tests/aegisbench/`：协议、数据、数学分母、审核绑定、Runner/原生边界、脱敏与离线集成测试。
- CI 增加离线评测测试与 smoke run；`.gitignore` 增加执行 scratch 和本机原生请求映射的排除。

没有修改后端业务、Planner、Runtime、三 Agent、Integration Gate、数据库、前端或原 API。

## 7. 验证

- 新增评测测试：32 项已实际通过；先观察 RED 再实现 GREEN。
- 原后端便携回归：398 passed，1 个真实缓存 embedding 测试明确排除。
- 前端：21 passed；TypeScript 交接契约与 17 个 JavaScript 语法检查通过。
- 原 OpenAPI/Pydantic：34 HTTP operations、5 Schema groups、40 合成对象验证通过；不连接数据库。
- 工程门禁：6 passed。历史 1261 工程整套数据库测试本阶段未重跑，不能把这些分项叠加宣称新的全量通过数。
- 全分支独立审查、敏感扫描和 GitHub CI 在最终发布前复核；最终记录见本报告后续验收段。

## 8. 当前限制与后续准备

正式成果仍需要真实人审：标注人逐条核对、另一人独立审核，再补真实结果 Claim 审查。数据缺独立 holdout、平衡正负类、利用验证正例和多来源冲突案例。摘要字段是严格匹配；流程步骤覆盖不证明语义推理正确。

Native AnswerEnvelope 最多一个资产，priority 体系与参考 triage policy 不同；字段/风险政策和任务范围需先在人审数据中统一，不能强行改业务或翻译 enum 来制造提高。原生 live adapter 的 guarded DB 正向完整链路没有配置和运行，因此不能说此阶段真实四基线比较已经完成。

下一次授权可逐步补人审 gold、独立 holdout、真实兼容模型与同语料实验；现阶段所有工具与材料已可供此工作使用。Phase 12-B 的调查 HTTP API 暴露仍是单独工作，本阶段不处理。

## 9. 停止条件

本阶段只完成 Benchmark 基础与候选数据建设。停止，不进入前端联调、UI、新 Agent 或核心业务优化。

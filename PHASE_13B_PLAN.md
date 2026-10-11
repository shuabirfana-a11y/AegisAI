# AegisBench Phase 13-B Implementation Plan

> For agentic workers: use superpowers:executing-plans inline, TDD per task and one fresh whole-branch review at the end. The user already supplied the implementation scope and requested execution.

**Goal:** 建立真实来源、可复查且不会编造成绩的安全评测框架。

**Architecture:** 在现有 evaluation 中增加独立 bench 子包，复用旧 gold 与指标函数、现有 Model Gateway/Orchestrator/版本比较；新的数据集不覆盖 v0.1。四个基线分别记录真实执行能力和不可用原因。

**Tech Stack:** Python 3.12、现有 Pydantic/pytest/jsonschema；没有新 Agent 框架或模型 SDK。

**Spec:** docs/superpowers/specs/2026-10-11-aegisbench.md

## Global Constraints

- 所有业务/API/数据库/前端文件保持原字节，不创建公共 API。
- 自动标签不能进入正式 gold，Mock 不能成为真实生成模型结果。
- 不启动服务、不改生产/开发数据，不默认调用付费模型。
- 运行时不能读取标准答案；比较数据源必须一致；失败不能移出可评分分母。
- 报告不含凭据；缺失分母为 null，不把候选样本当独立测试集。

## Review Focus

- expected_answer 或标签被误传入检索、提示词、Runtime。
- 候选标签/测试 fixture 通过伪造人工字段进入正式成绩。
- 引用不存在、定位不支持 Claim，却被计为 Evidence Coverage。
- 缺预测、超时、重复样本或缺失类别抬高成绩。
- 不同 corpus/model 或旧 assistant 冒充 Phase 11-D 产生不公平比较。

## Task 1：数据协议、真实来源与候选数据

Files: evaluation/bench/{__init__,schema,data,sources}.py；evaluation/datasets/AegisBench-v0.2-pilot/；evaluation/ground_truth/schema.md；tests/aegisbench/test_data.py。

Interfaces: load_benchmark(manifest_path) 返回 questions、annotations、eligible_gold、sources；旧 gold_exclusion_reason 为唯一人工准入门槛。

- [ ] 先写测试：标签不能出现在问题中；重复 ID、摘要漂移和越界 source 路径拒绝；机器标签和 TEST_FIXTURE 不准入。
- [ ] 运行并看到新增模块缺失的 RED，再实现 schema、数据加载和官方来源采集。
- [ ] 采集可验证真实资料，生成五类候选及独立参考标签，保留 unknown/复核状态。
- [ ] 验证数据集及 provenance；提交这一独立交付。

## Task 2：指标及 Outcome Audit

Files: evaluation/bench/quality.py；tests/aegisbench/test_quality.py。

Interfaces: score_variant(questions, annotations, predictions, audits) 返回分组指标、正式覆盖和问题明细；复用 evaluation.metrics 数学函数。

- [ ] 先写数值断言：缺预测入分母、零分母 null、Unknown 的弃答精确率/召回率、弱引用不等于支持、重复 audit 拒绝、没有人工 audit 的幻觉率 null。
- [ ] RED → 实现最小计分逻辑 → GREEN，保留支持性判断与必要多跳步骤的证据要求。
- [ ] 提交指标实现和真实测试输出。

## Task 3：四个基线及 Runner

Files: evaluation/bench/{adapters,runner}.py；evaluate.py；tests/aegisbench/test_runner.py。

Interfaces: adapter.run(question, corpus) 返回结构化 observed prediction，不接收标签；Runner 在运行完成后调用 score_variant。

- [ ] 先测无模型 RAG/AegisAI 不冒充成功、默认不触网/数据库、输入无 gold、失败记录及安全元数据。
- [ ] RED → 实现 keyword/fixed 实跑和可选 Gateway/Orchestrator 适配器 → GREEN。
- [ ] python evaluate.py 实际运行并保存每例结果和 JSON/Markdown 报告；正式无 gold 则 NOT_EVALUATED。

## Task 4：交付与验收

Files: evaluation/{README.md,BASELINES.md,METRICS.md}；evaluation/experiments/；evaluation/reports/；PHASE_13B_RESULT.md；.github/workflows/ci.yml 的评测测试步骤。

- [ ] 实际跑评测单元/集成、原基础后端/前端/Schema/业务哈希检查和敏感扫描。
- [ ] 最终独立审查，修复影响正确性问题；记录实际数据、结果和限制。
- [ ] Git 保存并发布本阶段独立评测 PR，保持团队分支与原基线；完成后停止。

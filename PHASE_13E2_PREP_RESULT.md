# Phase 13-E.2 准入冻结与首轮实验准备结果

日期：2026-10-13（北京时间）。**收到新复核包后，当前已由0/49更新为39/49人工批准；10条退回保留。本轮没有运行正式实验。**

## 1. 数据和准入

用户确认并提供“39通过/10退回”包。离线核对49条唯一HUMAN_RECORD：原Schema、题目/全题文件摘要、答案内容与复核绑定摘要、不同标注/复核身份字段、复核清单、冻结来源/精确定位全部通过。按原白名单投影39条，原Loader实际准入39，不是仅凭zip文件名计数。

原批准/退回文件字节保留到`evaluation/ground_truth/samples/approved`和`rejected`。原件evaluation.export_status仍NOT_PREPARED，**不修改签署内容**；机械导出结果另记 [IMPORT_RECORDS.json](docs/phase13e2/IMPORT_RECORDS.json)。39题的答案只按人声明的scored_fields复制，没有重写或给退回题补答案。

新冻结manifest：`evaluation/datasets/AegisBench-v0.3-human39-20261013/manifest.json`。共享旧不变49题/5公告簇来源，包含39 HUMAN_GOLD；10退回没有正式Gold。旧默认manifest仍是历史0金标版本，未来必须显式传入新manifest。原评分器、准入及默认值未改。

真实准入检查新manifest：exit0、39eligible、10门槛通过，无调查HTTP、模型或评分器调用。[检查记录](docs/phase13e2/readiness.json)。现有preflight的model_freeze_status是固定“未核验运行环境”的准备提示；本轮额外核对的是磁盘制品和计划配置，不能将两者混同。

## 2. 实验配置

`experiments/config/experiment-001-prepared.json`记录：Dataset版本/39批准/10退回及摘要；provider=openai_compatible；model=aegisai-qwen25-planner:latest；temperature=0.0；provider timeout=40秒；4096输出上限/json_object。它们来自原profile和Planner输入参数，**未宣称当前在线服务已使用这些值**。

模型manifest摘要`sha256:15aaf3fda3b8e9bb6724e5e9911eec3b9cbdb6bd967646b6bf49ee9846b7ec16`；manifest config和5layers共6个文件的大小/完整SHA均实际核对。只读文件、不加载模型、不调用API。[模型制品记录](docs/phase13e2/MODEL_ARTIFACT.json)。

Planner Prompt版本investigation-plan-v4；Prompt文本、Planner调用源码、确定性Composer和Answer契约均记录SHA。答案不存在独立LLM prompt，明确NOT_APPLICABLE_DETERMINISTIC_TEMPLATE。系统源commit为`c636c51111c64f04f0eec5c003d15df380a27a54`，即本轮之前的确切源码；数据/配置提交另外记录，不制造自引用版本。

## 3. Baseline、隔离与报告

Experiment-001准备完整链路；Experiment-002 RAG、Experiment-003无核验独立控制均NOT_READY。计划详见 [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md)。标准答案只有原准入与最终比较层可消费，API仅接原问题/资产输入，元数据和答案不发送给模型。报告模板所有指标null/NOT_EVALUATED，无输出或实验结论。

## 4. 测试

新增准备测试覆盖配置加载/版本与摘要、真实39准入、10退回排除、原件与投影一致、旧版本保留、GT请求隔离、空答案继续拒绝、模型/Prompt版本和空报告。首次6失败/1通过（材料尚未生成），材料完成后通过。实际命令和最终结果见 [验证记录](docs/phase13e2/verification.json)。

没有重新执行历史1426项或上一阶段DB/TCP调查；本轮不需要运行服务来准备数据。全部原业务、评测代码和旧冻结数据保持不变，只有进度/当前状态文档更新。

## 5. 是否允许启动

**数据门槛：通过（39≥10）。本轮执行授权：否。现在是否启动：否。**

本轮用户明确要求“准备后停止，不运行正式实验”。此外真实资产绑定/实际运行profile尚未冻结核对，输出独立OutcomeAudit尚未发生。Baseline未准备不妨碍以后单系统pilot，但禁止把它当公平对照。

当前只有2事实、17版本、10POC/Patch、10政策风险，0多跳。源事实、风险政策与原生输出映射差异须披露；不能重写人工答案或调Gate提高成绩。人工身份、查源真实性以用户提交和实际复核人确认负责，本轮机械核对不冒充重新人工复核。等待下一条正式实验指令。

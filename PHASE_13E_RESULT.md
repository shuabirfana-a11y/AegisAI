# Phase 13-E：AegisBench 正式评测准备结果

更新时间：2026-10-13（北京时间）。**本轮停在13-E.1准备检查，未执行13-E.2。正式准确率是未评测，不是0%。**

## 1. Ground Truth 状态

实际冻结候选 `AegisBench-v0.2.1-pilot`：49题，原人审准入通过0；49条 machine SOURCE_REFERENCE 均被排除。仓库人工工作流文件：DRAFT 0、REVIEWING 0、APPROVED 0、REJECTED 0。49张task DRAFT卡只是任务元数据。之前收到的外部DRAFT包尚未成为已批准、冻结的HUMAN_GOLD，本轮没有代填或导入。

门槛按首批建议采用10条原Loader核验通过的HUMAN_GOLD。既有Loader接受真实APPROVED/REVIEWED完成态，二者分列，不修改原审核语义；机器记录或同人换账号不算独立人审。

## 2. 评测入口与隔离

新增无网络检查 `python scripts/check_bench_readiness.py --output <新目录>`：检查冻结文件SHA、证据定位、双人元数据和人数；不足或数据无效返回3，只生成readiness报告，禁止开始正式实验。实际运行：49候选 / 0合格，`BLOCKED_MINIMUM_GOLD`，exit3。无HTTP、模型或评分器调用。

沿用Phase13-D `evaluate.py --mode online / offline`。没有改变HTTP、Planner、Agent、Gate、Runner或指标。GT只在准入核对和最终比较中使用，不进入Prompt/Context/检索/Tool请求；测试控制将HTTP客户端及评分器替换为禁止调用函数，检查仍正常拒绝。

返回0只代表数据门禁通过，不代表模型/Prompt/库存已冻结，也不自动运行实验。人工审查真实性、语义支持及公平性不能由格式检查自动证明。

## 3. Metrics

原Answer Accuracy、Risk Accuracy、Abstention Quality及Evidence Coverage/Hallucination门禁保持不变。后两项仍须独立OutcomeAudit绑定本次输出并审核完整Claim；未经审核显示NOT_EVALUATED。分类分母、失败、未覆盖样本须同时报告，不用工程pass数代替准确率。

本轮所有业务质量指标未计算，未生成0%准确率、0%幻觉率或相对提高结论。

## 4. Baseline

- RAG-only：NOT_IMPLEMENTED（本轮完整HTTP可比对照）。
- 无Verification Agent：NOT_IMPLEMENTED；不增加生产绕过开关。
- 完整AegisAI：公开HTTP入口已有，本轮未执行正式实验。

公平问题/语料/资产/模型/预算/截止时间的规划见 [Baseline计划](docs/phase13e/BASELINE_PLAN.md)。旧离线适配器的存在不代表公平对照已完成。

## 5. 实验配置与流程

[首批模板](evaluation/experiments/phase13e/pilot-v0.1.template.json)明确PREPARATION_TEMPLATE_NOT_EXECUTED、模型digest/Prompt SHA/正式Manifest/库存绑定均未冻结。它不是Runner自动读取的配置，不包含Key或真实个人库存。

10条合格题后可跑v0.1，无需等49题。先经准入，再创建新数据版本并冻结模型不可变摘要、Prompt摘要、Git/预算/库存，再用原HTTP入口运行。核对输出的真实模型与冻结配置，保留失败与漂移；独立复核输出后用OFFLINE重新计分。详见 [操作说明](docs/phase13e/EXPERIMENT_RUNBOOK.md)。本轮没有执行这些未来步骤。

## 6. 本轮测试

- 11项新增控制先RED，后GREEN；含0/9/10门槛、来源篡改、同人复核排除、GT隔离、报告及覆盖保护。独立审查发现的畸形清单/工作流处理已新增3项负例修复。
- AegisBench全套：95 passed（包含既有84项）。
- 便携后端：531 passed，1项原CI明确排除的真实缓存Embedding测试deselected；集合有重叠，不相加。
- 原契约检查：42个HTTP操作、40个合成对象通过。
- 原HTTP导出10文件和HTTP评测9组Schema一致。
- 原业务/评测/题目/人工标注/来源文件保持字节不变；记录见 [本轮验证](docs/phase13e/verification.json)。

历史1426项和上一阶段112项DB/TCP测试不冒充本轮重新执行。新测试用临时合成协议数据验证准入，未产生真实人工批准或业务实验分数。

## 7. 当前限制与停止

当前人工金标不足10；模型/Prompt/正式数据版本尚未冻结，对照未实现、来源库存公平性未证明、独立输出审核尚未开始。旧事实字段部分没有原生平面映射，跨资产问题也未完整覆盖，未来须公开样本覆盖/格式差异，不修改人工答案迎合输出。**停止在13-E.1，未执行正式实验。**不更改Agent/Gate/人工答案，不宣称提升，不部署。

PR #13当前仍OPEN/DRAFT，本轮从其实现提交建立独立准备分支，不能声称main已包含本轮评测入口。后续合并须负责人确认。

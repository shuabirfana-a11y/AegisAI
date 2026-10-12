# Phase 13-D：完整调查评测准备

PR #12 已合并 main，基线 59ea2a239556e70514ce19bba52141121a98d570。当前真实候选49题，正式 Approved 为0；本轮不发布准确率。

## 两种入口

```text
python evaluate.py --mode online --manifest evaluation/datasets/AegisBench-v0.2.1-pilot/manifest.json --output work/phase13d-e2e/preparation
python evaluate.py --mode offline --rescore-report work/phase13d-e2e/preparation/report.json --output work/phase13d-e2e/replay
```

没有 `--mode` 时保持原离线候选/框架检查入口。Online 只让原人工准入通过的题目进入 HTTP；0 approved 不创建网络客户端，不调用模型，所有质量指标显示 NOT_EVALUATED。Offline 不调用服务，只回放记录；实验侧记录、报告和问题/来源哈希不符时拒绝。

## 人工批准后的操作

先由不同人员标注、复核原 Schema，使用原导出流程形成带正确文件哈希的 approved dataset。人工身份/状态真实存在，不能只改字段充当审核。每题结论引用来源 catalog 的 URL、JSON Pointer、原文规范 JSON及获取时间。

配置本机 `AEGIS_ASSET_TOKEN` 和实际 API 地址；密钥只放进程环境。线上服务已经配置自己的模型与操作者身份，评测器不选择用户、不创建资产、不直接调用数据库、模型或 Agent。

版本/风险题先为每题显式绑定现有、属于操作者的资产和组件，使用 `--bindings <JSON文件>`。绑定对象的键为问题 ID，值可含 asset_id/component_id/snapshot_id/component/target。组件版本和目标不能覆盖题目原值。UUID 是实际服务器库存 ID，不能复制演示 ID 假装企业资产。

```json
{
  "<批准的问题ID>": {
    "asset_id": "<本机拥有的实际资产UUID>",
    "component_id": "<实际组件UUID>"
  }
}
```

一个题目需要多资产或多目标时，当前单资产调查内核不适配，报告明确 NOT_EVALUATED。版本缺失保持缺失，由原业务规则决定 UNKNOWN；不要从标准答案填进去。环境/暴露条件必须与本次库存观察一致。

## 真实调用流程

POST /api/investigations → GET status（有限轮询）→ GET trace/artifacts/integration/answer。

输出必须经过原 Planner、专业 Agent 与 Gate；评测器校验响应 Schema、调查/run/artifact引用和冻结答案关系。Gate 阻断、未知与冲突不改为通过；无风险视图不自动补 LOW 或 UNKNOWN。失败保留原分类，超时对本次已知调查尝试取消并记录结果。

模型/Prompt标识来自持久化 Trace。CLI仅接受真实模型输出进入正式质量门禁；Mock仅用于明确标识的工程控制。报告不会把成功 HTTP 或已确认 Claim 自动认作独立正确答案。

## 标准答案与原生字段

原 Annotation.expected_answer 为 JsonValue 字典，已能承载原生字段：affected（AFFECTED/NOT_AFFECTED/UNKNOWN）、verification_status、risk_level、priority，以及字段组合。native_answer_status/native_gate_status 保存原状态。

version_observations 和 impact_version_evidence 保存正式来源观察，含组件、版本、时间及引用。它们不是独立人工证据。旧候选的 cve/summary/cwes/cvss 等字段若未在原生交付中体现，保持缺失，不能用题目、参考答案或问答文本猜补。不要为匹配系统而改人工结论；不适配的答案格式/任务范围应单独报告。

风险优先级使用原 asset-priority-v1：P1/P2/P3/DEFER/REVIEW_REQUIRED。原参考 triage 的其他分类与此不等价，不做静默转换。

## 指标与复核

复用现有 score_variant：Answer Accuracy、Risk/Priority Accuracy、版本分类、Abstention Quality、流程覆盖和延迟。失败保留；失败调用不记作正确拒答。

Evidence Coverage/Hallucination Rate 还需要独立 OutcomeAudit，完整覆盖本次输出的陈述、风险及建议，绑定 prediction_sha256。只有引用有效或 Verification CONFIRMED 不能替代语义复核。待复核清单由原报告器产生，未经审核指标为 null。

原生来源 UUID/Locator/Hash 作为 native_citations 留存，不冒充 benchmark source_id 和冻结证据定位。复核人必须回到原 catalog 和输出内容建立真实证据对应关系。

## 三个 Baseline

| Baseline | 当前准备状态 |
|---|---|
| 普通 RAG | 独立控制待实施/导入，线上本轮不运行 |
| 无 Verification Agent | 独立消融控制待实施，不向生产链添加跳过开关 |
| 完整 AegisAI | 新公开 HTTP 采集与冻结记录回放入口 |

模型、输入、归一化数据和实际库存之间的数据一致性尚未独立证明。不能仅凭相同 URL/问题文件哈希声称公平三方对比，不能绕过旧 native adapter 的准入限制。新入口是公开调查的执行与输出评测准备，旧内部入口仍保持原门禁。

## 输出与留痕

report.json/report.md、predictions.jsonl、native-http-records.json、experiment.json、outcome-audit-pending.jsonl。包含数据集版本/指纹、实际模型/Prompt、Git与评测器文件哈希、时间、原生状态和客户端配置。不会覆盖旧实验或写入标注/数据集目录。

## 审查后的输入与失败约束

`binding.component` 只能重述原问题已给定且相同的字段，不能添加缺失版本或把 null 改成已知值。身份由 asset_id/component_id 绑定；若问题另有 package_name，则 name 为显示提示，按包名、生态和实际库存核对。单资产数组和嵌套 component 的版本/环境条件也参与校验。

HTTP 响应必须对应原问题、目标及原生 Agent/Gate/Artifact 引用。事实值、证据来源、风险视图与取得的冻结 Artifact 一致；每次已校验响应即时保存，后续失败不会丢掉已取得 Trace/证据。所有 Baseline 的 Mock 或缺少明确非 Mock 标识的成功结果均不能进入正式指标。

公开 Trace 只列主要交付 Artifact；Version Observation 的资产子任务源 Artifact UUID 尚不能逐个通过公开端点展开。当前核对调查 run、原资产子任务成功状态及观察的身份/版本，保留源 UUID；不声称已单独验证每个未公开的子 Artifact，也不直接查询数据库绕过边界。

Schema 可重复导出和检查：`python scripts/export_bench_http_schema.py --check`，直接读取现有 Pydantic 定义，无数据库连接。

本轮完成后停止，正式实验待真实人工批准与比较条件齐备后另行授权。

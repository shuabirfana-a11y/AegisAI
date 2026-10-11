# Phase 13-C：Ground Truth 人工标注流程建设结果

阶段范围：仅建设人工标准答案的生产规范、空表、独立复核、数据版本与进度管理。未填写人工答案，未运行评测，未调用 Agent 或模型，未改业务/评测代码。

## 交付入口

- [ANNOTATION_GUIDE.md](evaluation/ground_truth/ANNOTATION_GUIDE.md)：团队第一阅读入口，包含证据等级、六类判定、盲审、两人复核及退回流程。
- [schema.md](evaluation/ground_truth/schema.md) 与 [MANUAL_RECORD_SCHEMA.md](evaluation/ground_truth/MANUAL_RECORD_SCHEMA.md)：保留原契约，新增人工表单定义、哈希与白名单导出映射。
- [ground_truth_template.json](evaluation/ground_truth/ground_truth_template.json)：完全空白的工作表；template.json 为字节相同的兼容副本。
- [ground_truth_workflow.schema.json](evaluation/ground_truth/ground_truth_workflow.schema.json)：离线表单结构约束，不接入或修改 Runner。
- [QUESTION_CLASSIFICATION.md](evaluation/ground_truth/QUESTION_CLASSIFICATION.md)：49 个原问题 ID 的逐条分类、原始输入摘要及已有来源入口。
- [GROUND_TRUTH_PROGRESS.md](evaluation/ground_truth/GROUND_TRUTH_PROGRESS.md)：唯一领取/流程台账；progress.md 为入口。
- samples/draft、reviewing、approved、rejected：仅有目录占位文件，没有人工记录。

## 分类与真实进度

| 主类型 | 候选题数 |
|---|---:|
| 漏洞事实查询 | 5 |
| 版本影响判断 | 17 |
| Patch 分析 | 5 |
| POC 核验 | 5 |
| 资产风险分析 | 10 |
| 复杂多跳问答 | 7 |
| 合计 | 49 |

5 道 POC 题同时含 Patch 判断，附加标签不增加样本数。原 Runner 的五类 category 不变。

领取未分配 49，已领取 0；流程 NOT_STARTED 49，DRAFT/REVIEWING/APPROVED/REJECTED 均为 0。READY_FOR_RUNNER 与已冻结 HUMAN_GOLD 均为 0。当前没有人工查源、签署或独立复核记录。

## 流程与准入

候选题领取 → 人独立查源 → 完整填写 DRAFT → 第二位不同自然人 REVIEWING → APPROVED 或 REJECTED → 后续新版本冻结与准入 → Phase 13-D 评测。

答案与原子判断关联来源 URL、原文、时间、定位及源快照哈希；合理的 UNKNOWN/INSUFFICIENT_EVIDENCE 可批准，不强制填确定答案。身份字段不能证明真的有人参与，必须保存实际审核记录。人工批准与 Runner 可用性分别管理。

现有人工表单不能直接交给严格 Annotation。INSUFFICIENT_EVIDENCE 和 PoC/Patch 的 NO_EVIDENCE 到旧对应字段投影为 UNKNOWN，保留原判断与依据。新来源、政策或标签尚不能一致时阻塞导出，不改 Runner 迎合它们。

## 本阶段实际校验

- JSON Schema 自校验通过；两份空白模板均符合 Schema，内容完全相同。
- 在内存中检查 4 种非法形状：空表冒充 HUMAN_RECORD、空表宣称 APPROVED、未知字段、空表预填答案，均被拒绝。这些不是人工样本，也不是业务质量评测。
- 分类/台账均有 49 个唯一 ID，与冻结问题逐条一致；六类数量及 5 个复合标签一致。
- 四个人工目录只有占位文件；人工答案、真实身份和审批均未生成。
- 原问题、机器参考 annotations 与 5 份来源投影 SHA-256 全部匹配原 manifest。
- 原 schema.md 的全部字节前缀保留，只追加人工流程入口；后端、前端、Runner、metrics、已冻结数据与 CI 均未改动。
- 文档本地链接、Git 空白检查及现有仓库安全检查通过。未重新运行历史 1261 项工程测试，未生成 Accuracy 等新成绩。

## 当前限制与下一步

49 题仍属于 5 个相关公告簇的 pilot，不是独立 holdout。缺少已有合法独立验证材料支持的 VERIFIED_EXPLOIT 正类。当前 risk/multihop 对应参考政策符合性，不能宣传成真实资产专家风险准确率；后续需新问题/证据版本才可评测真实资产风险。

本阶段不提供自动导入、自动标注或新的评测工具；声明式结构检查不能代替来源支持性和独立真人复核。Phase 13-C 至此停止。Phase 13-D 由真实成员领取、试标、解决规范歧义、双人复核及冻结，再另行授权正式评测。

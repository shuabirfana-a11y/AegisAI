# 第一批10题人工标注工作单

当前：任务已备，标注人与复核人未分配。人工填写 0、独立复核 0、APPROVED 0。此工作单没有标准答案。

先由真人领取，再完整填写 [原表单](../../../ground_truth_template.json)，按 [标注规范](../../../ANNOTATION_GUIDE.md) 独立查源和复核。本工作单空栏只用于协作，不是合法的 HUMAN_RECORD，也不计入 DRAFT 完成。

## 批次清单

| 顺序 | ID / 任务卡 | 类型 | 原问题 |
|---:|---|---|---|
| 1 | [GHSA-53q9-r3pm-6pq6-facts](../../tasks/GHSA-53q9-r3pm-6pq6-facts.json) | VULNERABILITY_FACTS | 查询 CVE-2025-32434 的描述、CWE 和按版本区分的 CVSS。 |
| 2 | [GHSA-c67j-w6g6-q2cm-facts](../../tasks/GHSA-c67j-w6g6-q2cm-facts.json) | VULNERABILITY_FACTS | 查询 CVE-2025-68664 的描述、CWE 和按版本区分的 CVSS。 |
| 3 | [GHSA-935w-9g4m-p28p-facts](../../tasks/GHSA-935w-9g4m-p28p-facts.json) | VULNERABILITY_FACTS | 查询 CVE-2026-105752 的描述、CWE 和按版本区分的 CVSS。 |
| 4 | [GHSA-53q9-r3pm-6pq6-affected](../../tasks/GHSA-53q9-r3pm-6pq6-affected.json) | VERSION_IMPACT | torch 版本 2.5.1 是否受 CVE-2025-32434 影响？ |
| 5 | [GHSA-c67j-w6g6-q2cm-gap](../../tasks/GHSA-c67j-w6g6-q2cm-gap.json) | VERSION_IMPACT | langchain-core 0.4.0 是否命中 CVE-2025-68664 的任意影响区间？ |
| 6 | [GHSA-9rwj-6rc7-p77c-unknown](../../tasks/GHSA-9rwj-6rc7-p77c-unknown.json) | VERSION_IMPACT | langgraph-checkpoint-sqlite 版本 未提供 是否受 CVE-2025-67644 影响？ |
| 7 | [GHSA-c67j-w6g6-q2cm-release-and-poc](../../tasks/GHSA-c67j-w6g6-q2cm-release-and-poc.json) | POC_VERIFICATION | 按公告的修复版本记录判断 CVE-2025-68664 的 release fix；公开 PoC 是否经过独立验证？ |
| 8 | [GHSA-47fc-vmwq-366v-commit-candidate](../../tasks/GHSA-47fc-vmwq-366v-commit-candidate.json) | PATCH_ANALYSIS | 此链接仅出现在 CVE-2022-45907 的参考文献列表。没有代码验证记录时，能否认定为已验证补丁？ |
| 9 | [GHSA-9rwj-6rc7-p77c-risk-affected](../../tasks/GHSA-9rwj-6rc7-p77c-risk-affected.json) | ASSET_RISK | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2025-67644 的风险与优先级。 |
| 10 | [GHSA-935w-9g4m-p28p-risk-fixed](../../tasks/GHSA-935w-9g4m-p28p-risk-fixed.json) | ASSET_RISK | 按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2026-105752 的风险与优先级。 |

首批 3 facts、3 version、1 POC（含 Patch）、1 Patch、2 risk，覆盖五个公告簇。任务 ID 后缀和演示资产名称不能代替判断。

## 逐题填写区

### 1. GHSA-53q9-r3pm-6pq6-facts

查询 CVE-2025-32434 的描述、CWE 和按版本区分的 CVSS。

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "component": "torch",
  "ecosystem": "PyPI",
  "target": "CVE-2025-32434"
}
```

- [GHSA-53q9-r3pm-6pq6 候选定位包](evidence_candidates/GHSA-53q9-r3pm-6pq6.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-53q9-r3pm-6pq6)；[本次机器读取检查](source_checks/database-GHSA-53q9-r3pm-6pq6.json)。
- [MAINTAINER_ADVISORY 原始资料](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6)；[本次机器读取检查](source_checks/maintainer-GHSA-53q9-r3pm-6pq6.json)。

逐项填写 cve、summary、cwes、cvss；CVSS v3/v4 分开，检查缺失值和来源表达，不能顺带猜资产风险。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

### 2. GHSA-c67j-w6g6-q2cm-facts

查询 CVE-2025-68664 的描述、CWE 和按版本区分的 CVSS。

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "component": "langchain-core",
  "ecosystem": "PyPI",
  "target": "CVE-2025-68664"
}
```

- [GHSA-c67j-w6g6-q2cm 候选定位包](evidence_candidates/GHSA-c67j-w6g6-q2cm.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-c67j-w6g6-q2cm)；[本次机器读取检查](source_checks/database-GHSA-c67j-w6g6-q2cm.json)。
- [MAINTAINER_ADVISORY 原始资料](https://github.com/langchain-ai/langchain/security/advisories/GHSA-c67j-w6g6-q2cm)；[本次机器读取检查](source_checks/maintainer-GHSA-c67j-w6g6-q2cm.json)。

逐项填写 cve、summary、cwes、cvss；CVSS v3/v4 分开，检查缺失值和来源表达，不能顺带猜资产风险。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

### 3. GHSA-935w-9g4m-p28p-facts

查询 CVE-2026-105752 的描述、CWE 和按版本区分的 CVSS。

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "component": "vllm",
  "ecosystem": "PyPI",
  "target": "CVE-2026-105752"
}
```

- [GHSA-935w-9g4m-p28p 候选定位包](evidence_candidates/GHSA-935w-9g4m-p28p.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-935w-9g4m-p28p)；[本次机器读取检查](source_checks/database-GHSA-935w-9g4m-p28p.json)。
- [MAINTAINER_ADVISORY 原始资料](https://github.com/vllm-project/vllm/security/advisories/GHSA-935w-9g4m-p28p)；[本次机器读取检查](source_checks/maintainer-GHSA-935w-9g4m-p28p.json)。

逐项填写 cve、summary、cwes、cvss；CVSS v3/v4 分开，检查缺失值和来源表达，不能顺带猜资产风险。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

### 4. GHSA-53q9-r3pm-6pq6-affected

torch 版本 2.5.1 是否受 CVE-2025-32434 影响？

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "component": "torch",
  "ecosystem": "PyPI",
  "target": "CVE-2025-32434",
  "version": "2.5.1"
}
```

- [GHSA-53q9-r3pm-6pq6 候选定位包](evidence_candidates/GHSA-53q9-r3pm-6pq6.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-53q9-r3pm-6pq6)；[本次机器读取检查](source_checks/database-GHSA-53q9-r3pm-6pq6.json)。
- [MAINTAINER_ADVISORY 原始资料](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6)；[本次机器读取检查](source_checks/maintainer-GHSA-53q9-r3pm-6pq6.json)。

人判断 affected（AFFECTED / NOT_AFFECTED / INSUFFICIENT_EVIDENCE 或 UNKNOWN）；逐分支记录依据及开闭边界。需核对版本是否真实发布、题目是范围匹配还是真实部署，记录缺失前提。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

### 5. GHSA-c67j-w6g6-q2cm-gap

langchain-core 0.4.0 是否命中 CVE-2025-68664 的任意影响区间？

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "component": "langchain-core",
  "ecosystem": "PyPI",
  "target": "CVE-2025-68664",
  "version": "0.4.0"
}
```

- [GHSA-c67j-w6g6-q2cm 候选定位包](evidence_candidates/GHSA-c67j-w6g6-q2cm.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-c67j-w6g6-q2cm)；[本次机器读取检查](source_checks/database-GHSA-c67j-w6g6-q2cm.json)。
- [MAINTAINER_ADVISORY 原始资料](https://github.com/langchain-ai/langchain/security/advisories/GHSA-c67j-w6g6-q2cm)；[本次机器读取检查](source_checks/maintainer-GHSA-c67j-w6g6-q2cm.json)。

人判断 affected（AFFECTED / NOT_AFFECTED / INSUFFICIENT_EVIDENCE 或 UNKNOWN）；逐分支记录依据及开闭边界。需核对版本是否真实发布、题目是范围匹配还是真实部署，记录缺失前提。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

### 6. GHSA-9rwj-6rc7-p77c-unknown

langgraph-checkpoint-sqlite 版本 未提供 是否受 CVE-2025-67644 影响？

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "component": "langgraph-checkpoint-sqlite",
  "ecosystem": "PyPI",
  "target": "CVE-2025-67644",
  "version": null
}
```

- [GHSA-9rwj-6rc7-p77c 候选定位包](evidence_candidates/GHSA-9rwj-6rc7-p77c.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-9rwj-6rc7-p77c)；[本次机器读取检查](source_checks/database-GHSA-9rwj-6rc7-p77c.json)。
- [MAINTAINER_ADVISORY 原始资料](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-9rwj-6rc7-p77c)；[本次机器读取检查](source_checks/maintainer-GHSA-9rwj-6rc7-p77c.json)。

人判断 affected（AFFECTED / NOT_AFFECTED / INSUFFICIENT_EVIDENCE 或 UNKNOWN）；逐分支记录依据及开闭边界。需核对版本是否真实发布、题目是范围匹配还是真实部署，记录缺失前提。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

### 7. GHSA-c67j-w6g6-q2cm-release-and-poc

按公告的修复版本记录判断 CVE-2025-68664 的 release fix；公开 PoC 是否经过独立验证？

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "component": "langchain-core",
  "ecosystem": "PyPI",
  "target": "CVE-2025-68664"
}
```

- [GHSA-c67j-w6g6-q2cm 候选定位包](evidence_candidates/GHSA-c67j-w6g6-q2cm.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-c67j-w6g6-q2cm)；[本次机器读取检查](source_checks/database-GHSA-c67j-w6g6-q2cm.json)。
- [MAINTAINER_ADVISORY 原始资料](https://github.com/langchain-ai/langchain/security/advisories/GHSA-c67j-w6g6-q2cm)；[本次机器读取检查](source_checks/maintainer-GHSA-c67j-w6g6-q2cm.json)。

分别判断 poc_status 和 patch_status，注明 PoC 独立验证材料及 release/commit 的确认范围；只有链接不能代替验证记录。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

### 8. GHSA-47fc-vmwq-366v-commit-candidate

此链接仅出现在 CVE-2022-45907 的参考文献列表。没有代码验证记录时，能否认定为已验证补丁？

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "candidate_kind": "patch",
  "candidate_reference": "https://github.com/pytorch/pytorch/commit/767f6aa49fe20a2766b9843d01e3b7f7793df6a3",
  "component": "torch",
  "ecosystem": "PyPI",
  "target": "CVE-2022-45907"
}
```

- [GHSA-47fc-vmwq-366v 候选定位包](evidence_candidates/GHSA-47fc-vmwq-366v.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-47fc-vmwq-366v)；[本次机器读取检查](source_checks/database-GHSA-47fc-vmwq-366v.json)。
- [MAINTAINER_COMMIT_METADATA 原始资料](https://github.com/pytorch/pytorch/commit/767f6aa49fe20a2766b9843d01e3b7f7793df6a3)；[本次机器读取检查](source_checks/commit-767f6aa49fe20a2766b9843d01e3b7f7793df6a3.json)。

判断 patch_status；区分官方参考链接、已确认 release fix、commit 正确性或回归验证，写明依据范围。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

### 9. GHSA-9rwj-6rc7-p77c-risk-affected

按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2025-67644 的风险与优先级。

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "asset": {
    "component": "langgraph-checkpoint-sqlite",
    "id": "demo-GHSA-9rwj-6rc7-p77c-affected",
    "scenario": "CONTROLLED_NOT_PRODUCTION",
    "version": "3.0.0"
  },
  "component": "langgraph-checkpoint-sqlite",
  "ecosystem": "PyPI",
  "target": "CVE-2025-67644",
  "triage_policy": "benchmark-reference-triage-v1"
}
```

- [GHSA-9rwj-6rc7-p77c 候选定位包](evidence_candidates/GHSA-9rwj-6rc7-p77c.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-9rwj-6rc7-p77c)；[本次机器读取检查](source_checks/database-GHSA-9rwj-6rc7-p77c.json)。
- [MAINTAINER_ADVISORY 原始资料](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-9rwj-6rc7-p77c)；[本次机器读取检查](source_checks/maintainer-GHSA-9rwj-6rc7-p77c.json)。

填写 affected、risk_level、priority 的人工推导。本题声明 benchmark-reference-triage-v1，只测政策符合性；不是专家生产风险判断。保留版本、CVSS 版本和资产前提依据。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

### 10. GHSA-935w-9g4m-p28p-risk-fixed

按 benchmark-reference-triage-v1 评估此演示资产对 CVE-2026-105752 的风险与优先级。

原始条件（完整复制自冻结题目，不含人工标签）：

```json
{
  "asset": {
    "component": "vllm",
    "id": "demo-GHSA-935w-9g4m-p28p-fixed",
    "scenario": "CONTROLLED_NOT_PRODUCTION",
    "version": "0.30.0"
  },
  "component": "vllm",
  "ecosystem": "PyPI",
  "target": "CVE-2026-105752",
  "triage_policy": "benchmark-reference-triage-v1"
}
```

- [GHSA-935w-9g4m-p28p 候选定位包](evidence_candidates/GHSA-935w-9g4m-p28p.json)：包含冻结来源时间/哈希及原文定位，仍待人工选证。
- [GITHUB_REVIEWED_DATABASE 原始资料](https://api.github.com/advisories/GHSA-935w-9g4m-p28p)；[本次机器读取检查](source_checks/database-GHSA-935w-9g4m-p28p.json)。
- [MAINTAINER_ADVISORY 原始资料](https://github.com/vllm-project/vllm/security/advisories/GHSA-935w-9g4m-p28p)；[本次机器读取检查](source_checks/maintainer-GHSA-935w-9g4m-p28p.json)。

填写 affected、risk_level、priority 的人工推导。本题声明 benchmark-reference-triage-v1，只测政策符合性；不是专家生产风险判断。保留版本、CVSS 版本和资产前提依据。

- 标注人团队 ID：待领取。
- 人工标准答案：未填写（按题型填写 expected_answer，不强制每题都加 risk_level）。
- 关键 judgment、引用证据 ID/原文/时间/URL、版本边界：未填写。
- 不确定性、冲突、缺失资料及 should_abstain：未填写；允许保留证据不足。
- 记录文件、修订号、content_sha256：未产生。
- 第二人团队 ID、独立查源确认、review_note、时间、reviewed_content_sha256：未产生。

## 提交与质量门禁

1. 完整真人标注先保存 draft 记录，不能把机器资料包直接换个 origin 作为人工 gold。
2. 第二人自己查原始来源，核对答案是否被引文支持，而非仅看第一个人的“结论”。
3. 按原 Schema 保存真实两人确认、原子 judgment 与 SHA 绑定；资料不足可以给 UNKNOWN，但要记录调查范围和缺口。
4. 全批实际复核通过后才形成 Approved Dataset；当前没有进入 reviewing/approved 的人工记录。
5. 如使用新来源，需另建新冻结源目录/manifest；旧候选和机器标签不覆盖。不运行模型或 Evaluation Runner。

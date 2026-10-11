# AegisBench v0.2 pilot 与比赛演示材料

49 条候选问题：facts 5、version 17、POC/Patch 10、risk 10、multihop 7。依据 5 份 GitHub Advisory Database 官方 API 记录整理。来源获取时间与 upstream published_at/updated_at 分开记录，源投影与原 HTTP 输出分别保留 SHA-256。描述/可执行 PoC 正文不导出、不执行；原始字段投影不做推测或补写。所有答案是 SOURCE_REFERENCE / MACHINE / PENDING。

| 公告 | 漏洞 | 组件 | 官方来源 |
|---|---|---|---|
| GHSA-53q9-r3pm-6pq6 | CVE-2025-32434 | torch | [GitHub 公告](https://github.com/advisories/GHSA-53q9-r3pm-6pq6) |
| GHSA-47fc-vmwq-366v | CVE-2022-45907 | torch | [GitHub 公告](https://github.com/advisories/GHSA-47fc-vmwq-366v) |
| GHSA-c67j-w6g6-q2cm | CVE-2025-68664 | langchain-core | [GitHub 公告](https://github.com/advisories/GHSA-c67j-w6g6-q2cm) |
| GHSA-9rwj-6rc7-p77c | CVE-2025-67644 | langgraph-checkpoint-sqlite | [GitHub 公告](https://github.com/advisories/GHSA-9rwj-6rc7-p77c) |
| GHSA-935w-9g4m-p28p | CVE-2026-105752 | vllm | [GitHub 公告](https://github.com/advisories/GHSA-935w-9g4m-p28p) |

PyTorch 2025 记录的 v3 vector 缺失，只有有效 v4 评分，不把占位 0 当 v3 分数；LangChain 有两个影响分支，含版本空档/老分支修复边界；vLLM 这个案例的 v3 只有 3.1，不能因为是 AI 组件就叫高危。

## 可解释 Demo 场景

1. `GHSA-c67j-w6g6-q2cm-affected/fixed/older-fix/gap`：公告 → 版本区间并集 → 受影响/修复/空档；展示真实源 JSON Pointer。控制输入是版本比较场景，不声称该部署真实存在。
2. `GHSA-53q9-r3pm-6pq6-release-and-poc/commit-candidate`：公告确认修复 release；reference commit 留为候选；没有独立利用验证则 UNKNOWN，不能升级为 Verified Exploit。
3. `cross-advisory-priorities/missing-version`：多份真实公告加显式演示资产，比较已知与未知版本；本批只验证参考政策和流程记录，不假装已运行完整多 Agent 或取得人审语义多跳成绩。

冻结源离线可复现，网络中断仍可运行此阶段的关键词与固定流程演示。录制画面必须标明 OFFLINE PILOT、机器参考、人审待完成；不能用这些离线记录冒充 live LLM 调查。

## Attribution 与数据使用

来源是 GitHub Advisory Database 及每份公告引用的研究者/项目维护者。记录保存原公告链接与 creator/license/source URI；采用其 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 许可，依据 [官方许可证](https://github.com/github/advisory-database/blob/main/LICENSE.md)。本项目只做字段投影及控制场景构造，资料按 AS-IS 提供，不暗示上游认可项目。

这是便于审查的 pilot，不是独立 holdout。重复同一 CVE 的不同问题不是不同漏洞样本；部分 CVE 曾进入工程 fixtures。缺少经过独立验证的利用正例与真实 PoC 语义分类，不能宣传该类别准确率。实际资产均未扫描，风险草稿依赖评测政策，必须由团队标注/复核后再进入正式 gold。

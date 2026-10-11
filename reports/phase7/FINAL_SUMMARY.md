=== AegisAI Phase 7 Trusted Intelligence Complete ===

Phase 6 Verification:
PASS — 原278主体、347原文及冻结报告保持，原19次SyncRun不变。

Enrichment:
Vendor: PASS
EPSS: PASS
KEV: PASS
POC Discovery: PASS（限定5结果/3README，部分任务PARTIAL）
POC Verification: PASS（静态核验，利用可用性未评估）
Patch Discovery: PASS
Version Enrichment: PASS（不支持表达明确保留未知）

Trusted Intelligence:
Claims: 36（10 adopted）
Evidence: 60，均可追溯Raw/Source且哈希通过
Verification Results: 61
Conflicts: 6（open=2；resolved/退役=4）
Review Tasks: 38（open=34；cancelled=4，真实库未假冒人工resolution）

Real Cases:
Case 1: CVE-2025-32434 / PyTorch — CVE与OSV标识、GHSA与漏洞主题一致；真实PoC候选与Patch，厂商包名差异弃判。
Case 2: CVE-2026-64849 / MLflow — EPSS/真实KEV、fixed3.15.0、两个Confirmed官方PR、影响起点差异进入Review。
Case 3: CVE-2026-57173 / vLLM — 官方公告/补丁、版本表达差异与patched表达未知；限定GitHub搜索NO_RESULT。
Demo Candidate: CVE-2026-64849

Evaluation Sample:
Sample Size: 28
Correct: 0
Incorrect: 0
Uncertain: 28（全部待真实人工标注，不是错误率）

Tests:
Passed: 218
Failed: 0
Skipped: 0

Tool-ready Services:
investigate_vulnerability / find_vendor_advisories / find_poc_candidates / verify_poc_candidate / find_patch_candidates / get_epss / get_known_exploitation / get_claims / get_evidence / verify_claim / detect_conflicts / get_vulnerability_timeline
12项契约在docs/tooling/TOOL_CONTRACTS_V1.md；未接Agent/Dify。

Known Issues:
人工标注待完成；仅三家生态/明确PyPI表达；PoC静态而非利用可用性验证；厂商包名/范围表达差异保留；GitHub公共限流历史和有限检查覆盖；1个弃用警告。详见KNOWN_ISSUES.md。

Phase 7 Status:
PARTIAL — 工程实现/实际测试/三案例已交付，第66节人工样本标注未满足。

Next Phase:
Phase 8：资产接入 + SBOM/组件标准化 + 版本命中 + 资产风险变化 + 可解释处置优先级。
未启动，完成本阶段交付后停止。

Rulings I made:
- 无Git项目保留工作区与文件指纹，未创建分支/提交/PR；代价是以文件和日志回查。
- 完整文档和持续授权支持直接执行，无重复设计审批；代价是例行实现选择由助手决定。
- 不冒充人工标注，提供28条可审阅样本；代价是验收PARTIAL，没有准确率。
- 三个审查Minor按明确要求影响重新分级并纳入一次修复；代价是三项额外回归。

Deferred minors:
无。

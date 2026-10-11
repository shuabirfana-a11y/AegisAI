=== AegisAI Phase 8 Asset Risk Complete ===

Phase 7 Dependency Check: PARTIAL — 既有真实范围冲突、unsupported和28条人工标注待定保持。

Asset: PASS（后端资产接入与历史；全部is_demo库存）。
Manual Input: PASS。
CycloneDX: PASS（JSON1.6）。
SPDX: PASS（JSON2.3）。
Component Resolution: PASS（精确包/显式别名/歧义弃判）。
Version Matching: PARTIAL（PyPI引擎通过；其他生态及真实源未核验保留未知）。
Risk Analysis: PARTIAL（透明规则、解释、证据及处置已实现；真实Demo范围冲突未解决）。
Risk Change: PASS（版本/情报/核验/PoC等变化、不可变前后快照、源差量重算）。

Real Asset Cases:
Case 1: 手工PyTorch2.5.1 → 真实公开漏洞，最终UNCERTAIN，case_1/ case_1_final.json。
Case 2: CycloneDX导入MLflow3.14.0、torch2.6.0、vllm0.8.2-custom；重复导入0新增/0更新/0移除，case_2.json。
Case 3: 同资产MLflow3.14.0→3.15.0，技术比较AFFECTED→NOT_AFFECTED；真实范围冲突使最终仍UNCERTAIN，case_3/ case_3_final.json；不伪造风险解除。
Demo Candidate: MLflow / CVE-2026-64849；真实KEV、带日期EPSS、明确fixed3.15.0、相关官方PR（具体分支适用UNKNOWN）、Claim/Evidence/冲突及升级变化。生产资产未提供，所有案例为明确演示库存。

Asset Match Evaluation:
Sample Size: 30（真实来源+配置评测输入；实际Matcher输出见asset_match_evaluation.json）。
Correct: 0。
Incorrect: 0。
Uncertain: 30（ground truth待真实人工标注）。
False Positive: 待标注，null。
False Negative: 待标注，null。
Accuracy: 待标注，null；不将工程fixture冒充gold。

Performance: 实际PostgreSQL/审查修复构建、100个受控演示组件/300个漏洞组件pair，无生产SLA。
SBOM Import: 56.777s，含首次风险计算。
Matching: 38.873s。
Risk Recompute: 54.448s。
Risk Query: 1.405s（单资产当前风险计数与分页100/300）。

Tests:
Passed: 292。
Failed: 0。
Skipped: 0。
最终34次实际HTTP检查通过，匿名资产接口401、公开漏洞聚合无私有库存信息；工程用例另验证跨owner隐藏；0003往返/49表/25历史保护/零ORM漂移；独立审查发现的9项问题全部在一次修复中处理，13项新增回归先失败再通过。1项第三方AnyIO弃用警告。

Tool-ready Services: create_asset、add_asset_component、import_sbom、resolve_component、normalize_version、match_component_vulnerabilities、get_asset_risks、explain_asset_risk、get_remediation、get_asset_risk_changes；V1保留、V2实际服务已实现。未接LLM/Dify/Agent。

Known Issues: 人工gold未完成；真实源冲突/未核验仍存在；PyPI之外未知；100组件导入/计算较慢；单owner本地鉴权及管理员queue CLI，无常驻调度/生产IAM/高可用验证；SBOM限JSON1.6/2.3且5秒为协作检查；无用户生产库存；正式前端仍Mock。详见KNOWN_ISSUES.md。GitHub限流失败任务原样保留。

Phase 8 Status: PARTIAL — 主体实现和工程验证完成；正式指标与真实源核验条件未全部满足。

Next Phase: Phase 9 — Dify接入 + Hybrid Retrieval + Orchestrator + Multi-Agent协作 + Task Contract / Dependency Graph / Handoff / Integration Gate / Retry-Replan。

本轮已停止，不自行进入Phase9。工作区直接保留，无Git/Docker提交或部署宣称；开发库/API运行、专用测试库关闭。原595份冻结输入、0001/0002及原369份原文由acceptance.json核验。

性能时序：上述100组件计时在主要审查修复后记录；最后一项unsupported范围覆盖门控修复后已重跑全套工程测试与真实HTTP案例，未重复100组件计时。数值为已记录构建的实际测量，无最终版本SLA承诺。

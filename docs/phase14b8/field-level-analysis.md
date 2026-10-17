# Phase 14-B8：49 题逐字段与事实链分析

数据来自 B7 已保存的 49 题、47 个封存核验上下文及 12 份原始来源；只读提取。原评分规则与金标未改。
整题 3/49；计分字段 11/94；拆分 CVSS 子字段后 11/104。这不是人工语义正确率。

主断点采用每题唯一归因；证据缺失和合法拒答不等于软件错误。相互影响的次要问题在 JSON 中保留，不重复计数。

| 首个可测断点 | 题数 |
|---|---:|
| CLAIM | 10 |
| EVIDENCE | 20 |
| INPUT | 5 |
| IMPACT_SCOPE | 7 |
| MATCH | 3 |
| RISK | 2 |
| UNSUPPORTED_SCOPE | 2 |

证据支持率和幻觉率等待原复核人员对实际输出复核，当前为 PENDING。金标没有 product/版本范围等字段时标为未标注，不擅自扩充评分。

| 题号 | 金标字段 | 实际字段 | 整题 | 首断点 |
|---|---|---|---|---|
| GHSA-53q9-r3pm-6pq6-facts | {"cve": "CVE-2025-32434", "cvss_v3": {"score": 0.0, "vector_string": null}, "cvss_v4": {"score": 9.3, "vector_string": "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"}, "cwes": ["CWE-502"], "summary": "PyTorch: `torch.load` with `weights_only=True` leads to remote code execution"} | {"cve": "CVE-2025-32434"} | NO_MATCH | C:CLAIM |
| GHSA-53q9-r3pm-6pq6-affected | {"affected": "AFFECTED"} | {"affected": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-53q9-r3pm-6pq6-fixed | {"affected": "NOT_AFFECTED"} | {"affected": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-53q9-r3pm-6pq6-unknown | {"affected": "UNKNOWN"} | {} | NO_MATCH | H:INPUT |
| GHSA-53q9-r3pm-6pq6-release-and-poc | {"patch_status": "CONFIRMED_FIX", "poc_status": "NO_EVIDENCE"} | {} | NO_MATCH | G:EVIDENCE |
| GHSA-53q9-r3pm-6pq6-commit-candidate | {"patch_status": "PATCH_CANDIDATE"} | {} | NO_MATCH | C:CLAIM |
| GHSA-53q9-r3pm-6pq6-risk-affected | {"affected": "AFFECTED", "priority": "P1", "risk_level": "CRITICAL"} | {"affected": "UNKNOWN", "priority": "REVIEW_REQUIRED", "risk_level": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-53q9-r3pm-6pq6-risk-fixed | {"affected": "NOT_AFFECTED", "priority": "MONITOR", "risk_level": "LOW"} | {"affected": "UNKNOWN", "priority": "REVIEW_REQUIRED", "risk_level": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-53q9-r3pm-6pq6-multihop | {"priority_asset_ids": ["demo-GHSA-53q9-r3pm-6pq6-affected"]} | {"priority_asset_ids": []} | NO_MATCH | G:EVIDENCE |
| GHSA-47fc-vmwq-366v-facts | {"cve": "CVE-2022-45907", "cvss_v3": {"score": 9.8, "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}, "cvss_v4": {"score": 9.3, "vector_string": "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"}, "cwes": ["CWE-77"], "summary": "PyTorch vulnerable to arbitrary code execution"} | {} | NO_MATCH | C:CLAIM |
| GHSA-47fc-vmwq-366v-affected | {"affected": "AFFECTED"} | {"affected": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-47fc-vmwq-366v-fixed | {"affected": "NOT_AFFECTED"} | {"affected": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-47fc-vmwq-366v-unknown | {"affected": "UNKNOWN"} | {} | NO_MATCH | H:INPUT |
| GHSA-47fc-vmwq-366v-release-and-poc | {"patch_status": "CONFIRMED_FIX", "poc_status": "NO_EVIDENCE"} | {"patch_status": "CONFIRMED_FIX"} | NO_MATCH | G:EVIDENCE |
| GHSA-47fc-vmwq-366v-commit-candidate | {"patch_status": "PATCH_CANDIDATE"} | {"patch_status": "CONFIRMED_FIX"} | NO_MATCH | C:CLAIM |
| GHSA-47fc-vmwq-366v-risk-affected | {"affected": "AFFECTED", "priority": "P1", "risk_level": "CRITICAL"} | {} | NO_MATCH | G:EVIDENCE |
| GHSA-47fc-vmwq-366v-risk-fixed | {"affected": "NOT_AFFECTED", "priority": "MONITOR", "risk_level": "LOW"} | {} | NO_MATCH | G:EVIDENCE |
| GHSA-47fc-vmwq-366v-multihop | {"priority_asset_ids": ["demo-GHSA-47fc-vmwq-366v-affected"]} | {"priority_asset_ids": []} | NO_MATCH | G:EVIDENCE |
| GHSA-c67j-w6g6-q2cm-facts | {"cve": "CVE-2025-68664", "cvss_v3": {"score": 9.3, "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:L/A:N"}, "cvss_v4": {"score": 0.0, "vector_string": null}, "cwes": ["CWE-502"], "summary": "LangChain serialization injection vulnerability enables secret extraction in dumps/loads APIs"} | {} | NO_MATCH | C:CLAIM |
| GHSA-c67j-w6g6-q2cm-affected | {"affected": "AFFECTED"} | {} | NO_MATCH | B:IMPACT_SCOPE |
| GHSA-c67j-w6g6-q2cm-fixed | {"affected": "NOT_AFFECTED"} | {"affected": "UNKNOWN"} | NO_MATCH | B:IMPACT_SCOPE |
| GHSA-c67j-w6g6-q2cm-unknown | {"affected": "UNKNOWN"} | {} | NO_MATCH | H:INPUT |
| GHSA-c67j-w6g6-q2cm-release-and-poc | {"patch_status": "CONFIRMED_FIX", "poc_status": "NO_EVIDENCE"} | {} | NO_MATCH | G:EVIDENCE |
| GHSA-c67j-w6g6-q2cm-commit-candidate | {"patch_status": "PATCH_CANDIDATE"} | {} | NO_MATCH | C:CLAIM |
| GHSA-c67j-w6g6-q2cm-risk-affected | {"affected": "AFFECTED", "priority": "P1", "risk_level": "CRITICAL"} | {} | NO_MATCH | B:IMPACT_SCOPE |
| GHSA-c67j-w6g6-q2cm-risk-fixed | {"affected": "NOT_AFFECTED", "priority": "MONITOR", "risk_level": "LOW"} | {} | NO_MATCH | B:IMPACT_SCOPE |
| GHSA-c67j-w6g6-q2cm-multihop | {"priority_asset_ids": ["demo-GHSA-c67j-w6g6-q2cm-affected"]} | {"priority_asset_ids": []} | NO_MATCH | B:IMPACT_SCOPE |
| GHSA-9rwj-6rc7-p77c-facts | {"cve": "CVE-2025-67644", "cvss_v3": {"score": 7.3, "vector_string": "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:C/C:H/I:L/A:N"}, "cvss_v4": {"score": 0.0, "vector_string": null}, "cwes": ["CWE-89"], "summary": "LangGraph's SQLite is vulnerable to SQL injection via metadata filter key in SQLite checkpointer list method"} | {} | NO_MATCH | C:CLAIM |
| GHSA-9rwj-6rc7-p77c-affected | {"affected": "AFFECTED"} | {"affected": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-9rwj-6rc7-p77c-fixed | {"affected": "NOT_AFFECTED"} | {"affected": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-9rwj-6rc7-p77c-unknown | {"affected": "UNKNOWN"} | {} | NO_MATCH | H:INPUT |
| GHSA-9rwj-6rc7-p77c-release-and-poc | {"patch_status": "CONFIRMED_FIX", "poc_status": "NO_EVIDENCE"} | {} | NO_MATCH | G:EVIDENCE |
| GHSA-9rwj-6rc7-p77c-commit-candidate | {"patch_status": "PATCH_CANDIDATE"} | {} | NO_MATCH | C:CLAIM |
| GHSA-9rwj-6rc7-p77c-risk-affected | {"affected": "AFFECTED", "priority": "P2", "risk_level": "HIGH"} | {"affected": "UNKNOWN", "priority": "REVIEW_REQUIRED", "risk_level": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-9rwj-6rc7-p77c-risk-fixed | {"affected": "NOT_AFFECTED", "priority": "MONITOR", "risk_level": "LOW"} | {"affected": "UNKNOWN", "priority": "REVIEW_REQUIRED", "risk_level": "UNKNOWN"} | NO_MATCH | G:EVIDENCE |
| GHSA-9rwj-6rc7-p77c-multihop | {"priority_asset_ids": ["demo-GHSA-9rwj-6rc7-p77c-affected"]} | {"priority_asset_ids": []} | NO_MATCH | G:EVIDENCE |
| GHSA-935w-9g4m-p28p-facts | {"cve": "CVE-2026-105752", "cvss_v3": {"score": 3.1, "vector_string": "CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:L/A:N"}, "cvss_v4": {"score": 0.0, "vector_string": null}, "cwes": ["CWE-200", "CWE-524"], "summary": "vLLM: Harmony tool continuations drop `cache_salt` — restoring a cross-tenant prefix-cache membership oracle"} | {"cve": "CVE-2026-105752"} | NO_MATCH | C:CLAIM |
| GHSA-935w-9g4m-p28p-affected | {"affected": "AFFECTED"} | {"affected": "AFFECTED"} | MATCH | MATCH:MATCH |
| GHSA-935w-9g4m-p28p-fixed | {"affected": "NOT_AFFECTED"} | {"affected": "NOT_AFFECTED"} | MATCH | MATCH:MATCH |
| GHSA-935w-9g4m-p28p-unknown | {"affected": "UNKNOWN"} | {} | NO_MATCH | H:INPUT |
| GHSA-935w-9g4m-p28p-release-and-poc | {"patch_status": "CONFIRMED_FIX", "poc_status": "NO_EVIDENCE"} | {"patch_status": "CONFIRMED_FIX"} | NO_MATCH | G:EVIDENCE |
| GHSA-935w-9g4m-p28p-commit-candidate | {"patch_status": "PATCH_CANDIDATE"} | {"patch_status": "CONFIRMED_FIX"} | NO_MATCH | C:CLAIM |
| GHSA-935w-9g4m-p28p-risk-affected | {"affected": "AFFECTED", "priority": "P3", "risk_level": "LOW"} | {"affected": "AFFECTED", "priority": "P3", "risk_level": "MEDIUM"} | NO_MATCH | D:RISK |
| GHSA-935w-9g4m-p28p-risk-fixed | {"affected": "NOT_AFFECTED", "priority": "MONITOR", "risk_level": "LOW"} | {"affected": "NOT_AFFECTED", "priority": "DEFER", "risk_level": "LOW"} | NO_MATCH | D:RISK |
| GHSA-935w-9g4m-p28p-multihop | {"priority_asset_ids": ["demo-GHSA-935w-9g4m-p28p-affected"]} | {"priority_asset_ids": ["demo-GHSA-935w-9g4m-p28p-affected"]} | MATCH | MATCH:MATCH |
| GHSA-c67j-w6g6-q2cm-gap | {"affected": "NOT_AFFECTED"} | {"affected": "UNKNOWN"} | NO_MATCH | B:IMPACT_SCOPE |
| GHSA-c67j-w6g6-q2cm-older-fix | {"affected": "NOT_AFFECTED"} | {"affected": "UNKNOWN"} | NO_MATCH | B:IMPACT_SCOPE |
| cross-advisory-priorities | {"priority_asset_ids": ["demo-GHSA-53q9-r3pm-6pq6-cross", "demo-GHSA-c67j-w6g6-q2cm-cross"]} | {} | NO_MATCH | I:UNSUPPORTED_SCOPE |
| cross-advisory-missing-version | {"can_confirm_not_affected": false} | {} | NO_MATCH | I:UNSUPPORTED_SCOPE |

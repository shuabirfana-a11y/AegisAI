# 三组真实案例

全部来自 Phase6 现有数据库，原始数据非 fixture。PyTorch 展示候选与证据不足；MLflow 展示 KEV、版本与修复关联；vLLM 展示限定搜索无公开候选及版本核验。GitHub初始限流后恢复，已取得真实官方公告/README/Patch metadata。Case A为PyTorch标识/GHSA/漏洞主题在CVE与OSV中一致（关联转载只算一组）；厂商包名差异保留未知。Case B为MLflow KEV/固定版本/官方PR。Case C为vLLM影响表达差异、patched表达未知及限定范围无PoC候选。

### CVE-2025-32434

目标 `3df70d68-c31e-43a4-9c86-23485eb4e6f4`；vendor=CONFLICT, epss=CONFLICT, kev=NO_RESULT, poc=PARTIAL, patch=SUCCESS, version=SUCCESS。实际 13 Claim、25 Evidence、3 PoC 候选、1 Patch 候选、3 冲突。耗时 14499.3 ms / 7 HTTP 请求。

Fixed Version 原始断言：`[{"package": "torch", "version": "2.6.0", "ecosystem": "PyPI"}]`。EPSS、KEV、产品、影响范围、核验状态、引用来源、Timeline 全字段在 [CVE-2025-32434_api_detail.json](CVE-2025-32434_api_detail.json)；任务/Checked Sources/错误与原始 ID 在 [CVE-2025-32434_real_case.json](CVE-2025-32434_real_case.json)。

### CVE-2026-57173

目标 `9ffd574a-4dee-470f-b64c-4a6c370a8750`；vendor=CONFLICT, epss=CONFLICT, kev=NO_RESULT, poc=NO_RESULT, patch=CONFLICT, version=CONFLICT。实际 10 Claim、15 Evidence、0 PoC 候选、3 Patch 候选、2 冲突。耗时 24951.3 ms / 7 HTTP 请求。

Fixed Version 原始断言：`[{"package": "vllm", "version": null, "ecosystem": "PyPI", "raw_expression": ">=0.24.0"}, {"package": "vllm", "version": "0.24.0", "ecosystem": "PyPI"}]`。EPSS、KEV、产品、影响范围、核验状态、引用来源、Timeline 全字段在 [CVE-2026-57173_api_detail.json](CVE-2026-57173_api_detail.json)；任务/Checked Sources/错误与原始 ID 在 [CVE-2026-57173_real_case.json](CVE-2026-57173_real_case.json)。

### CVE-2026-64849

目标 `018e5add-2e85-49a1-8547-899e47950949`；vendor=CONFLICT, epss=CONFLICT, kev=CONFLICT, poc=PARTIAL, patch=CONFLICT, version=CONFLICT。实际 13 Claim、20 Evidence、3 PoC 候选、4 Patch 候选、1 冲突。耗时 16476.8 ms / 10 HTTP 请求。

Fixed Version 原始断言：`[{"package": "mlflow", "version": "3.15.0", "ecosystem": "PyPI"}]`。EPSS、KEV、产品、影响范围、核验状态、引用来源、Timeline 全字段在 [CVE-2026-64849_api_detail.json](CVE-2026-64849_api_detail.json)；任务/Checked Sources/错误与原始 ID 在 [CVE-2026-64849_real_case.json](CVE-2026-64849_real_case.json)。


Demo 优先候选：CVE-2026-64849；可展示真实官方公告→两个Confirmed官方PR→EPSS/KEV→Claim/Evidence→版本来源冲突→ReviewTask→Timeline→门禁；不执行PoC。当前最终状态以final_trust_recheck及api_detail为准，results中的CONFLICT是当次任务时状态，历史错误和退役冲突均保留。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

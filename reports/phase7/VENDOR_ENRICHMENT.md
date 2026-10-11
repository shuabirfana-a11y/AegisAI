# 厂商公告

范围限定 PyTorch `pytorch/pytorch`、vLLM `vllm-project/vllm`、MLflow `mlflow/mlflow`，来自现有 PyPI 包标识与 Phase2 冻结生态。按 CVE/GHSA 与官方仓库映射，查询 GitHub Repository Security Advisory API，发布/撤回状态和显式 CVE 必须匹配。

结构化 package/range/patched_versions 形成 Claim，Evidence 精确指向原始 JSON pointer。域外包与不匹配 CVE 为 UNRESOLVED，不按产品名称猜测。公告、OSV 和 CVE 的 GitHub 原出版来源归一化为同一 lineage；不能算三份独立背书。查询失败记录错误和 retryable，不能假称厂商没有公告。

官方 API 文档：https://docs.github.com/en/rest/security-advisories/repository-advisories 。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。

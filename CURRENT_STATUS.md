# 当前交付状态

2026-10-19：本地研究与演示版本，有已知限制。

当前代码包含任务完整性约束、Schema重试反馈、包身份/版本范围支持和来源关系归组修正，已有真实调查证据。启动入口以 README 与 QUICKSTART_WINDOWS.md 为准；早期阶段说明保留作历史资料。

最新完整自动评测和验证边界见 [docs/release/VALIDATION.md](docs/release/VALIDATION.md)。这些自动匹配结果不代表人工语义准确率。尚未证明整体架构优于普通单次模型；Windows组合Worker、并发、取消/超时恢复、风险政策绑定和跨机冷启动仍须进一步验收。

本次仅整理发布，未更改业务逻辑、模型、Gold、评分、Gate或Verification标准，未重新运行49题。

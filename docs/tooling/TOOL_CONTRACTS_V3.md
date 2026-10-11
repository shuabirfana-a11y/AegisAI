# ToolContractV3

共 30 个具名工具；具体输入见同目录 JSON。输入均禁止额外字段，拒绝任意SQL、URL、Shell和POC执行。

READ_ONLY HTTP工具需要Bearer鉴权；Actor由服务端环境配置，调用方不能提交Actor。需要WRITE、REVIEW_ACTION或EXTERNAL_NETWORK的调用仅在服务端许可的编排中执行。

返回 tool/status/data/evidence_refs/warnings/errors/retryable/trace_id/duration_ms。状态区分success/partial/no_result/failed。来源陈述不能提升为CONFIRMED，冲突和过期证据进入复核或弃答。每次调用持久化AgentRun/ToolCallRecord。

Fast至多2次工具；全局32次、最长120秒、Task默认30秒、并行3个角色、最多2次重试。公开trace仅列执行摘要。

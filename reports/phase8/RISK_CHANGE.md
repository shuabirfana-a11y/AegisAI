# 风险变化与针对性重算

AssetRiskSnapshot/AssetRiskChange不可变；版本、PoC、KEV、EPSS、Patch、匹配、核验和组件移除产生结构化前后状态事件。同输入重复重算不重复，A→B→A保留三次观察。AssetInventoryEvent保留added/updated/removed及版本revision。快照及匹配指纹包含最终核验状态与range/source/Claim/Evidence依赖，过期重算不能复用旧确定Match。

手工/导入变更同步重算本asset；intel事件dispatch查Range和package-scoped Claim的精确包相关资产，job_key=event/asset指纹避免重复。Phase6新SourceObservation/Range无情报事件时，比较依赖指纹差量，仅排变化资产，不在dispatch中计算风险；待处理资产不重复排source任务。due用SKIP LOCKED，失败30秒后可重试最多3次；事务失败不吞掉历史。无每日全库暴算/无Kafka。CLI为管理员本地工具，没有常驻调度daemon，后续部署需安排dispatch/due运行。

实际queue_actual.json保留排程/完成记录；资产数据不外传。GET检查库存revision、完整源/范围/Claim/Evidence依赖、新鲜度及后来的情报事件/任务，失效标is_stale、UNCERTAIN/REVIEW；早于新快照的已耗尽失败任务不永久污染新评估。

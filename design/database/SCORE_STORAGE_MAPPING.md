# 评分能力到数据及可重复统计

本轮只证明结构与约束，不生成赛题性能成绩。正式评分口径以requirements/SCORE_MAPPING与EVALUATION_REQUIREMENTS为准；初赛/决赛的百分比/时效是未来门槛。无真值或分母为0必须N/A，不临时硬编码统计数。

| 能力/指标 | 可计算的数据 | 分母/限制 |
|---|---|---|
| 多源类别 | Source.category/enabled + SyncRun成功/有效Observation | 已真实接入类别distinct，不是研究目录条数；CVE/OSV/KEV不直接算三类 |
| 持续/增量 | run.started/finished/status/cursors/coverage/gaps/retry_of | 实际完整窗口/恢复；checkpoint推进需同恢复事务 |
| 采集延迟 | 源published与首次有效retrieved/event detected | 新增前瞻样本，历史回补/未知/负时钟/漏采单列coverage |
| 富化维度/覆盖 | typed CVSS/CWE/Range/POC/Patch/知识/Asset Claim及Evidence | distinct合格维度/主体；候选/缺失/冲突分开，不是非null字段数 |
| 富化准确率/Recall | EvaluationCase validated gold + Result逐事实prediction | 正确相关输出/全部输出；可穷尽限定源时间产品gold内Recall |
| PoC | association与usability不同Claim/Case task | 相关不等于可用；不执行PoC，不把URL默认verified |
| Patch | SHA/release/branch + Claim/Evidence + EvaluationResult | 分支适用证据与完整真值，不用短SHA猜 |
| 版本与AI相关性 | parser/model/method、原表达、Assessment；Case/Result | 全体Accuracy与supported coverage；unknown/unsupported不可剔除 |
| QA/多跳/引用 | AgentRun/ToolCall/AgentCitation + Case rubric/Result | 完整2分题/全部测试题，partial另报；actual tool/evidence依赖，不保存私有思维 |
| 响应时间/稳定 | Run完整开始结束与Result.latency/status | P50/P95及逐题/timeout/失败，非首token；官方≤5s聚合口径需明确 |
| Agent编排/工具效率 | 实际工具名/输入输出摘要/sequence/attempt/status/duration | 任务完成、实际调用次数、错误恢复；当前模型仅预留，没有实际执行 |
| 工程与文档 | migrations + tests + schema/Raw历史 + Source/SyncRun | 本阶段迁移/约束实际通过；部署、监控、DevOps未实现 |

结果来源于真实逐项Case/Run/Result，最终测试集hash/as_of/config/model/environment固化。无模型、自主Agent、Collector运行时，相关指标为空/NA，不因存在表就声称赛题功能完成。现有开发种子待人工确认，新数据库fixture全部synthetic；真实Demo/Benchmark到指定后续阶段再开展。

# 独立代码审查与修复

审查使用独立上下文、只读方式检查实现、计划、文档与真实运行记录；没有修改数据库、启动进程或运行迁移。结果：无 Critical；4 项 Important；没有 Minor。以下均在同一轮修复中用6项能失败的回归用例复现，另补3项相邻检查点续跑用例，再跑完整套件验证：131/131通过、无失败和跳过、1项第三方弃用警告；没有重复派发审查。

| 问题 | 修复 | 红→绿回归 |
|---|---|---|
| KEV recheck 丢弃刚发现的变动/移除，却确认整个新目录 item_hashes | work 保留原 pending+changed+removed+recheck todo，只限制本次处理选择；下一次仍看得到尚未处理变化 | test_kev_recheck_retains_newly_discovered_item_work 的 updated/removed 两例 |
| CVE 基线100后降低limit10漏掉原已监测后90路径变化并推进commit | 先收集全部 prior_covered 变化，再应用处理limit；历史重建也保留全部已声明路径 | test_cve_smaller_limit_retains_entire_previously_covered_scope 的 ancestor/rebuild 两例 |
| 旧raw解析升级使用现在的取回时间，误把旧评分/版本标当前 | CLI保留raw原取回时间；API按raw首次取得的修订顺序，随后按解析/评估时间选同raw最新解析 | test_old_raw_parser_replay_cannot_replace_current_source_revision |
| CVE显式SEMVER类型被当PEP440，build metadata错误排序 | 来源versionType先门控；仅未声明或明确Python/PEP440再尝试PyPI规则，semver/git/custom等保留unsupported和原文 | test_cve_explicit_semver_never_uses_pep440_build_order |

CVE normalizer 明确升为 cve-normalizer-v0.2。已有100份实际CVE原文离线升级解析，原raw/主体/产品不变，旧解析不删除；详细计数见 parser_upgrade_validation.json。其后再重放345份CVE/OSV实际原文，完全 skipped。升级是离线解析，不冒充新网络同步；历史19次SyncRun与初始错误保持原样。

同一修复轮补齐CVE/OSV增量队列续跑：CVE以已发现candidate commit为diff起点，避免成功commit尚未确认时不断把已完成路径加入队列；OSV同一索引原文只继续剩余pending，recheck保留新发现项。3项回归在恢复旧实现片段时全部失败，交付代码完整套件全部通过；checkpoint_regression_before.txt保存失败输出。OSV索引改变仍保守重新发现，频繁变化时可能重复处理；有界原文存储和域幂等避免重复主体，不宣称全量CDC。实际50项OSV pending没有虚报清空。

解析升级首次执行已提交3条后遇到unsupported范围缺失range_type约束错误；补齐原始ECOSYSTEM类型再运行100条得到97 updated、3 skipped、0 failed。旧历史保留，所有100条现有cve-normalizer-v0.2解析，不把部分重试隐藏成一次原子100条升级。

保留的边界决定（审查提出但未当成这次四项缺陷）：全量覆盖与drain全部KEV不在有限批次任务范围；认证/TLS/分布式调度/stale-run恢复尚未实现；Docker未运行；复杂已存在CVE/候选历史归并等待后续复核；Phase7和UI联调未启动。代价是这些场景必须在后续阶段单独验收，不能靠本次131项工程测试代替。

对于来源刻意回退到完全相同旧字节且带更旧native时间，当前保守保留历史，并不把旧raw重放提升为最新来源修订。代价是合法回退需要显式复核/新来源状态事件才能采用；本阶段不自动把旧陈述当成较新的安全事实，也不把它静默删掉。

其他实施决定：单来源顺序CLI而非队列；项目无Git仓库，保留文件/指纹/ledger，未伪造commit；CVE固定commit数据体从官方HTTPS取以避开promisor blob网络失败；OSV索引只取前1000完整行并声明partial，窗口未完整则不确认watermark；原文按字节保存，JSON键序不同保留修订而非重排后冒充原文。代价/限制已分别在KNOWN_ISSUES与SYNC_IMPLEMENTATION说明。

# 增量同步、失败与重放

CLI 支持 source/all、limit、recheck 与 raw-id replay，具体命令见 ../../backend/README.md。SyncRun 先提交 running，再进行网络操作，结束写 finished_at、真实五项计数、错误、前后检查点、coverage 与 normalize/database/总耗时。来源失败不会写虚假成功时间；Source.last_success_at 只在 declared scope 无 pending/错误的 succeeded 后更新。

| 检查点 | 含义与恢复策略 |
|---|---|
| CVE commit/covered_paths/pending_paths | Git 祖先 diff 在已声明路径检查更新，扩大基线检查未覆盖路径；非祖先保守重建有限范围；失败不确认新 commit |
| OSV watermark/baseline_bound/index_raw_id/last_processed_ids/pending | PyPI 有限基线；modified index 24h overlap，保留同时间所有 ID；前段未覆盖完整窗口时不推进 watermark；失败/未处理继续 pending |
| KEV raw_id/etag/item_hashes/catalog_version/normalized_catalog_version/pending | 下载层完整目录与域处理层分开；安全更新缓存/hash，未全部处理不确认 normalized_catalog_version；304 复用完整 raw |

recheck 保留既有 backlog，不因只看上一批就消掉尚未处理的 ID。KEV 的 not-listed 只在完整新目录的条目差量中生成；不能把限量处理的缺席推导为移除，更不能把移除变成 false exploitation。

独立审查后补齐：KEV recheck期间新发现的changed/removed也加入pending；CVE处理limit降低不缩小以前声明的监测范围，先收集整个prior_covered变化/重建再限量。旧raw离线重放保留原取回时序，API不会把解析发生时间当成新的来源修订时间。

小批量续跑把已发现的前沿与已完成的水位分开：CVE以candidate_checkpoint.commit继续发现新diff，以pending_paths处理旧队列；未处理完不确认成功commit。OSV对同一index_raw_id的既有队列只处理剩余pending，不把本窗口已完成ID再次加入；索引改变时重新发现，允许保守重复取回但不跳过变化。OSV recheck也保留本次新发现项，下一次普通同步继续处理。纯适配器回归证明两条同时间记录在limit1下能分别完成并最终确认水位；此验证没有把实际数据库的50项OSV pending伪装成已处理。

逐条先独立 commit raw，再语义解析与域事务；解析/约束失败保留 raw 和失败 observation，然后继续下一条。原文相同且解析版本相同时域写入 skipped；本次 fetch/SyncRun 仍可记录。升级 normalizer 时显式变更版本，同 raw 新增不可变解析历史。单条 CVE/OSV replay 完全离线；目录必须带条目上下文通过 source 同步恢复。

计数单位是逻辑来源记录，不是 HTTP 请求或唯一漏洞。请求失败已尝试的 ID 计入 fetched+failed；开始取目录/元数据就失败的运行，fetched/records_failed 可为 0，但 operation error 和 failed run 必须存在。目录 raw 不计为一个 KEV 逻辑条目。new vulnerability 数独立保存在 run metadata。

OSV 公开接口的 JSON 键序可能变化；实际比较显示 semantic hash 相同而原始字节 hash 不同。当前按字节保存不可变 raw/解析修订并计 updated，不能把 updated 宣传为新增安全事实。原始字节相同的重查/离线重放全部跳过域写入；主体、产品与标识保持幂等。raw_representation_comparison.json 提供比较证据。

http_duration_ms 汇总最终成功的 HTTP 调用（包含它们内部恢复的重试），完全失败的调用未计入该字段；总同步时间则包括所有失败等待与 Git 元数据操作。因此不能用该 HTTP 字段冒充所有网络等待的总时间。

JSON 日志包含 event/source/sync_run_id/external_id/status/error_type/duration_ms 字段；逐条及 HTTP 层的未知上下文可为 null。错误只保存受控类型，不输出密码、连接串、请求头或任意外部异常文本。实际初始 Git、HTTP 超时及 gzip 失败全部保留在 sync_runs.json 与 logs/。

目前单来源顺序执行，没有分布式租约/队列；进程崩溃后的 running 需显式人工恢复，本阶段没有自动猜测超时并改状态。HTTP 是连接/读取超时，Git 单次操作 180s；没有整批硬截止时间。上述工程限制与全量恢复能力不能隐去。

# 真实数据验证

时间：2026-10-03T10:22:05.818386+00:00。正式本地库 aegis_phase6:55436，所有数量来自实际提交；测试库另行 rollback。三源均按 limit 1→10→100 运行，原始失败与恢复均保留。limit 是上限，不要求每次新增同数记录；CVE 扩大100路径时会扣除已覆盖10路径，所以初次 fetched=90。

| 来源 | limit | 类型 | 状态 | fetched | created | updated | skipped | failed | 总秒数 | HTTP请求 |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| CVE_LIST | 1 | initial | failed | 0 | 0 | 0 | 0 | 0 | 36.429 | 0 |
| OSV | 1 | initial | failed | 0 | 0 | 0 | 0 | 0 | 568.669 | 4 |
| CISA_KEV | 1 | initial | failed | 0 | 0 | 0 | 0 | 0 | 5.88 | 1 |
| CVE_LIST | 1 | incremental | succeeded | 1 | 1 | 0 | 0 | 0 | 18.782 | 0 |
| CISA_KEV | 1 | initial | partial | 1 | 1 | 0 | 0 | 0 | 4.316 | 1 |
| CISA_KEV | 10 | incremental | partial | 10 | 10 | 0 | 0 | 0 | 4.274 | 1 |
| CVE_LIST | 10 | incremental | failed | 0 | 0 | 0 | 0 | 0 | 14.982 | 0 |
| CISA_KEV | 100 | incremental | partial | 100 | 100 | 0 | 0 | 0 | 6.892 | 1 |
| OSV | 1 | initial | succeeded | 1 | 1 | 0 | 0 | 0 | 36.909 | 4 |
| CVE_LIST | 10 | incremental | succeeded | 9 | 9 | 0 | 0 | 0 | 76.259 | 9 |
| OSV | 10 | incremental | succeeded | 10 | 9 | 0 | 1 | 0 | 193.721 | 15 |
| OSV | 100 | incremental | partial | 100 | 82 | 0 | 8 | 10 | 1351.436 | 158 |
| CVE_LIST | 100 | incremental | partial | 90 | 85 | 0 | 0 | 5 | 102.32 | 90 |
| CVE_LIST | 100 | incremental | succeeded | 90 | 5 | 0 | 85 | 0 | 137.053 | 90 |
| CISA_KEV | 100 | recheck | partial | 100 | 0 | 0 | 100 | 0 | 9.496 | 1 |
| CVE_LIST | 100 | recheck | succeeded | 100 | 0 | 0 | 100 | 0 | 78.697 | 100 |
| OSV | 100 | recheck | succeeded | 100 | 8 | 92 | 0 | 0 | 93.745 | 101 |
| OSV | 100 | recheck | succeeded | 100 | 0 | 50 | 50 | 0 | 116.696 | 102 |
| OSV | 10 | incremental | partial | 10 | 0 | 3 | 7 | 0 | 46.569 | 11 |

开始即失败的 operation error 与 records_failed 分开：某些 Git/索引/解码失败 fetched=0、records_failed=0，但 run=failed 且 error_summary 非空。具体逐条错误、checkpoint、scope 和耗时见 sync_runs.json；HTTP 请求/计时来自对应 LIVE_RESULT 日志，没有用后面的成功覆写初始失败。全部日志在 logs/。

OSV 同语义响应会因 JSON 键序或数据集/API 表示不同产生新字节 hash；当前保存不可变 raw/解析历史并计 updated，不能把它当成新安全事实。重复100条 API 回查 created=0、新漏洞=0，但会出现 updated；精确原文字节的345份离线重放完全 skipped。比较证据见 raw_representation_comparison.json。HTTP duration 只累计最终成功调用，全部失败等待仍包含在总同步时间内。

| 来源 | distinct 已解析外部ID | raw 数 | 状态 | pending |
|---|---:|---:|---|---:|
| CISA_KEV | 111 | 1 | partial | 1622 |
| OSV | 100 | 246 | partial | 50 |
| CVE_LIST | 100 | 100 | succeeded | 0 |

主体数 278；raw 数 347；产品数 198。全部 347 份 raw 的 SHA256 与数据库字节一致。raw completeness 分布：{"complete": 346, "partial": 1}。KEV 同一完整目录的许多条目共用一个 raw UUID，因此不能按记录数推算 raw 数。

跨来源真实案例 CVE-2025-32434：唯一主体 UUID 3df70d68-c31e-43a4-9c86-23485eb4e6f4；来源 CVE_LIST、OSV；原文 3 份。cross_source_example.json 含原文 UUID/hash/固定 URL、原生时间、双方评分/版本与 locator；raw_examples/ 是对应实际字节。合并不表示独立证据或已核验，未伪造 KEV 第三条来源。

最初100上限运行的基础耗时（失败/重复记录也纳入该次实测）：

| 来源 | 运行UUID | fetched | normalize ms | DB ms | 总 ms |
|---|---|---:|---:|---:|---:|
| CVE_LIST | a736caa5-9c0a-4e3e-afb8-d439e7a50d76 | 90 | 34.71 | 4475.42 | 102320.28 |
| OSV | 5e6eab81-56bd-4fa1-8edc-db4754866a1c | 100 | 85.10 | 6449.53 | 1351435.88 |
| CISA_KEV | 207c39f6-357a-4488-a206-80445cdd53a0 | 100 | 136.35 | 3610.52 | 6891.94 |

API 实际 HTTP 验证全部返回预期状态，api_validation.json 保存响应与5次样本分布；包括真实健康状态、sources、runs、列表/详情、筛选，以及404/422。这是本机基本观察，不是比赛 Benchmark、准确率、并发压测或部署 SLA。离线原文重放结果另见 replay_validation.json，不能计为新增网络采集。

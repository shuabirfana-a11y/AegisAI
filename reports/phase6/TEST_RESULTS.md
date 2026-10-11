# 测试结果

实际运行 pytest backend/tests：131/131 passed，failed=0、skipped=0，1项第三方 AnyIO alias 弃用警告。结果时间 2026-10-03T10:19:53.963078+00:00；原输出 test_output.txt、逐项结果 test_results.json。使用 PostgreSQL 17.11，不使用 SQLite替代数据库测试。

65项使用真实 PostgreSQL（包括原阶段43项、域持久化13项、同步4项、API5项），2项元数据检查，其余64项为纯单元/适配器/无数据库健康检查。网络 mock 用于确定性失败/重试场景；不冒充公开数据实测。全套还保留原45项 Phase5 回归。

| 任务测试 | 实际证据 |
|---|---|
| TEST01 同CVE多来源 | 真库两来源、一个主体、两份raw和两份评分；公开数据另外验证 |
| TEST02 同记录重复 | 原文/产品/标识/引用/范围/评分不新增；同步返回 skipped |
| TEST03 内容变化 | 新 raw+observation，旧 raw/评分/描述留存；逐条 sync updated |
| TEST04 来源超时 | SyncRun failed/finished，last_success null，checkpoint 不前推 |
| TEST05 429 | 有界 Retry-After/backoff+jitter；400不重试 |
| TEST06 非JSON/坏格式 | 原文先存，解析失败记录，一条失败不阻止下条提交 |
| TEST07 版本解析 | PyPI上下界、含端点、pre/dev/post/local、unknown/SEMVER/GIT、0哨兵/last_affected |
| TEST08 来源字段冲突 | CVE/OSV描述/评分分开，低优先级不能覆盖主投影 |
| TEST09 非AI保留 | irrelevant raw 与域记录仍保留，三态筛选受控 |
| TEST10 重复同步 | SyncRun追加但域幂等；公开CVE与KEV100条重查、实际raw离线重放 |

其他有明确红→绿记录的修复：gzip一次解码、前段完整行及partial标识、recheck保留pending、固定commit HTTP blob、单CVE候选提升、多CVE不合并、未知供应商 FK、KEV无版本仍显示产品、完整发现窗口水位、严格空区间及SEMVER不冒用PEP440。最终独立审查的4项问题已修复；另外3项CVE/OSV小批量续跑与重查用例证明不会重复入队已完成项，也不会丢掉新发现项。显式解析器升级测试确认同 raw 新修订、旧 observation 不变；旧原文重放不能取代较新的来源修订。证据见INDEPENDENT_REVIEW.md与checkpoint_regression_before.txt。

迁移 upgrade→downgrade→upgrade 在专用空测试库通过，43表/22保护/ORM无漂移，证据 migration_validation.json。真实开发库没有 downgrade。Docker unavailable：未运行镜像或Compose，只静态核验。没有正式Benchmark、人工gold、POC执行或Agent问答测试。

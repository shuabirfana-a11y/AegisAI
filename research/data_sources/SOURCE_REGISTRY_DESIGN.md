# Source Registry 概念设计

本轮只有source_catalog.json的研究配置，不建表、不启用调度。Source、publisher、上游数据集、transport host分别表达；共享api.github.com不表示同一个发布者。

| 字段 | 概念语义 |
|---|---|
| source_id / name | 稳定源ID与展示名；修订配置不改业务身份 |
| source_type / category | 数据源形态与业务类别；供应链标准不当实时情报源 |
| authority_level | 权威范围，如身份/包版本/利用正证据；不使用全字段统一可信分 |
| acquisition_method / acquisition_mode | API/Dataset/Git/RSS/HTML；metadata/link/licensed text等范围 |
| base_url / allowed_hosts / allowed_paths | 固定官方接口和批准redirect；不从正文授予地址权限 |
| enabled | 本轮false，后续通过接入校验后启用 |
| update_interval | 秒数；初始配置与上游cadence分开，0表示规范不轮询 |
| last_sync_at / last_success_at | 本轮null；上次尝试与完整成功不能混用；probe checked_at另记 |
| status | PLANNED/DEFERRED/RUNNING/SUCCEEDED/PARTIAL/FAILED/RATE_LIMITED/STALE等 |
| rate_limit | 官方规则/确认时间、响应预算、UNKNOWN；认证secret只引用，不存在正文 |
| license / license_scope / redistribution | 数据/代码/单文档分别、内容模式和外发范围；UNKNOWN不等于开放 |
| notes / coverage_scope / tier / phase | 采用理由/限产品/年份/生态/覆盖缺口与批次 |
| checkpoint / parser_version / source_schema | 恢复位置与解析版本；正式存储实现留后阶段 |
| freshness_budget / observed_latency | 团队目标与真实测量；未实现时不填假结果 |
| checked_at / evidence_refs | 本轮只读核查证据；不计生产采集成功 |

首批设置：CVE_LIST、OSV、CISA_KEV各1h观察；第二批公告/博客/arXiv/NIST/CAC起始6h，EPSS每日，知识Git每周。根据实际发布与限制优化；时效来自真实前瞻测量，不由配置自动算合格。GitHub共享budget；arXiv全机器单连接3秒限制。

注册变更保留版本/操作者/理由，关闭源不删历史；开启前核对真实正文、许可模式、host/路径、分页/增量、schema、错误处理和恢复。没有这些只显示PLANNED/NEED_VERIFY，不能给用户显示绿色运行正常。

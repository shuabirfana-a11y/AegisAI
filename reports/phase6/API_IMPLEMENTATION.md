# 最小查询 API

本机 http://127.0.0.1:8000，接口交互说明 /docs。只有五条业务只读 GET，实际原型 8768 未接 API。

| 路径 | 返回与参数 |
|---|---|
| /health | 应用与数据库状态分开；数据库不可用 503；某 Source failed 不使应用 down |
| /api/v1/sources | 三源 enabled/status、实际 last_sync/last_success、checkpoint、记录数与最新错误 |
| /api/v1/sync-runs | source 可筛选，offset>=0、limit=1..100；真实计数/时间/错误/coverage |
| /api/v1/vulnerabilities | q 搜 canonical/CVE、source、ai_relevance 三态、offset/limit；modified_desc 或 published_desc |
| /api/v1/vulnerabilities/{id} | UUID 或 canonical_id；主体、来源陈述、原文 UUID/hash/URL、native 时间、版本、产品、评分、CWE/引用、KEV 快照 |

分页固定按时间降序+UUID稳定排序，缺失时间在末尾。参数受 Literal/边界约束，非法 source/AI 三态返回 422；不存在返回 404；SQL 使用参数绑定，q 的 LIKE 通配符按字面转义。

详情中的 source_variants、范围、评分、引用标 is_current，历史仍可见；field_provenance、locator、lineage 和 normalizer_version 保留。raw_payload 不通过列表/详情返回，避免把未知内容当作 UI 执行材料；原文 metadata 指向数据库中的完整不可变内容。没有版本也能显示 KEV 原生 product。verification_status=pending 保持来源断言与未来核验结论的界限。

current排序依据raw原始取回的修订顺序，同一raw再按解析/评估时间选择新解析。旧raw升级重放不会覆盖较新raw的当前评分/范围/AI筛选；原始取得时间与后来解析时间分开。

Session 随请求释放，engine 随 lifespan 创建/释放；启动不迁移、不自动创建表。应用 DB 日志隐藏 SQL 参数。当前没有身份认证、CORS 配置、写接口或生产权限；服务仅监听 loopback。实际 HTTP 输出与 timings 见 api_validation.json，测试覆盖 health/503/source failure/分页/筛选/详情/404/422。

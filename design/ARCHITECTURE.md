# V0.1 架构

选择模块化单体＋独立采集命令进程＋PostgreSQL＋本地raw目录。没有8个微服务。备选“Dify编排全部链路”增加非确定性与凭证面；备选“OpenCTI主体”运维与数据模型过重，因此不选。

| 模块 | 输入→输出 | 不承担 |
|---|---|---|
| Collector | 受控CVE/OSV/KEV配置/游标→字节、headers摘要、观察时间 | 实体/版本推理、任意URL/PoC |
| Normalizer | raw+source schema→NormalizedVulnerability候选 | 丢弃未知字段、覆盖冲突 |
| Dedup | CVE/source外部ID/hash→复用身份或新revision | 删除跨来源观察 |
| Entity Resolution | 生态+包+官方repo映射→product/package/未确认 | 名字相似自动合并 |
| Version Service | range type/生态/events→解析状态及区间 | LLM判断版本、所有生态用SemVer |
| AI Filter | 已有产品映射+有范围的规则→RELATED/UNRELATED/UNKNOWN | 单关键词确认AI影响 |
| Enrichment | CVE CNA/ADP与OSV observations→字段claims/refs | 用最后到达字段抹掉不同source |
| Evidence Service | raw+字段定位→Evidence、claim支持/反驳链接 | 仅保存一个URL或LLM摘要 |
| API | 已持久化记录+授权→来源化只读JSON | 触发任意URL、自由SQL、可信状态修改 |

进程内函数/结构化对象通信；API与collector共享模型和数据库，不共享事务session。数据库不向外网发布；原始目录仅collector写/API受限读。API读取由完整提交的revision生成的projection，不能见到半个事务。

```mermaid
flowchart LR
 C[CVE List] --> CO[Collector]
 O[OSV] --> CO
 K[CISA KEV] --> CO
 CO --> R[原始字节与hash]
 CO --> N[Normalizer与去重]
 N --> E[实体 版本 AI规则]
 E --> Q[Claims与Evidence]
 R --> Q
 Q --> P[(PostgreSQL)]
 P --> A[只读REST API]
 A -.V0.2语义工具.-> F[Dify]
```

Source adapter、Version adapter、Blob store、AI classifier有协议/接口边界，但不为未来实现多个服务。v0.2再换对象存储、worker队列/更多生态并增加受限Agent Tool；原始hash、稳定ID和审核状态不变。

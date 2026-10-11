# 身份解析与幂等

CVE 是全局规范身份；CVE 语法与数据库全局命名空间约束一致。source:external_id 是无 CVE 记录的候选身份。明确 GHSA/OSV aliases 持久化为 ExternalIdentifier 与 VulnerabilityIdentifier；不使用标题相似度、LLM 或关键词合并。

同 CVE 多来源解析到一个 Vulnerability，但独立 RawDocument、SourceObservation、版本与 CVSS 保留。一个公告含多个 CVE 时连接多个独立主体，不能把不同 CVE 归并成一个。无 CVE 候选后来出现唯一明确 CVE 且该 CVE 尚无主体时，提升 canonical_id 并保留原 UUID 与来源历史，写身份变更元数据；已有另一主体或多 CVE 的歧义情形不强制合并。

source/external_id 的事务锁与按固定顺序取得的身份/alias advisory locks，配合数据库唯一索引保障同批幂等。相同 Source+external_id+raw revision+normalizer_version 已解析时，返回 skipped，不重复建产品、引用、评分、范围或 AI assessment；每次真实同步仍可追加 fetch observation 与 SyncRun。

原文变化则追加 raw/normalized/domain 历史，旧版本不可修改。normalizer 版本显式升级时允许同 raw 追加新解析修订；已测试旧版本仍保留、raw 数不变。主投影优先级为 CVE_LIST > OSV > KEV，同优先级按来源 modified 时间，避免后同步的低优先级描述覆盖原值；API 同时公开所有来源版本及 is_current。

产品使用显式 PyPI 规范包名和人工注册表。未知生态限制在来源和供应商 namespace；未知 vendor 不能与其他 vendor 错配。数据库复合 FK 保证范围使用的软件包属于所填产品。

真实案例是 CVE-2025-32434，两个来源 CVE_LIST + OSV、一个主体、至少两份原文与双方评分；API 和数据集的字节表示不同还会保留新修订。具体 UUID/hash/URL 和实测输出见 cross_source_example.json。二者可能复用上游同一公告；去重成功不代表两条独立证据或已完成核验。

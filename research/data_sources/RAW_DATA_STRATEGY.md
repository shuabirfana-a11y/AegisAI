# RawDocument 与证据策略

必须留原文才能定位结论、发现schema变化、重放标准化和追查错误。只留解析字段会丢原始范围、未知扩展、发布者与冲突依据。RawDocument是概念对象，不是本轮数据库表。

| 属性 | 语义 |
|---|---|
| raw_document_id | 系统稳定文档身份；内容可物理复用但不吞来源 |
| source / external_id | 注册源与源原生ID；聚合平台和原始publisher另存 |
| source_url / final_url | 请求与实际最终地址；合法redirect可回查；API分页/查询范围明确 |
| retrieved_at / first_retrieved_at | 本次成功获取与首次有效获取UTC；不能冒充出版日期 |
| published_at / modified_at | 原生出版/更改时间，可null；保留原字符串和时区/解析状态 |
| content_type / encoding | 实际响应类型及解析依据；类型不符不能当JSON成功 |
| raw_payload / raw_payload_ref | 原始entity字节或受控存储引用；压缩/解码规则独立记录 |
| content_hash | SHA-256原文entity字节；hash不证明发布者或内容正确 |
| transport_hash / parsed_text_hash | 若保留压缩wire或抽取正文则分别hash，不与raw混用 |
| http_status / ETag / Last-Modified | 传输观察；304没有新正文，不创建伪空raw |
| publisher / upstream_lineage / license | 发布者、转载依赖、单记录内容许可和使用范围 |
| snapshot_revision / completeness | commit/date/generation/catalog与完整/partial；probe的32KB CSV片段不能当全量快照 |
| trust / retention / redaction | UNTRUSTED；使用范围和保留策略；secret不进raw，必要脱敏另记影响hash |

RawDocument → Normalized Record → Evidence → Claim：一份raw可有多条标准记录（如KEV目录）；一个标准记录可提供很多字段级Evidence；一条Claim可被多个Evidence支持、反驳或提供上下文。Evidence记录raw_id、JSON Pointer/XPath/HTML定位/PDF页与段、excerpt/hash、publisher、observed_at、source revision、关系；locator必须针对对应raw版本解析，不能只存URL。

同URL新内容产生新raw revision，旧版不可原位覆盖；同字节多source可共享blob，但保留各自Source Observation、请求与时间。KEV使用catalog raw与条目locator；CVE容器发布者分别记录，ADP数组真实索引随raw确定。无需每次304保存相同全文。

原文按许可与数据类别保存：结构化公开核心源保留所有采用修订；至少覆盖项目评测/答辩可回放窗口，期限起始建议180天（团队配置、不是官方条款）。博客/CAC许可不明确默认metadata+link+必要证据引用，禁止自动公开全文；arXiv只先保存元数据/摘要，全文逐篇许可核对；NIST按出版声明/第三方标记处理。License unknown时不得称完全可再分发。

研究目录evidence/只保存本轮官方响应，用于内部审阅，不自动打包公开。生产parser不得执行HTML、PDF附件、RSS代码；保留下载文件并不授权运行它们。本文没有创建存储服务或表。

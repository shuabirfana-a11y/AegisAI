# 原始数据与来源观察

RawDocument是一份不可变内容修订；原文准确字节BYTEA+SHA256、source/external/URL、出版/修改/获取时间、content_type/publisher/许可/完整性均保留。parsed_payload JSONB只是方便结构化源解码，不能hash重新序列化JSON并假装原字节。16MiB上限超出则失败/缺口，不下载截断全文冒充完整；后续按实际体积迁移Object Storage引用与内容校验，此轮没有存储服务。

source+external是稳定来源记录身份；source+external+hash是修订幂等键。store_raw在同一键重复输入用INSERT ON CONFLICT DO NOTHING返回旧ID；不能DO UPDATE原文。相同ID内容变产生新Raw，旧Evidence仍固定原版本。相同字节不同源生成各自Raw/观察，未来可以复用blob，但不能丢publisher或算独立票。

SourceObservation在每次成功获取/标准化尝试结束追加，记录run/raw、publisher/upstream observation、lineage、locator、normalizer版本、输出缓存和解析状态。观察已追加后不原位改成parsed；raw先存、随后标准化完成追加新的完整观察，查询以指定raw/parser版本的完成观察为准。304观察只能连接仍存在的缓存raw，不创建空正文；失败HTTP观察raw可null，不能成为Evidence。

Source Registry从Phase 2选型导入时enabled=false、last_success=null、planned，不能复制probe checked_at为同步成功。源类别/权威范围可解释，authority不是概率。SyncRun queued/running→terminal，计数单位和覆盖在metadata/coverage_scope说明；cursor_before/after持久化，在raw/normalized/failed-ID与checkpoint同一恢复事务完成前不得推进成功高水位。succeeded要求finished且records_failed=0；partial保留失败清单，失败不能覆盖Source.last_success。

所有输入UNTRUSTED，不执行HTML、PDF、附件或PoC。metadata/content允许存储不等于允许再分发；许可未知默认metadata/link/必要引用。JSON/HTML/RSS原编码与必要解码记录在metadata；时间null及原粒度保留，不用retrieved代填published。跨层FK使Evidence来源与raw/source/observation对应。TEST-07及新增raw修订/多源同字节测试是真库测试，不表示正式Collector已实现。

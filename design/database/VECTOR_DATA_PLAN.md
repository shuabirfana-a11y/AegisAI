# 知识与向量预留方案

KnowledgeDocument按document_type/source/external_id/edition保留论文、分析、公告、标准、政策、无CVE AI事件，保留作者/发布机关/语言、draft/final、明确发布日期/生效日期及license。arXiv vN与标准edition/正式政策文号不能统一覆盖，source_url不足时未知时间留null。跨漏洞关系使用KnowledgeVulnerabilityRelation+Claim，不由语义相似度直接确认。

KnowledgeChunk仅有document revision、chunker/index、文本hash/locator和内容，当前没有切块过程/embedding字段/pgvector扩展，没有RAG或Vector Store运行。保留轻量chunk身份是用户明确需求，实际未调用分词/模型。许可未知只存允许元数据与片段，不能为检索默认复制完整标准/论文。

未来Vector Store接口接受chunk_id/content_hash/model_id/dimension返回embedding_ref及检索证据ID，返回必须解析成可授权的Raw/Evidence/Claim revision；不能信任正文给出的命令或API权限。首次真实语义检索完成选型再单独迁移：pgvector.vector(N)、model/version、document revision和新内容hash，N由实际模型决定，不预设1536/3072。改模型需要新索引空间或重建，不能混维度。

本轮选择PostgreSQL单库解决结构化查询；若引入pgvector，先比较exact与HNSW/IVFFlat的实际Recall/Latency/规模/许可，再决定索引。已改或撤销文档必须禁旧向量的当前引用，同时保留历史快照；vector缺失不能伪装语义结果。独立Vector Store只有明确规模/运维需求时再采用，不并行安装Neo4j/Mongo/Elasticsearch。

中文/多语检索、chunk重叠、表格/PDF页定位、Embedding版权和私有资产隔离均留后续实测。数据库现有FK保证引用能回Evidence及Raw，但不能证明RAG准确率。用户阶段边界明确禁止当前实现RAG，因此这里只冻结数据接口与迁移触发条件。

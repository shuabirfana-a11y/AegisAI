# 索引与查询策略

PK/UNIQUE自带B-tree，不能再给canonical_id/source_key/PURL重复索引。下面列出显式索引；低基数状态全局索引和覆盖索引后续依据真实查询计划扩展，不预报性能。复合Claim(vulnerability,status)适合某漏洞四态，不声称支持所有全局状态查询。

| 表 | 索引 | 顺序列 | 类型/谓词 |
|---|---|---|---|
| `core.products` | `ix_products_name` | canonical_name | B-tree |
| `core.vulnerabilities` | `ix_vulnerabilities_modified` | modified_at | B-tree |
| `core.vulnerabilities` | `ix_vulnerabilities_published` | published_at | B-tree |
| `core.vulnerabilities` | `ix_vulnerabilities_severity` | primary_severity | B-tree |
| `core.product_aliases` | `ix_product_aliases_lookup` | namespace, normalized_alias | B-tree |
| `raw.raw_documents` | `ix_raw_documents_identity_time` | source_id, external_id, retrieved_at | B-tree |
| `raw.sync_runs` | `ix_sync_runs_source_started` | source_id, started_at | B-tree |
| `app.asset_components` | `ix_components_asset` | asset_id | B-tree |
| `intel.epss_snapshots` | `ix_epss_vuln_date` | vulnerability_id, score_date | B-tree |
| `intel.knowledge_documents` | `ix_knowledge_type_date` | document_type, published_at | B-tree |
| `intel.known_exploitation` | `ix_kev_status` | catalog_status | B-tree |
| `raw.source_observations` | `ix_observations_raw_time` | raw_document_id, retrieved_at | B-tree |
| `core.affected_version_ranges` | `ix_ranges_vuln_package` | vulnerability_id, package_identifier_id | B-tree |
| `core.cvss_assessments` | `ix_cvss_vuln_version` | vulnerability_id, version | B-tree |
| `core.vulnerability_identifiers` | `uq_vi_one_cve_owner` | identifier_id | UNIQUE B-tree WHERE identifier_type='CVE' |
| `intel.poc_candidates` | `ix_poc_status` | status | B-tree |
| `intel.claims` | `ix_claims_root_status` | vulnerability_id, verification_status | B-tree |
| `intel.claims` | `uq_claims_adopted_knowledge_scope` | knowledge_document_id, predicate, scope_key | UNIQUE B-tree WHERE adopted AND knowledge_document_id IS NOT NULL |
| `intel.claims` | `uq_claims_adopted_vuln_scope` | vulnerability_id, predicate, scope_key | UNIQUE B-tree WHERE adopted AND vulnerability_id IS NOT NULL |
| `app.asset_vulnerability_matches` | `ix_matches_component_status` | asset_component_id, match_status | B-tree |
| `app.review_tasks` | `ix_reviews_status_priority` | status, priority | B-tree |
| `intel.evidence` | `ix_evidence_claim` | claim_id | B-tree |
| `intel.intelligence_events` | `ix_events_vuln_detected` | vulnerability_id, detected_at | B-tree |

Raw按source/external/retrieved查修订；SyncRun按source/start查最后任务；Evidence已有UNIQUE以claim_id为前缀且显式单列索引当前便于主要查询，正式数据量到达后用EXPLAIN ANALYZE判断是否合并冗余。包PURL exact查询走UNIQUE，别名按namespace/normalized查但不自动并实体。日期、severity、PoC状态、KEV目录态、Review状态/priority支持主要筛选；页游标用(time,id)稳定排序，offset仅小演示列表。

GIN/全文：本阶段不建全metadata JSONB GIN，也不对全文/向量作虚假性能承诺。英文/ID检索可后续独立迁移generated tsvector(simple)+GIN；中文需评估分词/substring或向量，不能称simple配置已支持中文语义搜索。JSONB仅在明确containment负载出现时加jsonb_path_ops索引。长URL/PURL的B-tree大小上限是已知风险；标准化层需校验并隔离异常，禁止截断成同一身份，必要时添加digest key及原值碰撞核对。

# 表关系与一致性

所有持久化引用使用显式FK，无通用entity_type/entity_id悬空链接。Nullable组合FK的MATCH SIMPLE是PostgreSQL行为，关键对象另有独立FK、非null和CHECK；未来写入服务必须验证业务scope，不能把FK当成事实真伪核验。

| 父表 | 子表 | FK列 | 基数与删除 |
|---|---|---|---|
| `app.agent_runs` | `app.tool_call_records` | agent_run_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `core.external_identifiers` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.products` | `core.package_identifiers` | product_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.products` | `core.product_aliases` | product_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `core.product_aliases` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `core.references` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `evaluation.datasets` | `evaluation.cases` | dataset_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `evaluation.datasets` | `evaluation.runs` | dataset_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `raw.raw_documents` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sync_runs` | `raw.sync_runs` | retry_of_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `raw.sync_runs` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `app.assets` | `app.asset_components` | asset_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.package_identifiers` | `app.asset_components` | package_identifier_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.products` | `app.asset_components` | product_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.package_identifiers` | `app.asset_components` | package_identifier_id, product_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `evaluation.cases` | `evaluation.results` | case_id, dataset_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `evaluation.runs` | `evaluation.results` | run_id, dataset_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `evaluation.cases` | `evaluation.results` | case_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `evaluation.datasets` | `evaluation.results` | dataset_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `evaluation.runs` | `evaluation.results` | run_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.raw_documents` | `intel.epss_snapshots` | raw_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `intel.epss_snapshots` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `intel.epss_snapshots` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.raw_documents` | `intel.knowledge_documents` | raw_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `intel.knowledge_documents` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.raw_documents` | `intel.known_exploitation` | raw_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `intel.known_exploitation` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `intel.known_exploitation` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.raw_documents` | `raw.source_observations` | raw_document_id, source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sync_runs` | `raw.source_observations` | sync_run_id, source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.raw_documents` | `raw.source_observations` | raw_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `raw.source_observations` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sync_runs` | `raw.source_observations` | sync_run_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `raw.source_observations` | upstream_observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `core.affected_version_ranges` | observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.package_identifiers` | `core.affected_version_ranges` | package_identifier_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.products` | `core.affected_version_ranges` | product_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `core.affected_version_ranges` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `core.affected_version_ranges` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.package_identifiers` | `core.affected_version_ranges` | package_identifier_id, product_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.knowledge_documents` | `core.ai_relevance_assessments` | knowledge_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `core.ai_relevance_assessments` | observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `core.ai_relevance_assessments` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `core.cvss_assessments` | observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `core.cvss_assessments` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `core.cvss_assessments` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.external_identifiers` | `core.vulnerability_identifiers` | identifier_id, identifier_type | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.external_identifiers` | `core.vulnerability_identifiers` | identifier_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `core.vulnerability_identifiers` | observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `core.vulnerability_identifiers` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `core.vulnerability_references` | observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.references` | `core.vulnerability_references` | reference_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `core.vulnerability_references` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `core.vulnerability_weaknesses` | observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `core.vulnerability_weaknesses` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.weaknesses` | `core.vulnerability_weaknesses` | weakness_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.knowledge_documents` | `intel.knowledge_chunks` | document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.raw_documents` | `intel.knowledge_chunks` | raw_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `intel.patch_candidates` | observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.products` | `intel.patch_candidates` | product_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `intel.patch_candidates` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `intel.patch_candidates` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `intel.poc_candidates` | observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `intel.poc_candidates` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `intel.poc_candidates` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.ai_relevance_assessments` | `core.vulnerability_ai_categories` | assessment_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.ai_security_categories` | `core.vulnerability_ai_categories` | category_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `core.vulnerability_ai_categories` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.cvss_assessments` | `intel.claims` | cvss_assessment_id, vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.patch_candidates` | `intel.claims` | patch_candidate_id, vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.poc_candidates` | `intel.claims` | poc_candidate_id, vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `app.asset_components` | `intel.claims` | asset_component_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.cvss_assessments` | `intel.claims` | cvss_assessment_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.knowledge_documents` | `intel.claims` | knowledge_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.package_identifiers` | `intel.claims` | package_identifier_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.patch_candidates` | `intel.claims` | patch_candidate_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.poc_candidates` | `intel.claims` | poc_candidate_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.products` | `intel.claims` | product_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.affected_version_ranges` | `intel.claims` | range_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `intel.claims` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `app.asset_components` | `app.asset_vulnerability_matches` | asset_component_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `app.asset_vulnerability_matches` | claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.affected_version_ranges` | `app.asset_vulnerability_matches` | matched_range_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.package_identifiers` | `app.asset_vulnerability_matches` | package_identifier_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `app.asset_vulnerability_matches` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `app.asset_components` | `app.asset_vulnerability_matches` | asset_component_id, package_identifier_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.affected_version_ranges` | `app.asset_vulnerability_matches` | matched_range_id, vulnerability_id, package_identifier_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `app.review_tasks` | claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `intel.evidence` | claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `intel.evidence` | claim_id, scope_key | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `intel.evidence` | observation_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.source_observations` | `intel.evidence` | observation_id, raw_document_id, source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.raw_documents` | `intel.evidence` | raw_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.raw_documents` | `intel.evidence` | raw_document_id, source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `intel.evidence` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `intel.knowledge_vulnerability_relations` | claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.knowledge_documents` | `intel.knowledge_vulnerability_relations` | knowledge_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `intel.knowledge_vulnerability_relations` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `intel.verification_results` | claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `app.agent_runs` | `app.agent_citations` | agent_run_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `app.agent_citations` | claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.evidence` | `app.agent_citations` | evidence_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.verification_results` | `app.agent_citations` | claim_id, claim_revision | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.evidence` | `app.agent_citations` | evidence_id, claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `app.audit_logs` | claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `app.review_tasks` | `app.audit_logs` | review_task_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.verification_results` | `app.audit_logs` | verification_result_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `intel.intelligence_events` | claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.evidence` | `intel.intelligence_events` | evidence_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.knowledge_documents` | `intel.intelligence_events` | knowledge_document_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `raw.sources` | `intel.intelligence_events` | source_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `core.vulnerabilities` | `intel.intelligence_events` | vulnerability_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.evidence` | `intel.verification_evidence` | evidence_id, claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.verification_results` | `intel.verification_evidence` | verification_result_id, claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.claims` | `intel.verification_evidence` | claim_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.evidence` | `intel.verification_evidence` | evidence_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |
| `intel.verification_results` | `intel.verification_evidence` | verification_result_id | 父1→子0..N；RESTRICT；精确唯一关系另见约束 |

Evidence复合FK保证raw/source/observation吻合、Claim scope吻合；VerificationEvidence保证核验与证据属于同一Claim；包→产品、match→组件包/漏洞范围、citation→Claim核验revision使用复合FK。CVE归属唯一，公告外部身份可多漏洞连接。历史表不级联删除。

# 主键 唯一 外键与检查约束

所有表UUID PK。主要约束由数据库实际执行，不依赖前端验证。Source.source_key唯一；canonical_id唯一；外部(namespace,type,value)唯一；包PURL及生态身份唯一；Raw修订(source,external,hash)唯一；PoC URL按漏洞唯一；Patch key按漏洞/产品/分支/type唯一；actor/request_key幂等。所有版本/评分/核验/目录三态均显式CHECK。

| 表 | 约束名 | 类型 | 字段/表达式 |
|---|---|---|---|
| `app.agent_runs` | `ck_agent_runs_duration_nonnegative` | CHECK | `duration_ms IS NULL OR duration_ms>=0` |
| `app.agent_runs` | `ck_agent_runs_status_values` | CHECK | `status IN ('queued','running','succeeded','partial','failed','timeout','cancelled')` |
| `core.ai_security_categories` | `uq_ai_security_categories_category_key` | UNIQUE | `category_key` |
| `core.products` | `uq_products_canonical_key` | UNIQUE | `canonical_key` |
| `core.vulnerabilities` | `ck_vulnerabilities_canonical_cve` | CHECK | `canonical_id !~* '^CVE-' OR canonical_id ~ '^CVE-[0-9]{4}-[0-9]{4,}$'` |
| `core.vulnerabilities` | `ck_vulnerabilities_primary_severity_values` | CHECK | `primary_severity IN ('critical','high','medium','low','info','unknown')` |
| `core.vulnerabilities` | `ck_vulnerabilities_status_values` | CHECK | `status IN ('published','withdrawn','rejected','unknown')` |
| `core.vulnerabilities` | `uq_vulnerabilities_canonical_id` | UNIQUE | `canonical_id` |
| `core.weaknesses` | `uq_weaknesses_cwe_id` | UNIQUE | `cwe_id` |
| `evaluation.datasets` | `ck_datasets_split_values` | CHECK | `split IN ('development','validation','final_test')` |
| `evaluation.datasets` | `uq_datasets_dataset_key_revision_hash` | UNIQUE | `dataset_key, revision_hash` |
| `raw.sources` | `ck_sources_authority_level_values` | CHECK | `authority_level IN ('official','authoritative','secondary','community')` |
| `raw.sources` | `ck_sources_interval_nonnegative` | CHECK | `update_interval >= 0` |
| `raw.sources` | `ck_sources_status_values` | CHECK | `status IN ('planned','deferred','running','succeeded','partial','failed','rate_limited','stale','need_review')` |
| `raw.sources` | `uq_sources_source_key` | UNIQUE | `source_key` |
| `app.tool_call_records` | `ck_tool_call_records_position_duration` | CHECK | `sequence_no>=0 AND attempt>0 AND (duration_ms IS NULL OR duration_ms>=0)` |
| `app.tool_call_records` | `ck_tool_call_records_status_values` | CHECK | `status IN ('succeeded','partial','failed','timeout','cancelled')` |
| `app.tool_call_records` | `fk_tool_call_records_agent_run_id_agent_runs` | FK RESTRICT | `agent_run_id→app.agent_runs.id` |
| `app.tool_call_records` | `uq_tool_call_records_agent_run_id_sequence_no_attempt` | UNIQUE | `agent_run_id, sequence_no, attempt` |
| `core.external_identifiers` | `ck_external_identifiers_global_cve` | CHECK | `identifier_type<>'CVE' OR (namespace='global' AND normalized_value ~ '^CVE-[0-9]{4}-[0-9]{4,}$')` |
| `core.external_identifiers` | `ck_external_identifiers_type_uppercase` | CHECK | `identifier_type=upper(identifier_type)` |
| `core.external_identifiers` | `fk_external_identifiers_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `core.external_identifiers` | `uq_external_identifiers_id_identifier_type` | UNIQUE | `id, identifier_type` |
| `core.external_identifiers` | `uq_external_identifiers_namespace_identifier_type_normalized_value` | UNIQUE | `namespace, identifier_type, normalized_value` |
| `core.package_identifiers` | `fk_package_identifiers_product_id_products` | FK RESTRICT | `product_id→core.products.id` |
| `core.package_identifiers` | `uq_package_identifiers_ecosystem_namespace_package_name` | UNIQUE | `ecosystem, namespace, package_name` |
| `core.package_identifiers` | `uq_package_identifiers_id_product_id` | UNIQUE | `id, product_id` |
| `core.package_identifiers` | `uq_package_identifiers_purl` | UNIQUE | `purl` |
| `core.product_aliases` | `fk_product_aliases_product_id_products` | FK RESTRICT | `product_id→core.products.id` |
| `core.product_aliases` | `fk_product_aliases_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `core.product_aliases` | `uq_product_aliases_product_id_namespace_alias_type_normalized_alias` | UNIQUE | `product_id, namespace, alias_type, normalized_alias` |
| `core.references` | `fk_references_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `core.references` | `uq_references_canonical_url` | UNIQUE | `canonical_url` |
| `evaluation.cases` | `ck_cases_ground_truth_status_values` | CHECK | `ground_truth_status IN ('draft','validated','unknown')` |
| `evaluation.cases` | `fk_cases_dataset_id_datasets` | FK RESTRICT | `dataset_id→evaluation.datasets.id` |
| `evaluation.cases` | `uq_cases_dataset_id_case_key` | UNIQUE | `dataset_id, case_key` |
| `evaluation.cases` | `uq_cases_id_dataset_id` | UNIQUE | `id, dataset_id` |
| `evaluation.runs` | `ck_runs_status_values` | CHECK | `status IN ('succeeded','partial','failed','timeout','cancelled')` |
| `evaluation.runs` | `ck_runs_time_order` | CHECK | `finished_at>=started_at` |
| `evaluation.runs` | `fk_runs_dataset_id_datasets` | FK RESTRICT | `dataset_id→evaluation.datasets.id` |
| `evaluation.runs` | `uq_runs_id_dataset_id` | UNIQUE | `id, dataset_id` |
| `raw.raw_documents` | `ck_raw_documents_inline_size_limit` | CHECK | `octet_length(raw_payload) <= 16777216` |
| `raw.raw_documents` | `ck_raw_documents_sha256` | CHECK | `content_hash ~ '^[0-9a-f]{64}$'` |
| `raw.raw_documents` | `fk_raw_documents_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `raw.raw_documents` | `uq_raw_documents_id_source_id` | UNIQUE | `id, source_id` |
| `raw.raw_documents` | `uq_raw_revision` | UNIQUE | `source_id, external_id, content_hash` |
| `raw.sync_runs` | `ck_sync_runs_counts_nonnegative` | CHECK | `records_fetched>=0 AND records_created>=0 AND records_updated>=0 AND records_skipped>=0 AND records_failed>=0` |
| `raw.sync_runs` | `ck_sync_runs_status_values` | CHECK | `status IN ('queued','running','succeeded','partial','failed','rate_limited','cancelled','need_review')` |
| `raw.sync_runs` | `ck_sync_runs_success_no_failed` | CHECK | `status <> 'succeeded' OR records_failed=0` |
| `raw.sync_runs` | `ck_sync_runs_terminal_finished` | CHECK | `status NOT IN ('succeeded','partial','failed','cancelled') OR finished_at IS NOT NULL` |
| `raw.sync_runs` | `ck_sync_runs_time_order` | CHECK | `finished_at IS NULL OR finished_at >= started_at` |
| `raw.sync_runs` | `fk_sync_runs_retry_of_id_sync_runs` | FK RESTRICT | `retry_of_id→raw.sync_runs.id` |
| `raw.sync_runs` | `fk_sync_runs_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `raw.sync_runs` | `uq_sync_runs_id_source_id` | UNIQUE | `id, source_id` |
| `app.asset_components` | `ck_asset_components_positive_revision` | CHECK | `inventory_revision>0` |
| `app.asset_components` | `ck_asset_components_source_values` | CHECK | `source IN ('manual','sbom','scanner')` |
| `app.asset_components` | `fk_asset_components_asset_id_assets` | FK RESTRICT | `asset_id→app.assets.id` |
| `app.asset_components` | `fk_asset_components_package_identifier_id_package_identifiers` | FK RESTRICT | `package_identifier_id→core.package_identifiers.id` |
| `app.asset_components` | `fk_asset_components_product_id_products` | FK RESTRICT | `product_id→core.products.id` |
| `app.asset_components` | `fk_component_package_product` | FK RESTRICT | `package_identifier_id→core.package_identifiers.id, product_id→core.package_identifiers.product_id` |
| `app.asset_components` | `uq_asset_components_id_package_identifier_id` | UNIQUE | `id, package_identifier_id` |
| `evaluation.results` | `ck_results_score_latency` | CHECK | `latency_ms>=0 AND (rubric_score IS NULL OR rubric_score BETWEEN 0 AND 2)` |
| `evaluation.results` | `ck_results_status_values` | CHECK | `status IN ('succeeded','partial','failed','timeout','abstained','unknown')` |
| `evaluation.results` | `fk_result_case_dataset` | FK RESTRICT | `case_id→evaluation.cases.id, dataset_id→evaluation.cases.dataset_id` |
| `evaluation.results` | `fk_result_run_dataset` | FK RESTRICT | `run_id→evaluation.runs.id, dataset_id→evaluation.runs.dataset_id` |
| `evaluation.results` | `fk_results_case_id_cases` | FK RESTRICT | `case_id→evaluation.cases.id` |
| `evaluation.results` | `fk_results_dataset_id_datasets` | FK RESTRICT | `dataset_id→evaluation.datasets.id` |
| `evaluation.results` | `fk_results_run_id_runs` | FK RESTRICT | `run_id→evaluation.runs.id` |
| `evaluation.results` | `uq_results_run_id_case_id` | UNIQUE | `run_id, case_id` |
| `intel.epss_snapshots` | `ck_epss_snapshots_probability_bounds` | CHECK | `score BETWEEN 0 AND 1 AND (percentile IS NULL OR percentile BETWEEN 0 AND 1)` |
| `intel.epss_snapshots` | `fk_epss_snapshots_raw_document_id_raw_documents` | FK RESTRICT | `raw_document_id→raw.raw_documents.id` |
| `intel.epss_snapshots` | `fk_epss_snapshots_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `intel.epss_snapshots` | `fk_epss_snapshots_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `intel.epss_snapshots` | `uq_epss_snapshots_vulnerability_id_source_id_score_date_model_version_raw_document_id` | UNIQUE | `vulnerability_id, source_id, score_date, model_version, raw_document_id` |
| `intel.knowledge_documents` | `ck_knowledge_documents_document_type_values` | CHECK | `document_type IN ('advisory','blog','paper','analysis','ai_event','standard','policy','knowledge')` |
| `intel.knowledge_documents` | `fk_knowledge_documents_raw_document_id_raw_documents` | FK RESTRICT | `raw_document_id→raw.raw_documents.id` |
| `intel.knowledge_documents` | `fk_knowledge_documents_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `intel.knowledge_documents` | `uq_knowledge_documents_source_id_external_id_edition` | UNIQUE | `source_id, external_id, edition` |
| `intel.known_exploitation` | `ck_known_exploitation_absence_requires_complete` | CHECK | `catalog_status<>'not_listed_as_of' OR catalog_complete IS TRUE` |
| `intel.known_exploitation` | `ck_known_exploitation_catalog_status_values` | CHECK | `catalog_status IN ('listed','not_listed_as_of','unknown')` |
| `intel.known_exploitation` | `ck_known_exploitation_no_false_negative` | CHECK | `(catalog_status='listed' AND known_exploited IS TRUE) OR (catalog_status<>'listed' AND known_exploited IS NULL)` |
| `intel.known_exploitation` | `fk_known_exploitation_raw_document_id_raw_documents` | FK RESTRICT | `raw_document_id→raw.raw_documents.id` |
| `intel.known_exploitation` | `fk_known_exploitation_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `intel.known_exploitation` | `fk_known_exploitation_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `intel.known_exploitation` | `uq_known_exploitation_vulnerability_id_source_id_raw_document_id` | UNIQUE | `vulnerability_id, source_id, raw_document_id` |
| `raw.source_observations` | `ck_source_observations_304_requires_cached_body` | CHECK | `http_status IS NULL OR http_status<>304 OR raw_document_id IS NOT NULL` |
| `raw.source_observations` | `ck_source_observations_parse_status_values` | CHECK | `parse_status IN ('pending','parsed','unsupported','failed')` |
| `raw.source_observations` | `fk_observation_raw_source` | FK RESTRICT | `raw_document_id→raw.raw_documents.id, source_id→raw.raw_documents.source_id` |
| `raw.source_observations` | `fk_observation_run_source` | FK RESTRICT | `sync_run_id→raw.sync_runs.id, source_id→raw.sync_runs.source_id` |
| `raw.source_observations` | `fk_source_observations_raw_document_id_raw_documents` | FK RESTRICT | `raw_document_id→raw.raw_documents.id` |
| `raw.source_observations` | `fk_source_observations_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `raw.source_observations` | `fk_source_observations_sync_run_id_sync_runs` | FK RESTRICT | `sync_run_id→raw.sync_runs.id` |
| `raw.source_observations` | `fk_source_observations_upstream_observation_id_source_observations` | FK RESTRICT | `upstream_observation_id→raw.source_observations.id` |
| `raw.source_observations` | `uq_source_observations_id_raw_document_id_source_id` | UNIQUE | `id, raw_document_id, source_id` |
| `core.affected_version_ranges` | `ck_affected_version_ranges_parse_status_values` | CHECK | `parse_status IN ('parsed','unsupported','failed')` |
| `core.affected_version_ranges` | `ck_affected_version_ranges_parsed_has_machine_value` | CHECK | `parse_status <> 'parsed' OR events IS NOT NULL OR explicit_versions IS NOT NULL OR introduced IS NOT NULL OR fixed IS NOT NULL OR last_affected IS NOT NULL OR limit_version IS NOT NULL` |
| `core.affected_version_ranges` | `ck_affected_version_ranges_raw_expression_present` | CHECK | `length(raw_expression)>0` |
| `core.affected_version_ranges` | `ck_affected_version_ranges_verification_status_values` | CHECK | `verification_status IN ('pending','confirmed','insufficient','conflict')` |
| `core.affected_version_ranges` | `fk_affected_version_ranges_observation_id_source_observations` | FK RESTRICT | `observation_id→raw.source_observations.id` |
| `core.affected_version_ranges` | `fk_affected_version_ranges_package_identifier_id_package_identifiers` | FK RESTRICT | `package_identifier_id→core.package_identifiers.id` |
| `core.affected_version_ranges` | `fk_affected_version_ranges_product_id_products` | FK RESTRICT | `product_id→core.products.id` |
| `core.affected_version_ranges` | `fk_affected_version_ranges_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `core.affected_version_ranges` | `fk_affected_version_ranges_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `core.affected_version_ranges` | `fk_range_package_product` | FK RESTRICT | `package_identifier_id→core.package_identifiers.id, product_id→core.package_identifiers.product_id` |
| `core.affected_version_ranges` | `uq_affected_version_ranges_id_vulnerability_id_package_identifier_id` | UNIQUE | `id, vulnerability_id, package_identifier_id` |
| `core.ai_relevance_assessments` | `ck_ai_relevance_assessments_method_values` | CHECK | `method IN ('rule','product','package','llm','human')` |
| `core.ai_relevance_assessments` | `ck_ai_relevance_assessments_one_subject` | CHECK | `num_nonnulls(vulnerability_id,knowledge_document_id)=1` |
| `core.ai_relevance_assessments` | `ck_ai_relevance_assessments_result_values` | CHECK | `result IN ('relevant','irrelevant','uncertain')` |
| `core.ai_relevance_assessments` | `fk_ai_relevance_assessments_knowledge_document_id_knowledge_documents` | FK RESTRICT | `knowledge_document_id→intel.knowledge_documents.id` |
| `core.ai_relevance_assessments` | `fk_ai_relevance_assessments_observation_id_source_observations` | FK RESTRICT | `observation_id→raw.source_observations.id` |
| `core.ai_relevance_assessments` | `fk_ai_relevance_assessments_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `core.cvss_assessments` | `ck_cvss_assessments_score_bounds` | CHECK | `base_score BETWEEN 0 AND 10` |
| `core.cvss_assessments` | `ck_cvss_assessments_severity_values` | CHECK | `severity IN ('critical','high','medium','low','info','unknown')` |
| `core.cvss_assessments` | `ck_cvss_assessments_version_values` | CHECK | `version IN ('2.0','3.0','3.1','4.0')` |
| `core.cvss_assessments` | `fk_cvss_assessments_observation_id_source_observations` | FK RESTRICT | `observation_id→raw.source_observations.id` |
| `core.cvss_assessments` | `fk_cvss_assessments_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `core.cvss_assessments` | `fk_cvss_assessments_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `core.cvss_assessments` | `uq_cvss_assessments_id_vulnerability_id` | UNIQUE | `id, vulnerability_id` |
| `core.vulnerability_identifiers` | `fk_vi_identifier_type` | FK RESTRICT | `identifier_id→core.external_identifiers.id, identifier_type→core.external_identifiers.identifier_type` |
| `core.vulnerability_identifiers` | `fk_vulnerability_identifiers_identifier_id_external_identifiers` | FK RESTRICT | `identifier_id→core.external_identifiers.id` |
| `core.vulnerability_identifiers` | `fk_vulnerability_identifiers_observation_id_source_observations` | FK RESTRICT | `observation_id→raw.source_observations.id` |
| `core.vulnerability_identifiers` | `fk_vulnerability_identifiers_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `core.vulnerability_identifiers` | `uq_vulnerability_identifiers_vulnerability_id_identifier_id` | UNIQUE | `vulnerability_id, identifier_id` |
| `core.vulnerability_references` | `fk_vulnerability_references_observation_id_source_observations` | FK RESTRICT | `observation_id→raw.source_observations.id` |
| `core.vulnerability_references` | `fk_vulnerability_references_reference_id_references` | FK RESTRICT | `reference_id→core.references.id` |
| `core.vulnerability_references` | `fk_vulnerability_references_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `core.vulnerability_references` | `uq_vulnerability_references_vulnerability_id_reference_id_observation_id` | UNIQUE | `vulnerability_id, reference_id, observation_id` |
| `core.vulnerability_weaknesses` | `fk_vulnerability_weaknesses_observation_id_source_observations` | FK RESTRICT | `observation_id→raw.source_observations.id` |
| `core.vulnerability_weaknesses` | `fk_vulnerability_weaknesses_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `core.vulnerability_weaknesses` | `fk_vulnerability_weaknesses_weakness_id_weaknesses` | FK RESTRICT | `weakness_id→core.weaknesses.id` |
| `core.vulnerability_weaknesses` | `uq_vulnerability_weaknesses_vulnerability_id_weakness_id_observation_id` | UNIQUE | `vulnerability_id, weakness_id, observation_id` |
| `intel.knowledge_chunks` | `ck_knowledge_chunks_position` | CHECK | `chunk_index>=0 AND document_revision>0` |
| `intel.knowledge_chunks` | `fk_knowledge_chunks_document_id_knowledge_documents` | FK RESTRICT | `document_id→intel.knowledge_documents.id` |
| `intel.knowledge_chunks` | `fk_knowledge_chunks_raw_document_id_raw_documents` | FK RESTRICT | `raw_document_id→raw.raw_documents.id` |
| `intel.knowledge_chunks` | `uq_knowledge_chunks_document_id_document_revision_chunker_version_chunk_index` | UNIQUE | `document_id, document_revision, chunker_version, chunk_index` |
| `intel.patch_candidates` | `ck_patch_candidates_commit_has_sha` | CHECK | `patch_type <> 'commit' OR commit_sha IS NOT NULL` |
| `intel.patch_candidates` | `ck_patch_candidates_fixed_has_version` | CHECK | `patch_type <> 'fixed_version' OR release_version IS NOT NULL` |
| `intel.patch_candidates` | `ck_patch_candidates_full_commit` | CHECK | `commit_sha IS NULL OR commit_sha ~ '^([0-9a-f]{40}|[0-9a-f]{64})$'` |
| `intel.patch_candidates` | `ck_patch_candidates_patch_type_values` | CHECK | `patch_type IN ('commit','pull_request','release','vendor_patch','fixed_version')` |
| `intel.patch_candidates` | `ck_patch_candidates_status_values` | CHECK | `status IN ('candidate','confirmed','rejected','unknown')` |
| `intel.patch_candidates` | `fk_patch_candidates_observation_id_source_observations` | FK RESTRICT | `observation_id→raw.source_observations.id` |
| `intel.patch_candidates` | `fk_patch_candidates_product_id_products` | FK RESTRICT | `product_id→core.products.id` |
| `intel.patch_candidates` | `fk_patch_candidates_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `intel.patch_candidates` | `fk_patch_candidates_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `intel.patch_candidates` | `uq_patch_candidates_id_vulnerability_id` | UNIQUE | `id, vulnerability_id` |
| `intel.patch_candidates` | `uq_patch_candidates_vulnerability_id_product_id_branch_patch_type_identity_key` | UNIQUE | `vulnerability_id, product_id, branch, patch_type, identity_key` |
| `intel.poc_candidates` | `ck_poc_candidates_status_values` | CHECK | `status IN ('candidate','confirmed','rejected','unknown')` |
| `intel.poc_candidates` | `ck_poc_candidates_usability_status_values` | CHECK | `usability_status IN ('not_evaluated','unknown','verified_usable','unusable')` |
| `intel.poc_candidates` | `fk_poc_candidates_observation_id_source_observations` | FK RESTRICT | `observation_id→raw.source_observations.id` |
| `intel.poc_candidates` | `fk_poc_candidates_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `intel.poc_candidates` | `fk_poc_candidates_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `intel.poc_candidates` | `uq_poc_candidates_id_vulnerability_id` | UNIQUE | `id, vulnerability_id` |
| `intel.poc_candidates` | `uq_poc_candidates_vulnerability_id_canonical_url` | UNIQUE | `vulnerability_id, canonical_url` |
| `core.vulnerability_ai_categories` | `fk_vulnerability_ai_categories_assessment_id_ai_relevance_assessments` | FK RESTRICT | `assessment_id→core.ai_relevance_assessments.id` |
| `core.vulnerability_ai_categories` | `fk_vulnerability_ai_categories_category_id_ai_security_categories` | FK RESTRICT | `category_id→core.ai_security_categories.id` |
| `core.vulnerability_ai_categories` | `fk_vulnerability_ai_categories_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `core.vulnerability_ai_categories` | `uq_vulnerability_ai_categories_vulnerability_id_category_id_assessment_id` | UNIQUE | `vulnerability_id, category_id, assessment_id` |
| `intel.claims` | `ck_claims_one_root` | CHECK | `num_nonnulls(vulnerability_id,knowledge_document_id)=1` |
| `intel.claims` | `ck_claims_one_subject` | CHECK | `num_nonnulls(product_id,package_identifier_id,range_id,poc_candidate_id,patch_candidate_id,asset_component_id,cvss_assessment_id)<=1` |
| `intel.claims` | `ck_claims_revision_positive` | CHECK | `revision>0` |
| `intel.claims` | `ck_claims_verification_status_values` | CHECK | `verification_status IN ('pending','confirmed','insufficient','conflict')` |
| `intel.claims` | `fk_claim_cvss_root` | FK RESTRICT | `cvss_assessment_id→core.cvss_assessments.id, vulnerability_id→core.cvss_assessments.vulnerability_id` |
| `intel.claims` | `fk_claim_patch_root` | FK RESTRICT | `patch_candidate_id→intel.patch_candidates.id, vulnerability_id→intel.patch_candidates.vulnerability_id` |
| `intel.claims` | `fk_claim_poc_root` | FK RESTRICT | `poc_candidate_id→intel.poc_candidates.id, vulnerability_id→intel.poc_candidates.vulnerability_id` |
| `intel.claims` | `fk_claims_asset_component_id_asset_components` | FK RESTRICT | `asset_component_id→app.asset_components.id` |
| `intel.claims` | `fk_claims_cvss_assessment_id_cvss_assessments` | FK RESTRICT | `cvss_assessment_id→core.cvss_assessments.id` |
| `intel.claims` | `fk_claims_knowledge_document_id_knowledge_documents` | FK RESTRICT | `knowledge_document_id→intel.knowledge_documents.id` |
| `intel.claims` | `fk_claims_package_identifier_id_package_identifiers` | FK RESTRICT | `package_identifier_id→core.package_identifiers.id` |
| `intel.claims` | `fk_claims_patch_candidate_id_patch_candidates` | FK RESTRICT | `patch_candidate_id→intel.patch_candidates.id` |
| `intel.claims` | `fk_claims_poc_candidate_id_poc_candidates` | FK RESTRICT | `poc_candidate_id→intel.poc_candidates.id` |
| `intel.claims` | `fk_claims_product_id_products` | FK RESTRICT | `product_id→core.products.id` |
| `intel.claims` | `fk_claims_range_id_affected_version_ranges` | FK RESTRICT | `range_id→core.affected_version_ranges.id` |
| `intel.claims` | `fk_claims_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `intel.claims` | `uq_claims_claim_key` | UNIQUE | `claim_key` |
| `intel.claims` | `uq_claims_id_scope_key` | UNIQUE | `id, scope_key` |
| `intel.claims` | `uq_claims_id_vulnerability_id` | UNIQUE | `id, vulnerability_id` |
| `app.asset_vulnerability_matches` | `ck_asset_vulnerability_matches_certain_has_range` | CHECK | `match_status='unknown' OR matched_range_id IS NOT NULL` |
| `app.asset_vulnerability_matches` | `ck_asset_vulnerability_matches_match_status_values` | CHECK | `match_status IN ('affected','not_affected','unknown')` |
| `app.asset_vulnerability_matches` | `ck_asset_vulnerability_matches_positive_revisions` | CHECK | `component_revision>0 AND claim_revision>0` |
| `app.asset_vulnerability_matches` | `fk_asset_vulnerability_matches_asset_component_id_asset_components` | FK RESTRICT | `asset_component_id→app.asset_components.id` |
| `app.asset_vulnerability_matches` | `fk_asset_vulnerability_matches_claim_id_claims` | FK RESTRICT | `claim_id→intel.claims.id` |
| `app.asset_vulnerability_matches` | `fk_asset_vulnerability_matches_matched_range_id_affected_version_ranges` | FK RESTRICT | `matched_range_id→core.affected_version_ranges.id` |
| `app.asset_vulnerability_matches` | `fk_asset_vulnerability_matches_package_identifier_id_package_identifiers` | FK RESTRICT | `package_identifier_id→core.package_identifiers.id` |
| `app.asset_vulnerability_matches` | `fk_asset_vulnerability_matches_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `app.asset_vulnerability_matches` | `fk_match_component_package` | FK RESTRICT | `asset_component_id→app.asset_components.id, package_identifier_id→app.asset_components.package_identifier_id` |
| `app.asset_vulnerability_matches` | `fk_match_range_scope` | FK RESTRICT | `matched_range_id→core.affected_version_ranges.id, vulnerability_id→core.affected_version_ranges.vulnerability_id, package_identifier_id→core.affected_version_ranges.package_identifier_id` |
| `app.asset_vulnerability_matches` | `uq_asset_vulnerability_matches_asset_component_id_vulnerability_id_component_revision_claim_revision_matcher_version` | UNIQUE | `asset_component_id, vulnerability_id, component_revision, claim_revision, matcher_version` |
| `app.review_tasks` | `ck_review_tasks_revision_priority` | CHECK | `revision>0 AND priority BETWEEN 0 AND 4` |
| `app.review_tasks` | `ck_review_tasks_status_values` | CHECK | `status IN ('open','assigned','resolved','deferred','cancelled')` |
| `app.review_tasks` | `fk_review_tasks_claim_id_claims` | FK RESTRICT | `claim_id→intel.claims.id` |
| `intel.evidence` | `ck_evidence_stance_values` | CHECK | `stance IN ('support','contradict','neutral')` |
| `intel.evidence` | `fk_evidence_claim_id_claims` | FK RESTRICT | `claim_id→intel.claims.id` |
| `intel.evidence` | `fk_evidence_claim_scope` | FK RESTRICT | `claim_id→intel.claims.id, scope_key→intel.claims.scope_key` |
| `intel.evidence` | `fk_evidence_observation_id_source_observations` | FK RESTRICT | `observation_id→raw.source_observations.id` |
| `intel.evidence` | `fk_evidence_observation_raw` | FK RESTRICT | `observation_id→raw.source_observations.id, raw_document_id→raw.source_observations.raw_document_id, source_id→raw.source_observations.source_id` |
| `intel.evidence` | `fk_evidence_raw_document_id_raw_documents` | FK RESTRICT | `raw_document_id→raw.raw_documents.id` |
| `intel.evidence` | `fk_evidence_raw_source` | FK RESTRICT | `raw_document_id→raw.raw_documents.id, source_id→raw.raw_documents.source_id` |
| `intel.evidence` | `fk_evidence_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `intel.evidence` | `uq_evidence_claim_id_observation_id_locator_key_stance` | UNIQUE | `claim_id, observation_id, locator_key, stance` |
| `intel.evidence` | `uq_evidence_id_claim_id` | UNIQUE | `id, claim_id` |
| `intel.knowledge_vulnerability_relations` | `fk_knowledge_vulnerability_relations_claim_id_claims` | FK RESTRICT | `claim_id→intel.claims.id` |
| `intel.knowledge_vulnerability_relations` | `fk_knowledge_vulnerability_relations_knowledge_document_id_knowledge_documents` | FK RESTRICT | `knowledge_document_id→intel.knowledge_documents.id` |
| `intel.knowledge_vulnerability_relations` | `fk_knowledge_vulnerability_relations_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `intel.knowledge_vulnerability_relations` | `uq_knowledge_vulnerability_relations_knowledge_document_id_vulnerability_id_relation_type_claim_id` | UNIQUE | `knowledge_document_id, vulnerability_id, relation_type, claim_id` |
| `intel.verification_results` | `ck_verification_results_positive_revision` | CHECK | `claim_revision>0` |
| `intel.verification_results` | `ck_verification_results_status_values` | CHECK | `status IN ('pending','confirmed','insufficient','conflict')` |
| `intel.verification_results` | `ck_verification_results_verified_by_type_values` | CHECK | `verified_by_type IN ('system','human')` |
| `intel.verification_results` | `fk_verification_results_claim_id_claims` | FK RESTRICT | `claim_id→intel.claims.id` |
| `intel.verification_results` | `uq_verification_results_claim_id_claim_revision` | UNIQUE | `claim_id, claim_revision` |
| `intel.verification_results` | `uq_verification_results_claim_id_claim_revision_decision_key` | UNIQUE | `claim_id, claim_revision, decision_key` |
| `intel.verification_results` | `uq_verification_results_id_claim_id` | UNIQUE | `id, claim_id` |
| `app.agent_citations` | `ck_agent_citations_positive_position` | CHECK | `citation_index>0 AND claim_revision>0` |
| `app.agent_citations` | `fk_agent_citations_agent_run_id_agent_runs` | FK RESTRICT | `agent_run_id→app.agent_runs.id` |
| `app.agent_citations` | `fk_agent_citations_claim_id_claims` | FK RESTRICT | `claim_id→intel.claims.id` |
| `app.agent_citations` | `fk_agent_citations_evidence_id_evidence` | FK RESTRICT | `evidence_id→intel.evidence.id` |
| `app.agent_citations` | `fk_citation_claim_revision` | FK RESTRICT | `claim_id→intel.verification_results.claim_id, claim_revision→intel.verification_results.claim_revision` |
| `app.agent_citations` | `fk_citation_evidence_claim` | FK RESTRICT | `evidence_id→intel.evidence.id, claim_id→intel.evidence.claim_id` |
| `app.agent_citations` | `uq_agent_citations_agent_run_id_citation_index` | UNIQUE | `agent_run_id, citation_index` |
| `app.audit_logs` | `fk_audit_logs_claim_id_claims` | FK RESTRICT | `claim_id→intel.claims.id` |
| `app.audit_logs` | `fk_audit_logs_review_task_id_review_tasks` | FK RESTRICT | `review_task_id→app.review_tasks.id` |
| `app.audit_logs` | `fk_audit_logs_verification_result_id_verification_results` | FK RESTRICT | `verification_result_id→intel.verification_results.id` |
| `app.audit_logs` | `uq_audit_logs_actor_request_key` | UNIQUE | `actor, request_key` |
| `intel.intelligence_events` | `ck_intelligence_events_one_root` | CHECK | `num_nonnulls(vulnerability_id,knowledge_document_id)=1` |
| `intel.intelligence_events` | `fk_intelligence_events_claim_id_claims` | FK RESTRICT | `claim_id→intel.claims.id` |
| `intel.intelligence_events` | `fk_intelligence_events_evidence_id_evidence` | FK RESTRICT | `evidence_id→intel.evidence.id` |
| `intel.intelligence_events` | `fk_intelligence_events_knowledge_document_id_knowledge_documents` | FK RESTRICT | `knowledge_document_id→intel.knowledge_documents.id` |
| `intel.intelligence_events` | `fk_intelligence_events_source_id_sources` | FK RESTRICT | `source_id→raw.sources.id` |
| `intel.intelligence_events` | `fk_intelligence_events_vulnerability_id_vulnerabilities` | FK RESTRICT | `vulnerability_id→core.vulnerabilities.id` |
| `intel.intelligence_events` | `uq_intelligence_events_event_key` | UNIQUE | `event_key` |
| `intel.verification_evidence` | `fk_ve_evidence_claim` | FK RESTRICT | `evidence_id→intel.evidence.id, claim_id→intel.evidence.claim_id` |
| `intel.verification_evidence` | `fk_ve_result_claim` | FK RESTRICT | `verification_result_id→intel.verification_results.id, claim_id→intel.verification_results.claim_id` |
| `intel.verification_evidence` | `fk_verification_evidence_claim_id_claims` | FK RESTRICT | `claim_id→intel.claims.id` |
| `intel.verification_evidence` | `fk_verification_evidence_evidence_id_evidence` | FK RESTRICT | `evidence_id→intel.evidence.id` |
| `intel.verification_evidence` | `fk_verification_evidence_verification_result_id_verification_results` | FK RESTRICT | `verification_result_id→intel.verification_results.id` |
| `intel.verification_evidence` | `uq_verification_evidence_verification_result_id_evidence_id` | UNIQUE | `verification_result_id, evidence_id` |

仅(source_id,external_id)不能约束RawDocument唯一，否则新内容必须覆盖旧Evidence；这里唯一到内容hash，源稳定记录身份由source+external分组。需要logical header时以后追加独立头表，不提前建立无用层。ProductAlias不全局唯一：相同字符串可以属于不同产品/namespace，解析必须先取已核验且唯一的包/别名候选。

原文/证据/核验等22个历史表装不可UPDATE/DELETE触发器，列表见RETENTION_POLICY。CVE唯一所有者用partial unique index，公告不限制一对一。采用Claim按root/predicate/scope部分唯一，CVSS采用有typed assessment FK。CHECK不能跨表证明原文是否真正支持命题；此部分明确留给第6阶段核验与授权服务。[PostgreSQL约束说明](https://www.postgresql.org/docs/17/ddl-constraints.html)。

// Generated in memory from current Python JSON Schema. INTERNAL schemas are not HTTP API contracts.
// UUID/date/date-time are strings on the wire; JSON Schema numeric bounds and cross-field validators still apply.
// Schemaless dictionaries map to unknown. Do not treat static TypeScript types as runtime validation.
export type HttpSourceRow = {
  "source_key": string;
  "name": string;
  "source_type": string;
  "category": string;
  "authority_level": "official" | "authoritative" | "secondary" | "community";
  "authority_scope": string;
  "acquisition_method": string;
  "base_url": string;
  "enabled": boolean;
  "update_interval": number;
  "last_sync_at": (string | null);
  "last_success_at": (string | null);
  "status": "planned" | "deferred" | "running" | "succeeded" | "partial" | "failed" | "rate_limited" | "stale" | "need_review";
  "license_scope": string;
  "checkpoint": (JsonValue | null);
  "coverage_scope": (JsonValue | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpSyncRunRow = {
  /** format=uuid */
  "source_id": string;
  /** format=date-time */
  "started_at": string;
  "finished_at": (string | null);
  "status": "queued" | "running" | "succeeded" | "partial" | "failed" | "rate_limited" | "cancelled" | "need_review";
  "records_fetched": number;
  "records_created": number;
  "records_updated": number;
  "records_skipped": number;
  "records_failed": number;
  "cursor_before": (JsonValue | null);
  "cursor_after": (JsonValue | null);
  "mode": string;
  "coverage_scope": (JsonValue | null);
  "known_gaps": (JsonValue | null);
  "error_summary": (string | null);
  "retry_of_id": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpVulnerabilityRow = {
  "canonical_id": string;
  "title": string;
  "description": (string | null);
  "published_at": (string | null);
  "modified_at": (string | null);
  "status": "published" | "withdrawn" | "rejected" | "unknown";
  "primary_severity": "critical" | "high" | "medium" | "low" | "info" | "unknown";
  "revision": number;
  "deleted_at": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpExternalIdentifierRow = {
  "namespace": string;
  "identifier_type": string;
  "identifier_value": string;
  "normalized_value": string;
  /** format=uuid */
  "source_id": string;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpRawDocumentRow = {
  /** format=uuid */
  "source_id": string;
  "external_id": string;
  "source_url": string;
  "published_at": (string | null);
  "modified_at": (string | null);
  /** format=date-time */
  "retrieved_at": string;
  "content_type": string;
  "content_hash": string;
  "completeness": string;
  "publisher": string;
  "license_scope": string;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpAffectedVersionRangeRow = {
  /** format=uuid */
  "vulnerability_id": string;
  /** format=uuid */
  "product_id": string;
  /** format=uuid */
  "package_identifier_id": string;
  /** format=uuid */
  "source_id": string;
  /** format=uuid */
  "observation_id": string;
  "introduced": (string | null);
  "fixed": (string | null);
  "last_affected": (string | null);
  "limit_version": (string | null);
  "range_type": string;
  "raw_expression": string;
  "events": (JsonValue | null);
  "explicit_versions": (JsonValue | null);
  "branch": (string | null);
  "scope_key": string;
  "parse_status": "parsed" | "unsupported" | "failed";
  "parse_reason": (string | null);
  "parser_version": string;
  "verification_status": "pending" | "confirmed" | "insufficient" | "conflict" | "rejected";
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpCvssAssessmentRow = {
  /** format=uuid */
  "vulnerability_id": string;
  /** format=uuid */
  "source_id": string;
  /** format=uuid */
  "observation_id": string;
  "version": "2.0" | "3.0" | "3.1" | "4.0";
  "vector": (string | null);
  "base_score": number;
  "severity": "critical" | "high" | "medium" | "low" | "info" | "unknown";
  "provider": string;
  "assessment_kind": string;
  "scope_key": string;
  "published_at": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpProductRow = {
  "canonical_key": string;
  "canonical_name": string;
  "vendor": (string | null);
  "product_type": string;
  "homepage": (string | null);
  "deleted_at": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpWeaknessRow = {
  "cwe_id": string;
  "name": string;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpReferenceRow = {
  "url": string;
  "canonical_url": string;
  "title": (string | null);
  "reference_type": string;
  /** format=uuid */
  "source_id": string;
  "published_at": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpAiRelevanceAssessmentRow = {
  "vulnerability_id": (string | null);
  "knowledge_document_id": (string | null);
  "method": "rule" | "product" | "package" | "llm" | "human";
  "result": "relevant" | "irrelevant" | "uncertain";
  "reason_summary": string;
  "model_version": (string | null);
  /** format=date-time */
  "evaluated_at": string;
  "observation_id": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpEnrichmentJobRow = {
  /** format=uuid */
  "vulnerability_id": string;
  "enrichment_type": string;
  "status": "queued" | "running" | "success" | "partial" | "no_result" | "failed" | "conflict" | "cancelled";
  /** format=date-time */
  "scheduled_at": string;
  "started_at": (string | null);
  "finished_at": (string | null);
  "attempt": number;
  "error_code": (string | null);
  "retryable": boolean;
  "trace_id": string;
  "duration_ms": (number | null);
  "result": (JsonValue | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpClaimRow = {
  "claim_key": string;
  "vulnerability_id": (string | null);
  "knowledge_document_id": (string | null);
  "product_id": (string | null);
  "package_identifier_id": (string | null);
  "range_id": (string | null);
  "poc_candidate_id": (string | null);
  "patch_candidate_id": (string | null);
  "asset_component_id": (string | null);
  "cvss_assessment_id": (string | null);
  "claim_type": string;
  "predicate": string;
  "value_json": JsonValue;
  "scope_key": string;
  "branch": (string | null);
  "cvss_version": (string | null);
  "assessment_kind": (string | null);
  "as_of_date": (string | null);
  "verification_status": "CONFIRMED" | "PENDING" | "INSUFFICIENT_EVIDENCE" | "CONFLICT" | "REJECTED";
  "adopted": boolean;
  "revision": number;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpEvidenceRow = {
  /** format=uuid */
  "claim_id": string;
  /** format=uuid */
  "source_id": string;
  /** format=uuid */
  "raw_document_id": string;
  /** format=uuid */
  "observation_id": string;
  "scope_key": string;
  "evidence_type": string;
  "stance": "support" | "contradict" | "neutral";
  "excerpt": string;
  "excerpt_hash": string;
  "source_url": string;
  "published_at": (string | null);
  /** format=date-time */
  "retrieved_at": string;
  "locator": JsonValue;
  "locator_key": string;
  "observed_value": (JsonValue | null);
  "publisher": string;
  "lineage_key": string;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
  "claim_verification_status"?: "CONFIRMED" | "PENDING" | "INSUFFICIENT_EVIDENCE" | "CONFLICT" | "REJECTED";
  "source_key"?: string;
};

export type HttpPocCandidateRow = {
  /** format=uuid */
  "vulnerability_id": string;
  /** format=uuid */
  "source_id": string;
  /** format=uuid */
  "observation_id": string;
  "url": string;
  "canonical_url": string;
  "repository": (string | null);
  "commit": (string | null);
  "author": (string | null);
  "candidate_type": string;
  "status": "candidate" | "confirmed" | "rejected" | "unknown";
  "usability_status": "not_evaluated" | "unknown" | "verified_usable" | "unusable";
  /** format=date-time */
  "first_seen_at": string;
  /** format=date-time */
  "last_seen_at": string;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpPatchCandidateRow = {
  /** format=uuid */
  "vulnerability_id": string;
  /** format=uuid */
  "product_id": string;
  /** format=uuid */
  "source_id": string;
  /** format=uuid */
  "observation_id": string;
  "patch_type": "commit" | "pull_request" | "release" | "vendor_patch" | "fixed_version";
  "identity_key": string;
  "url": (string | null);
  "commit_sha": (string | null);
  "release_version": (string | null);
  "branch": string;
  "status": "candidate" | "confirmed" | "rejected" | "unknown";
  /** format=date-time */
  "first_seen_at": string;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpIntelligenceEventRow = {
  "event_key": string;
  "vulnerability_id": (string | null);
  "knowledge_document_id": (string | null);
  "claim_id": (string | null);
  "evidence_id": (string | null);
  "source_id": (string | null);
  "event_type": string;
  "occurred_at": (string | null);
  /** format=date-time */
  "detected_at": string;
  "summary": string;
  "payload": (JsonValue | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpEpssSnapshotRow = {
  /** format=uuid */
  "vulnerability_id": string;
  /** format=uuid */
  "source_id": string;
  /** format=uuid */
  "raw_document_id": string;
  "score": number;
  "percentile": (number | null);
  /** format=date */
  "score_date": string;
  /** format=date-time */
  "observed_at": string;
  "model_version": string;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpKnownExploitationRow = {
  /** format=uuid */
  "vulnerability_id": string;
  /** format=uuid */
  "source_id": string;
  /** format=uuid */
  "raw_document_id": string;
  "known_exploited": (boolean | null);
  "catalog_status": "listed" | "not_listed_as_of" | "unknown";
  "catalog_complete": boolean;
  "catalog_version": string;
  /** format=date-time */
  "observed_at": string;
  "date_added": (string | null);
  "due_date": (string | null);
  "required_action": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpConflictRecordRow = {
  "conflict_key": string;
  /** format=uuid */
  "vulnerability_id": string;
  /** format=uuid */
  "claim_a_id": string;
  /** format=uuid */
  "claim_b_id": string;
  "scope_key": string;
  "conflict_type": string;
  /** format=date-time */
  "detected_at": string;
  "status": "open" | "resolved" | "deferred";
  "review_task_id": (string | null);
  "resolution": (JsonValue | null);
  "resolved_at": (string | null);
  "resolved_by": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpVerificationResultRow = {
  /** format=uuid */
  "claim_id": string;
  "claim_revision": number;
  "status": "CONFIRMED" | "PENDING" | "INSUFFICIENT_EVIDENCE" | "CONFLICT" | "REJECTED";
  "verification_method": string;
  "reason_summary": string;
  /** format=date-time */
  "verified_at": string;
  "verified_by_type": "system" | "human";
  "verified_by_id": string;
  "decision_key": string;
  "adopted_value": (JsonValue | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpReviewTaskRow = {
  /** format=uuid */
  "claim_id": string;
  "review_type": string;
  "priority": number;
  "status": "open" | "assigned" | "resolved" | "deferred" | "cancelled";
  "reason": string;
  "assigned_to": (string | null);
  "resolved_at": (string | null);
  "resolution": (string | null);
  "resolution_note": (string | null);
  "before_state": (JsonValue | null);
  "after_state": (JsonValue | null);
  "revision": number;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpAuditLogRow = {
  "actor": string;
  "action": string;
  /** format=uuid */
  "claim_id": string;
  "review_task_id": (string | null);
  "verification_result_id": (string | null);
  "before_state": JsonValue;
  "after_state": JsonValue;
  "reason": string;
  /** format=date-time */
  "occurred_at": string;
  "request_key": string;
  "request_hash": string;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpAssetRow = {
  "name": string;
  "asset_type": string;
  "owner_principal": string;
  "is_demo": boolean;
  "deleted_at": (string | null);
  "environment": "production" | "staging" | "development" | "unknown";
  "exposure": "internet" | "internal" | "development" | "unknown";
  "description": (string | null);
  "request_key": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpAssetComponentRow = {
  /** format=uuid */
  "asset_id": string;
  "product_id": (string | null);
  "package_identifier_id": (string | null);
  "version": (string | null);
  "raw_package_name": (string | null);
  "source": "manual" | "sbom" | "scanner";
  "inventory_revision": number;
  "identity_status": string;
  "deleted_at": (string | null);
  "purl": (string | null);
  "ecosystem": (string | null);
  "namespace": (string | null);
  "normalized_version": (string | null);
  "resolution_method": (string | null);
  "inventory_key": (string | null);
  "first_seen_at": (string | null);
  "last_seen_at": (string | null);
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  /** format=date-time */
  "updated_at": string;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpAssetRiskChangeRow = {
  /** format=uuid */
  "asset_id": string;
  /** format=uuid */
  "component_id": string;
  /** format=uuid */
  "vulnerability_id": string;
  "previous_snapshot_id": (string | null);
  /** format=uuid */
  "snapshot_id": string;
  "event_type": string;
  "event_key": string;
  /** format=date-time */
  "occurred_at": string;
  "before_state": (JsonValue | null);
  "after_state": JsonValue;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type HttpAssetInventoryEventRow = {
  /** format=uuid */
  "asset_id": string;
  "component_id": (string | null);
  "event_type": string;
  "actor": string;
  "request_key": string;
  "request_hash": string;
  /** format=date-time */
  "occurred_at": string;
  "payload": JsonValue;
  /** format=uuid */
  "id": string;
  /** format=date-time */
  "created_at": string;
  "metadata": JsonValue;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type JsonValue = (null | boolean | number | string | Array<JsonValue> | Record<string, JsonValue>);


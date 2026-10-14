/** Generated from actual Pydantic/OpenAPI. ISO datetimes are strings. */
export type AssetRiskPage = {
  "items": Array<Record<string, unknown>>;
  "total": number;
  "offset": number;
  "limit": number;
  "scope"?: string;
};

export type EnrichmentProgress = {
  "kind": string;
  "job_id": string;
  "status": "queued" | "running" | "success" | "partial" | "no_result" | "failed" | "conflict" | "cancelled";
  "error_code"?: (string | null);
  "retryable"?: boolean;
  "finished_at"?: (string | null);
};

export type HTTPValidationError = {
  "detail"?: Array<ValidationError>;
  [key: string]: unknown;
};

export type IntelligencePage = {
  "items": Array<SecurityIntelligenceObject>;
  "total": number;
  "offset": number;
  "limit": number;
};

export type IntelligenceRecord = {
  "id": string;
  "type": string;
  "title": string;
  "canonical_id"?: (string | null);
  "sources": Array<string>;
  "status": "DISCOVERED" | "NORMALIZED" | "ENRICHING" | "VERIFIED" | "AVAILABLE";
  "verification_status": "CONFIRMED" | "PENDING" | "CONFLICT" | "INSUFFICIENT_EVIDENCE";
  "execution_mode"?: "LIVE" | "MOCK" | "UNSPECIFIED";
  "enrichment_progress"?: Array<EnrichmentProgress>;
  "query_available": boolean;
  "verified_claims"?: number;
  "active_claims"?: number;
  "evidence_count"?: number;
  "knowledge_chunks"?: number;
  "stages": Array<"DISCOVERED" | "NORMALIZED" | "ENRICHING" | "VERIFIED" | "AVAILABLE">;
  "observed_at": string;
  "published_at"?: (string | null);
  "warnings"?: Array<string>;
};

export type POCArtifact = {
  "schema_version"?: "poc-artifact-v1";
  "id": string;
  "vulnerability_id": string;
  "source": string;
  "reference": string;
  "title": string;
  "description"?: (string | null);
  "language"?: (string | null);
  "status": "NO_EVIDENCE" | "POC_CANDIDATE" | "VERIFIED_EXPLOIT";
  "created_time": string;
  "verified_time"?: (string | null);
  "evidence_ref": Array<string>;
  "evidence"?: Array<POCEvidence>;
  "verification"?: Array<POCVerification>;
  "association_status": string;
  "usability_status": string;
  "omitted_evidence_count"?: number;
  "excluded_evidence_count"?: number;
  "omitted_verification_count"?: number;
  "exploit_executed"?: false;
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
};

export type POCEvidence = {
  "id": string;
  "type"?: "POC_EVIDENCE";
  "claim_id": string;
  "source": string;
  "reference": string;
  "content": string;
  "raw_document_id": string;
  "observation_id": string;
  "hash": string;
  "retrieved_time": string;
  "is_current": boolean;
  "stance": "support" | "contradict" | "neutral";
  "supports_exploit_validation"?: boolean;
};

export type POCPage = {
  "vulnerability_id": string;
  "canonical_id": string;
  "status": "NO_EVIDENCE" | "POC_CANDIDATE" | "VERIFIED_EXPLOIT";
  "search_status": "NOT_RUN" | "COMPLETED" | "PARTIAL" | "FAILED";
  "items": Array<POCArtifact>;
  "total": number;
  "stored_count": number;
  "omitted_count": number;
  "offset": number;
  "limit": number;
  "as_of": string;
  "warnings"?: Array<string>;
  "limitations"?: Array<string>;
};

export type POCVerification = {
  "id": string;
  "claim_id": string;
  "claim_type": string;
  "status": "CONFIRMED" | "PENDING" | "INSUFFICIENT_EVIDENCE" | "CONFLICT" | "REJECTED";
  "current_revision": boolean;
  "verified_time": string;
  "method": string;
  "verified_by_type": "human" | "system";
  "evidence_ref": Array<string>;
  "exploit_validation"?: boolean;
};

export type PipelineRun = {
  "sync_run_id": string;
  "cycle_id": string;
  "last_cycle_id": string;
  "source": string;
  "execution_mode": "LIVE" | "MOCK" | "UNSPECIFIED";
  "status": "RUNNING" | "SUCCESS" | "PARTIAL" | "FAILED" | "CANCELLED";
  "collection_status": string;
  "processed_jobs": number;
  "failed_jobs": number;
  "pending_jobs"?: number;
  "targets": Array<string>;
  "document_ids": Array<string>;
  "started_at": string;
  "updated_at": string;
  "errors"?: Array<string>;
};

export type PipelineRunPage = {
  "items": Array<PipelineRun>;
  "total": number;
  "offset": number;
  "limit": number;
  "scheduler_semantics"?: string;
};

export type RecordPage = {
  "items": Array<IntelligenceRecord>;
  "total": number;
  "offset": number;
  "limit": number;
  "availability_semantics"?: string;
};

export type SecurityIntelligenceObject = {
  "schema_version"?: "security-intelligence-v1";
  "id": string;
  "source": Array<string>;
  "title": string;
  "type": "vulnerability" | "paper" | "blog" | "advisory" | "analysis" | "knowledge";
  "cve_id"?: (string | null);
  "affected_product"?: Array<string>;
  "affected_version"?: Array<Record<string, unknown>>;
  "fixed_versions"?: Array<Record<string, unknown>>;
  "cvss"?: Array<Record<string, unknown>>;
  "cwe"?: Array<string>;
  "published_time"?: (string | null);
  "modified_time"?: (string | null);
  "edition"?: (string | null);
  "is_current"?: (boolean | null);
  "canonical_publication_id"?: (string | null);
  "references"?: Array<SourceReference>;
  "status"?: "SOURCE_ASSERTED" | "CANDIDATE" | "CONFLICT";
  "publication_status"?: string;
  "poc_status"?: "POC_CANDIDATE" | "VERIFIED_EXPLOIT" | "NO_EVIDENCE";
  "poc_search_status"?: "NOT_RUN" | "COMPLETED" | "PARTIAL" | "FAILED";
  "pocs"?: Array<Record<string, unknown>>;
  "patches"?: Array<Record<string, unknown>>;
  "related_documents"?: Array<Record<string, unknown>>;
  "evidence"?: Array<Record<string, unknown>>;
  "asset_risk_access"?: "AUTHENTICATED_ONLY";
  "content_trust_level"?: "UNTRUSTED_EXTERNAL_CONTENT";
  "limitations"?: Array<string>;
};

export type SourceReference = {
  "source": string;
  "raw_document_id": string;
  "hash": string;
  "reference": string;
  "locator"?: Record<string, unknown>;
  "retrieved_at": string;
  "published_at"?: (string | null);
};

export type SourceStatusPage = {
  "items": Array<Record<string, unknown>>;
  "total": number;
  "source_category_count": number;
  "collected_source_category_count"?: number;
  "coverage"?: string;
};

export type ValidationError = {
  "loc": Array<(string | number)>;
  "msg": string;
  "type": string;
  "input"?: unknown;
  "ctx"?: Record<string, unknown>;
  [key: string]: unknown;
};

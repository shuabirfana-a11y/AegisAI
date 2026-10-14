/** Generated from actual Pydantic/OpenAPI. ISO datetimes are strings. */
export type AssetRiskPage = {
  "items": Array<Record<string, unknown>>;
  "total": number;
  "offset": number;
  "limit": number;
  "scope"?: string;
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

// Generated from current Python JSON Schema. INTERNAL schemas are not HTTP API contracts.
// UUID/date/date-time are strings on the wire; JSON Schema numeric bounds and cross-field validators still apply.
// Schemaless dictionaries map to unknown. Do not treat static TypeScript types as runtime validation.
export type AnalysisSnapshotInput = {
  /** format=uuid */
  "context_id": string;
};

export type AssetInput = {
  /** format=uuid */
  "asset_id": string;
};

export type ClaimInput = {
  /** format=uuid */
  "claim_id": string;
};

export type ComponentInput = {
  /** format=uuid */
  "component_id": string;
};

export type EmptyInput = Record<string, unknown>;

export type IdInput = {
  /** format=uuid */
  "id": string;
};

export type RefreshInput = {
  /** maxLength=80, pattern=^(CVE-\d{4}-\d{4,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27})$ */
  "target": string;
  /** minimum=1, maximum=100 */
  "limit"?: number;
  "refresh"?: boolean;
};

export type RemediationInput = {
  /** maxLength=80, pattern=^(CVE-\d{4}-\d{4,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27})$ */
  "target": string;
  /** minimum=1, maximum=100 */
  "limit"?: number;
  /** format=uuid */
  "package_id": string;
};

export type ResolutionInput = {
  /** maxLength=200 */
  "name": string;
  "ecosystem"?: (string | null);
  "package_name"?: (string | null);
  "version"?: (string | null);
  "purl"?: (string | null);
};

export type ReviewInput = {
  /** format=uuid */
  "claim_id": string;
  /** maxLength=500 */
  "reason"?: string;
};

export type RiskInput = {
  /** format=uuid */
  "asset_id": string;
  /** format=uuid */
  "snapshot_id": string;
};

export type RisksInput = {
  "asset_id"?: (string | null);
  /** minimum=1, maximum=100 */
  "limit"?: number;
};

export type SearchInput = {
  "q"?: (string | null);
  "product"?: (string | null);
  "high_severity"?: boolean;
  "ai_relevance"?: ("relevant" | "irrelevant" | "uncertain" | null);
  "days"?: (number | null);
  /** minimum=1, maximum=100 */
  "limit"?: number;
};

export type SemanticInput = {
  /** minLength=1, maxLength=2000 */
  "query": string;
  /** minimum=1, maximum=20 */
  "limit"?: number;
};

export type TargetInput = {
  /** maxLength=80, pattern=^(CVE-\d{4}-\d{4,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27})$ */
  "target": string;
  /** minimum=1, maximum=100 */
  "limit"?: number;
};

export type VerificationSnapshotInput = {
  /** format=uuid */
  "context_id": string;
  /** maxItems=32 */
  "claim_ids"?: Array<string>;
};

export type VersionInspectionInput = {
  /** maxLength=200 */
  "name": string;
  "ecosystem"?: (string | null);
  "package_name"?: (string | null);
  /** minLength=1, maxLength=200 */
  "version": string;
  "purl"?: (string | null);
  /** maxLength=80, pattern=^(CVE-\d{4}-\d{4,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27})$ */
  "target": string;
};


// Generated from current Python JSON Schema. INTERNAL schemas are not HTTP API contracts.
// UUID and date-time are wire strings; Python validation and JSON Schema bounds still apply.
// Schemaless dictionaries map to unknown; static types do not validate external content.

export type AnalysisSnapshotInput = {
  "context_id": string;
};

export type AssetInput = {
  "asset_id": string;
};

export type CandidateTargetInput = {
  "target": string;
  "limit"?: number;
  "candidate_reference"?: (string | null);
};

export type ClaimInput = {
  "claim_id": string;
};

export type ComponentInput = {
  "component_id": string;
};

export type EmptyInput = Record<string, unknown>;

export type EvidenceInput = {
  "target": string;
  "limit"?: number;
  "claim_id"?: (string | null);
  "candidate_reference"?: (string | null);
};

export type IdInput = {
  "id": string;
};

export type RefreshInput = {
  "target": string;
  "limit"?: number;
  "refresh"?: boolean;
};

export type RemediationInput = {
  "target": string;
  "limit"?: number;
  "package_id": string;
};

export type ResolutionInput = {
  "name": string;
  "ecosystem"?: (string | null);
  "package_name"?: (string | null);
  "version"?: (string | null);
  "purl"?: (string | null);
};

export type ReviewInput = {
  "claim_id": string;
  "reason"?: string;
};

export type RiskInput = {
  "asset_id": string;
  "snapshot_id": string;
};

export type RisksInput = {
  "asset_id"?: (string | null);
  "limit"?: number;
};

export type SearchInput = {
  "q"?: (string | null);
  "product"?: (string | null);
  "high_severity"?: boolean;
  "ai_relevance"?: ("relevant" | "irrelevant" | "uncertain" | null);
  "days"?: (number | null);
  "limit"?: number;
};

export type SemanticInput = {
  "query": string;
  "limit"?: number;
};

export type TargetInput = {
  "target": string;
  "limit"?: number;
};

export type VerificationSnapshotInput = {
  "context_id": string;
  "claim_ids"?: Array<string>;
};

export type VersionInspectionInput = {
  "name": string;
  "ecosystem"?: (string | null);
  "package_name"?: (string | null);
  "version": string;
  "purl"?: (string | null);
  "target": string;
};

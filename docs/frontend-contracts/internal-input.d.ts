// Generated from current Python JSON Schema. INTERNAL schemas are not HTTP API contracts.
// UUID and date-time are wire strings; Python validation and JSON Schema bounds still apply.
// Schemaless dictionaries map to unknown; static types do not validate external content.

export type AnalysisRequest = {
  "investigation_run_id": string;
  "investigation_task_id": string;
  "investigation_artifact_id": string;
  "verification_run_id": string;
  "verification_task_id": string;
  "verification_artifact_id": string;
  "asset_id"?: (string | null);
  "component_id"?: (string | null);
  "task_type"?: "risk_analysis" | "asset_impact_analysis" | "remediation_prioritization";
  "request_key": string;
  "model_assistance"?: boolean;
};

export type ArtifactRef = {
  "run_id": string;
  "task_id": string;
  "artifact_id": string;
  "schema_version": "investigation-artifact-v1" | "verification-artifact-v1" | "risk-analysis-artifact-v1";
};

export type IntegrationRequest = {
  "request_key": string;
  "run_id"?: (string | null);
  "planner_run_id"?: (string | null);
  "objective_source"?: "stored_planner_request" | "new_structured_request";
  "objective_profile"?: "overview_v1" | "asset_impact_v1" | "asset_risk_v1";
  "explicit_objective"?: (ObjectiveContract | null);
  "investigation"?: (ArtifactRef | null);
  "verification"?: (ArtifactRef | null);
  "analysis"?: (ArtifactRef | null);
  "optional_tasks"?: Array<OptionalTask>;
  "policy_version"?: "integration-policy-v1";
};

export type InvestigationArtifactReference = {
  "run_id": string;
  "task_id": string;
  "artifact_id": string;
};

export type InvestigationOptions = {
  "objective_profile"?: ("overview_v1" | "asset_impact_v1" | "asset_risk_v1" | null);
  "timeout_seconds"?: number;
};

export type InvestigationRequest = {
  "schema_version"?: "investigation-request-v1";
  "request_id"?: string;
  "planner_input": PlannerInput;
  "time_scope"?: (TimeScope | null);
  "user_context"?: UserContext;
  "investigation_options"?: InvestigationOptions;
};

export type ObjectiveContract = {
  "question": string;
  "targets"?: Array<string>;
  "asset_id"?: (string | null);
  "component_id"?: (string | null);
  "package_name"?: (string | null);
  "version"?: (string | null);
  "required_outcomes"?: Array<"identity" | "overview" | "asset" | "version_impact" | "remediation_status" | "precise_remediation" | "risk" | "priority" | "verified_exploitation">;
  "window_days"?: (number | null);
  "requires_current"?: boolean;
  "scope_gaps"?: Array<string>;
};

export type OptionalTask = {
  "run_id": string;
  "task_id": string;
};

export type PlannerInput = {
  "query": QueryRequest;
  "component_id"?: (string | null);
  "snapshot_id"?: (string | null);
  "component"?: (ResolutionInput | null);
  "candidate_reference"?: (string | null);
};

export type QueryRequest = {
  "question": string;
  "asset_id"?: (string | null);
  "target"?: (string | null);
  "mode"?: "auto" | "fast" | "deep";
  "request_key": string;
  "realtime"?: boolean;
};

export type ResolutionInput = {
  "name": string;
  "ecosystem"?: (string | null);
  "package_name"?: (string | null);
  "version"?: (string | null);
  "purl"?: (string | null);
};

export type TimeScope = {
  "window_days"?: (number | null);
  "requires_current"?: boolean;
};

export type UserContext = {
  "display_language"?: "zh-CN";
  "notes"?: string;
};

export type VerificationRequest = {
  "source_run_id": string;
  "source_task_id": string;
  "source_artifact_id": string;
  "task_type"?: "evidence_verification" | "claim_validation" | "conflict_detection";
  "claim_ids"?: Array<string>;
  "request_key": string;
  "model_assistance"?: boolean;
  "include_source_facts"?: boolean;
  "supporting_artifacts"?: Array<InvestigationArtifactReference>;
  "asset_id"?: (string | null);
  "component_id"?: (string | null);
  "supplement_id"?: (string | null);
};

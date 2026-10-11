// Generated in memory from current Python JSON Schema. INTERNAL schemas are not HTTP API contracts.
// UUID/date/date-time are strings on the wire; JSON Schema numeric bounds and cross-field validators still apply.
// Schemaless dictionaries map to unknown. Do not treat static TypeScript types as runtime validation.
export type AnalysisRequest = {
  /** format=uuid */
  "investigation_run_id": string;
  /** pattern=^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ */
  "investigation_task_id": string;
  /** format=uuid */
  "investigation_artifact_id": string;
  /** format=uuid */
  "verification_run_id": string;
  /** pattern=^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ */
  "verification_task_id": string;
  /** format=uuid */
  "verification_artifact_id": string;
  "asset_id"?: (string | null);
  "component_id"?: (string | null);
  "task_type"?: "risk_analysis" | "asset_impact_analysis" | "remediation_prioritization";
  /** minLength=1, maxLength=150 */
  "request_key": string;
  "model_assistance"?: boolean;
};

export type ArtifactRef = {
  /** format=uuid */
  "run_id": string;
  /** pattern=^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ */
  "task_id": string;
  /** format=uuid */
  "artifact_id": string;
  "schema_version": "investigation-artifact-v1" | "verification-artifact-v1" | "risk-analysis-artifact-v1";
};

export type IntegrationRequest = {
  /** minLength=1, maxLength=150 */
  "request_key": string;
  "run_id"?: (string | null);
  "planner_run_id"?: (string | null);
  "objective_source"?: "stored_planner_request" | "new_structured_request";
  "objective_profile"?: "overview_v1" | "asset_impact_v1" | "asset_risk_v1";
  "explicit_objective"?: (ObjectiveContract | null);
  "investigation"?: (ArtifactRef | null);
  "verification"?: (ArtifactRef | null);
  "analysis"?: (ArtifactRef | null);
  /** maxItems=16 */
  "optional_tasks"?: Array<OptionalTask>;
  "policy_version"?: "integration-policy-v1";
};

export type InvestigationOptions = {
  "objective_profile"?: ("overview_v1" | "asset_impact_v1" | "asset_risk_v1" | null);
  /** minimum=1, maximum=300 */
  "timeout_seconds"?: number;
};

export type InvestigationRequest = {
  "schema_version"?: "investigation-request-v1";
  /** format=uuid */
  "request_id"?: string;
  "planner_input": PlannerInput;
  "time_scope"?: (TimeScope | null);
  "user_context"?: UserContext;
  "investigation_options"?: InvestigationOptions;
};

export type ObjectiveContract = {
  /** minLength=1, maxLength=2000 */
  "question": string;
  /** maxItems=3 */
  "targets"?: Array<string>;
  "asset_id"?: (string | null);
  "component_id"?: (string | null);
  "package_name"?: (string | null);
  "version"?: (string | null);
  /** minItems=1, maxItems=9 */
  "required_outcomes"?: Array<"identity" | "overview" | "asset" | "version_impact" | "remediation_status" | "precise_remediation" | "risk" | "priority" | "verified_exploitation">;
  "window_days"?: (number | null);
  "requires_current"?: boolean;
  "scope_gaps"?: Array<string>;
};

export type OptionalTask = {
  /** format=uuid */
  "run_id": string;
  /** pattern=^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ */
  "task_id": string;
};

export type PlannerInput = {
  "query": QueryRequest;
  "component_id"?: (string | null);
  "snapshot_id"?: (string | null);
  "component"?: (ResolutionInput | null);
};

export type QueryRequest = {
  /** minLength=1, maxLength=2000 */
  "question": string;
  "asset_id"?: (string | null);
  "target"?: (string | null);
  "mode"?: "auto" | "fast" | "deep";
  /** minLength=1, maxLength=150 */
  "request_key": string;
  "realtime"?: boolean;
};

export type ResolutionInput = {
  /** maxLength=200 */
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
  /** maxLength=1000 */
  "notes"?: string;
};

export type VerificationRequest = {
  /** format=uuid */
  "source_run_id": string;
  /** pattern=^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ */
  "source_task_id": string;
  /** format=uuid */
  "source_artifact_id": string;
  "task_type"?: "evidence_verification" | "claim_validation" | "conflict_detection";
  /** maxItems=32 */
  "claim_ids"?: Array<string>;
  /** minLength=1, maxLength=150 */
  "request_key": string;
  "model_assistance"?: boolean;
};


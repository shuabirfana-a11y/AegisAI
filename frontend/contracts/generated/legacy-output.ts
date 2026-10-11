// Generated from current Python JSON Schema. INTERNAL schemas are not HTTP API contracts.
// UUID/date/date-time are strings on the wire; JSON Schema numeric bounds and cross-field validators still apply.
// Schemaless dictionaries map to unknown. Do not treat static TypeScript types as runtime validation.
export type TaskArtifact = {
  "task_id": string;
  "agent": "Investigation" | "Verification" | "SecurityAnalysis";
  "status": "success" | "partial" | "failed" | "blocked";
  "result": Record<string, unknown>;
  "claims"?: Array<Record<string, unknown>>;
  "evidence_refs"?: Array<Record<string, unknown>>;
  "unresolved"?: Array<string>;
  "warnings"?: Array<string>;
  "errors"?: Array<Record<string, unknown>>;
  "trace_id": string;
  /** format=date-time */
  "started_at": string;
  /** format=date-time */
  "finished_at": string;
};

export type TaskContract = {
  /** minLength=1, maxLength=100 */
  "task_id": string;
  /** maxLength=500 */
  "goal": string;
  "task_type": "Investigation" | "Verification" | "SecurityAnalysis";
  "inputs": Record<string, unknown>;
  "constraints"?: Record<string, unknown>;
  "dependencies"?: Array<string>;
  "allowed_tools": Array<string>;
  "expected_output"?: Record<string, unknown>;
  "evidence_required"?: boolean;
  "acceptance_criteria"?: Array<string>;
  /** minimum=1, maximum=60 */
  "timeout"?: number;
  "retry_policy"?: Record<string, unknown>;
  "failure_policy"?: "abstain" | "replan" | "human_review";
};

export type ToolEnvelope = {
  "tool": string;
  "status": "success" | "partial" | "no_result" | "failed";
  "data"?: unknown;
  "evidence_refs"?: Array<Record<string, unknown>>;
  "warnings"?: Array<string>;
  "errors"?: Array<Record<string, unknown>>;
  "retryable"?: boolean;
  "trace_id": string;
  /** minimum=0 */
  "duration_ms": number;
};

export type LegacyTaskContract = TaskContract;

export type LegacyTaskArtifact = TaskArtifact;


// Generated from current Python JSON Schema. INTERNAL schemas are not HTTP API contracts.
// UUID and date-time are wire strings; Python validation and JSON Schema bounds still apply.
// Schemaless dictionaries map to unknown; static types do not validate external content.
export type ActionView = {
  "action_id": string;
  "action_type": string;
  "summary": string;
  "category": "IMMEDIATE" | "FURTHER_INVESTIGATION" | "LONG_TERM_HARDENING";
  "fixed_version"?: (string | null);
  "patch_reference"?: (string | null);
  "claim_ids"?: Array<string>;
  "evidence_ids"?: Array<string>;
  "action_provenance": "VERIFIED_CLAIM" | "GENERAL_PRECAUTION";
  "applicability": "CONFIRMED" | "UNKNOWN" | "NOT_APPLICABLE";
  "source_artifact": ArtifactRef;
  "conclusion_scope": "ACCEPTED" | "OBSERVATION";
};

export type AgentContract = {
  "agent_id": string;
  "agent_type": "investigation" | "verification" | "security_analysis";
  "description": string;
  "supported_tasks": Array<("vulnerability_lookup" | "version_match" | "evidence_search" | "patch_analysis" | "risk_analysis" | "asset_lookup" | "evidence_verification" | "claim_validation" | "conflict_detection" | "asset_impact_analysis" | "remediation_prioritization")>;
  "allowed_tools": Array<string>;
  "input_schema"?: "ProfessionalAgentInput-v1";
  "output_schema"?: "AgentArtifact-v1";
  "timeout_seconds"?: number;
};

export type AgentRunTrace = {
  "agent_id": string;
  "agent_type": "investigation" | "verification" | "security_analysis";
  "task_id": string;
  "run_id": string;
  "input_artifact"?: Array<ArtifactReference>;
  "output_artifact"?: (ArtifactReference | null);
  "execution_time"?: (number | null);
  "status": TaskState;
  "attempted": boolean;
  "capability_state": "interface_only" | "implementation_registered";
  "errors"?: Array<Record<string, unknown>>;
};

export type AgentTrace = {
  "run_id": string;
  "status": string;
  "artifact_references": Array<ArtifactRef>;
  "task_statuses": Record<string, string>;
  "tool_calls"?: Array<ToolSummary>;
};

export type AnalysisRun = {
  "agent_id"?: "security_analysis_agent";
  "run_id": string;
  "task_id": string;
  "actor": string;
  "input_artifact_ids": Array<string>;
  "input_snapshot_hash": string;
  "asset_match_result": AssetMatchResult;
  "version_match_result": VersionMatchResult;
  "verification_status": VerificationStatus;
  "claim_dispositions"?: Array<Record<string, unknown>>;
  "risk_factors"?: Array<RiskFactor>;
  "mitigating_factors"?: Array<RiskFactor>;
  "risk_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  "priority": "P0" | "P1" | "P2" | "P3" | "DEFER" | "REVIEW_REQUIRED";
  "rule_ids": Array<string>;
  "model_assist_used": boolean;
  "model_assist_status": string;
  "output_artifact_id": string;
  "execution_time": number;
  "start_time"?: (string | null);
  "end_time"?: (string | null);
  "status": TaskState;
  "tools_called"?: Array<Record<string, unknown>>;
};

export type AnalysisRunResult = {
  "run_id": string;
  "runtime_status": string;
  "artifacts"?: Array<RiskAnalysisArtifact>;
  "traces"?: Array<AnalysisRun>;
};

export type AnswerEnvelope = {
  "schema_version"?: "answer-envelope-v1";
  "answer_id": string;
  "logical_investigation_id": string;
  "original_question": string;
  "answer_status": "COMPLETE" | "COMPLETE_WITH_WARNINGS" | "INCOMPLETE" | "REVIEW_REQUIRED" | "FAILED" | "CANCELLED";
  "integration_status"?: ("PASS" | "PASS_WITH_WARNINGS" | "REPLAN_REQUIRED" | "HUMAN_REVIEW_REQUIRED" | "FAILED" | null);
  "summary": string;
  "key_findings"?: Array<string>;
  "affected_assets"?: Array<AssetView>;
  "risk_assessment"?: (RiskView | null);
  "recommended_actions"?: Array<ActionView>;
  "verified_claims"?: Array<VerifiedFact>;
  "disputed_claims"?: Array<DisputedClaim>;
  "citations"?: Array<Citation>;
  "evidence_observations"?: Array<EvidenceObservation>;
  "evidence_references"?: Array<string>;
  "warnings"?: Array<string>;
  "unresolved_items"?: Array<string>;
  "integration_result_id"?: (string | null);
  "agent_run_references"?: Array<string>;
  "accepted_source_run_references"?: Array<string>;
  "trace_reference": string;
  "generated_at": string;
  "historical_snapshot"?: true;
  "fact_origin"?: "FROZEN_GATE_CONTEXT";
  "explanation_provider"?: "DETERMINISTIC_TEMPLATE";
};

export type ArtifactRef = {
  "run_id": string;
  "task_id": string;
  "artifact_id": string;
  "schema_version": "investigation-artifact-v1" | "verification-artifact-v1" | "risk-analysis-artifact-v1";
};

export type ArtifactReference = {
  "artifact_id": string;
  "agent_id": string;
  "task_id": string;
  "run_id": string;
  "artifact_type": "investigation_result" | "verification_result" | "security_analysis_result";
  "status": TaskState;
};

export type AssetMatchResult = {
  "status"?: "MATCHED" | "NOT_MATCHED" | "UNKNOWN";
  "reason"?: string;
  "claim_ids"?: Array<string>;
  "package_identifier_id"?: (string | null);
};

export type AssetView = {
  "asset_id": (string | null);
  "component_id": (string | null);
  "deployed_version": (string | null);
  "provenance"?: "USER_INVENTORY_NOT_SCANNED";
  "source_artifact": ArtifactRef;
  "claim_ids"?: Array<string>;
};

export type Citation = {
  "evidence_id": string;
  "claim_id": string;
  "hash": string;
  "source_id": string;
  "raw_document_id": string;
  "observation_id": string;
  "reference": Record<string, unknown>;
  "verification_artifact": ArtifactRef;
};

export type ClaimType = "AFFECTS_PRODUCT" | "AFFECTS_VERSION" | "FIXED_VERSION" | "POC_EXISTS" | "POC_ASSOCIATION" | "PATCH_EXISTS" | "FIX_COMMIT" | "KNOWN_EXPLOITED" | "VENDOR_CONFIRMED" | "EXPLOIT_CONDITION" | "REMEDIATION" | "CVSS_SCORE" | "CWE" | "SOURCE_FACT";

export type ClaimVerification = {
  "claim": VerificationClaim;
  "status": VerificationStatus;
  "confidence": number;
  "supporting_evidence_ids"?: Array<string>;
  "conflicting_evidence_ids"?: Array<string>;
  "reason_code": string;
  "reason_summary": string;
  "rules_applied"?: Array<string>;
  "score_components"?: Record<string, unknown>;
  "warnings"?: Array<string>;
  "unresolved_items"?: Array<string>;
};

export type DisputedClaim = {
  "claim_id": string;
  "claim_type": ClaimType;
  "verification_status": "PENDING" | "CONFLICT" | "INSUFFICIENT_EVIDENCE" | "REJECTED";
  "value": Record<string, unknown>;
  "scope_key": string;
  "supporting_evidence_ids"?: Array<string>;
  "conflicting_evidence_ids"?: Array<string>;
  "verification_artifact": ArtifactRef;
  "conclusion_scope"?: "OBSERVATION";
};

export type EvidenceObservation = {
  "evidence_id": string;
  "claim_id": string;
  "verification_status": VerificationStatus;
  "scope_key": string;
  "hash"?: (string | null);
  "source_id"?: (string | null);
  "raw_document_id"?: (string | null);
  "observation_id"?: (string | null);
  "reference": Record<string, unknown>;
  "stance": "support" | "contradict" | "neutral";
  "directness": "direct" | "mention" | "unknown";
  "integrity_status": "VALID" | "MISSING" | "INVALID";
  "is_current": boolean;
  "verification_artifact": ArtifactRef;
  "conclusion_scope"?: "OBSERVATION";
};

export type ExploitationSignal = {
  "status"?: "KNOWN_EXPLOITED" | "VERIFIED_POC_ASSOCIATION" | "POC_CANDIDATE" | "UNKNOWN";
  "usability"?: "NOT_EVALUATED";
  "claim_ids"?: Array<string>;
  "evidence_ids"?: Array<string>;
  "epss"?: Array<Record<string, unknown>>;
};

export type GateCheck = {
  "gate": "completion" | "integrity" | "evidence" | "consistency" | "objective" | "freshness";
  "code": string;
  "outcome"?: "PASS" | "WARNING" | "BLOCKED" | "ERROR" | "NOT_APPLICABLE";
  "blocking"?: "NONE" | "REPLAN" | "HUMAN" | "FATAL";
  "message": string;
  "refs"?: Array<string>;
  "objective"?: ("identity" | "overview" | "asset" | "version_impact" | "remediation_status" | "precise_remediation" | "risk" | "priority" | "verified_exploitation" | null);
};

export type ImpactVersionEvidence = {
  "id": string;
  "type"?: "IMPACT_VERSION_EVIDENCE";
  "vulnerability_id": string;
  "package_identifier_id"?: (string | null);
  "claim_id": string;
  "affected_versions"?: Array<Record<string, unknown>>;
  "fixed_versions"?: Array<Record<string, unknown>>;
  "evidence_ids"?: Array<string>;
  "source": string;
  "reference": Record<string, unknown>;
  "raw_document_id"?: (string | null);
  "observation_id"?: (string | null);
  "hash"?: (string | null);
  "status"?: "CONFIRMED" | "PENDING" | "CONFLICT" | "INSUFFICIENT_EVIDENCE" | "REJECTED";
};

export type IntegrationResult = {
  "integration_id": string;
  "logical_investigation_id": string;
  "trace_id": string;
  "run_id"?: (string | null);
  "source_run_ids"?: Array<string>;
  "status": "PASS" | "PASS_WITH_WARNINGS" | "REPLAN_REQUIRED" | "HUMAN_REVIEW_REQUIRED" | "FAILED";
  "objective_coverage"?: Array<ObjectiveCoverage>;
  "task_completion_summary"?: Array<TaskExecution>;
  "checks": Array<GateCheck>;
  "passed_checks"?: Array<string>;
  "failed_checks"?: Array<string>;
  "blocking_issues"?: Array<string>;
  "warnings"?: Array<string>;
  "unresolved_items"?: Array<string>;
  "artifact_references"?: Array<ArtifactRef>;
  "evidence_references"?: Array<Record<string, unknown>>;
  "replan_reasons"?: Array<string>;
  "human_review_reasons"?: Array<string>;
  "final_result_references"?: Array<ArtifactRef>;
  "partial_result_references"?: Array<ArtifactRef>;
  "input_hash": string;
  "objective_hash": string;
  "policy_version"?: "integration-policy-v1";
  "created_at": string;
  "evaluation_time": string;
  "historical_snapshot"?: true;
  "persistence"?: "STORED" | "NOT_STORED";
};

export type IntegrationTrace = {
  "integration_id": string;
  "logical_investigation_id": string;
  "source_run_ids": Array<string>;
  "artifact_references": Array<ArtifactRef>;
  "rule_version": string;
  "checks": Array<GateCheck>;
  "evidence_references": Array<Record<string, unknown>>;
  "status": "PASS" | "PASS_WITH_WARNINGS" | "REPLAN_REQUIRED" | "HUMAN_REVIEW_REQUIRED" | "FAILED";
  "blocking_issues": Array<string>;
  "execution_time_ms": number;
  "error_codes"?: Array<string>;
};

export type InvestigationArtifact = {
  "artifact_id": string;
  "task_id": string;
  "agent_id"?: "investigation_agent";
  "run_id": string;
  "schema_version"?: "investigation-artifact-v1";
  "status": "COMPLETE" | "PARTIAL" | "CONFLICT" | "INSUFFICIENT_EVIDENCE";
  "runtime_status": TaskState;
  "partial_result"?: boolean;
  "information_status"?: "CONFIRMED" | "CANDIDATE" | "CONFLICT" | "INSUFFICIENT_EVIDENCE";
  "vulnerability_id"?: (string | null);
  "canonical_id"?: (string | null);
  "description"?: (string | null);
  "component"?: (Record<string, unknown> | null);
  "asset"?: (Record<string, unknown> | null);
  "affected_versions"?: Array<Record<string, unknown>>;
  "fixed_versions"?: Array<Record<string, unknown>>;
  "version_match"?: (Record<string, unknown> | null);
  "cvss"?: Array<Record<string, unknown>>;
  "cwe"?: Array<Record<string, unknown>>;
  "poc_candidates"?: Array<Record<string, unknown>>;
  "patch_information"?: Array<Record<string, unknown>>;
  "evidence"?: Array<Record<string, unknown>>;
  "uncertainties"?: Array<string>;
  "conflicts"?: Array<Record<string, unknown>>;
  "confidence"?: (number | null);
  "failed_tools"?: Array<Record<string, unknown>>;
  "tool_calls"?: Array<Record<string, unknown>>;
  "dependency_artifact_ids"?: Array<string>;
  "evidence_storage"?: "artifact" | "tool_receipts";
  "receipt_references"?: Record<string, unknown>;
  "findings"?: Array<Record<string, unknown>>;
};

export type InvestigationArtifactReference = {
  "run_id": string;
  "task_id": string;
  "artifact_id": string;
};

export type InvestigationContext = {
  "schema_version"?: "investigation-context-v1";
  "logical_investigation_id": string;
  "owner": string;
  "original_request": InvestigationRequest;
  "request_hash": string;
  "resolved_scope": ResolvedScope;
  "current_stage"?: "CREATED" | "PLANNING" | "INVESTIGATING" | "VERIFYING" | "ANALYZING" | "INTEGRATING" | "COMPOSING" | "COMPLETED" | "WAITING_REVIEW" | "FAILED" | "CANCELLED";
  "overall_status"?: "RUNNING" | "SUCCEEDED" | "SUCCEEDED_WITH_WARNINGS" | "INCOMPLETE" | "REVIEW_REQUIRED" | "FAILED" | "CANCELLED";
  "planner_run_id"?: (string | null);
  "investigation_run_id"?: (string | null);
  "verification_run_id"?: (string | null);
  "analysis_run_id"?: (string | null);
  "artifact_references"?: Array<ArtifactRef>;
  "integration_result_id"?: (string | null);
  "gate_logical_investigation_id"?: (string | null);
  "gate_input_hash"?: (string | null);
  "objective_hash"?: (string | null);
  "answer_id"?: (string | null);
  "stage_keys"?: Record<string, string>;
  "warnings"?: Array<string>;
  "unresolved_items"?: Array<string>;
  "events"?: Array<StageEvent>;
  "created_at": string;
  "updated_at": string;
  "deadline_at": string;
  "cancel_requested_at"?: (string | null);
  "cancel_observed_at"?: (string | null);
  "finished_at"?: (string | null);
  "error_code"?: (string | null);
  "revision"?: number;
  "policy_version"?: "orchestration-policy-v1";
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

export type InvestigationResult = {
  "context": InvestigationContext;
  "status": InvestigationStatus;
  "answer"?: (AnswerEnvelope | null);
  "persistence"?: "STORED" | "NOT_STORED";
  "delivery_error"?: (string | null);
};

export type InvestigationRunResult = {
  "run_id": string;
  "runtime_status": string;
  "artifacts": Array<InvestigationArtifact>;
  "blocked_tasks"?: Array<string>;
  "input_required_tasks"?: Array<string>;
  "traces"?: Array<InvestigationTaskTrace>;
};

export type InvestigationStatus = {
  "logical_investigation_id": string;
  "current_stage": "CREATED" | "PLANNING" | "INVESTIGATING" | "VERIFYING" | "ANALYZING" | "INTEGRATING" | "COMPOSING" | "COMPLETED" | "WAITING_REVIEW" | "FAILED" | "CANCELLED";
  "overall_status": "RUNNING" | "SUCCEEDED" | "SUCCEEDED_WITH_WARNINGS" | "INCOMPLETE" | "REVIEW_REQUIRED" | "FAILED" | "CANCELLED";
  "planner_run_id"?: (string | null);
  "investigation_run_id"?: (string | null);
  "verification_run_id"?: (string | null);
  "analysis_run_id"?: (string | null);
  "cancel_requested"?: boolean;
  "recovery_required"?: boolean;
  "warnings"?: Array<string>;
  "error_code"?: (string | null);
  "revision": number;
  "updated_at": string;
};

export type InvestigationTaskTrace = {
  "agent_id"?: "investigation_agent";
  "task_id": string;
  "tools_called"?: Array<Record<string, unknown>>;
  "start_time"?: (string | null);
  "end_time"?: (string | null);
  "status": TaskState;
  "artifact_id"?: (string | null);
  "attempted": boolean;
};

export type InvestigationTrace = {
  "schema_version"?: string;
  "logical_investigation_id": string;
  "original_question": string;
  "planner": (PlannerSummary | null);
  "events": Array<StageEvent>;
  "agent_runs": Array<AgentTrace>;
  "integration_result_id": (string | null);
  "integration_status": ("PASS" | "PASS_WITH_WARNINGS" | "REPLAN_REQUIRED" | "HUMAN_REVIEW_REQUIRED" | "FAILED" | null);
  "answer_id": (string | null);
  "warnings": Array<string>;
  "unresolved_items": Array<string>;
  "error_code": (string | null);
  "historical_snapshot"?: boolean;
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

export type ObjectiveCoverage = {
  "outcome": "identity" | "overview" | "asset" | "version_impact" | "remediation_status" | "precise_remediation" | "risk" | "priority" | "verified_exploitation";
  "status": "SATISFIED" | "ABSTAINED" | "MISSING" | "CONFLICT";
  "references"?: Array<string>;
};

export type PatchAvailability = {
  "status"?: "CONFIRMED_PRESENT" | "UNCONFIRMED" | "UNKNOWN";
  "claim_ids"?: Array<string>;
  "evidence_ids"?: Array<string>;
  "applied"?: "UNKNOWN";
  "applicability"?: "CONFIRMED" | "UNKNOWN";
};

export type PlannerInput = {
  "query": QueryRequest;
  "component_id"?: (string | null);
  "snapshot_id"?: (string | null);
  "component"?: (ResolutionInput | null);
};

export type PlannerSummary = {
  "planner_run_id": string;
  "validation_status": string;
  "retry_count": number;
  "prompt_version": string;
  "task_ids"?: Array<string>;
};

export type QueryRequest = {
  "question": string;
  "asset_id"?: (string | null);
  "target"?: (string | null);
  "mode"?: "auto" | "fast" | "deep";
  "request_key": string;
  "realtime"?: boolean;
};

export type RecommendedAction = {
  "action_id": string;
  "action_type": string;
  "category": "IMMEDIATE" | "FURTHER_INVESTIGATION" | "LONG_TERM_HARDENING";
  "summary": string;
  "target_component"?: (string | null);
  "fixed_version"?: (string | null);
  "patch_reference"?: (string | null);
  "claim_ids"?: Array<string>;
  "evidence_ids"?: Array<string>;
  "preconditions"?: Array<string>;
  "action_provenance": "VERIFIED_CLAIM" | "GENERAL_PRECAUTION";
  "applicability"?: "CONFIRMED" | "UNKNOWN" | "NOT_APPLICABLE";
};

export type ResolutionInput = {
  "name": string;
  "ecosystem"?: (string | null);
  "package_name"?: (string | null);
  "version"?: (string | null);
  "purl"?: (string | null);
};

export type ResolvedScope = {
  "planner_input": PlannerInput;
  "targets": Array<string>;
  "component_origin": "EXPLICIT" | "QUESTION_EXTRACTED" | "MISSING";
  "objective_profile": "overview_v1" | "asset_impact_v1" | "asset_risk_v1";
  "objective_source": "stored_planner_request" | "new_structured_request";
  "objective": ObjectiveContract;
  "route": Record<string, unknown>;
};

export type RiskAnalysisArtifact = {
  "verification_status": VerificationStatus;
  "asset_id"?: (string | null);
  "component"?: (string | null);
  "version"?: (string | null);
  "asset_match_status"?: "MATCHED" | "NOT_MATCHED" | "UNKNOWN";
  "version_match_status"?: "AFFECTED" | "NOT_AFFECTED" | "UNKNOWN";
  "asset_match_result"?: AssetMatchResult;
  "version_match_result"?: VersionMatchResult;
  "exploitation_signal"?: ExploitationSignal;
  "patch_availability"?: PatchAvailability;
  "risk_level"?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  "priority"?: "P0" | "P1" | "P2" | "P3" | "DEFER" | "REVIEW_REQUIRED";
  "affected"?: (boolean | null);
  "risk_factors"?: Array<RiskFactor>;
  "mitigating_factors"?: Array<RiskFactor>;
  "recommended_actions"?: Array<RecommendedAction>;
  "evidence_refs"?: Array<Record<string, unknown>>;
  "reasoning_summary"?: string;
  "claim_dispositions"?: Array<Record<string, unknown>>;
  "confidence"?: number;
  "confidence_kind"?: "uncalibrated_heuristic";
  "warnings"?: Array<string>;
  "unresolved_items"?: Array<string>;
  "rule_ids"?: Array<string>;
  "rules_version"?: "analysis-rules-v1";
  "priority_details"?: Record<string, unknown>;
  "partial_result"?: boolean;
  "coverage_complete"?: boolean;
  "model_assist_used"?: boolean;
  "model_assist_status"?: "DISABLED" | "SUCCEEDED" | "FAILED" | "SKIPPED";
  "model_calls"?: Array<Record<string, unknown>>;
  "artifact_id": string;
  "task_id": string;
  "agent_id"?: "security_analysis_agent";
  "run_id": string;
  "schema_version"?: "risk-analysis-artifact-v1";
  "context_id": string;
  "input_artifact_ids": Array<string>;
  "input_snapshot_hash": string;
  "evaluation_time": string;
  "source_verification_time": string;
  "inventory_revision"?: (number | null);
  "execution_status": TaskState;
  "tool_calls"?: Array<Record<string, unknown>>;
  "historical_snapshot"?: true;
  "scope_notice"?: string;
};

export type RiskFactor = {
  "factor_id": string;
  "code": string;
  "reason": string;
  "value"?: unknown;
  "claim_ids"?: Array<string>;
  "evidence_ids"?: Array<string>;
  "provenance": "verified_claim" | "asset_inventory" | "candidate" | "source_assertion";
  "influences_decision"?: boolean;
  "rejected_reason"?: (string | null);
};

export type RiskView = {
  "risk_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  "priority": "P0" | "P1" | "P2" | "P3" | "DEFER" | "REVIEW_REQUIRED";
  "affected": (boolean | null);
  "verification_status": VerificationStatus;
  "source_artifact": ArtifactRef;
  "asset_match_status": "MATCHED" | "NOT_MATCHED" | "UNKNOWN";
  "version_match_status": "AFFECTED" | "NOT_AFFECTED" | "UNKNOWN";
  "exploitation_status": "KNOWN_EXPLOITED" | "VERIFIED_POC_ASSOCIATION" | "POC_CANDIDATE" | "UNKNOWN";
  "usability"?: "NOT_EVALUATED";
  "patch_status": "CONFIRMED_PRESENT" | "UNCONFIRMED" | "UNKNOWN";
  "patch_applied"?: "UNKNOWN";
  "conclusion_scope": "ACCEPTED" | "OBSERVATION";
};

export type RunSnapshot = {
  "run_id": string;
  "trace_id": string;
  "status": string;
  "result"?: (Record<string, unknown> | null);
};

export type StageEvent = {
  "stage": "CREATED" | "PLANNING" | "INVESTIGATING" | "VERIFYING" | "ANALYZING" | "INTEGRATING" | "COMPOSING" | "COMPLETED" | "WAITING_REVIEW" | "FAILED" | "CANCELLED";
  "code": string;
  "at"?: string;
  "overall_status"?: ("RUNNING" | "SUCCEEDED" | "SUCCEEDED_WITH_WARNINGS" | "INCOMPLETE" | "REVIEW_REQUIRED" | "FAILED" | "CANCELLED" | null);
  "references"?: Record<string, string>;
};

export type TaskArtifact = {
  "artifact_id"?: string;
  "run_id": string;
  "task_id": string;
  "status": TaskState;
  "result"?: Record<string, unknown>;
  "evidence"?: Array<Record<string, unknown>>;
  "tool_calls"?: Array<Record<string, unknown>>;
  "confidence"?: (number | null);
  "unresolved_questions"?: Array<string>;
  "warnings"?: Array<string>;
  "errors"?: Array<Record<string, unknown>>;
  "start_time"?: (string | null);
  "end_time": string;
};

export type TaskExecution = {
  "run_id": string;
  "task_id": string;
  "semantic_type": string;
  "status": TaskState;
  "run_status": string;
  "required"?: boolean;
  "dependencies"?: Array<string>;
  "error_codes"?: Array<string>;
};

export type TaskState = "CREATED" | "PENDING" | "READY" | "RUNNING" | "SUCCESS" | "FAILED" | "WAITING_REVIEW" | "BLOCKED";

export type TaskTrace = {
  "run_id": string;
  "task_id": string;
  "task_type": string;
  "start_time"?: (string | null);
  "end_time"?: (string | null);
  "status"?: TaskState;
  "tools_called"?: Array<Record<string, unknown>>;
  "model_called"?: Array<Record<string, unknown>>;
  "error"?: Array<Record<string, unknown>>;
  "artifact_id"?: (string | null);
  "dependencies"?: Array<string>;
  "transitions"?: Array<Record<string, unknown>>;
};

export type TimeScope = {
  "window_days"?: (number | null);
  "requires_current"?: boolean;
};

export type ToolSummary = {
  "record_id": string;
  "task_id": string;
  "tool": string;
  "status": string;
  "duration_ms": number;
  "evidence_ids"?: Array<string>;
};

export type TraceSnapshot = {
  "run_id": string;
  "trace_id": string;
  "tasks": Array<TaskTrace>;
  "artifacts": Array<TaskArtifact>;
};

export type UserContext = {
  "display_language"?: "zh-CN";
  "notes"?: string;
};

export type VerificationArtifact = {
  "claims"?: Array<ClaimVerification>;
  "verification_status": VerificationStatus;
  "confidence": number;
  "supporting_evidence"?: Array<VerificationEvidence>;
  "conflicting_evidence"?: Array<VerificationEvidence>;
  "conflicts"?: Array<VerificationConflict>;
  "warnings"?: Array<string>;
  "unresolved_items"?: Array<string>;
  "partial_result"?: boolean;
  "model_calls"?: Array<Record<string, unknown>>;
  "model_hints"?: Array<Record<string, unknown>>;
  "rules_version"?: "verification-rules-v1";
  "version_observations"?: Array<VersionObservation>;
  "impact_version_evidence"?: Array<ImpactVersionEvidence>;
  "artifact_id": string;
  "task_id": string;
  "run_id": string;
  "agent_id"?: "verification_agent";
  "schema_version"?: "verification-artifact-v1";
  "source_run_id": string;
  "source_artifact_id": string;
  "source_snapshot_hash": string;
  "evaluation_time": string;
  "execution_status"?: TaskState;
  "tool_calls"?: Array<Record<string, unknown>>;
};

export type VerificationClaim = {
  "claim_id": string;
  "statement": string;
  "claim_type": ClaimType;
  "source_task_id": string;
  "related_entities"?: Record<string, unknown>;
  "status"?: VerificationStatus;
  "value": Record<string, unknown>;
  "scope_key": string;
  "vulnerability_id": string;
  "package_identifier_id"?: (string | null);
  "branch"?: (string | null);
  "claim_revision"?: (number | null);
  "origin"?: "stored" | "derived";
  "source_field"?: (string | null);
  "evidence_ids"?: Array<string>;
};

export type VerificationConflict = {
  "conflict_type": string;
  "claim_ids": Array<string>;
  "evidence_ids": Array<string>;
  "scope_key": string;
  "reason": string;
};

export type VerificationEvidence = {
  "evidence_id": string;
  "claim_id": string;
  "source_id"?: (string | null);
  "source_key"?: string;
  "source_type"?: string;
  "source_name"?: string;
  "source_time"?: (string | null);
  "content": string;
  "reference": Record<string, unknown>;
  "hash"?: (string | null);
  "authority_score"?: number;
  "directness_score"?: number;
  "authority_level"?: ("official" | "authoritative" | "secondary" | "community" | null);
  "authority_scope"?: (string | null);
  "lineage_key"?: (string | null);
  "observation_id"?: (string | null);
  "raw_document_id"?: (string | null);
  "published_at"?: (string | null);
  "retrieved_at"?: (string | null);
  "excerpt_hash"?: (string | null);
  "observed_value"?: Record<string, unknown>;
  "scope_key": string;
  "vulnerability_id"?: (string | null);
  "stance"?: "support" | "contradict" | "neutral";
  "directness"?: "direct" | "mention" | "unknown";
  "evidence_type"?: string;
  "is_current"?: boolean;
  "integrity_status"?: "VALID" | "MISSING" | "INVALID";
  "exclusion_reasons"?: Array<string>;
  "details"?: Record<string, unknown>;
};

export type VerificationRun = {
  "agent_id"?: "verification_agent";
  "run_id": string;
  "task_id": string;
  "input_artifact": Record<string, unknown>;
  "output_artifact"?: (string | null);
  "claims_checked"?: Array<string>;
  "evidence_used"?: Array<string>;
  "verification_result"?: (VerificationStatus | null);
  "confidence"?: number;
  "execution_time": number;
  "start_time"?: (string | null);
  "end_time"?: (string | null);
  "status": TaskState;
  "tools_called"?: Array<Record<string, unknown>>;
  "rules_version"?: string;
};

export type VerificationRunResult = {
  "run_id": string;
  "runtime_status": string;
  "artifacts"?: Array<VerificationArtifact>;
  "traces"?: Array<VerificationRun>;
};

export type VerificationStatus = "CONFIRMED" | "PENDING" | "INSUFFICIENT_EVIDENCE" | "CONFLICT" | "REJECTED";

export type VerifiedFact = {
  "claim_id": string;
  "claim_type": ClaimType;
  "verification_status"?: "CONFIRMED";
  "value": Record<string, unknown>;
  "evidence_ids": Array<string>;
  "source_artifact": ArtifactRef;
};

export type VersionMatchResult = {
  "status"?: "AFFECTED" | "NOT_AFFECTED" | "UNKNOWN";
  "affected"?: (boolean | null);
  "reason"?: string;
  "claim_ids"?: Array<string>;
  "comparisons"?: Array<Record<string, unknown>>;
  "normalization"?: Record<string, unknown>;
};

export type VersionObservation = {
  "id": string;
  "type"?: "VERSION_OBSERVATION";
  "asset_id": string;
  "component_id": string;
  "asset_name": string;
  "component": string;
  "version"?: (string | null);
  "package_identifier_id"?: (string | null);
  "package_name"?: (string | null);
  "ecosystem"?: string;
  "namespace"?: string;
  "purl"?: (string | null);
  "environment"?: "production" | "staging" | "development" | "unknown";
  "exposure"?: "internet" | "internal" | "development" | "unknown";
  "criticality"?: "unknown";
  "inventory_revision": number;
  "asset_updated_at": string;
  "component_updated_at": string;
  "source"?: "OWNER_INVENTORY_NOT_SCANNED";
  "created_at": string;
  "source_artifact": InvestigationArtifactReference;
  "receipt_id": string;
  "receipt_hash": string;
  "is_demo": boolean;
};

export type RuntimeTaskArtifact = TaskArtifact;
export type RuntimeTaskTrace = TaskTrace;
export type RuntimeRunSnapshot = RunSnapshot;
export type RuntimeTraceSnapshot = TraceSnapshot;
export type EvidenceReference = Citation;

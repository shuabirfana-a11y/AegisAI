/**
 * API_NOT_EXPOSED. AgentTrace is the Phase 11-D run summary (run_id/task_statuses/tool_calls).
 * AgentRunTrace is the professional framework task-level trace. Legacy HTTP trace stays separate.
 */
export type { AgentTrace, InvestigationTrace, AgentRunTrace, RuntimeTaskTrace, RuntimeTaskArtifact,
 RuntimeRunSnapshot, RuntimeTraceSnapshot, TaskState, ArtifactRef, ToolSummary, PlannerSummary, StageEvent
} from './generated/internal-output.js';
export type { LegacyAssistantTrace, LegacyToolTrace, LegacyTaskRun } from './generated/http-responses.js';

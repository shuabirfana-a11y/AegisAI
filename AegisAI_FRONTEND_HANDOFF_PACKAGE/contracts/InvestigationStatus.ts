/** API_NOT_EXPOSED. Stage, overall outcome, Gate and Answer state are distinct. */
import type { InvestigationStatus as BackendStatus } from './generated/internal-output.js';
export type { InvestigationStatus, StageEvent } from './generated/internal-output.js';
export type InvestigationStage = BackendStatus['current_stage'];
export type InvestigationOverallStatus = BackendStatus['overall_status'];

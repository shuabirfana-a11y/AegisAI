/** API_NOT_EXPOSED. Gate logical ID is not the root investigation logical ID. */
import type { IntegrationResult as BackendGate } from './generated/internal-output.js';
export type { IntegrationResult, IntegrationTrace, GateCheck, ObjectiveCoverage, TaskExecution, ArtifactRef
} from './generated/internal-output.js';
export type IntegrationStatus = BackendGate['status'];

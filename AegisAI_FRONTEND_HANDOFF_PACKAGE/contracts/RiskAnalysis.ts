/** API_NOT_EXPOSED. Unknown impact is null, not false. A PoC association does not prove usability. */
import type { RiskAnalysisArtifact as BackendRisk } from './generated/internal-output.js';
export type { RiskAnalysisArtifact as RiskAnalysis, RiskAnalysisArtifact, RiskFactor, RecommendedAction,
 ExploitationSignal, PatchAvailability, AssetMatchResult, VersionMatchResult
} from './generated/internal-output.js';
export type RiskLevel = BackendRisk['risk_level'];
export type RiskPriority = BackendRisk['priority'];
export type { LegacyAssetRiskPayload, CurrentAssetRisk, HistoricalAssetRisk } from './generated/http-responses.js';

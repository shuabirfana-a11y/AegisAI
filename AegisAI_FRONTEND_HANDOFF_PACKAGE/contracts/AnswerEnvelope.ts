/**
 * API_NOT_EXPOSED. Answer status is COMPLETE/INCOMPLETE/etc; Gate status is PASS/REPLAN_REQUIRED/etc.
 * Exact wire names: key_findings, risk_assessment, recommended_actions, citations/evidence_observations.
 */
import type { AnswerEnvelope as BackendAnswer } from './generated/internal-output.js';
export type { AnswerEnvelope, VerifiedFact, Citation, DisputedClaim, EvidenceObservation,
 RiskView, AssetView, ActionView, ArtifactRef } from './generated/internal-output.js';
export type AnswerStatus = BackendAnswer['answer_status'];

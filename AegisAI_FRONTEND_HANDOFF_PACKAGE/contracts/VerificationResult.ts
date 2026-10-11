/**
 * API_NOT_EXPOSED. VerificationResult here aliases the professional VerificationArtifact.
 * HttpVerificationResult is the existing DB row inside vulnerability detail verification_results.
 */
import type { HttpVerificationResultRow } from './generated/http-data-columns.js';
export type { VerificationArtifact as VerificationResult, VerificationArtifact, VerificationRun,
 VerificationRunResult, ClaimVerification, VerificationConflict, VerificationStatus
} from './generated/internal-output.js';
export type HttpVerificationResult = HttpVerificationResultRow & {
 content_trust_level: 'UNTRUSTED_EXTERNAL_CONTENT';
};

/**
 * Claim is the professional VerificationClaim DTO. HttpClaim is the current DB-backed HTTP row.
 * Do not exchange value (snapshot) and value_json (HTTP row), or assume derived claim IDs are UUIDs.
 */
export type { VerificationClaim as Claim, VerificationClaim, ClaimVerification, ClaimType,
 VerificationStatus, VerifiedFact, DisputedClaim } from './generated/internal-output.js';
export type { ClaimRow as HttpClaim } from './generated/http-responses.js';

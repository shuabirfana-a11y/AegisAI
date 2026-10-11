/**
 * API_NOT_EXPOSED. EvidenceReference = Answer Citation, with a hash and source/raw/observation IDs.
 * Snapshot evidence_id / claim_id are strings and may be derived rather than database UUIDs.
 */
export type { EvidenceReference, Citation, EvidenceObservation, VerificationEvidence, ArtifactRef
} from './generated/internal-output.js';
export type { EvidenceRow as HttpEvidence } from './generated/http-responses.js';

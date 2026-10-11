/**
 * Manually mapped from FastAPI handler return values and SQLAlchemy columns.
 * These types DO NOT come from FastAPI response_model (all 34 are absent).
 * See FRONTEND_HANDOFF.md for HTTP/internal/proposed boundaries.
 */
import type * as Row from './http-data-columns.js';
import type { LegacyTaskContract, LegacyTaskArtifact, ToolEnvelope } from './legacy-output.js';
type Plain<T> = Omit<T, 'content_trust_level'>;
type Enriched<T> = T & { content_trust_level: 'UNTRUSTED_EXTERNAL_CONTENT' };
export type JsonValue = Row.JsonValue;
export type UUID = string;
export type DateTime = string;
export type VerificationStatus = 'CONFIRMED' | 'PENDING' | 'INSUFFICIENT_EVIDENCE' | 'CONFLICT' | 'REJECTED';
export interface Page<T> { items: T[]; total: number; offset: number; limit: number; }
export interface EnrichedPage<T> extends Page<T> { content_trust_level: 'UNTRUSTED_EXTERNAL_CONTENT'; }
export interface Health {
 application: 'up'; database: 'up' | 'down'; sources: string; scope: 'local development';
}
export type SourceItem = Omit<Row.HttpSourceRow, 'metadata' | 'content_trust_level'> & {
 last_sync: UUID | null; latest_error: string | null;
 records: { raw_documents: number; processed_observations: number };
};
export interface SourcesResponse { items: SourceItem[]; total: number; status_semantics: string; }
export type SyncRunsResponse = Page<Plain<Row.HttpSyncRunRow>>;
export type VulnerabilityListItem = Omit<Row.HttpVulnerabilityRow, 'metadata' | 'content_trust_level'>;
export interface VulnerabilityListResponse extends Page<VulnerabilityListItem> {
 data_status: string; coverage: string;
}
export interface VulnerabilityFilters {
 q?: string; source?: 'CVE_LIST' | 'OSV' | 'CISA_KEV';
 ai_relevance?: 'relevant' | 'irrelevant' | 'uncertain';
 offset?: number; limit?: number; sort?: 'modified_desc' | 'published_desc';
}
export interface SourceVariant {
 source: string; external_id: string; observation_id: UUID; raw_document_id: UUID;
 is_current: boolean; title: unknown; description: unknown; published_at: unknown; modified_at: unknown;
 record_status: unknown; field_provenance: unknown; lineage: unknown;
 verification_status: 'pending'; normalizer_version: string | null;
}
export type SourceDocument = Plain<Row.HttpRawDocumentRow> & {
 raw_document_id: UUID; source_key: string; source_published_at: unknown;
 source_modified_at: unknown; locator: JsonValue; untrusted: true;
};
export type ClaimRow = Enriched<Row.HttpClaimRow>;
export type EvidenceRow = Enriched<Row.HttpEvidenceRow> & {
 claim_verification_status: VerificationStatus; source_key: string;
};
export type ReviewRow = Enriched<Row.HttpReviewTaskRow>;
export type AuditRow = Enriched<Row.HttpAuditLogRow>;
export type ReviewDetail = ReviewRow & { claim: ClaimRow; evidence: EvidenceRow[]; audit: AuditRow[] };
export type VulnerabilityDetail = Plain<Row.HttpVulnerabilityRow> & {
 source_variants: SourceVariant[]; source_documents: SourceDocument[];
 external_identifiers: Array<Plain<Row.HttpExternalIdentifierRow>>;
 affected_versions: Array<Plain<Row.HttpAffectedVersionRangeRow> & { source_key: string; is_current: boolean }>;
 cvss_assessments: Array<Plain<Row.HttpCvssAssessmentRow> & { source_key: string; is_current: boolean }>;
 products: Array<Plain<Row.HttpProductRow>>; cwe: Array<Plain<Row.HttpWeaknessRow>>;
 references: Array<Plain<Row.HttpReferenceRow> & { observation_id: UUID; is_current: boolean }>;
 ai_relevance: Array<Plain<Row.HttpAiRelevanceAssessmentRow> & { is_current: boolean }>;
 verification_status: 'pending';
 enrichment: Array<Enriched<Row.HttpEnrichmentJobRow>>;
 claims: ClaimRow[]; evidence: EvidenceRow[];
 pocs: Array<Enriched<Row.HttpPocCandidateRow>>; patches: Array<Enriched<Row.HttpPatchCandidateRow>>;
 timeline: Array<Enriched<Row.HttpIntelligenceEventRow>>;
 epss: Array<Enriched<Row.HttpEpssSnapshotRow>>; known_exploitation: Array<Enriched<Row.HttpKnownExploitationRow>>;
 conflicts: Array<Enriched<Row.HttpConflictRecordRow>>;
 verification_results: Array<Enriched<Row.HttpVerificationResultRow>>; reviews: ReviewRow[];
};
export type AssetRow = Enriched<Row.HttpAssetRow>;
export type ComponentRow = Enriched<Row.HttpAssetComponentRow>;
export type AssetDetail = AssetRow & { components: ComponentRow[] };
export interface AssetOverview {
 assets: number; components: number; affected_components: number; critical_high: number;
 confirmed_poc: number; kev: number; patch_available: number; uncertain_matches: number;
 not_evaluated_components: number; is_demo_inventory_included: boolean; counts_unit: string;
}
export interface LegacyAssetRiskPayload {
 asset_id: UUID; asset_name: string; is_demo: boolean; environment: string; exposure: string;
 component_id: UUID; component_name: string | null; installed_version: string | null;
 normalized_version: string | null; vulnerability_id: UUID; canonical_id: string; title: string;
 severity: 'critical' | 'high' | 'medium' | 'low' | 'info' | 'unknown';
 match_status: 'AFFECTED' | 'NOT_AFFECTED' | 'UNCERTAIN' | 'NOT_EVALUATED';
 verification_status: VerificationStatus; priority: 'P0' | 'P1' | 'P2' | 'P3' | 'REVIEW' | 'INFO';
 kev: { confirmed: boolean; catalog_status: string; known_exploited: boolean | null;
  as_of: DateTime | null; catalog_version: string | null; claim_ids: string[]; evidence_ids: string[] };
 poc: { confirmed: boolean; confirmed_count: number; status: string; search_as_of: DateTime | null;
  usability: 'NOT_EVALUATED'; claim_ids: string[]; evidence_ids: string[] };
 epss: { score: number | null; percentile: number | null; date: string | null; model_version: string | null;
  status: 'UNKNOWN' | 'STALE' | 'SOURCE_ASSERTED'; observed_score?: number; raw_document_id?: UUID; snapshot_id?: UUID };
 remediation: Record<string, unknown>; match_explanation: Record<string, unknown>; evidence_refs: Array<Record<string, unknown>>;
 component_revision: number; content_trust_level: 'UNTRUSTED_EXTERNAL_CONTENT';
 dependency_state: Record<string, unknown>; risk_factors: Array<Record<string, unknown>>; factor_codes: string[];
 why_now: string; recommended_action: string; rule_version: string; high_epss_threshold: number;
 match_id: UUID; intelligence_fingerprint: string;
 component_removed?: true; historical_match_status?: string;
}
export type CurrentAssetRisk = LegacyAssetRiskPayload & { snapshot_id: UUID; evaluated_at: DateTime; is_stale: boolean };
export type HistoricalAssetRisk = LegacyAssetRiskPayload & { snapshot_id: UUID; evaluated_at: DateTime; historical: true };
export interface AssetRisksResponse extends Page<CurrentAssetRisk> { coverage: string; }
export type RiskChangeResponse = Page<Enriched<Row.HttpAssetRiskChangeRow>>;
export type InventoryHistoryItem = Omit<Enriched<Row.HttpAssetInventoryEventRow>, 'payload'> & { changes: JsonValue; summary: Record<string, JsonValue> };
export type InventoryHistoryResponse = Page<InventoryHistoryItem>;
export interface SbomImportResponse {
 format: 'CycloneDX' | 'SPDX'; sha256: string; added: number; updated: number; removed: number;
 added_ids: UUID[]; updated_ids: UUID[]; removed_ids: UUID[]; component_count: number;
 content_trust_level: 'UNTRUSTED_EXTERNAL_CONTENT';
}
export type LegacyAssistantState = 'PLANNING' | 'RUNNING' | 'WAITING_TOOL' | 'VERIFYING' | 'REPLANNING'
 | 'WAITING_REVIEW' | 'COMPLETED' | 'FAILED';
export interface LegacyAssistantFullResult {
 route: Record<string, unknown>; plan: LegacyTaskContract[]; artifacts: LegacyTaskArtifact[];
 gate: { status: string; reason: string }; answer: string; facts: Array<Record<string, unknown>>;
 asset_candidates: Array<Record<string, unknown>>; narrative_candidates: Array<Record<string, unknown>>;
 related_vulnerabilities: Array<Record<string, unknown>>; related_assets: Array<Record<string, unknown>>;
 evidence_refs: Array<Record<string, unknown>>; warnings: string[]; unresolved: string[];
 capability: string; coverage: string; human_reviews: Array<Record<string, unknown>>;
}
export interface LegacyAssistantFailureResult { answer: string; warnings: string[]; evidence_refs: Array<Record<string, unknown>>; }
export interface LegacyAssistantRun {
 run_id: UUID; trace_id: UUID; status: LegacyAssistantState; route: Record<string, unknown> | null;
 result: LegacyAssistantFullResult | LegacyAssistantFailureResult | null; warnings: string[];
 started_at: DateTime; finished_at: DateTime | null; duration_ms: number | null;
}
export type LegacyTaskRun = Omit<LegacyTaskContract, 'status'> & Partial<Omit<LegacyTaskArtifact, 'status'>> & {
 status: 'pending' | 'running' | 'success' | 'partial' | 'failed' | 'blocked';
};
export interface LegacyToolTrace {
 id: UUID; tool_name: string; status: 'succeeded' | 'partial' | 'failed' | 'timeout' | 'cancelled';
 sequence_no: number; attempt: number; started_at: DateTime; finished_at: DateTime | null;
 duration_ms: number | null; input_summary: Record<string, unknown>; output_summary: Record<string, unknown>;
 errors: Array<Record<string, unknown>>; evidence_refs: Array<Record<string, unknown>>;
}
export interface LegacyAssistantTrace {
 run_id: UUID; trace_id: UUID; items: LegacyToolTrace[]; events: Array<Record<string, unknown>>; disclosure: string;
}
export interface ToolContractsResponse {
 version: 'ToolContractV3'; content_trust_level: 'UNTRUSTED_EXTERNAL_CONTENT';
 tools: Array<{ name: string; input_schema: Record<string, unknown>; permission: string; category: string; description: string }>;
}
export interface ValidationErrorDetail { loc: Array<string | number>; msg: string; type: string; input?: unknown; ctx?: Record<string, unknown>; }
export interface HttpFailure { detail: string | ValidationErrorDetail[]; }
export type { ToolEnvelope };

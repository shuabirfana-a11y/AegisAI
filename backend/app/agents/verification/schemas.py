"""Execution DTOs, not a second ORM or a model-defined trust protocol."""
from typing import Annotated, Any, Literal
import math
from uuid import UUID
from pydantic import AwareDatetime, Field, StrictBool, model_validator
from app.runtime.contracts import FrozenModel, TaskId, TaskState, ARTIFACT_LIMIT, json_bytes
from app.enrichment.contracts import ClaimType, VerificationStatus
from app.agents.asset_observations import InvestigationArtifactReference, VersionObservation, ImpactVersionEvidence
from app.agents.verification.conflict_evidence import ConflictEvidenceArtifact

RULES_VERSION = 'verification-rules-v1'
SNAPSHOT_LIMIT = 2 * 1024 * 1024
Score = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Hash = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
Identifier = Annotated[str, Field(min_length=1, max_length=200)]
VerificationTaskType = Literal['evidence_verification','claim_validation','conflict_detection']


class Bounded(FrozenModel):
    @model_validator(mode='after')
    def finite_bounded_json(self):
        def check(value):
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError('Finite JSON data required')
            if isinstance(value, dict):
                for item in value.values(): check(item)
            elif isinstance(value, (tuple, list)):
                for item in value: check(item)
        # Pydantic's JSON mode converts an Any-contained NaN to null: inspect first.
        check(self.model_dump(mode='python'))
        json_bytes(self.model_dump(mode='json'), SNAPSHOT_LIMIT)
        return self


class VerificationRequest(Bounded):
    source_run_id: UUID
    source_task_id: TaskId
    source_artifact_id: UUID
    task_type: VerificationTaskType = 'evidence_verification'
    claim_ids: tuple[Identifier, ...] = Field(default=(), max_length=32)
    request_key: str = Field(min_length=1, max_length=150)
    model_assistance: StrictBool = False
    supporting_artifacts: tuple[InvestigationArtifactReference,...] = Field(default=(),max_length=16,exclude_if=lambda v:not v)
    asset_id: UUID | None = Field(None,exclude_if=lambda v:v is None)
    component_id: UUID | None = Field(None,exclude_if=lambda v:v is None)
    supplement_id: UUID | None = Field(None,exclude_if=lambda v:v is None)

    @model_validator(mode='after')
    def unique_selection(self):
        if self.component_id is not None and self.asset_id is None:
            raise ValueError('Component observation requires asset scope')
        refs=[(r.run_id,r.task_id,r.artifact_id) for r in self.supporting_artifacts]
        if len(set(refs))!=len(refs) or any(r.run_id!=self.source_run_id for r in self.supporting_artifacts):
            raise ValueError('Supporting artifacts must be unique and in the source run')
        if len(set(self.claim_ids)) != len(self.claim_ids):
            raise ValueError('Duplicate claim selection')
        if self.task_type == 'claim_validation' and not self.claim_ids:
            raise ValueError('claim_validation requires explicit claim IDs')
        return self


class VerificationClaim(Bounded):
    claim_id: Identifier
    statement: str = Field(min_length=1, max_length=2400)
    claim_type: ClaimType
    source_task_id: TaskId
    related_entities: dict[str, Any] = Field(default_factory=dict)
    status: VerificationStatus = VerificationStatus.PENDING
    value: dict[str, Any]
    scope_key: str = Field(min_length=1, max_length=256)
    vulnerability_id: str = Field(min_length=1, max_length=80)
    package_identifier_id: str | None = None
    branch: str | None = None
    claim_revision: int | None = Field(None, ge=1)
    origin: Literal['stored','derived'] = 'derived'
    source_field: str | None = Field(None, max_length=500)
    evidence_ids: tuple[Identifier, ...] = Field(default=(), max_length=16)


class VerificationEvidence(Bounded):
    evidence_id: Identifier
    claim_id: Identifier
    source_id: UUID | None = None
    source_key: str = Field(default='unknown', max_length=100)
    source_type: str = Field(default='unknown', max_length=80)
    source_name: str = Field(default='Unknown source', max_length=300)
    source_time: AwareDatetime | None = None
    content: str = Field(max_length=2400)
    reference: dict[str, Any]
    hash: Hash | None = None
    authority_score: Score = 0
    directness_score: Score = 0
    authority_level: Literal['official','authoritative','secondary','community'] | None = None
    authority_scope: str | None = Field(None, max_length=2000)
    lineage_key: str | None = Field(None, max_length=1000)
    observation_id: UUID | None = None
    raw_document_id: UUID | None = None
    published_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime | None = None
    excerpt_hash: Hash | None = None
    observed_value: dict[str, Any] = Field(default_factory=dict)
    scope_key: str
    vulnerability_id: str | None = None
    stance: Literal['support','contradict','neutral'] = 'neutral'
    directness: Literal['direct','mention','unknown'] = 'unknown'
    evidence_type: str = 'source_excerpt'
    is_current: bool = False
    integrity_status: Literal['VALID','MISSING','INVALID'] = 'MISSING'
    exclusion_reasons: tuple[str, ...] = ()
    details: dict[str, Any] = Field(default_factory=dict)


class VerificationSourceSnapshot(Bounded):
    supplementary_run_ids: tuple[UUID,...] = Field(default=(),max_length=1,exclude_if=lambda v:not v)
    source_run_id: UUID
    source_task_id: TaskId
    source_artifact_id: UUID
    source_snapshot_as_of: AwareDatetime
    artifact: dict[str, Any]
    receipt_references: tuple[dict[str, Any], ...] = ()
    claims: tuple[VerificationClaim, ...] = Field(default=(), max_length=32)
    evidence: tuple[VerificationEvidence, ...] = Field(default=(), max_length=128)
    omitted_claim_ids: tuple[str, ...] = Field(default=(), max_length=256)
    omitted_claim_count: int = Field(default=0, ge=0)
    omitted_evidence_count: int = Field(default=0, ge=0)
    warnings: tuple[str, ...] = ()
    unresolved_items: tuple[str, ...] = ()
    parent_planner_run_id: str | None = None
    conflict_evidence_artifacts:tuple[ConflictEvidenceArtifact,...]=Field(default=(),max_length=32,exclude_if=lambda v:not v)

    @model_validator(mode='after')
    def conflict_provenance(self):
        if self.conflict_evidence_artifacts:
            from app.agents.verification.conflict_evidence import conflict_artifacts
            if self.conflict_evidence_artifacts!=conflict_artifacts(self.artifact,self.evidence):
                raise ValueError('CONFLICT_ARTIFACT_PROVENANCE_MISMATCH')
        return self
    version_observations: tuple[VersionObservation,...] = Field(default=(),max_length=1,exclude_if=lambda v:not v)
    impact_version_evidence: tuple[ImpactVersionEvidence,...] = Field(default=(),max_length=128,exclude_if=lambda v:not v)


class VerificationContext(Bounded):
    context_id: UUID
    owner: str = Field(min_length=1, max_length=150)
    request: VerificationRequest
    request_hash: Hash
    source_snapshot_hash: Hash
    evaluation_time: AwareDatetime
    rules_version: Literal['verification-rules-v1'] = RULES_VERSION
    snapshot: VerificationSourceSnapshot
    model_identity: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode='after')
    def source_identity(self):
        if (self.request.source_run_id, self.request.source_task_id, self.request.source_artifact_id) != (
            self.snapshot.source_run_id,self.snapshot.source_task_id,self.snapshot.source_artifact_id):
            raise ValueError('Verification source identity mismatch')
        if self.evaluation_time!=self.snapshot.source_snapshot_as_of:
            raise ValueError('Evaluation time must match the sealed source snapshot')
        return self


class VerificationConflict(Bounded):
    conflict_type: str
    claim_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    scope_key: str
    reason: str


class ClaimVerification(Bounded):
    claim: VerificationClaim
    status: VerificationStatus
    confidence: Score
    supporting_evidence_ids: tuple[str, ...] = ()
    conflicting_evidence_ids: tuple[str, ...] = ()
    reason_code: str
    reason_summary: str
    rules_applied: tuple[str, ...] = ()
    score_components: dict[str, Any] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    unresolved_items: tuple[str, ...] = ()


class VerificationAssessment(Bounded):
    claims: tuple[ClaimVerification, ...] = ()
    verification_status: VerificationStatus
    confidence: Score
    supporting_evidence: tuple[VerificationEvidence, ...] = ()
    conflicting_evidence: tuple[VerificationEvidence, ...] = ()
    conflicts: tuple[VerificationConflict, ...] = ()
    warnings: tuple[str, ...] = ()
    unresolved_items: tuple[str, ...] = ()
    partial_result: bool = False
    model_calls: tuple[dict[str, Any], ...] = ()
    model_hints: tuple[dict[str, Any], ...] = ()
    rules_version: Literal['verification-rules-v1'] = RULES_VERSION
    version_observations: tuple[VersionObservation,...] = Field(default=(),max_length=1,exclude_if=lambda v:not v)
    impact_version_evidence: tuple[ImpactVersionEvidence,...] = Field(default=(),max_length=128,exclude_if=lambda v:not v)


class VerificationArtifact(VerificationAssessment):
    artifact_id: UUID
    task_id: TaskId
    run_id: UUID
    agent_id: Literal['verification_agent'] = 'verification_agent'
    schema_version: Literal['verification-artifact-v1'] = 'verification-artifact-v1'
    source_run_id: UUID
    source_artifact_id: UUID
    source_snapshot_hash: Hash
    evaluation_time: AwareDatetime
    execution_status: TaskState = TaskState.WAITING_REVIEW
    tool_calls: tuple[dict[str, Any], ...] = ()

    @model_validator(mode='after')
    def artifact_size(self):
        json_bytes(self.model_dump(mode='json'), ARTIFACT_LIMIT)
        return self


class VerificationRun(Bounded):
    agent_id: Literal['verification_agent'] = 'verification_agent'
    run_id: UUID
    task_id: TaskId
    input_artifact: dict[str, Any]
    output_artifact: UUID | None = None
    claims_checked: tuple[str, ...] = ()
    evidence_used: tuple[str, ...] = ()
    verification_result: VerificationStatus | None = None
    confidence: Score = 0
    execution_time: int = Field(ge=0)
    start_time: AwareDatetime | None = None
    end_time: AwareDatetime | None = None
    status: TaskState
    tools_called: tuple[dict[str, Any], ...] = ()
    rules_version: str = RULES_VERSION


class VerificationRunResult(Bounded):
    run_id: UUID
    runtime_status: str
    artifacts: tuple[VerificationArtifact, ...] = ()
    traces: tuple[VerificationRun, ...] = ()

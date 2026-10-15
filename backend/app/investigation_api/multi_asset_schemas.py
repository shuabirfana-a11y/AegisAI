"""Bounded batch transport; execution coverage is separate from child verdicts."""
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, StrictInt, field_validator
from app.investigation_api.schemas import PublicModel
from app.tooling.contracts import Target
from app.agents.analysis.schemas import RiskLevel, Priority
from app.integration.contracts import Status, ArtifactRef
from app.orchestration.answer_contracts import Citation, EvidenceObservation, ActionView


class BatchRequest(PublicModel):
    vulnerability_id: Target
    asset_ids: tuple[UUID,...] = Field(min_length=1,max_length=100)
    timeout_seconds: StrictInt = Field(900,ge=1,le=1500)
    child_timeout_seconds: StrictInt = Field(300,ge=1,le=300)
    idempotency_key: str | None = Field(None,min_length=1,max_length=150)

    @field_validator('vulnerability_id',mode='before')
    @classmethod
    def canonical_id(cls,value):
        return str(value).strip().upper() if str(value).strip().upper().startswith('CVE-') else str(value).strip().lower()


class InventoryComponent(PublicModel):
    component_id: UUID
    product_id: UUID | None = None
    package_identifier_id: UUID | None = None
    name: str | None = None
    package_name: str | None = None
    ecosystem: str = 'unknown'
    namespace: str = ''
    purl: str | None = None
    version: str | None = None
    inventory_revision: int = Field(ge=1)
    source: str
    identity_status: str


class BatchSnapshot(PublicModel):
    asset_id: UUID
    asset_name: str
    captured_at: AwareDatetime
    inventory_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    environment: str = 'unknown'
    exposure: str = 'unknown'
    criticality: Literal['unknown'] = 'unknown'
    is_demo: bool = False
    components: tuple[InventoryComponent,...] = Field(default=(),max_length=100)
    selected_component_id: UUID | None = None
    provenance: Literal['USER_INVENTORY_NOT_SCANNED'] = 'USER_INVENTORY_NOT_SCANNED'


class CandidateRelations(PublicModel):
    node_ids: tuple[str,...] = ()
    edge_ids: tuple[str,...] = ()
    warnings: tuple[str,...] = ()
    truncated: bool = False
    meaning: Literal['CANDIDATE_RELATIONS_NOT_IMPACT_PROOF'] = 'CANDIDATE_RELATIONS_NOT_IMPACT_PROOF'


ItemExecution=Literal['NOT_STARTED','RUNNING','COMPLETED','NEED_CONTEXT','FAILED','NOT_EXECUTED']
BatchExecution=Literal['QUEUED','RUNNING','CANCEL_REQUESTED','COMPLETED','CANCELLED','TIMED_OUT','FAILED']


class BatchItem(PublicModel):
    snapshot: BatchSnapshot
    relations: CandidateRelations = Field(default_factory=CandidateRelations)
    execution_status: ItemExecution = 'NOT_STARTED'
    child_request_key: str | None = None
    investigation_id: UUID | None = None
    planner_run_id: UUID | None = None
    artifact_references: tuple[ArtifactRef,...] = ()
    integration_result_id: UUID | None = None
    answer_id: UUID | None = None
    gate_status: Status | None = None
    verification_status: str | None = None
    impact: Literal['AFFECTED','NOT_AFFECTED','UNKNOWN'] = 'UNKNOWN'
    risk_level: RiskLevel = 'UNKNOWN'
    priority: Priority = 'REVIEW_REQUIRED'
    evidence_ids: tuple[str,...] = ()
    claim_ids: tuple[str,...] = ()
    citations: tuple[Citation,...] = ()
    evidence_observations: tuple[EvidenceObservation,...] = ()
    recommended_actions: tuple[ActionView,...] = ()
    missing_fields: tuple[str,...] = ()
    unresolved_items: tuple[str,...] = ()
    warnings: tuple[str,...] = ()
    error_code: str | None = None
    snapshot_valid: bool = True
    evaluation_time: AwareDatetime | None = None
    historical_snapshot: Literal[True] = True
    current_safety_evaluated: Literal[False] = False


class BatchSummary(PublicModel):
    counts: dict[str,int]
    actionable_asset_ids: tuple[UUID,...]
    unresolved_asset_ids: tuple[UUID,...]
    unaffected_asset_ids: tuple[UUID,...]
    sorting_rule: Literal['EXISTING_PRIORITY_THEN_ASSET_UUID'] = 'EXISTING_PRIORITY_THEN_ASSET_UUID'
    scope_notice: str = '仅评价指定漏洞与固定库存快照；未知、失败和未执行不表示安全。'


class BatchResponse(PublicModel):
    schema_version: Literal['multi-asset-batch-v1'] = 'multi-asset-batch-v1'
    batch_id: UUID
    vulnerability_id: str
    execution_status: BatchExecution
    items: tuple[BatchItem,...]
    summary: BatchSummary
    created_at: AwareDatetime
    updated_at: AwareDatetime
    deadline_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    cancel_requested_at: AwareDatetime | None = None
    cancellation_observed: bool = False
    recovery_required: bool = False
    reused: bool = False
    duplicate_asset_count: int = 0
    warnings: tuple[str,...] = ()
    max_assets: int
    model_provider: str
    model_name: str
    execution_mode: Literal['MOCK','REAL']
    revision: int = 0


class BatchRecord(PublicModel):
    owner: str
    request_key: str
    request_hash: str
    request: BatchRequest
    response: BatchResponse

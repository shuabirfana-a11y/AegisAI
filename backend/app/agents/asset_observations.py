"""Immutable observed inventory and source-bound impact references, never verdicts."""
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, Field
from app.runtime.contracts import FrozenModel, TaskId


class InvestigationArtifactReference(FrozenModel):
    run_id: UUID
    task_id: TaskId
    artifact_id: UUID


class VersionObservation(FrozenModel):
    id: UUID
    type: Literal['VERSION_OBSERVATION'] = 'VERSION_OBSERVATION'
    asset_id: UUID
    component_id: UUID
    asset_name: str = Field(max_length=200)
    component: str = Field(max_length=300)
    version: str | None = Field(None,max_length=200)
    package_identifier_id: str | None = None
    package_name: str | None = None
    ecosystem: str = 'unknown'
    namespace: str = ''
    purl: str | None = None
    environment: Literal['production','staging','development','unknown'] = 'unknown'
    exposure: Literal['internet','internal','development','unknown'] = 'unknown'
    criticality: Literal['unknown'] = 'unknown'
    inventory_revision: int = Field(ge=1)
    asset_updated_at: AwareDatetime
    component_updated_at: AwareDatetime
    source: Literal['OWNER_INVENTORY_NOT_SCANNED'] = 'OWNER_INVENTORY_NOT_SCANNED'
    created_at: AwareDatetime
    source_artifact: InvestigationArtifactReference
    receipt_id: UUID
    receipt_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    is_demo: bool


class ImpactVersionEvidence(FrozenModel):
    id: str = Field(min_length=1,max_length=200)
    type: Literal['IMPACT_VERSION_EVIDENCE'] = 'IMPACT_VERSION_EVIDENCE'
    vulnerability_id: str
    package_identifier_id: str | None = None
    claim_id: str
    affected_versions: tuple[dict,...] = ()
    fixed_versions: tuple[dict,...] = ()
    evidence_ids: tuple[str,...] = ()
    source: str
    reference: dict
    raw_document_id: UUID | None = None
    observation_id: UUID | None = None
    hash: str | None = None
    status: Literal['CONFIRMED','PENDING','CONFLICT','INSUFFICIENT_EVIDENCE','REJECTED'] = 'PENDING'

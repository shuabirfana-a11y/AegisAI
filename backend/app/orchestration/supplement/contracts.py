from typing import Literal
from uuid import UUID
from pydantic import Field, AwareDatetime, ConfigDict
from app.integration.contracts import Sized, ArtifactRef
from app.orchestration.contracts import InvestigationContext, InvestigationResult

VERSION='evidence-supplement-v1'
TYPE='evidence-supplement-v1'
NS='evidence_supplement_v1'
State=Literal['DISABLED','NOT_ELIGIBLE','RUNNING','VERIFYING','ANALYZING','INTEGRATING','COMPLETED','STOPPED','CANCELLED','FAILED']
TERMINAL=frozenset({'DISABLED','NOT_ELIGIBLE','COMPLETED','STOPPED','CANCELLED','FAILED'})

class SupplementToolCall(Sized):
    record_id: UUID
    tool: Literal['get_evidence']
    status: Literal['succeeded','partial','failed','timeout','cancelled']
    evidence_ids: tuple[UUID,...]=Field(default=(),max_length=16)

class SupplementSummary(Sized):
    policy_version: Literal['evidence-supplement-v1']=VERSION
    supplement_id: UUID|None=None
    parent_investigation_id: UUID
    parent_integration_id: UUID|None=None
    status: State
    eligible: bool=False
    reason: str=Field(max_length=100)
    claim_ids: tuple[str,...]=Field(default=(),max_length=3)
    acquisition_run_id: UUID|None=None
    acquisition_artifact: ArtifactRef|None=None
    new_evidence_ids: tuple[str,...]=Field(default=(),max_length=48)
    resolved_claim_ids: tuple[str,...]=Field(default=(),max_length=3)
    extra_acquisition_calls: int=Field(default=0,ge=0,le=3)
    extra_model_calls: Literal[0]=0
    extra_total_tool_calls: int=Field(default=0,ge=0,le=5)
    latest_result_version: Literal[1,2]=1
    result_version: Literal[1,2]=1
    cancel_requested: bool=False
    recovery_required: bool=False
    error_code: str|None=Field(None,max_length=100)
    heartbeat_at: AwareDatetime|None=None
    started_at: AwareDatetime|None=None
    finished_at: AwareDatetime|None=None
    deadline_at: AwareDatetime|None=None
    tool_calls: tuple[SupplementToolCall,...]=Field(default=(),max_length=3)

class SupplementSpec(Sized):
    parent_investigation_id: UUID
    parent_integration_id: UUID
    parent_gate_hash: str
    source_artifact: ArtifactRef
    supporting_artifacts: tuple[ArtifactRef,...]=()
    target: str
    claim_ids: tuple[str,...]=Field(min_length=1,max_length=3)
    inventory_hash: str
    gap_hash: str
    batch_id: UUID|None=None

class SupplementRecord(Sized):
    model_config=ConfigDict(extra='forbid',frozen=False,validate_assignment=True,hide_input_in_errors=True)
    size_limit=4*1024*1024
    summary: SupplementSummary
    spec: SupplementSpec
    original: InvestigationResult
    context: InvestigationContext
    result: InvestigationResult|None=None
    worker_token: UUID=Field(exclude=True,repr=False)
    revision: int=0

class SupplementView(Sized):
    size_limit=4*1024*1024
    summary: SupplementSummary
    result: InvestigationResult

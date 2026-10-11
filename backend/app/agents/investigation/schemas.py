from typing import Literal
from uuid import UUID
from datetime import datetime
from pydantic import Field, model_validator
from app.runtime.contracts import FrozenModel, TaskId, TaskState, ARTIFACT_LIMIT, json_bytes

InvestigationStatus = Literal['COMPLETE','PARTIAL','CONFLICT','INSUFFICIENT_EVIDENCE']
InformationStatus = Literal['CONFIRMED','CANDIDATE','CONFLICT','INSUFFICIENT_EVIDENCE']

class InvestigationArtifact(FrozenModel):
    artifact_id: UUID
    task_id: TaskId
    agent_id: Literal['investigation_agent'] = 'investigation_agent'
    run_id: UUID
    schema_version: Literal['investigation-artifact-v1'] = 'investigation-artifact-v1'
    status: InvestigationStatus
    runtime_status: TaskState
    partial_result: bool = False
    information_status: InformationStatus = 'CANDIDATE'
    vulnerability_id: str | None = None
    canonical_id: str | None = None
    description: str | None = None
    component: dict | None = None
    asset: dict | None = None
    affected_versions: list[dict] = Field(default_factory=list)
    fixed_versions: list[dict] = Field(default_factory=list)
    version_match: dict | None = None
    cvss: list[dict] = Field(default_factory=list)
    cwe: list[dict] = Field(default_factory=list)
    poc_candidates: list[dict] = Field(default_factory=list)
    patch_information: list[dict] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    conflicts: list[dict] = Field(default_factory=list)
    confidence: float | None = Field(None,ge=0,le=1,allow_inf_nan=False)
    failed_tools: list[dict] = Field(default_factory=list)
    tool_calls: list[dict] = Field(default_factory=list)
    dependency_artifact_ids: tuple[str,...] = ()
    evidence_storage: Literal['artifact','tool_receipts'] = 'artifact'
    receipt_references: dict = Field(default_factory=dict)
    findings: list[dict] = Field(default_factory=list)

    @model_validator(mode='after')
    def bounded(self):
        json_bytes(self.model_dump(mode='python',exclude={'artifact_id','run_id'}),ARTIFACT_LIMIT)
        json_bytes(self.model_dump(mode='json'),ARTIFACT_LIMIT)
        return self

class InvestigationTaskTrace(FrozenModel):
    agent_id: Literal['investigation_agent']='investigation_agent'
    task_id: TaskId
    tools_called:list[dict]=Field(default_factory=list)
    start_time:datetime|None=None
    end_time:datetime|None=None
    status:TaskState
    artifact_id:UUID|None=None
    attempted:bool

class InvestigationRunResult(FrozenModel):
    run_id: UUID
    runtime_status: str
    artifacts: tuple[InvestigationArtifact,...]
    blocked_tasks: tuple[str,...] = ()
    input_required_tasks:tuple[str,...]=()
    traces:tuple[InvestigationTaskTrace,...]=()

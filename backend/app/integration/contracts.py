"""Versioned Gate protocol. Client input contains references, never business artifacts."""
from datetime import datetime
import math
from typing import Annotated, Any, Literal, ClassVar
from uuid import UUID
from pydantic import AwareDatetime, Field, model_validator
from app.runtime.contracts import FrozenModel, TaskId, TaskState, json_bytes
from app.agents.investigation.schemas import InvestigationArtifact
from app.agents.verification.schemas import VerificationArtifact, VerificationSourceSnapshot
from app.agents.analysis.schemas import RiskAnalysisArtifact, AssetContextSnapshot

POLICY_VERSION='integration-policy-v1'
Hash=Annotated[str,Field(pattern=r'^[a-f0-9]{64}$')]
Profile=Literal['overview_v1','asset_impact_v1','asset_risk_v1']
Outcome=Literal['identity','overview','asset','version_impact','remediation_status','precise_remediation','risk','priority','verified_exploitation']
Status=Literal['PASS','PASS_WITH_WARNINGS','REPLAN_REQUIRED','HUMAN_REVIEW_REQUIRED','FAILED']

class Sized(FrozenModel):
    size_limit: ClassVar[int]=64*1024
    @model_validator(mode='after')
    def finite_size(self):
        def finite(v):
            if isinstance(v,float) and not math.isfinite(v):raise ValueError('Finite JSON required')
            if isinstance(v,dict):
                for i in v.values():finite(i)
            if isinstance(v,(tuple,list)):
                for i in v:finite(i)
        finite(self.model_dump(mode='python'))
        json_bytes(self.model_dump(mode='json'),self.size_limit)
        return self

class ArtifactRef(Sized):
    run_id: UUID
    task_id: TaskId
    artifact_id: UUID
    schema_version: Literal['investigation-artifact-v1','verification-artifact-v1','risk-analysis-artifact-v1']

class ObjectiveContract(Sized):
    question: str=Field(min_length=1,max_length=2000)
    targets: tuple[str,...]=Field(default=(),max_length=3)
    asset_id: UUID|None=None
    component_id: UUID|None=None
    package_name: str|None=Field(None,max_length=300)
    version: str|None=Field(None,max_length=100)
    required_outcomes: tuple[Outcome,...]=Field(default=('identity','overview'),min_length=1,max_length=9)
    window_days: int|None=Field(None,ge=1,le=365)
    requires_current: bool=False
    scope_gaps: tuple[str,...]=()
    @model_validator(mode='after')
    def unique(self):
        if len(set(self.targets))!=len(self.targets) or len(set(self.required_outcomes))!=len(self.required_outcomes):raise ValueError('Duplicate scope')
        if self.component_id and not self.asset_id:raise ValueError('Component requires asset')
        return self

class OptionalTask(Sized):
    run_id: UUID
    task_id: TaskId

class IntegrationRequest(Sized):
    request_key: str=Field(min_length=1,max_length=150)
    run_id: UUID|None=None
    planner_run_id: UUID|None=None
    objective_source: Literal['stored_planner_request','new_structured_request']='stored_planner_request'
    objective_profile: Profile='asset_impact_v1'
    explicit_objective: ObjectiveContract|None=None
    investigation: ArtifactRef|None=None
    verification: ArtifactRef|None=None
    analysis: ArtifactRef|None=None
    optional_tasks: tuple[OptionalTask,...]=Field(default=(),max_length=16)
    policy_version: Literal['integration-policy-v1']=POLICY_VERSION
    @model_validator(mode='after')
    def references(self):
        if not self.request_key.strip():raise ValueError('Nonblank request key required')
        if (self.objective_source=='new_structured_request')!=(self.explicit_objective is not None):raise ValueError('Explicit objective only for new request')
        refs=[r for r in (self.investigation,self.verification,self.analysis) if r]
        if len({r.artifact_id for r in refs})!=len(refs):raise ValueError('Duplicate artifact')
        for ref,schema in zip((self.investigation,self.verification,self.analysis),('investigation-artifact-v1','verification-artifact-v1','risk-analysis-artifact-v1')):
            if ref and ref.schema_version!=schema:raise ValueError('Artifact schema does not match stage')
        if len({(r.run_id,r.task_id) for r in self.optional_tasks})!=len(self.optional_tasks):raise ValueError('Duplicate optional task')
        return self

class TaskExecution(Sized):
    run_id: UUID
    task_id: TaskId
    semantic_type: str
    status: TaskState
    run_status: str
    required: bool=True
    dependencies: tuple[TaskId,...]=()
    error_codes: tuple[str,...]=()

class GateCheck(Sized):
    gate: Literal['completion','integrity','evidence','consistency','objective','freshness']
    code: str=Field(min_length=1,max_length=100)
    outcome: Literal['PASS','WARNING','BLOCKED','ERROR','NOT_APPLICABLE']='PASS'
    blocking: Literal['NONE','REPLAN','HUMAN','FATAL']='NONE'
    message: str=Field(max_length=2000)
    refs: tuple[str,...]=Field(default=(),max_length=256)
    objective: Outcome|None=None

class IntegrationContext(Sized):
    size_limit: ClassVar[int]=4*1024*1024
    integration_id: UUID
    logical_investigation_id: UUID
    owner: str=Field(min_length=1,max_length=150)
    request: IntegrationRequest
    objective: ObjectiveContract|None=None
    objective_hash: Hash
    evaluation_time: AwareDatetime
    investigation: InvestigationArtifact|None=None
    verification: VerificationArtifact|None=None
    analysis: RiskAnalysisArtifact|None=None
    verification_source: VerificationSourceSnapshot|None=None
    asset_snapshot: AssetContextSnapshot|None=None
    tasks: tuple[TaskExecution,...]=Field(default=(),max_length=48)
    source_run_ids: tuple[UUID,...]=Field(default=(),max_length=3)
    source_fingerprints: dict[str,Hash]=Field(default_factory=dict)
    trace_references: tuple[str,...]=Field(default=(),max_length=5)
    capture_checks: tuple[GateCheck,...]=Field(default=(),max_length=32)
    input_hash: Hash
    policy_version: Literal['integration-policy-v1']=POLICY_VERSION

class ObjectiveCoverage(Sized):
    outcome: Outcome
    status: Literal['SATISFIED','ABSTAINED','MISSING','CONFLICT']
    references: tuple[str,...]=()

class IntegrationResult(Sized):
    size_limit: ClassVar[int]=512*1024
    integration_id: UUID
    logical_investigation_id: UUID
    trace_id: UUID
    run_id: UUID|None=None
    source_run_ids: tuple[UUID,...]=()
    status: Status
    objective_coverage: tuple[ObjectiveCoverage,...]=()
    task_completion_summary: tuple[TaskExecution,...]=()
    checks: tuple[GateCheck,...]
    passed_checks: tuple[str,...]=()
    failed_checks: tuple[str,...]=()
    blocking_issues: tuple[str,...]=()
    warnings: tuple[str,...]=()
    unresolved_items: tuple[str,...]=()
    artifact_references: tuple[ArtifactRef,...]=()
    evidence_references: tuple[dict[str,Any],...]=Field(default=(),max_length=128)
    replan_reasons: tuple[str,...]=()
    human_review_reasons: tuple[str,...]=()
    final_result_references: tuple[ArtifactRef,...]=()
    partial_result_references: tuple[ArtifactRef,...]=()
    input_hash: Hash
    objective_hash: Hash
    policy_version: Literal['integration-policy-v1']=POLICY_VERSION
    created_at: AwareDatetime
    evaluation_time: AwareDatetime
    historical_snapshot: Literal[True]=True
    persistence: Literal['STORED','NOT_STORED']='STORED'

class IntegrationTrace(Sized):
    size_limit: ClassVar[int]=8*1024*1024
    integration_id: UUID
    logical_investigation_id: UUID
    source_run_ids: tuple[UUID,...]
    artifact_references: tuple[ArtifactRef,...]
    rule_version: str
    checks: tuple[GateCheck,...]
    evidence_references: tuple[dict[str,Any],...]
    status: Status
    blocking_issues: tuple[str,...]
    execution_time_ms: int=Field(ge=0)
    error_codes: tuple[str,...]=()

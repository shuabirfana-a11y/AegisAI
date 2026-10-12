"""Bounded analysis views; source artifacts and verification statuses are immutable inputs."""
from typing import Any, Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, StrictBool, model_validator
from app.runtime.contracts import TaskId, TaskState, ARTIFACT_LIMIT, json_bytes
from app.agents.verification.schemas import Bounded, Score, Hash, VerificationClaim, VerificationArtifact
from app.agents.investigation.schemas import InvestigationArtifact
from app.enrichment.contracts import VerificationStatus

RULES_VERSION='analysis-rules-v1'
AnalysisTaskType=Literal['risk_analysis','asset_impact_analysis','remediation_prioritization']
RiskLevel=Literal['CRITICAL','HIGH','MEDIUM','LOW','UNKNOWN']
Priority=Literal['P0','P1','P2','P3','DEFER','REVIEW_REQUIRED']


class AnalysisRequest(Bounded):
    investigation_run_id: UUID
    investigation_task_id: TaskId
    investigation_artifact_id: UUID
    verification_run_id: UUID
    verification_task_id: TaskId
    verification_artifact_id: UUID
    asset_id: UUID | None = None
    component_id: UUID | None = None
    task_type: AnalysisTaskType = 'risk_analysis'
    request_key: str = Field(min_length=1,max_length=150)
    model_assistance: StrictBool = False

    @model_validator(mode='after')
    def scope(self):
        if not self.request_key.strip():raise ValueError('Nonblank request key required')
        if self.component_id is not None and self.asset_id is None:raise ValueError('Component requires asset')
        return self


class AssetContextSnapshot(Bounded):
    asset_id: UUID | None = None
    component_id: UUID | None = None
    component: str | None = Field(None,max_length=300)
    package_identifier_id: str | None = None
    package_name: str | None = None
    ecosystem: str = 'unknown'
    namespace: str = ''
    purl: str | None = None
    deployed_version: str | None = None
    inventory_revision: int | None = Field(None,ge=1)
    asset_updated_at: AwareDatetime | None = None
    component_updated_at: AwareDatetime | None = None
    captured_at: AwareDatetime
    environment: Literal['production','staging','development','unknown'] = 'unknown'
    exposure: Literal['internet','internal','development','unknown'] = 'unknown'
    criticality: Literal['unknown'] = 'unknown'
    is_demo: bool = False
    context_status: Literal['RESOLVED','MISSING','AMBIGUOUS','UNRESOLVED','LIMITED'] = 'MISSING'
    unresolved_items: tuple[str,...] = ()
    provenance: Literal['USER_INVENTORY_NOT_SCANNED'] = 'USER_INVENTORY_NOT_SCANNED'
    asset_name: str | None = Field(None,max_length=200,exclude_if=lambda v:v is None)
    version_observation_id: UUID | None = Field(None,exclude_if=lambda v:v is None)


class AnalysisInputs(Bounded):
    investigation: InvestigationArtifact
    verification: VerificationArtifact
    asset: AssetContextSnapshot
    source_claims: tuple[VerificationClaim,...] = Field(default=(),max_length=32)
    source_verification_task: Literal['evidence_verification','claim_validation','conflict_detection']
    source_snapshot_hash: Hash
    receipt_references: tuple[dict[str,Any],...] = ()
    coverage_complete: bool = True
    omitted_claim_count: int = Field(0,ge=0)
    omitted_evidence_count: int = Field(0,ge=0)
    epss: tuple[dict[str,Any],...] = Field(default=(),max_length=10)
    warnings: tuple[str,...] = ()

    @model_validator(mode='after')
    def handoff(self):
        i=self.investigation;v=self.verification
        if (v.source_run_id,v.source_artifact_id)!=(i.run_id,i.artifact_id):raise ValueError('Analysis handoff mismatch')
        if v.source_snapshot_hash!=self.source_snapshot_hash:raise ValueError('Source snapshot hash mismatch')
        return self


class AnalysisContext(Bounded):
    context_id: UUID
    owner: str = Field(min_length=1,max_length=150)
    request: AnalysisRequest
    request_hash: Hash
    input_snapshot_hash: Hash
    evaluation_time: AwareDatetime
    inputs: AnalysisInputs
    rules_version: Literal['analysis-rules-v1'] = RULES_VERSION
    priority_rule_version: Literal['asset-priority-v1'] = 'asset-priority-v1'
    model_identity: dict[str,str] = Field(default_factory=dict)

    @model_validator(mode='after')
    def identities(self):
        r=self.request;i=self.inputs.investigation;v=self.inputs.verification
        if (r.investigation_run_id,r.investigation_task_id,r.investigation_artifact_id)!=(i.run_id,i.task_id,i.artifact_id):
            raise ValueError('Investigation identity mismatch')
        if (r.verification_run_id,r.verification_task_id,r.verification_artifact_id)!=(v.run_id,v.task_id,v.artifact_id):
            raise ValueError('Verification identity mismatch')
        if self.inputs.asset.asset_id!=r.asset_id:raise ValueError('Asset identity mismatch')
        if r.component_id is not None and self.inputs.asset.component_id!=r.component_id:raise ValueError('Component identity mismatch')
        return self


class AssetMatchResult(Bounded):
    status: Literal['MATCHED','NOT_MATCHED','UNKNOWN'] = 'UNKNOWN'
    reason: str = 'Asset identity is unresolved'
    claim_ids: tuple[str,...] = ()
    package_identifier_id: str | None = None


class VersionMatchResult(Bounded):
    status: Literal['AFFECTED','NOT_AFFECTED','UNKNOWN'] = 'UNKNOWN'
    affected: StrictBool | None = None
    reason: str = 'Version impact is unresolved'
    claim_ids: tuple[str,...] = ()
    comparisons: tuple[dict[str,Any],...] = ()
    normalization: dict[str,Any] = Field(default_factory=dict)


class RiskFactor(Bounded):
    factor_id: str = Field(min_length=1,max_length=150)
    code: str
    reason: str = Field(max_length=2400)
    value: Any = None
    claim_ids: tuple[str,...] = ()
    evidence_ids: tuple[str,...] = ()
    provenance: Literal['verified_claim','asset_inventory','candidate','source_assertion']
    influences_decision: bool = False
    rejected_reason: str | None = None


class RecommendedAction(Bounded):
    action_id: str = Field(min_length=1,max_length=150)
    action_type: str
    category: Literal['IMMEDIATE','FURTHER_INVESTIGATION','LONG_TERM_HARDENING']
    summary: str = Field(max_length=2400)
    target_component: str | None = None
    fixed_version: str | None = None
    patch_reference: str | None = None
    claim_ids: tuple[str,...] = ()
    evidence_ids: tuple[str,...] = ()
    preconditions: tuple[str,...] = ()
    action_provenance: Literal['VERIFIED_CLAIM','GENERAL_PRECAUTION']
    applicability: Literal['CONFIRMED','UNKNOWN','NOT_APPLICABLE'] = 'UNKNOWN'


class ExploitationSignal(Bounded):
    status: Literal['KNOWN_EXPLOITED','VERIFIED_POC_ASSOCIATION','POC_CANDIDATE','UNKNOWN'] = 'UNKNOWN'
    usability: Literal['NOT_EVALUATED'] = 'NOT_EVALUATED'
    claim_ids: tuple[str,...] = ()
    evidence_ids: tuple[str,...] = ()
    epss: tuple[dict[str,Any],...] = ()


class PatchAvailability(Bounded):
    status: Literal['CONFIRMED_PRESENT','UNCONFIRMED','UNKNOWN'] = 'UNKNOWN'
    claim_ids: tuple[str,...] = ()
    evidence_ids: tuple[str,...] = ()
    applied: Literal['UNKNOWN'] = 'UNKNOWN'
    applicability: Literal['CONFIRMED','UNKNOWN'] = 'UNKNOWN'


class RiskAssessment(Bounded):
    verification_status: VerificationStatus
    asset_id: UUID | None = None
    component: str | None = None
    version: str | None = None
    asset_match_status: Literal['MATCHED','NOT_MATCHED','UNKNOWN'] = 'UNKNOWN'
    version_match_status: Literal['AFFECTED','NOT_AFFECTED','UNKNOWN'] = 'UNKNOWN'
    asset_match_result: AssetMatchResult = Field(default_factory=AssetMatchResult)
    version_match_result: VersionMatchResult = Field(default_factory=VersionMatchResult)
    exploitation_signal: ExploitationSignal = Field(default_factory=ExploitationSignal)
    patch_availability: PatchAvailability = Field(default_factory=PatchAvailability)
    risk_level: RiskLevel = 'UNKNOWN'
    priority: Priority = 'REVIEW_REQUIRED'
    affected: StrictBool | None = None
    risk_factors: tuple[RiskFactor,...] = Field(default=(),max_length=128)
    mitigating_factors: tuple[RiskFactor,...] = Field(default=(),max_length=128)
    recommended_actions: tuple[RecommendedAction,...] = Field(default=(),max_length=32)
    evidence_refs: tuple[dict[str,Any],...] = Field(default=(),max_length=128)
    reasoning_summary: str = Field(default='依据不足，需要复核；未知不等于不受影响。',max_length=8000)
    claim_dispositions: tuple[dict[str,Any],...] = Field(default=(),max_length=32)
    confidence: Score = 0
    confidence_kind: Literal['uncalibrated_heuristic'] = 'uncalibrated_heuristic'
    warnings: tuple[str,...] = ()
    unresolved_items: tuple[str,...] = ()
    rule_ids: tuple[str,...] = ('R0_ABSTAIN',)
    rules_version: Literal['analysis-rules-v1'] = RULES_VERSION
    priority_details: dict[str,Any] = Field(default_factory=dict)
    partial_result: bool = False
    coverage_complete: bool = True
    model_assist_used: bool = False
    model_assist_status: Literal['DISABLED','SUCCEEDED','FAILED','SKIPPED'] = 'DISABLED'
    model_calls: tuple[dict[str,Any],...] = ()

    @model_validator(mode='after')
    def decision_gate(self):
        if self.verification_status!=VerificationStatus.CONFIRMED and (
            self.affected is not None or self.risk_level!='UNKNOWN' or self.priority!='REVIEW_REQUIRED'):
            raise ValueError('Unverified facts cannot determine impact or risk')
        if self.partial_result or not self.coverage_complete:
            if self.affected is not None or self.risk_level!='UNKNOWN' or self.priority!='REVIEW_REQUIRED':
                raise ValueError('Incomplete result must abstain')
        if self.risk_level=='UNKNOWN' and self.priority!='REVIEW_REQUIRED':raise ValueError('Unknown risk requires review')
        if self.risk_level in ('CRITICAL','HIGH','MEDIUM') and (
            self.asset_match_status!='MATCHED' or self.version_match_status!='AFFECTED' or self.affected is not True):
            raise ValueError('Risk requires confirmed asset/version impact')
        if self.risk_level=='LOW' and (self.affected is not False or self.priority!='DEFER' or
            not (self.asset_match_status=='NOT_MATCHED' or self.version_match_status=='NOT_AFFECTED')):
            raise ValueError('Low risk requires explicit scoped non-impact')
        return self


class RiskAnalysisArtifact(RiskAssessment):
    artifact_id: UUID
    task_id: TaskId
    agent_id: Literal['security_analysis_agent'] = 'security_analysis_agent'
    run_id: UUID
    schema_version: Literal['risk-analysis-artifact-v1'] = 'risk-analysis-artifact-v1'
    context_id: UUID
    input_artifact_ids: tuple[UUID,...]
    input_snapshot_hash: Hash
    evaluation_time: AwareDatetime
    source_verification_time: AwareDatetime
    inventory_revision: int | None = None
    execution_status: TaskState
    tool_calls: tuple[dict[str,Any],...] = ()
    historical_snapshot: Literal[True] = True
    scope_notice: str = '仅针对本次固定漏洞、所选组件和库存版本；不表示整个资产实时安全。'

    @model_validator(mode='after')
    def artifact_size(self):
        json_bytes(self.model_dump(mode='json'),ARTIFACT_LIMIT)
        return self


class AnalysisRun(Bounded):
    agent_id: Literal['security_analysis_agent'] = 'security_analysis_agent'
    run_id: UUID
    task_id: TaskId
    actor: str
    input_artifact_ids: tuple[UUID,...]
    input_snapshot_hash: Hash
    asset_match_result: AssetMatchResult
    version_match_result: VersionMatchResult
    verification_status: VerificationStatus
    claim_dispositions: tuple[dict[str,Any],...] = ()
    risk_factors: tuple[RiskFactor,...] = ()
    mitigating_factors: tuple[RiskFactor,...] = ()
    risk_level: RiskLevel
    priority: Priority
    rule_ids: tuple[str,...]
    model_assist_used: bool
    model_assist_status: str
    output_artifact_id: UUID
    execution_time: int = Field(ge=0)
    start_time: AwareDatetime | None = None
    end_time: AwareDatetime | None = None
    status: TaskState
    tools_called: tuple[dict[str,Any],...] = ()


class AnalysisRunResult(Bounded):
    run_id: UUID
    runtime_status: str
    artifacts: tuple[RiskAnalysisArtifact,...] = ()
    traces: tuple[AnalysisRun,...] = ()

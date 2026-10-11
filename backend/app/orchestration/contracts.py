"""Versioned upper protocol, separate from Runtime and business decision states."""
from typing import Literal, ClassVar
from uuid import UUID, uuid4
from pydantic import AwareDatetime, Field, StrictInt, model_validator
from app.agents.contracts import fingerprint
from app.integration.contracts import Sized, ObjectiveContract, ArtifactRef, Profile
from app.planner.schemas import PlannerInput
from app.utils.time import utcnow
from app.orchestration.answer_contracts import AnswerEnvelope

Stage = Literal['CREATED','PLANNING','INVESTIGATING','VERIFYING','ANALYZING',
                'INTEGRATING','COMPOSING','COMPLETED','WAITING_REVIEW','FAILED','CANCELLED']
Overall = Literal['RUNNING','SUCCEEDED','SUCCEEDED_WITH_WARNINGS','INCOMPLETE',
                  'REVIEW_REQUIRED','FAILED','CANCELLED']
TERMINAL_STAGES = frozenset({'COMPLETED','WAITING_REVIEW','FAILED','CANCELLED'})
TYPE = 'investigation-orchestrator-v1'
NAMESPACE = 'orchestration_v1'


def valid_actor(actor):
    if not isinstance(actor,str) or not actor.strip() or len(actor)>150:
        raise ValueError('AUTHENTICATED_ACTOR_REQUIRED')
    return actor


class TimeScope(Sized):
    window_days: StrictInt | None = Field(None,ge=1,le=365)
    requires_current: bool = False


class UserContext(Sized):
    display_language: Literal['zh-CN'] = 'zh-CN'
    notes: str = Field(default='',max_length=1000)


class InvestigationOptions(Sized):
    objective_profile: Profile | None = None
    timeout_seconds: StrictInt = Field(default=300,ge=1,le=300)


class InvestigationRequest(Sized):
    schema_version: Literal['investigation-request-v1'] = 'investigation-request-v1'
    request_id: UUID = Field(default_factory=uuid4)
    planner_input: PlannerInput
    time_scope: TimeScope | None = None
    user_context: UserContext = Field(default_factory=UserContext)
    investigation_options: InvestigationOptions = Field(default_factory=InvestigationOptions)

    @model_validator(mode='after')
    def key_required(self):
        key=self.planner_input.query.request_key
        if not isinstance(key,str) or not key.strip():raise ValueError('IDEMPOTENCY_KEY_REQUIRED')
        return self

    @property
    def request_key(self):return self.planner_input.query.request_key

    @property
    def user_query(self):return self.planner_input.query.question


def capture_request(request):
    if isinstance(request,InvestigationRequest):
        # model_copy(update=...) and nested mutable models must not bypass validation.
        request=request.model_dump(mode='python')
    checked=InvestigationRequest.model_validate(request)
    return InvestigationRequest.model_validate_json(checked.model_dump_json())


def request_fingerprint(request):
    raw=capture_request(request).model_dump(mode='json',exclude={'request_id'})
    return fingerprint(raw)


class ResolvedScope(Sized):
    planner_input: PlannerInput
    targets: tuple[str,...] = Field(max_length=3)
    component_origin: Literal['EXPLICIT','QUESTION_EXTRACTED','MISSING']
    objective_profile: Profile
    objective_source: Literal['stored_planner_request','new_structured_request']
    objective: ObjectiveContract
    route: dict


class InvestigationPolicy(Sized):
    timeout_seconds: StrictInt = Field(default=300,ge=1,le=300)
    max_active: StrictInt = Field(default=2,ge=1,le=2)
    lease_seconds: StrictInt = Field(default=90,ge=10,le=300)
    poll_seconds: float = Field(default=0.2,ge=0.02,le=1)
    heartbeat_seconds: float = Field(default=5,ge=1,le=30)
    version: Literal['orchestration-policy-v1'] = 'orchestration-policy-v1'


class StageEvent(Sized):
    stage: Stage
    code: str = Field(min_length=1,max_length=100)
    at: AwareDatetime = Field(default_factory=utcnow)
    overall_status: Overall | None = None
    references: dict[str,str] = Field(default_factory=dict)


class InvestigationContext(Sized):
    size_limit: ClassVar[int] = 2*1024*1024
    schema_version: Literal['investigation-context-v1'] = 'investigation-context-v1'
    logical_investigation_id: UUID
    owner: str = Field(min_length=1,max_length=150)
    original_request: InvestigationRequest
    request_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    resolved_scope: ResolvedScope
    current_stage: Stage = 'CREATED'
    overall_status: Overall = 'RUNNING'
    planner_run_id: UUID | None = None
    investigation_run_id: UUID | None = None
    verification_run_id: UUID | None = None
    analysis_run_id: UUID | None = None
    artifact_references: tuple[ArtifactRef,...] = Field(default=(),max_length=3)
    integration_result_id: UUID | None = None
    gate_logical_investigation_id: UUID | None = None
    gate_input_hash: str | None = None
    objective_hash: str | None = None
    answer_id: UUID | None = None
    stage_keys: dict[str,str] = Field(default_factory=dict)
    warnings: tuple[str,...] = Field(default=(),max_length=128)
    unresolved_items: tuple[str,...] = Field(default=(),max_length=128)
    events: tuple[StageEvent,...] = Field(default=(),max_length=128)
    created_at: AwareDatetime
    updated_at: AwareDatetime
    deadline_at: AwareDatetime
    cancel_requested_at: AwareDatetime | None = None
    cancel_observed_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None
    error_code: str | None = Field(None,max_length=100)
    revision: StrictInt = Field(default=0,ge=0)
    policy_version: Literal['orchestration-policy-v1'] = 'orchestration-policy-v1'

    @model_validator(mode='after')
    def identity(self):
        valid_actor(self.owner)
        if self.request_hash!=request_fingerprint(self.original_request):
            raise ValueError('REQUEST_HASH_INVALID')
        if self.resolved_scope.planner_input.query.question!=self.original_request.user_query:
            raise ValueError('ORIGINAL_QUESTION_CHANGED')
        if self.deadline_at<self.created_at:raise ValueError('INVALID_DEADLINE')
        return self


class InvestigationStatus(Sized):
    logical_investigation_id: UUID
    current_stage: Stage
    overall_status: Overall
    planner_run_id: UUID | None = None
    investigation_run_id: UUID | None = None
    verification_run_id: UUID | None = None
    analysis_run_id: UUID | None = None
    cancel_requested: bool = False
    recovery_required: bool = False
    warnings: tuple[str,...] = ()
    error_code: str | None = None
    revision: int
    updated_at: AwareDatetime


class ClaimReceipt(Sized):
    size_limit: ClassVar[int] = 2*1024*1024
    logical_id: UUID
    fresh: bool
    context: InvestigationContext
    worker_token: UUID | None = Field(None,exclude=True,repr=False)


class InvestigationResult(Sized):
    size_limit: ClassVar[int] = 2*1024*1024
    context: InvestigationContext
    status: InvestigationStatus
    answer: AnswerEnvelope | None = None
    persistence: Literal['STORED','NOT_STORED'] = 'STORED'
    delivery_error: str|None=Field(None,max_length=100)


def stage_key(logical_id,stage):return 'orchestration:'+str(logical_id)+':'+stage

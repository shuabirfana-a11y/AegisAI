"""Browser contracts; internal request and business verdicts are not redefined."""
from copy import deepcopy
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, create_model
from app.assistant.contracts import QueryRequest
from app.tooling.contracts import ResolutionInput, Target
from app.planner.schemas import PlannerInput
from app.orchestration.contracts import (
    InvestigationRequest, InvestigationOptions, InvestigationStatus, Stage, Overall, TimeScope,
)
from app.orchestration.trace import InvestigationTrace
from app.orchestration.answer_contracts import AnswerEnvelope
from app.agents.investigation.schemas import InvestigationArtifact
from app.agents.verification.schemas import VerificationArtifact
from app.agents.analysis.schemas import RiskAnalysisArtifact
from app.integration.contracts import IntegrationResult
from app.investigation_api.errors import ApiFailure


class PublicModel(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)


class AssetScope(PublicModel):
    asset_id: UUID | None = None
    component_id: UUID | None = None
    snapshot_id: UUID | None = None
    component: ResolutionInput | None = None
    target: Target | None = None


class CreateOptions(InvestigationOptions):
    mode: Literal['auto', 'fast', 'deep'] = 'auto'
    realtime: bool = False
    time_scope: TimeScope | None = None


class InvestigationCreateRequest(PublicModel):
    user_query: str = Field(min_length=1, max_length=2000)
    asset_scope: AssetScope = Field(default_factory=AssetScope)
    options: CreateOptions = Field(default_factory=CreateOptions)
    idempotency_key: str | None = Field(None, min_length=1, max_length=150)

    def to_internal(self, header_key=None):
        key = checked_key(self.idempotency_key, header_key)
        scope, options = self.asset_scope, self.options
        return InvestigationRequest(planner_input=PlannerInput(
            query=QueryRequest(question=self.user_query, asset_id=scope.asset_id,
                               target=scope.target, mode=options.mode, request_key=key,
                               realtime=options.realtime),
            component_id=scope.component_id, snapshot_id=scope.snapshot_id, component=scope.component),
            time_scope=options.time_scope,
            investigation_options=InvestigationOptions(objective_profile=options.objective_profile,
                                                      timeout_seconds=options.timeout_seconds))


def checked_key(body_key, header_key):
    if header_key is not None and (not header_key.strip() or len(header_key) > 150):
        raise ApiFailure('INVALID_IDEMPOTENCY_KEY', '幂等键应为 1–150 个字符。', status=422)
    if body_key is not None and not body_key.strip():
        raise ApiFailure('INVALID_IDEMPOTENCY_KEY', '幂等键不能为空白。', status=422)
    if body_key and header_key and body_key != header_key:
        raise ApiFailure('IDEMPOTENCY_KEY_MISMATCH', '请求体与请求头的幂等键不一致。', status=422)
    if not (body_key or header_key):
        raise ApiFailure('IDEMPOTENCY_KEY_REQUIRED', '请提供 Idempotency-Key 或 idempotency_key。', status=422)
    return body_key or header_key


class ApiError(PublicModel):
    error_code: str
    message: str
    request_id: UUID
    retryable: bool = False


class InvestigationStatusResponse(InvestigationStatus):
    investigation_id: UUID
    status: Stage
    created_at: AwareDatetime
    finished_at: AwareDatetime | None = None


class InvestigationCreateResponse(InvestigationStatusResponse):
    reused: bool
    persistence: Literal['STORED'] = 'STORED'
    execution_backend: Literal['IN_PROCESS_BOUNDED_WORKER'] = 'IN_PROCESS_BOUNDED_WORKER'
    model_provider: str
    is_mock: bool


class TraceStage(PublicModel):
    agent: str | None = None
    stage: Stage
    status: str
    time: AwareDatetime
    run_id: UUID | None = None
    artifact_ids: tuple[UUID, ...] = ()


class TraceResponse(InvestigationTrace):
    investigation_id: UUID
    stages: tuple[TraceStage, ...]
    revision: int


def public_artifact_model(name, source, excluded):
    # Copy annotations/constraints, not business validators requiring private receipts.
    fields = {key: (field.annotation, deepcopy(field))
              for key, field in source.model_fields.items() if key not in excluded}
    return create_model(name, __base__=PublicModel, **fields)


PRIVATE_ARTIFACT_FIELDS = frozenset({
    'tool_calls', 'failed_tools', 'model_calls', 'model_hints', 'receipt_references',
    'input_snapshot_hash', 'source_snapshot_hash', 'context_id',
})
PublicInvestigationArtifact = public_artifact_model('PublicInvestigationArtifact', InvestigationArtifact, PRIVATE_ARTIFACT_FIELDS)
PublicVerificationArtifact = public_artifact_model('PublicVerificationArtifact', VerificationArtifact, PRIVATE_ARTIFACT_FIELDS)
PublicRiskAnalysisArtifact = public_artifact_model('PublicRiskAnalysisArtifact', RiskAnalysisArtifact, PRIVATE_ARTIFACT_FIELDS)
IntegrationResponse = public_artifact_model('IntegrationResponse', IntegrationResult, frozenset())
AnswerResponse = public_artifact_model('AnswerResponse', AnswerEnvelope, frozenset())


class ArtifactResponse(PublicModel):
    investigation_id: UUID
    revision: int
    investigation: PublicInvestigationArtifact | None = None
    verification: PublicVerificationArtifact | None = None
    analysis: PublicRiskAnalysisArtifact | None = None
    content_trust_level: Literal['UNTRUSTED_EXTERNAL_CONTENT'] = 'UNTRUSTED_EXTERNAL_CONTENT'
    projection_version: Literal['investigation-api-public-v1'] = 'investigation-api-public-v1'


class HistoryItem(InvestigationStatusResponse):
    original_question: str
    answer_id: UUID | None = None
    integration_result_id: UUID | None = None


class HistoryResponse(PublicModel):
    items: tuple[HistoryItem, ...]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    sort: Literal['created_desc', 'created_asc']
    status_filter: Overall | None = None

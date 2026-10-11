"""Professional metadata supplements, never replaces, runtime authority."""
import hashlib
import json
from uuid import UUID
from typing import Annotated, Literal
from pydantic import Field, StrictInt, model_validator
from app.runtime.contracts import FrozenModel, TaskId, TaskPlan, TaskState, json_bytes
from app.planner.schemas import PlannerType
from app.tooling.contracts import REGISTRY

AgentType = Literal['investigation', 'verification', 'security_analysis']
ArtifactType = Literal['investigation_result', 'verification_result', 'security_analysis_result']
REGISTRY_VERSION = 'professional-agents-v1'
AgentTaskType = PlannerType | Literal['asset_lookup','evidence_verification','claim_validation','conflict_detection',
                                     'asset_impact_analysis','remediation_prioritization']


class AgentFrameworkError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def fingerprint(value) -> str:
    # Validate finite/bounded JSON first; canonicalize for stable identity.
    json_bytes(value, 8 * 1024 * 1024)
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


class AgentContract(FrozenModel):
    agent_id: TaskId
    agent_type: AgentType
    description: str = Field(min_length=1, max_length=500)
    supported_tasks: tuple[AgentTaskType, ...] = Field(min_length=1, max_length=5)
    allowed_tools: tuple[str, ...] = Field(max_length=8)
    input_schema: Literal['ProfessionalAgentInput-v1'] = 'ProfessionalAgentInput-v1'
    output_schema: Literal['AgentArtifact-v1'] = 'AgentArtifact-v1'
    timeout_seconds: Annotated[StrictInt, Field(ge=1, le=60)] = 30

    @model_validator(mode='after')
    def validate_registration(self):
        if len(set(self.supported_tasks)) != len(self.supported_tasks):
            raise ValueError('Duplicate supported tasks')
        if len(set(self.allowed_tools)) != len(self.allowed_tools) or any(t not in REGISTRY for t in self.allowed_tools):
            raise ValueError('Invalid registered tool set')
        return self


class AgentBinding(FrozenModel):
    task_id: TaskId
    semantic_type: AgentTaskType
    agent_id: TaskId
    agent_type: AgentType
    artifact_type: ArtifactType
    contract: AgentContract
    implementation_key: str = Field(min_length=1, max_length=100)
    task_fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def consistent(self):
        if self.agent_id != self.contract.agent_id or self.agent_type != self.contract.agent_type or self.semantic_type not in self.contract.supported_tasks:
            raise ValueError('Binding does not match capability contract')
        if self.artifact_type != self.agent_type + '_result':
            raise ValueError('Artifact type does not match capability')
        return self


class BoundAgentPlan(FrozenModel):
    plan_json: str
    bindings_json: str
    registry_fingerprint: str

    @property
    def captured_plan(self) -> TaskPlan: return TaskPlan.model_validate_json(self.plan_json)

    @property
    def bindings(self) -> dict[str, AgentBinding]:
        return {k: AgentBinding.model_validate(v) for k,v in json.loads(self.bindings_json).items()}

    def binding(self, task_id: str) -> AgentBinding | None: return self.bindings.get(task_id)


class ArtifactReference(FrozenModel):
    artifact_id: UUID
    agent_id: TaskId
    task_id: TaskId
    run_id: UUID
    artifact_type: ArtifactType
    status: TaskState


class AgentRunTrace(FrozenModel):
    agent_id: TaskId
    agent_type: AgentType
    task_id: TaskId
    run_id: UUID
    input_artifact: tuple[ArtifactReference, ...] = ()
    output_artifact: ArtifactReference | None = None
    execution_time: Annotated[StrictInt, Field(ge=0)] | None = None
    status: TaskState
    attempted: bool
    capability_state: Literal['interface_only','implementation_registered']
    errors: tuple[dict, ...] = ()

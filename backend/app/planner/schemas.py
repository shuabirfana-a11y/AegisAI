"""Candidates carry intent; only validated immutable snapshots reach Runtime."""
import json
from copy import deepcopy
from typing import Any, Literal
from uuid import UUID
from pydantic import ConfigDict, Field, model_validator
from app.assistant.contracts import QueryRequest
from app.runtime.contracts import FrozenModel, TaskContract, TaskInput, RuntimePolicy, json_bytes
from app.tooling.contracts import ResolutionInput

PlannerType = Literal['vulnerability_lookup', 'version_match', 'evidence_search',
                      'patch_analysis', 'risk_analysis']
PROMPT_VERSION = 'task-plan-v1'
REGISTRY_VERSION = 'planner-registry-v1'
VALIDATOR_VERSION = 'planner-validator-v1'

class ModelIdentity(FrozenModel):
    provider: str
    model: str
    is_mock: bool

class PlannerInput(FrozenModel):
    query: QueryRequest
    component_id: UUID | None = None
    snapshot_id: UUID | None = None
    component: ResolutionInput | None = None

def _task_input_schema():
    schema = TaskInput.model_json_schema()
    step_schema = schema.pop('$defs')['ToolStep']
    schema['properties']['steps']['items'] = step_schema
    return schema


def _task_contract_schema(schema):
    # Describe the structural conditions already enforced by TaskContract.valid_payload.
    # Do not change its validator, defaults, permissions, or execution behavior.
    # Complete branches also support decoders that ignore siblings of anyOf.
    tool, missing = deepcopy(schema), deepcopy(schema)
    for branch, kind, input_field in ((tool, 'tool_sequence', 'steps'),
                                      (missing, 'input_required', 'required_fields')):
        branch['properties']['task_type'] = {'type': 'string', 'const': kind}
        branch['properties']['input_data']['required'] = [input_field]
    tool['required'] = list(dict.fromkeys(tool['required'] + ['allowed_tools']))
    tool['properties']['allowed_tools']['minItems'] = 1
    tool['properties']['input_data']['properties']['steps']['minItems'] = 1
    tool['properties']['input_data']['properties']['required_fields']['maxItems'] = 0
    missing['required'] = list(dict.fromkeys(missing['required'] + ['task_type', 'max_tool_calls']))
    missing['properties']['allowed_tools']['maxItems'] = 0
    missing['properties']['max_tool_calls'] = {'type': 'integer', 'const': 0}
    missing['properties']['input_data']['properties']['steps']['maxItems'] = 0
    missing['properties']['input_data']['properties']['required_fields']['minItems'] = 1
    schema.clear()
    schema['anyOf'] = [tool, missing]


class PlannerTaskContract(TaskContract):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False,
                              populate_by_name=True, json_schema_extra=_task_contract_schema)
    planner_type: PlannerType = Field(alias='type')
    input_data: dict[str, Any] = Field(json_schema_extra=_task_input_schema())

class PlannerPlan(FrozenModel):
    plan_id: UUID
    objective: str = Field(min_length=1, max_length=500)
    tasks: tuple[PlannerTaskContract, ...] = Field(min_length=1, max_length=16)
    reasoning_summary: str = Field(min_length=1, max_length=600)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode='after')
    def bounded(self):
        json_bytes(self.model_dump(mode='json', by_alias=True), 65536)
        return self

class ValidationIssue(FrozenModel):
    code: str
    path: str
    message: str

class PlannerContext(FrozenModel):
    planner_run_id: UUID
    trace_id: UUID
    actor: str = Field(min_length=1, max_length=150)
    policy: RuntimePolicy
    route_json: str
    scope_json: str
    prompt_version: str = PROMPT_VERSION
    registry_version: str = REGISTRY_VERSION
    model_calls_json: str = '[]'

    @property
    def route(self):return json.loads(self.route_json)
    @property
    def scope(self):return json.loads(self.scope_json)
    @property
    def model_calls(self):return json.loads(self.model_calls_json)

class ValidatedPlan(FrozenModel):
    runtime_plan_json: str
    semantic_types_json: str
    candidate_json: str
    validator_version: str = VALIDATOR_VERSION
    plan_hash: str

class PlannerAttempt(FrozenModel):
    attempt_index: int = Field(ge=1, le=2)
    model_call: dict
    diagnostic: dict | None = None
    raw_unavailable_reason: str | None = None
    issues: tuple[ValidationIssue, ...] = ()
    validation_status: Literal['VALIDATED', 'REJECTED']

class PlanningOutcome(FrozenModel):
    status: Literal['VALIDATED', 'PLANNING_FAILED']
    validated_plan: ValidatedPlan | None = None
    issues: tuple[ValidationIssue, ...] = ()
    attempts: tuple[PlannerAttempt, ...] = ()

    @model_validator(mode='after')
    def consistent(self):
        if (self.status == 'VALIDATED') != (self.validated_plan is not None):
            raise ValueError('Planning status and validated snapshot must agree')
        return self

class PlannerSnapshot(FrozenModel):
    planner_run_id: UUID
    trace_id: UUID
    planning_status: Literal['PLANNING', 'VALIDATED', 'PLANNING_FAILED']
    runtime_run_id: UUID | None = None
    runtime_status: str | None = None

class PlannerRunTrace(FrozenModel):
    planner_run_id: UUID
    trace_id: UUID
    user_query: str
    model: ModelIdentity
    prompt_version: str
    registry_version: str
    generated_plan: dict | None = None
    validation_status: str
    retry_count: int = Field(ge=0, le=1)
    latency: float = Field(ge=0)
    error: tuple[ValidationIssue, ...] = ()
    attempts: tuple[PlannerAttempt, ...] = ()
    validated_plan: ValidatedPlan | None = None
    runtime_run_id: UUID | None = None
    runtime_status: str | None = None

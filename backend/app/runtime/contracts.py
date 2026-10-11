"""Versioned runtime contracts; execution success never certifies security facts.

The old role contracts remain intact. New task kinds must be explicitly added,
not supplied as executable code or dynamically imported from user input.
"""
from datetime import datetime
from enum import StrEnum
import json
from typing import Any, Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from app.tooling.contracts import ToolEnvelope


INPUT_LIMIT = 64 * 1024
ARTIFACT_LIMIT = 512 * 1024
METADATA_LIMIT = 8 * 1024 * 1024
WIRE_LIMIT = 4 * 1024 * 1024
TaskId = Annotated[str, Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')]
Permission = Literal['READ_ONLY', 'WRITE', 'REVIEW_ACTION', 'EXTERNAL_NETWORK']
Criterion = Literal['tools_succeeded', 'output_nonempty', 'evidence_present']


def json_bytes(value: Any, limit: int) -> bytes:
    """No NaN, Python objects, invalid Unicode, or silent data truncation."""
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False,
                         separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError('Finite JSON data required') from exc
    if len(raw) > limit:
        raise ValueError('JSON size limit exceeded')
    return raw


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)


class TaskState(StrEnum):
    CREATED = 'CREATED'
    PENDING = 'PENDING'
    READY = 'READY'
    RUNNING = 'RUNNING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    WAITING_REVIEW = 'WAITING_REVIEW'
    BLOCKED = 'BLOCKED'


TERMINAL = frozenset({TaskState.SUCCESS, TaskState.FAILED,
                      TaskState.WAITING_REVIEW, TaskState.BLOCKED})


class ToolStep(FrozenModel):
    name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)


class TaskInput(FrozenModel):
    steps: tuple[ToolStep, ...] = Field(default_factory=tuple, max_length=8)
    required_fields: tuple[str, ...] = Field(default_factory=tuple, max_length=8)


class TaskContract(FrozenModel):
    task_id: TaskId
    task_type: Literal['tool_sequence', 'input_required'] = 'tool_sequence'
    description: str = Field(min_length=1, max_length=500)
    input_data: dict[str, Any]
    dependencies: tuple[TaskId, ...] = Field(default_factory=tuple, max_length=16)
    allowed_tools: tuple[str, ...] = Field(default_factory=tuple, max_length=8)
    expected_output: Literal['ToolSequenceResult-v1'] = 'ToolSequenceResult-v1'
    acceptance_criteria: tuple[Criterion, ...] = ('tools_succeeded', 'output_nonempty')
    max_tool_calls: Annotated[StrictInt, Field(ge=0, le=8)] = 2
    timeout_seconds: Annotated[StrictInt, Field(ge=1, le=60)] = 30

    @model_validator(mode='after')
    def valid_payload(self):
        json_bytes(self.input_data, INPUT_LIMIT)
        inputs = TaskInput.model_validate(self.input_data)
        if len(set(self.allowed_tools)) != len(self.allowed_tools):
            raise ValueError('Duplicate allowed tools')
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError('Duplicate dependencies')
        if len(inputs.steps) > self.max_tool_calls:
            raise ValueError('Task call budget exceeded')
        if self.task_type == 'input_required':
            if inputs.steps or self.allowed_tools or self.max_tool_calls or not inputs.required_fields:
                raise ValueError('Input-required task must have zero tools and explicit missing fields')
        elif not inputs.steps or inputs.required_fields:
            raise ValueError('Tool task must contain steps')
        if any(s.name not in self.allowed_tools for s in inputs.steps):
            raise ValueError('Step is not in task allowlist')
        return self


class RuntimePolicy(FrozenModel):
    permissions: frozenset[Permission] = frozenset({'READ_ONLY'})
    max_tasks: Annotated[StrictInt, Field(ge=1, le=16)] = 16
    max_depth: Annotated[StrictInt, Field(ge=1, le=8)] = 8
    max_tool_calls: Annotated[StrictInt, Field(ge=0, le=32)] = 32
    max_parallel: Annotated[StrictInt, Field(ge=1, le=3)] = 3
    run_timeout_seconds: Annotated[StrictInt, Field(ge=1, le=120)] = 120


class TaskPlan(FrozenModel):
    version: Literal['runtime-v1'] = 'runtime-v1'
    tasks: tuple[TaskContract, ...] = Field(min_length=1, max_length=16)
    route: dict[str, Any] = Field(default_factory=dict)


class WorkerContext(FrozenModel):
    run_id: UUID
    trace_id: UUID
    actor: str = Field(min_length=1, max_length=150)
    permissions: frozenset[Permission] = frozenset({'READ_ONLY'})
    deadline: float = Field(gt=0)


class RunContext(WorkerContext):
    policy: RuntimePolicy = Field(default_factory=RuntimePolicy)
    database_url: str | None = Field(default=None, exclude=True, repr=False)


class ToolReceipt(FrozenModel):
    call_index: Annotated[StrictInt, Field(ge=1, le=8)]
    name: str
    arguments: dict[str, Any]
    started_at: datetime
    finished_at: datetime
    envelope: ToolEnvelope


class TaskArtifact(FrozenModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    task_id: TaskId
    status: TaskState
    result: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict] = Field(default_factory=list)
    tool_calls: list[dict] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    unresolved_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime

    @model_validator(mode='after')
    def valid_artifact(self):
        if self.status not in TERMINAL:
            raise ValueError('Artifact requires a terminal state')
        for value in (self.start_time, self.end_time):
            if value is not None and value.utcoffset() is None:
                raise ValueError('Aware timestamps required')
        if self.start_time and self.end_time < self.start_time:
            raise ValueError('Ordered timestamps required')
        json_bytes(self.model_dump(mode='json'), ARTIFACT_LIMIT)
        return self


class TaskTrace(FrozenModel):
    run_id: UUID
    task_id: TaskId
    task_type: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: TaskState = TaskState.CREATED
    tools_called: list[dict] = Field(default_factory=list)
    model_called: list[dict] = Field(default_factory=list)
    error: list[dict] = Field(default_factory=list)
    artifact_id: UUID | None = None
    dependencies: tuple[str, ...] = ()
    transitions: list[dict] = Field(default_factory=list)


class ToolContract(FrozenModel):
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    permission: Permission
    timeout: float = Field(gt=0, le=60)


class ExecutionOutcome(FrozenModel):
    artifact: TaskArtifact
    receipts: tuple[ToolReceipt, ...] = ()
    cleanup_verified: bool = True


class RunOutcome(FrozenModel):
    run_id: UUID
    artifacts: tuple[TaskArtifact, ...]
    traces: tuple[TaskTrace, ...]
    status: str


class RunSnapshot(FrozenModel):
    run_id: UUID
    trace_id: UUID
    status: str
    result: dict | None = None


class TraceSnapshot(FrozenModel):
    run_id: UUID
    trace_id: UUID
    tasks: tuple[TaskTrace, ...]
    artifacts: tuple[TaskArtifact, ...]

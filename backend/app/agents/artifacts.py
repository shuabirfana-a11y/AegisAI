"""Typed handoffs preserve original identity, provenance and uncertainty."""
from pydantic import Field, model_validator
from app.runtime.contracts import (TaskArtifact, TaskContract, WorkerContext, FrozenModel,
                                   TaskId, TaskState, ARTIFACT_LIMIT, WIRE_LIMIT, json_bytes)
from app.agents.contracts import AgentBinding, ArtifactType, AgentFrameworkError


def validate_artifact_json(source: TaskArtifact) -> None:
    # JSON-mode Pydantic serialization may turn NaN into null. Check raw
    # flexible payloads before converting typed UUID/time metadata to JSON.
    json_bytes({'result':source.result,'evidence':source.evidence,
                'tool_calls':source.tool_calls,'confidence':source.confidence}, ARTIFACT_LIMIT)
    json_bytes(source.model_dump(mode='json'), ARTIFACT_LIMIT)


class AgentArtifact(TaskArtifact):
    agent_id: TaskId
    artifact_type: ArtifactType
    unresolved_items: tuple[str, ...] = ()

    @model_validator(mode='after')
    def unresolved_preserved(self):
        validate_artifact_json(self)
        if self.unresolved_items != tuple(self.unresolved_questions):
            raise ValueError('Unresolved items must preserve runtime uncertainty')
        return self

    @classmethod
    def from_task_artifact(cls, source: TaskArtifact, binding: AgentBinding) -> 'AgentArtifact':
        try:
            if set(source.__dict__) - set(TaskArtifact.model_fields):
                raise ValueError('Unexpected original Artifact fields')
            validate_artifact_json(source)
            source = TaskArtifact.model_validate_json(source.model_dump_json())
            binding = AgentBinding.model_validate_json(binding.model_dump_json())
            if source.task_id != binding.task_id:
                raise ValueError('Artifact binding identity mismatch')
            return cls(**source.model_dump(), agent_id=binding.agent_id,
                       artifact_type=binding.artifact_type, unresolved_items=tuple(source.unresolved_questions))
        except (ValueError, TypeError, AttributeError) as exc:
            raise AgentFrameworkError('AGENT_ARTIFACT_INVALID') from exc

    def to_task_artifact(self) -> TaskArtifact:
        validate_artifact_json(self)
        captured = AgentArtifact.model_validate_json(self.model_dump_json())
        return TaskArtifact.model_validate({k:v for k,v in captured.model_dump().items()
                                           if k in TaskArtifact.model_fields})


def validate_persisted_extension(source: TaskArtifact, binding: AgentBinding, receipts) -> None:
    """Reserve the original Store's canonical reference expansion before success.

    UUID record IDs are 36 characters and RuntimePolicy caps run calls at 32.
    Actual sequence numbers therefore cannot be larger than this reservation.
    Full tool envelopes remain in immutable ToolCallRecord rows, not this view.
    """
    calls = [{'record_id':'ffffffff-ffff-ffff-ffff-ffffffffffff','sequence_no':32,
              'call_index':r.call_index,'tool_name':r.name,'status':r.envelope.status,
              'duration_ms':r.envelope.duration_ms} for r in receipts]
    try:
        validate_artifact_json(source)
        stored = TaskArtifact.model_validate({**source.model_dump(),'tool_calls':calls})
        AgentArtifact.from_task_artifact(stored,binding)
    except (ValueError,TypeError) as exc:
        raise AgentFrameworkError('ARTIFACT_SIZE_LIMIT') from exc


class AgentExecutionRequest(FrozenModel):
    task: TaskContract
    context: WorkerContext
    input_artifacts: tuple[AgentArtifact, ...] = Field(default_factory=tuple, max_length=16)

    @model_validator(mode='after')
    def validate_inputs(self):
        if tuple(a.task_id for a in self.input_artifacts) != self.task.dependencies:
            raise ValueError('Exact ordered dependency artifacts required')
        if len({a.artifact_id for a in self.input_artifacts}) != len(self.input_artifacts):
            raise ValueError('Duplicate dependency artifact')
        if any(a.run_id != self.context.run_id or a.status != TaskState.SUCCESS for a in self.input_artifacts):
            raise ValueError('Only accepted same-run artifacts may be handed off')
        json_bytes(self.model_dump(mode='json'), WIRE_LIMIT)
        return self


def build_handoff(task: TaskContract, context: WorkerContext, dependencies: dict[str,TaskArtifact],
                  bindings: dict[str,AgentBinding]) -> tuple[AgentArtifact, ...]:
    try:
        task = TaskContract.model_validate_json(task.model_dump_json())
        if set(dependencies) != set(task.dependencies):
            raise ValueError('Dependencies must exactly match the task')
        values = []
        for key in task.dependencies:
            source = dependencies[key]
            if source.task_id != key or source.run_id != context.run_id or source.status != TaskState.SUCCESS:
                raise ValueError('Accepted dependency identity required')
            values.append(AgentArtifact.from_task_artifact(source, bindings[key]))
        request = AgentExecutionRequest(task=task, context=context, input_artifacts=values)
        return request.input_artifacts
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise AgentFrameworkError('AGENT_HANDOFF_INVALID') from exc

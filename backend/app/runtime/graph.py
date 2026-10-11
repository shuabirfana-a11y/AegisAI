"""Reuse the existing topology algorithm; snapshots prevent post-validation edits."""
from dataclasses import dataclass
from app.assistant.graph import levels
from app.tooling.contracts import REGISTRY
from app.runtime.contracts import RuntimePolicy, TaskContract, TaskInput, TaskPlan


@dataclass(frozen=True)
class TaskGraph:
    plan_json: str
    layers: tuple[tuple[str, ...], ...]

    @property
    def tasks(self) -> tuple[TaskContract, ...]:
        return TaskPlan.model_validate_json(self.plan_json).tasks

    def task(self, task_id: str) -> TaskContract:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(task_id)


class TaskGraphBuilder:
    def __init__(self):
        self._tasks: dict[str, str] = {}

    def add_task(self, task: TaskContract) -> None:
        if task.task_id in self._tasks:
            raise ValueError('Duplicate task identity')
        self._tasks[task.task_id] = task.model_dump_json()

    def compile(self) -> TaskPlan:
        return TaskPlan(tasks=[TaskContract.model_validate_json(s) for s in self._tasks.values()])


def compile_graph(plan: TaskPlan, policy: RuntimePolicy) -> TaskGraph:
    # Re-validation also rejects data mutated inside an otherwise frozen model.
    captured = TaskPlan.model_validate_json(plan.model_dump_json())
    if len(captured.tasks) > policy.max_tasks:
        raise ValueError('Graph task budget exceeded')
    layers_ = levels(captured.tasks)
    if len(layers_) > policy.max_depth:
        raise ValueError('Graph depth budget exceeded')
    if sum(t.max_tool_calls for t in captured.tasks) > policy.max_tool_calls:
        raise ValueError('Reserved run call budget exceeded')
    for task in captured.tasks:
        for name in task.allowed_tools:
            if name not in REGISTRY:
                raise ValueError('Unknown tool in task allowlist')
        for step in TaskInput.model_validate(task.input_data).steps:
            spec = REGISTRY[step.name]
            parsed = spec.input.model_validate(step.arguments).model_dump(mode='json')
            needed = {spec.permission}
            if parsed.get('refresh'):
                needed.update({'EXTERNAL_NETWORK', 'WRITE'})
            if not needed <= policy.permissions:
                raise PermissionError('Task exceeds server permissions')
    return TaskGraph(captured.model_dump_json(),
                     tuple(tuple(t.task_id for t in layer) for layer in layers_))

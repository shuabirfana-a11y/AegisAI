"""Route by server-validated semantics, never descriptions or tool guesses."""
import json
from app.agents.contracts import AgentBinding, BoundAgentPlan, AgentFrameworkError, fingerprint
from app.agents.registry import RegistrySnapshot
from app.runtime.contracts import TaskContract, TaskInput, TaskPlan, RuntimePolicy
from app.runtime.graph import compile_graph
from app.planner.registry import TASK_REGISTRY


class AgentRouter:
    def __init__(self, snapshot: RegistrySnapshot, *, task_registry=None):
        self.snapshot = snapshot
        self.task_registry = TASK_REGISTRY if task_registry is None else task_registry

    def route(self, task: TaskContract, semantic_type: str) -> AgentBinding:
        task = TaskContract.model_validate_json(task.model_dump_json())
        registration = self.snapshot.for_task(semantic_type)
        role = self.task_registry.get(semantic_type)
        if registration is None or role is None:
            raise AgentFrameworkError('AGENT_NOT_FOUND')
        if task.task_type == 'input_required':
            raise AgentFrameworkError('AGENT_TASK_UNASSIGNED')
        tools = set(task.allowed_tools) | {s.name for s in TaskInput.model_validate(task.input_data).steps}
        if not tools <= set(registration.contract.allowed_tools) & role.tools:
            raise AgentFrameworkError('AGENT_TOOL_FORBIDDEN')
        if not role.criteria <= set(task.acceptance_criteria):
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        contract = registration.contract
        return AgentBinding(task_id=task.task_id, semantic_type=semantic_type,
            agent_id=contract.agent_id, agent_type=contract.agent_type, artifact_type=contract.agent_type+'_result',
            contract=contract, implementation_key=registration.implementation_key,
            task_fingerprint=fingerprint(task.model_dump(mode='json')))

    def bind_plan(self, plan: TaskPlan, semantic_types: dict[str,str], policy: RuntimePolicy) -> BoundAgentPlan:
        plan = TaskPlan.model_validate_json(plan.model_dump_json())
        if 'professional_agents_v1' in plan.route or set(semantic_types) != {t.task_id for t in plan.tasks}:
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        bindings = {}
        for task in plan.tasks:
            kind = semantic_types[task.task_id]
            if kind not in self.task_registry or self.snapshot.for_task(kind) is None:
                raise AgentFrameworkError('AGENT_NOT_FOUND')
            if task.task_type != 'input_required':
                bindings[task.task_id] = self.route(task,kind).model_dump(mode='json')
        route = {**plan.route,'professional_agents_v1':{
            'registry':self.snapshot.metadata,'registry_fingerprint':self.snapshot.fingerprint,
            'semantic_types':semantic_types, 'bindings':bindings}}
        graph = compile_graph(TaskPlan(tasks=plan.tasks,route=route), policy)
        return BoundAgentPlan(plan_json=graph.plan_json,bindings_json=json.dumps(bindings),
                              registry_fingerprint=self.snapshot.fingerprint)

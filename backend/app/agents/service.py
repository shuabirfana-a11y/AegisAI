"""Opt-in Runtime subtype; existing Planner and default services are unchanged."""
import hashlib
import json
from app.agents.contracts import AgentFrameworkError, BoundAgentPlan, fingerprint
from app.agents.registry import create_default_registry
from app.agents.router import AgentRouter
from app.agents.executor import AgentExecutor
from app.planner.schemas import PlannerPlan
from app.planner.trace import PlannerTraceStore
from app.runtime.contracts import TaskContract, TaskPlan, json_bytes, METADATA_LIMIT
from app.runtime.scheduler import Scheduler
from app.runtime.service import RuntimeService


class ProfessionalRuntimeService(RuntimeService):
    def __init__(self, engine, *, registry=None, policy=None, model_gateway=None):
        super().__init__(engine,policy=policy,model_gateway=model_gateway)
        self.registry = (registry if registry is not None else create_default_registry()).freeze()
        self.planner_store = PlannerTraceStore(engine)

    def run_plan(self, plan: TaskPlan, actor: str, request_key: str):
        json_bytes(plan.route,METADATA_LIMIT)
        plan = TaskPlan.model_validate_json(plan.model_dump_json())
        if not isinstance(actor,str) or not 1 <= len(actor) <= 150:
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        if 'professional_agents_v1' in plan.route or not plan.route.get('planner_run_id'):
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        try:
            audit = self.planner_store.read(plan.route['planner_run_id'],actor)
            validated = audit.validated_plan
            if audit.validation_status != 'VALIDATED' or validated is None:
                raise AgentFrameworkError('AGENT_PLAN_INVALID')
            if hashlib.sha256(validated.runtime_plan_json.encode('utf-8')).hexdigest() != validated.plan_hash:
                raise AgentFrameworkError('AGENT_PLAN_INVALID')
            canonical = TaskPlan.model_validate_json(validated.runtime_plan_json)
            if fingerprint(canonical.model_dump(mode='json')) != fingerprint(plan.model_dump(mode='json')):
                raise AgentFrameworkError('AGENT_PLAN_INVALID')
            candidate = PlannerPlan.model_validate_json(validated.candidate_json)
            semantics = json.loads(validated.semantic_types_json)
            if semantics != {t.task_id:t.planner_type for t in candidate.tasks}:
                raise AgentFrameworkError('AGENT_PLAN_INVALID')
            tasks = tuple(TaskContract.model_validate({k:v for k,v in t.model_dump().items() if k!='planner_type'})
                          for t in candidate.tasks)
            if tasks != plan.tasks: raise AgentFrameworkError('AGENT_PLAN_INVALID')
        except LookupError:
            raise
        except (ValueError,TypeError,AttributeError) as exc:
            raise AgentFrameworkError('AGENT_PLAN_INVALID') from exc
        bound = AgentRouter(self.registry).bind_plan(plan,semantics,self.policy)
        return super().run_plan(bound.captured_plan,actor,request_key)

    def _make_scheduler(self, plan: TaskPlan) -> Scheduler:
        ns = plan.route.get('professional_agents_v1')
        # Inherited deterministic run() retains the original default path.
        if ns is None: return super()._make_scheduler(plan)
        if ns['registry_fingerprint'] != self.registry.fingerprint or fingerprint(ns['registry']) != self.registry.fingerprint:
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        bound = BoundAgentPlan(plan_json=plan.model_dump_json(),bindings_json=json.dumps(ns['bindings']),
                              registry_fingerprint=self.registry.fingerprint)
        return Scheduler(executor=AgentExecutor(bound,self.registry))

    def read_agent_trace(self, run_id, actor):
        from app.agents.trace import ProfessionalTraceStore
        return ProfessionalTraceStore(self.engine).read(run_id,actor)

"""Owned-plan adapter into the original Runtime and Scheduler, without a new engine."""
import hashlib,json
from app.agents.service import ProfessionalRuntimeService
from app.agents.contracts import AgentFrameworkError,BoundAgentPlan,fingerprint
from app.agents.router import AgentRouter
from app.agents.executor import AgentExecutor
from app.agents.investigation.roles import ROLES,PROMPT_VERSION,REGISTRY_VERSION
from app.agents.investigation.planning import InvestigationPlan
from app.runtime.service import RuntimeService
from app.runtime.contracts import TaskPlan,TaskContract,json_bytes,METADATA_LIMIT
from app.runtime.scheduler import Scheduler

class InvestigationRuntimeAdapter(ProfessionalRuntimeService):
    def run_plan(self,plan,actor,request_key):
        json_bytes(plan.route,METADATA_LIMIT)
        plan=TaskPlan.model_validate_json(plan.model_dump_json())
        if 'professional_agents_v1' in plan.route or not plan.route.get('planner_run_id'):
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        audit=self.planner_store.read(plan.route['planner_run_id'],actor)
        validated=audit.validated_plan
        if audit.validation_status!='VALIDATED' or validated is None or audit.prompt_version!=PROMPT_VERSION or audit.registry_version!=REGISTRY_VERSION:
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        if hashlib.sha256(validated.runtime_plan_json.encode()).hexdigest()!=validated.plan_hash:
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        canonical=TaskPlan.model_validate_json(validated.runtime_plan_json)
        if fingerprint(plan.model_dump(mode='json'))!=fingerprint(canonical.model_dump(mode='json')):
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        candidate=InvestigationPlan.model_validate_json(validated.candidate_json)
        semantics=json.loads(validated.semantic_types_json)
        if semantics!={t.task_id:t.planner_type for t in candidate.tasks}:
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        tasks=tuple(TaskContract.model_validate({k:v for k,v in t.model_dump().items() if k!='planner_type'}) for t in candidate.tasks)
        if tasks!=plan.tasks:raise AgentFrameworkError('AGENT_PLAN_INVALID')
        bound=AgentRouter(self.registry,task_registry=ROLES).bind_plan(plan,semantics,self.policy)
        return RuntimeService.run_plan(self,bound.captured_plan,actor,request_key)
    def _make_scheduler(self,plan):
        ns=plan.route.get('professional_agents_v1')
        if ns is None:return RuntimeService._make_scheduler(self,plan)
        if ns['registry_fingerprint']!=self.registry.fingerprint or fingerprint(ns['registry'])!=self.registry.fingerprint:
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        bound=BoundAgentPlan(plan_json=plan.model_dump_json(),bindings_json=json.dumps(ns['bindings']),registry_fingerprint=self.registry.fingerprint)
        return Scheduler(executor=AgentExecutor(bound,self.registry,task_registry=ROLES))


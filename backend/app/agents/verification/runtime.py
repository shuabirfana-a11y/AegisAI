"""Server-constructed verification plans enter the existing Runtime unchanged."""
import json
from app.agents.contracts import AgentFrameworkError,BoundAgentPlan,fingerprint
from app.agents.router import AgentRouter
from app.agents.executor import AgentExecutor
from app.agents.verification.context_store import VerificationContextStore
from app.agents.verification.registry import create_verification_registry
from app.agents.verification.roles import TOOLS,ROLES
from app.runtime.contracts import TaskContract,TaskPlan
from app.runtime.service import RuntimeService
from app.runtime.scheduler import Scheduler


def verification_plan(context):
    tool=TOOLS[context.request.task_type]
    task=TaskContract(task_id='verify',description='Read-only '+context.request.task_type,max_tool_calls=1,
        allowed_tools=(tool,),timeout_seconds=30,acceptance_criteria=('tools_succeeded','output_nonempty'),
        input_data={'steps':[{'name':tool,'arguments':{'context_id':str(context.context_id),
                                                     'claim_ids':list(context.request.claim_ids)}}]})
    return TaskPlan(tasks=(task,),route={'verification_v1':{
        'context_id':str(context.context_id),'source_snapshot_hash':context.source_snapshot_hash,
        'request_hash':context.request_hash,'rules_version':context.rules_version,
        'source_run_id':str(context.snapshot.source_run_id),'source_artifact_id':str(context.snapshot.source_artifact_id),
        'parent_planner_run_id':context.snapshot.parent_planner_run_id}})


class VerificationRuntimeAdapter(RuntimeService):
    def __init__(self,engine,*,policy=None,registry=None):
        super().__init__(engine,policy=policy)
        self.registry=(registry or create_verification_registry()).freeze()
        self.context_store=VerificationContextStore(engine)

    def run(self,*args,**kwargs):raise AgentFrameworkError('AGENT_PLAN_INVALID')
    def run_plan(self,*args,**kwargs):raise AgentFrameworkError('AGENT_PLAN_INVALID')

    def run_context(self,context,*,actor):
        saved=self.context_store.read(context.context_id,actor=actor)
        if fingerprint(saved.model_dump(mode='json'))!=fingerprint(context.model_dump(mode='json')):
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        plan=verification_plan(saved)
        bound=AgentRouter(self.registry,task_registry=ROLES).bind_plan(plan,{'verify':saved.request.task_type},self.policy)
        key='verification:'+fingerprint([actor,saved.request.request_key])
        return RuntimeService.run_plan(self,bound.captured_plan,actor,key)

    def _make_scheduler(self,plan):
        ns=plan.route.get('professional_agents_v1')
        if (not ns or not plan.route.get('verification_v1') or ns['registry_fingerprint']!=self.registry.fingerprint
            or fingerprint(ns['registry'])!=self.registry.fingerprint):
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        bound=BoundAgentPlan(plan_json=plan.model_dump_json(),bindings_json=json.dumps(ns['bindings']),
                             registry_fingerprint=self.registry.fingerprint)
        return Scheduler(executor=AgentExecutor(bound,self.registry,task_registry=ROLES))

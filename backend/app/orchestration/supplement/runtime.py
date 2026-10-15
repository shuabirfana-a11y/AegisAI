"""Server-generated fixed evidence task through the unchanged Router/Executor/DAG."""
from app.runtime.contracts import TaskPlan,TaskContract,RuntimePolicy
from app.runtime.service import RuntimeService
from app.agents.investigation.runtime import InvestigationRuntimeAdapter
from app.agents.investigation.registry import create_investigation_registry
from app.agents.investigation.agent import IntelligenceInvestigationAgent
from app.agents.investigation.roles import ROLES
from app.agents.router import AgentRouter
from app.agents.contracts import fingerprint
from app.agents.asset_observations import InvestigationArtifactReference
from app.orchestration.handoff import artifact_ref

def plan_for(record):
    spec=record.spec
    steps=[{'name':'get_evidence','arguments':{'target':spec.target,'claim_id':id,'limit':16}} for id in spec.claim_ids]
    task=TaskContract(task_id='supplement_evidence',description='Read source evidence for explicitly unresolved scoped Claims',
        input_data={'steps':steps},allowed_tools=('get_evidence',),max_tool_calls=len(steps),
        acceptance_criteria=('tools_succeeded','output_nonempty','evidence_present'))
    return TaskPlan(tasks=(task,),route={'supplement_v1':{'supplement_id':str(record.summary.supplement_id),
        'parent_investigation_id':str(spec.parent_investigation_id),'gap_hash':spec.gap_hash,
        'parent_integration_id':str(spec.parent_integration_id)}})

class SupplementRuntime(InvestigationRuntimeAdapter):
    def __init__(self,engine,record):
        super().__init__(engine,registry=create_investigation_registry(IntelligenceInvestigationAgent()),
            policy=RuntimePolicy(max_tool_calls=len(record.spec.claim_ids),max_tasks=1,max_parallel=1))
        self.record=record
    def run_fixed(self,actor):
        if actor!=self.record.context.owner:raise PermissionError('Owner mismatch')
        # The client supplies no plan or scope. Every task is fixed from the
        # atomically claimed spec, with the existing semantic/tool whitelist.
        plan=plan_for(self.record)
        bound=AgentRouter(self.registry,task_registry=ROLES).bind_plan(plan,{'supplement_evidence':'evidence_search'},self.policy)
        return RuntimeService.run_plan(self,bound.captured_plan,actor,'supplement:'+str(self.record.summary.supplement_id)+':evidence')

def read_extra_sources(engine,request,actor):
    """Validate the cross-run extension before the original Snapshot reader uses it."""
    from sqlalchemy import select
    from app.db import models as m
    from app.db.session import transaction
    from app.orchestration.supplement.store import SupplementStore
    from app.agents.investigation.reader import InvestigationReader
    store=SupplementStore(engine)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,request.supplement_id)
        record=store._decode(row,actor)
    spec=record.spec;ref=spec.source_artifact
    if (request.source_run_id,request.source_task_id,request.source_artifact_id)!=(ref.run_id,ref.task_id,ref.artifact_id):
        raise ValueError('SUPPLEMENT_SOURCE_MISMATCH')
    if request.request_key!=record.context.stage_keys['verification'] or tuple(request.supporting_artifacts)!=tuple(
            InvestigationArtifactReference(
                run_id=r.run_id,task_id=r.task_id,artifact_id=r.artifact_id) for r in spec.supporting_artifacts):
        raise ValueError('SUPPLEMENT_REQUEST_BINDING_INVALID')
    if request.asset_id!=record.context.resolved_scope.planner_input.query.asset_id or request.component_id!=record.context.resolved_scope.planner_input.component_id:
        raise ValueError('SUPPLEMENT_ASSET_MISMATCH')
    rid=record.summary.acquisition_run_id
    if rid is None or record.summary.acquisition_artifact is None:raise ValueError('SUPPLEMENT_RECEIPT_MISSING')
    actual=InvestigationReader(engine).read(rid,actor)
    if len(actual.artifacts)!=1 or actual.artifacts[0].partial_result or actual.artifacts[0].runtime_status!='SUCCESS':
        raise ValueError('SUPPLEMENT_EXECUTION_INCOMPLETE')
    if artifact_ref(actual.artifacts[0])!=record.summary.acquisition_artifact:
        raise ValueError('SUPPLEMENT_ARTIFACT_BINDING_INVALID')
    with transaction(engine) as db:
        row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==rid,m.AgentRun.actor_principal==actor,m.AgentRun.agent_type=='runtime-v1'))
        ns=row.details['runtime_v1'];plan=TaskPlan.model_validate(ns['plan']);expected=plan_for(record)
        if plan.tasks!=expected.tasks or plan.route.get('supplement_v1')!=expected.route['supplement_v1']:
            raise ValueError('SUPPLEMENT_PLAN_CHANGED')
        return row.id,plan,ns

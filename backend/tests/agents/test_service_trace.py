import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from app.runtime.contracts import RuntimePolicy, TaskPlan
from tests.planner.test_end_to_end import seeded_plan,seeded_input
from tests.planner.fixtures import gateway_with_responses
from tests.agents.test_executor import delegate_registry


def service_for(engine,plans,registry=None,policy=None):
    from app.agents.service import ProfessionalRuntimeService
    from app.planner.llm_planner import LLMTaskPlanner
    from app.planner.trace import PlannerTraceStore
    from app.planner.service import PlannerService
    policy=policy or RuntimePolicy()
    gateway,calls,_=gateway_with_responses(plans)
    runtime=ProfessionalRuntimeService(engine,registry=registry,policy=policy)
    return PlannerService(engine,LLMTaskPlanner(gateway,PlannerTraceStore(engine)),runtime,policy),gateway,calls


def test_default_runtime_hook_preserves_original_behavior(engine):
    from app.runtime.service import RuntimeService
    from app.runtime.scheduler import Scheduler
    from tests.agents.fixtures import task
    assert type(RuntimeService(engine)._make_scheduler(TaskPlan(tasks=[task()]))) is Scheduler


def test_professional_runtime_reads_owned_validated_planner_types(engine,runtime_seed):
    from app.agents.trace import ProfessionalTraceStore
    svc,gw,calls=service_for(engine,[seeded_plan(runtime_seed)])
    try:
        saved=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
        trace=ProfessionalTraceStore(engine).read(saved.runtime_run_id,runtime_seed.actor)
        assert trace.agents[0].agent_id=='investigation_agent'
        assert trace.agents[0].status=='FAILED' and trace.agents[0].attempted
        assert trace.agents[0].capability_state=='interface_only'
        assert trace.agents[0].errors[0]['code']=='AGENT_NOT_IMPLEMENTED'
        assert trace.artifacts[0].result=={} and len(calls)==1
    finally:gw.close()


@pytest.mark.parametrize('change',['owner','binding','task','planner_id'])
def test_forged_plan_binding_or_other_actor_is_rejected(engine,runtime_seed,change):
    from app.agents.contracts import AgentFrameworkError
    from app.planner.trace import PlannerTraceStore
    svc,gw,_=service_for(engine,[seeded_plan(runtime_seed)])
    try:
        saved=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
        trace=PlannerTraceStore(engine).read(saved.planner_run_id,runtime_seed.actor)
        plan=TaskPlan.model_validate_json(trace.validated_plan.runtime_plan_json);actor=runtime_seed.actor
        if change=='owner':actor='someone-else'
        if change=='binding':plan.route['professional_agents_v1']={'fake':True}
        if change=='task':plan=TaskPlan(tasks=[plan.tasks[0].model_copy(update={'description':'Forged'})],route=plan.route)
        if change=='planner_id':plan.route['planner_run_id']=str(uuid4())
        with pytest.raises((AgentFrameworkError,LookupError)):
            svc.runtime.run_plan(plan,actor,'forged-'+uuid4().hex)
    finally:gw.close()


def test_registry_change_conflicts_on_same_request_key(engine,runtime_seed):
    from app.agents.service import ProfessionalRuntimeService
    from app.assistant.storage import IdempotencyConflict
    from app.planner.trace import PlannerTraceStore
    svc,gw,_=service_for(engine,[seeded_plan(runtime_seed)])
    try:
        saved=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
        trace=PlannerTraceStore(engine).read(saved.planner_run_id,runtime_seed.actor)
        new_runtime=ProfessionalRuntimeService(engine,registry=delegate_registry(process=True))
        with pytest.raises(IdempotencyConflict):
            new_runtime.run_plan(TaskPlan.model_validate_json(trace.validated_plan.runtime_plan_json),runtime_seed.actor,
                'planner-runtime:'+str(saved.planner_run_id))
    finally:gw.close()


def test_trace_rebuilds_chain_from_persisted_artifacts(engine,runtime_seed):
    from app.agents.trace import ProfessionalTraceStore
    svc,gw,_=service_for(engine,[seeded_plan(runtime_seed)],delegate_registry(process=True))
    try:
        saved=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
        trace=ProfessionalTraceStore(engine).read(saved.runtime_run_id,runtime_seed.actor)
        assert trace.agents[0].status=='SUCCESS' and trace.agents[0].execution_time>=0
        assert trace.agents[0].output_artifact.artifact_id==trace.artifacts[0].artifact_id
        assert trace.artifacts[0].tool_calls[0]['record_id']
        assert ProfessionalTraceStore(engine).read(saved.runtime_run_id,runtime_seed.actor)==trace
        with pytest.raises(LookupError):ProfessionalTraceStore(engine).read(saved.runtime_run_id,'someone-else')
    finally:gw.close()


def test_concurrent_tasks_keep_canonical_tool_record_refs(engine,runtime_seed):
    from app.agents.trace import ProfessionalTraceStore
    from tests.planner.fixtures import task
    p=seeded_plan(runtime_seed)
    p['tasks'].append(task(task_id='second',arguments={'target':runtime_seed.cve}))
    svc,gw,_=service_for(engine,[p],delegate_registry(process=True))
    try:
        saved=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
        trace=ProfessionalTraceStore(engine).read(saved.runtime_run_id,runtime_seed.actor)
        assert len(trace.agents)==len(trace.artifacts)==2
        assert all(n.status=='SUCCESS' for n in trace.agents)
        assert len({a.tool_calls[0]['record_id'] for a in trace.artifacts})==2
    finally:gw.close()


def test_blocked_and_interface_only_are_not_reported_success(engine,runtime_seed):
    from app.agents.trace import ProfessionalTraceStore
    from tests.planner.fixtures import task
    p=seeded_plan(runtime_seed)
    p['tasks'].append(task('patch_analysis','patch','find_patch_candidates',{'target':runtime_seed.cve},['lookup']))
    svc,gw,_=service_for(engine,[p])
    try:
        saved=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
        trace=ProfessionalTraceStore(engine).read(saved.runtime_run_id,runtime_seed.actor)
        assert [n.status for n in trace.agents]==['FAILED','BLOCKED']
        assert [n.attempted for n in trace.agents]==[True,False]
        assert trace.agents[1].input_artifact==()
    finally:gw.close()

from datetime import date
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.runtime.contracts import TaskPlan, RuntimePolicy
from tests.agents.fixtures import task,context,outcome
from tests.agents.test_executor import delegate_registry
from tests.agents.test_service_trace import service_for
from tests.planner.test_end_to_end import seeded_plan,seeded_input


def chain_plan(engine,seed):
    from app.db import models as m
    from app.db.session import transaction
    from app.utils.time import utcnow
    from tests.planner.fixtures import task as planner_task
    with transaction(engine) as db:
        vulnerability=db.scalar(select(m.Vulnerability).where(m.Vulnerability.canonical_id==seed.cve))
        raw=db.scalar(select(m.RawDocument).where(m.RawDocument.external_id==seed.cve))
        db.add(m.EpssSnapshot(vulnerability_id=vulnerability.id,source_id=raw.source_id,raw_document_id=raw.id,
            score=Decimal('0.123'),percentile=Decimal('0.5'),score_date=date.today(),observed_at=utcnow(),
            model_version='SYNTHETIC_FRAMEWORK_'+uuid4().hex,details={'is_test':True,'not_benchmark':True}))
    plan=seeded_plan(seed)
    plan['tasks'] += [planner_task('evidence_search','evidence','get_evidence',{'target':seed.cve},['lookup']),
                     planner_task('risk_analysis','risk','get_epss',{'target':seed.cve},['evidence'])]
    plan['tasks'][1]['acceptance_criteria'].append('evidence_present')
    return plan


def test_planner_runtime_agent_artifact_chain(engine,runtime_seed):
    from app.agents.trace import ProfessionalTraceStore
    observations=[];registry=delegate_registry(process=True,observations=observations)
    svc,gw,calls=service_for(engine,[chain_plan(engine,runtime_seed)],registry)
    try:
        saved=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
        trace=ProfessionalTraceStore(engine).read(saved.runtime_run_id,runtime_seed.actor)
        assert [n.agent_id for n in trace.agents]==['investigation_agent','verification_agent','security_analysis_agent']
        assert all(n.status=='SUCCESS' and n.attempted for n in trace.agents)
        assert saved.runtime_status=='COMPLETED' and len(calls)==1
        assert len(observations)==3
        for previous,current in zip(trace.agents,trace.agents[1:]):
            assert current.input_artifact[0].artifact_id==previous.output_artifact.artifact_id
            assert current.input_artifact[0].run_id==saved.runtime_run_id
        assert all(a.confidence is None for a in trace.artifacts)
        assert any(r.get('verified') is False for r in trace.artifacts[1].evidence)
        assert trace.artifacts[2].result['dependencies']=={'evidence':str(trace.artifacts[1].artifact_id)}
    finally:gw.close()


def test_interface_only_dependency_blocks_next_agent(engine,runtime_seed):
    from app.agents.trace import ProfessionalTraceStore
    svc,gw,_=service_for(engine,[chain_plan(engine,runtime_seed)])
    try:
        saved=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
        trace=ProfessionalTraceStore(engine).read(saved.runtime_run_id,runtime_seed.actor)
        assert [a.status for a in trace.agents]==['FAILED','BLOCKED','BLOCKED']
        assert [a.attempted for a in trace.agents]==[True,False,False]
        assert not any(a.tool_calls for a in trace.artifacts)
    finally:gw.close()


def test_repeat_request_does_not_reexecute_or_change_binding(engine,runtime_seed):
    observations=[];registry=delegate_registry(process=True,observations=observations)
    svc,gw,calls=service_for(engine,[seeded_plan(runtime_seed)],registry)
    try:
        request=seeded_input(runtime_seed)
        first=svc.plan_and_run(request,runtime_seed.actor)
        second=svc.plan_and_run(request,runtime_seed.actor)
        assert first==second and len(calls)==len(observations)==1
    finally:gw.close()


def test_agent_deadline_does_not_extend_task_timeout(monkeypatch):
    from app.agents.executor import AgentExecutor
    from app.agents.router import AgentRouter
    import app.agents.executor as executor_module
    clock={'now':10.0}
    monkeypatch.setattr(executor_module.time,'monotonic',lambda:clock['now'])
    def action(request):
        result=outcome(request.task,request.context)
        clock['now']=12.0
        return result
    snapshot=delegate_registry(action=action,timeout=30).freeze()
    item=task(timeout_seconds=1)
    bound=AgentRouter(snapshot).bind_plan(TaskPlan(tasks=[item]),{'lookup':'vulnerability_lookup'},RuntimePolicy())
    got=AgentExecutor(bound,snapshot).execute(item,context(deadline=100),{})
    assert got.artifact.status=='FAILED' and got.artifact.errors[0]['code']=='TASK_TIMEOUT'
    assert len(got.receipts)==1


def test_registered_prototype_cancellation_does_not_cross_runs(engine,runtime_seed):
    from app.agents.executor import AgentExecutor
    from app.agents.router import AgentRouter
    snapshot=delegate_registry(process=True).freeze()
    item=task(arguments={'target':runtime_seed.cve})
    bound=AgentRouter(snapshot).bind_plan(TaskPlan(tasks=[item]),{'lookup':'vulnerability_lookup'},RuntimePolicy())
    first=AgentExecutor(bound,snapshot);second=AgentExecutor(bound,snapshot)
    url=engine.url.render_as_string(hide_password=False)
    assert first.execute(item,context(actor=runtime_seed.actor),{},database_url=url).artifact.status=='SUCCESS'
    first.cancel_all()
    assert second.execute(item,context(actor=runtime_seed.actor),{},database_url=url).artifact.status=='SUCCESS'

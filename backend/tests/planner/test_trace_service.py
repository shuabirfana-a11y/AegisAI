import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from app.db import models as m
from app.db.session import transaction
from app.runtime.contracts import RuntimePolicy
from app.runtime.service import RuntimeService
from app.planner.trace import PlannerTraceStore
from app.planner.service import PlannerService
from app.planner.llm_planner import LLMTaskPlanner
from app.assistant.storage import IdempotencyConflict, create_run, summary
from tests.planner.fixtures import valid_plan,cve_input,gateway_with_responses,context_for

def counts(engine):
    with transaction(engine) as s:return (s.scalar(select(func.count()).select_from(m.AgentRun).where(m.AgentRun.agent_type=='runtime-v1')),
        s.scalar(select(func.count()).select_from(m.ToolCallRecord)))

def service_for(engine,responses,policy=None):
    policy=policy or RuntimePolicy();gw,calls,records=gateway_with_responses(responses)
    planner=LLMTaskPlanner(gw,PlannerTraceStore(engine))
    return PlannerService(engine,planner,RuntimeService(engine,policy=policy),policy),gw,calls,records

def test_real_attempt_trace_and_runtime_count(engine,runtime_seed):
    i=cve_input(target=runtime_seed.cve,question=runtime_seed.cve+'是什么？');p=valid_plan()
    p['tasks'][0]['input_data']['steps'][0]['arguments']['target']=runtime_seed.cve
    service,gw,calls,records=service_for(engine,['PRIVATE_BAD_JSON',p])
    saved=service.plan_and_run(i,runtime_seed.actor)
    tr=service.read_trace(saved.planner_run_id,runtime_seed.actor)
    assert tr.validation_status=='VALIDATED' and tr.retry_count==1 and tr.latency>=0
    assert tr.generated_plan and len(tr.attempts)==2 and tr.attempts[0].diagnostic['raw_output']=='PRIVATE_BAD_JSON'
    assert tr.model.is_mock and tr.prompt_version and tr.attempts[0].model_call['request_id']==records.records[0].request_id
    assert saved.runtime_run_id and saved.runtime_status=='COMPLETED'
    with transaction(engine) as db:
        row=db.get(m.AgentRun,saved.runtime_run_id)
        assert row.details['result']['generation_calls']==2
        assert len([e for e in row.details['events'] if e.get('state')=='model_called'])==2
        assert 'PRIVATE_BAD_JSON' not in json.dumps(row.details)
        planner_row=db.get(m.AgentRun,saved.planner_run_id)
        assert 'PRIVATE_BAD_JSON' not in json.dumps(summary(planner_row),default=str)
    gw.close()

def test_idempotency_returns_same_run_and_rejects_changed_body(engine):
    service,gw,calls,records=service_for(engine,[valid_plan()]);i=cve_input();actor='planner-owner-'+uuid4().hex
    first=service.plan_and_run(i,actor);before=counts(engine);second=service.plan_and_run(i,actor)
    assert first==second and len(calls)==1 and counts(engine)==before
    with pytest.raises(IdempotencyConflict):service.plan_and_run(cve_input(request_key=i.query.request_key,question='changed'),actor)
    gw.close()

def test_owner_and_type_scope(engine):
    service,gw,calls,records=service_for(engine,['{bad']);actor='owner-'+uuid4().hex
    saved=service.plan_and_run(cve_input(),actor)
    with pytest.raises(LookupError):service.read_trace(saved.planner_run_id,'other')
    with pytest.raises(LookupError):service.read_trace(uuid4(),actor)
    gw.close()

def test_concurrent_creation_exactly_one_fresh_and_old_namespace(engine):
    store=PlannerTraceStore(engine);i=cve_input();actor='owner-'+uuid4().hex
    service,gw,calls,records=service_for(engine,[valid_plan()]);planner=service.planner
    def create():return store.create(i,actor,RuntimePolicy(),model_identity=planner.model_identity,
                                      prompt_version=planner.prompt_version,registry_version=planner.registry_version)
    with ThreadPoolExecutor(4) as pool:results=list(pool.map(lambda _:create(),range(4)))
    assert sum(f for _,f in results)==1 and len({s.planner_run_id for s,f in results})==1
    assert not calls
    with transaction(engine) as db:
        old,fresh=create_run(db,i.query,actor)
        assert fresh and old.id!=results[0][0].planner_run_id
    gw.close()

def test_validation_failure_never_starts_runtime(engine):
    service,gw,calls,records=service_for(engine,['{bad','{bad']);before=counts(engine)
    saved=service.plan_and_run(cve_input(),'owner-'+uuid4().hex)
    assert saved.planning_status=='PLANNING_FAILED' and not saved.runtime_run_id
    assert counts(engine)==before
    gw.close()

def test_audit_save_failure_stops_tools(engine,monkeypatch):
    service,gw,calls,records=service_for(engine,[valid_plan()]);before=counts(engine)
    monkeypatch.setattr(service.planner.trace_sink,'record_attempt',lambda *args: (_ for _ in ()).throw(OSError()))
    saved=service.plan_and_run(cve_input(),'owner-'+uuid4().hex)
    assert saved.planning_status=='PLANNING_FAILED' and counts(engine)==before
    gw.close()

def test_changed_policy_does_not_use_cached_authorization(engine):
    service,gw,calls,records=service_for(engine,[valid_plan()]);i=cve_input();actor='owner-'+uuid4().hex
    service.plan_and_run(i,actor)
    other,gw2,c2,r2=service_for(engine,[valid_plan()],RuntimePolicy(max_tool_calls=0))
    with pytest.raises(IdempotencyConflict):other.plan_and_run(i,actor)
    assert not c2;gw.close();gw2.close()

def test_unmatched_policy_rejected(engine):
    service,gw,calls,records=service_for(engine,[valid_plan()])
    with pytest.raises(ValueError):PlannerService(engine,service.planner,service.runtime,RuntimePolicy(max_tool_calls=0))
    gw.close()

@pytest.mark.parametrize('old_status',['PLANNING','RUNNING'])
def test_late_pending_snapshot_cannot_regress_completed_runtime(engine,runtime_seed,old_status):
    from app.runtime.contracts import RunSnapshot
    from tests.planner.test_end_to_end import seeded_plan,seeded_input
    service,gw,calls,records=service_for(engine,[seeded_plan(runtime_seed)])
    finished=service.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
    runtime_trace=service.runtime.read_trace(finished.runtime_run_id,runtime_seed.actor)
    late=RunSnapshot(run_id=finished.runtime_run_id,trace_id=runtime_trace.trace_id,status=old_status)
    updated=service.store.link_runtime(finished.planner_run_id,runtime_seed.actor,late)
    assert updated.runtime_status=='COMPLETED'
    assert service.read_trace(finished.planner_run_id,runtime_seed.actor).runtime_status=='COMPLETED'
    gw.close()

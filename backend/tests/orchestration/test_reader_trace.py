from copy import deepcopy
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import fingerprint
from app.orchestration.contracts import NAMESPACE,TYPE


def test_duplicate_completed_request_reuses_answer_without_any_new_run(engine,completed_chain):
    seed,request,svc,result,calls=completed_chain
    with transaction(engine) as db:before=db.scalar(select(func.count()).select_from(m.AgentRun).where(m.AgentRun.actor_principal==seed.actor))
    again=svc.investigate(request.model_copy(update={'request_id':uuid4()}),actor=seed.actor)
    assert again.answer==result.answer and len(calls)==1
    with transaction(engine) as db:assert before==db.scalar(select(func.count()).select_from(m.AgentRun).where(m.AgentRun.actor_principal==seed.actor))


def test_trace_is_owner_bound_and_links_real_tools_and_artifacts(engine,completed_chain):
    seed,_,svc,result,_=completed_chain
    id=result.context.logical_investigation_id
    trace=svc.get_trace(id,actor=seed.actor)
    assert trace.answer_id==result.answer.answer_id and trace.integration_result_id==result.context.integration_result_id
    assert len(trace.agent_runs)==3 and all(run.tool_calls for run in trace.agent_runs)
    assert trace.planner.validation_status=='VALIDATED'
    assert {r.run_id for r in trace.agent_runs}==set(result.answer.agent_run_references)
    with pytest.raises(LookupError):svc.get_trace(id,actor='other-owner')
    with pytest.raises(LookupError):svc.get_result(id,actor='other-owner')
    assert 'worker_token' not in trace.model_dump_json()


def test_rehashed_answer_tamper_is_rejected_against_frozen_gate(engine,completed_chain):
    seed,_,svc,result,_=completed_chain;id=result.context.logical_investigation_id
    with transaction(engine) as db:
        row=db.get(m.AgentRun,id);saved=deepcopy(row.details);raw=deepcopy(row.details)
        raw[NAMESPACE]['answer']['summary']='A fabricated successful answer'
        raw[NAMESPACE]['answer_hash']=fingerprint(raw[NAMESPACE]['answer']);row.details=raw
    try:
        with pytest.raises(ValueError,match='ANSWER'):svc.get_result(id,actor=seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,id).details=saved


def test_trace_reads_legitimate_active_run_before_planner_link_is_written(engine,monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from app.orchestration.service import InvestigationOrchestrator
    from app.runtime.process import ProcessSupervisor
    from tests.orchestration.fixtures import scenario
    entered=threading.Event();release=threading.Event();original=ProcessSupervisor.execute
    def paused(self,*a,**k):entered.set();assert release.wait(15);return original(self,*a,**k)
    monkeypatch.setattr(ProcessSupervisor,'execute',paused)
    seed,request,gw,_,_=scenario(engine);svc=InvestigationOrchestrator(engine,gw)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(svc.investigate,request,actor=seed.actor)
            try:
                assert entered.wait(15)
                with transaction(engine) as db:id=db.scalar(select(m.AgentRun.id).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==seed.actor))
                trace=svc.get_trace(id,actor=seed.actor)
                assert trace.planner.validation_status=='VALIDATED' and len(trace.agent_runs)==1 and trace.answer_id is None
                assert trace.agent_runs[0].run_id==svc.get_status(id,actor=seed.actor).investigation_run_id
            finally:release.set()
            assert future.result(timeout=30).status.overall_status=='SUCCEEDED'
    finally:release.set();gw.close()


def test_historical_answer_does_not_refresh_sources_or_repeat_gate(engine,completed_chain):
    seed,_,svc,result,_=completed_chain
    with transaction(engine) as db:
        source=db.get(m.Source,seed.source_id);old=source.authority_level;source.authority_level='community'
    try:
        assert svc.get_result(result.context.logical_investigation_id,actor=seed.actor).answer==result.answer
    finally:
        with transaction(engine) as db:db.get(m.Source,seed.source_id).authority_level=old


def test_trace_retains_real_run_after_planner_link_failure_and_rejects_wrong_backlink(engine,monkeypatch):
    from app.orchestration.service import InvestigationOrchestrator
    from app.planner.trace import PlannerTraceStore
    from tests.orchestration.fixtures import scenario
    def failed_link(*a,**kw):raise RuntimeError('Synthetic Planner link-write failure')
    monkeypatch.setattr(PlannerTraceStore,'link_runtime',failed_link)
    seed,request,gw,_,_=scenario(engine);svc=InvestigationOrchestrator(engine,gw)
    try:
        result=svc.investigate(request,actor=seed.actor)
        assert result.answer.answer_status=='FAILED' and result.context.investigation_run_id
        trace=svc.get_trace(result.context.logical_investigation_id,actor=seed.actor)
        assert len(trace.agent_runs)==1 and trace.agent_runs[0].run_id==result.context.investigation_run_id
        with transaction(engine) as db:
            row=db.get(m.AgentRun,result.context.investigation_run_id);saved=deepcopy(row.details);raw=deepcopy(saved)
            raw['runtime_v1']['plan']['route']['planner_run_id']=str(uuid4());row.details=raw
        try:
            with pytest.raises(ValueError,match='TRACE_PLANNER_RUN_MISMATCH'):
                svc.get_trace(result.context.logical_investigation_id,actor=seed.actor)
        finally:
            with transaction(engine) as db:db.get(m.AgentRun,result.context.investigation_run_id).details=saved
    finally:gw.close()


def test_result_status_comes_from_same_atomic_snapshot(engine,completed_chain,monkeypatch):
    seed,_,svc,result,_=completed_chain
    monkeypatch.setattr(svc.store,'status',lambda *a,**k:(_ for _ in ()).throw(AssertionError('A second read can race')))
    actual=svc.get_result(result.context.logical_investigation_id,actor=seed.actor)
    assert actual.context.revision==actual.status.revision


def test_schema_and_cross_gate_binding_tamper_are_rejected(engine,completed_chain):
    seed,_,svc,result,_=completed_chain;id=result.context.logical_investigation_id
    with transaction(engine) as db:
        row=db.get(m.AgentRun,id);saved=deepcopy(row.details);raw=deepcopy(row.details)
        raw[NAMESPACE]['context']['integration_result_id']=str(uuid4())
        raw[NAMESPACE]['context_hash']=fingerprint(raw[NAMESPACE]['context']);row.details=raw
    try:
        with pytest.raises(LookupError):svc.get_result(id,actor=seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,id).details=saved

import threading
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func
import pytest
from app.db import models as m
from app.db.session import transaction
from app.orchestration.contracts import TYPE
from app.integration.service import IntegrationService
from tests.orchestration.fixtures import scenario


@pytest.mark.parametrize('mode,status',[('optional_failure','PASS_WITH_WARNINGS'),
    ('insufficient','REPLAN_REQUIRED'),('conflict','HUMAN_REVIEW_REQUIRED'),('unknown_version','REPLAN_REQUIRED')])
def test_real_chain_preserves_domain_statuses(engine,mode,status):
    from app.orchestration.service import InvestigationOrchestrator
    from app.agents.analysis.service import SecurityAnalysisService
    seed,request,gw,_,_=scenario(engine,mode)
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        gate=IntegrationService(engine).read(result.context.integration_result_id,actor=seed.actor)
        assert gate.status==status,(gate.status,gate.blocking_issues)
        if mode=='insufficient':assert result.context.verification_run_id is None and result.context.analysis_run_id is None
        if mode in ('conflict','unknown_version'):
            risk=SecurityAnalysisService(engine).read_results(result.context.analysis_run_id,actor=seed.actor).artifacts[0]
            assert risk.risk_level=='UNKNOWN' and risk.affected is None and risk.priority=='REVIEW_REQUIRED'
        if mode=='conflict':
            from app.orchestration.answer_sources import AnswerSourcesLoader
            source,_,_=AnswerSourcesLoader(engine).load(result.context,actor=seed.actor)
            all_evidence={e.evidence_id for e in (*source.verification.supporting_evidence,*source.verification.conflicting_evidence)}
            assert all_evidence<=set(result.answer.evidence_references)
            conflicts={c.claim.claim_id for c in source.verification.claims if c.status=='CONFLICT'}
            assert conflicts and conflicts<={c.claim_id for c in result.answer.disputed_claims}
            assert not conflicts&{c.claim_id for c in result.answer.verified_claims}
            observations={e.evidence_id:e for e in result.answer.evidence_observations}
            for e in (*source.verification.supporting_evidence,*source.verification.conflicting_evidence):
                assert (observations[e.evidence_id].hash,observations[e.evidence_id].claim_id)==(e.hash,e.claim_id)
                assert observations[e.evidence_id].conclusion_scope=='OBSERVATION'
    finally:gw.close()


def test_unsupported_calendar_scope_blocks_actual_gate_pass(engine):
    from app.orchestration.service import InvestigationOrchestrator
    seed,request,gw,_,_=scenario(engine)
    raw=request.model_dump(mode='json')
    raw['planner_input']['query']['question']='仅依据2025年1月1日至2025年1月31日的资料，'+request.user_query
    request=type(request).model_validate(raw)
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        assert 'UNSUPPORTED_TIME_SCOPE' in result.context.resolved_scope.objective.scope_gaps
        assert result.context.analysis_run_id and result.answer.integration_status=='REPLAN_REQUIRED'
        assert result.answer.answer_status=='INCOMPLETE' and result.answer.original_question==request.user_query
        gate=IntegrationService(engine).read(result.context.integration_result_id,actor=seed.actor)
        assert any(c.code=='UNSUPPORTED_TIME_SCOPE' for c in gate.checks)
    finally:gw.close()


def test_planning_failure_is_terminal_and_creates_no_agent_run(engine):
    from app.orchestration.service import InvestigationOrchestrator
    from tests.planner.fixtures import gateway_with_responses
    seed,request,old,_,_=scenario(engine);old.close();gw,calls,_=gateway_with_responses([{'invalid_plan':True}])
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        assert result.status.current_stage=='FAILED' and result.context.error_code=='PLANNING_FAILED'
        assert result.context.investigation_run_id is None and len(calls)==2
        with transaction(engine) as db:
            assert db.scalar(select(func.count()).select_from(m.AgentRun).where(m.AgentRun.actor_principal==seed.actor,m.AgentRun.agent_type=='runtime-v1'))==0
    finally:gw.close()


def test_cancel_inflight_model_preserves_planner_and_starts_no_agent(engine):
    from app.orchestration.service import InvestigationOrchestrator
    seed,request,gw,_,_=scenario(engine);entered=threading.Event();release=threading.Event()
    provider=gw.text_provider if hasattr(gw,'text_provider') else gw._text_provider
    original=provider.generate_structured
    def paused(req,schema):
        entered.set();assert release.wait(10);return original(req,schema)
    provider.generate_structured=paused
    svc=InvestigationOrchestrator(engine,gw)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(svc.investigate,request,actor=seed.actor)
            try:
                assert entered.wait(10)
                with transaction(engine) as db:
                    id=db.scalar(select(m.AgentRun.id).where(m.AgentRun.actor_principal==seed.actor,m.AgentRun.agent_type==TYPE))
                assert svc.cancel(id,actor=seed.actor).cancel_requested
            finally:release.set()
            result=future.result(timeout=10)
        assert result.status.current_stage=='CANCELLED' and result.context.planner_run_id
        assert result.context.investigation_run_id is None
        assert svc.get_status(id,actor=seed.actor).overall_status=='CANCELLED'
    finally:release.set();gw.close()


def test_cancel_wins_when_final_seal_has_not_committed(engine,monkeypatch):
    from app.orchestration.store import PostgresInvestigationStore
    from app.orchestration.service import InvestigationOrchestrator
    entered=threading.Event();release=threading.Event();original=PostgresInvestigationStore.seal
    def paused(self,id,**kw):entered.set();assert release.wait(10);return original(self,id,**kw)
    monkeypatch.setattr(PostgresInvestigationStore,'seal',paused)
    seed,request,gw,_,_=scenario(engine);svc=InvestigationOrchestrator(engine,gw)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(svc.investigate,request,actor=seed.actor)
            assert entered.wait(30)
            with transaction(engine) as db:id=db.scalar(select(m.AgentRun.id).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==seed.actor))
            svc.cancel(id,actor=seed.actor);release.set();result=future.result(timeout=10)
        assert result.status.overall_status=='CANCELLED' and result.answer.answer_status=='CANCELLED'
        assert result.answer.integration_status is None and result.context.integration_result_id
        assert not result.answer.verified_claims
        assert svc.get_result(id,actor=seed.actor).answer==result.answer
    finally:release.set();gw.close()


def test_database_write_failure_never_claims_stored_completion_or_leaks_exception(engine,monkeypatch):
    from app.orchestration.store import PostgresInvestigationStore
    from app.orchestration.service import InvestigationOrchestrator
    def unavailable(*a,**k):raise RuntimeError('connection lost api_key=SECRET_DB_VALUE')
    monkeypatch.setattr(PostgresInvestigationStore,'seal',unavailable)
    monkeypatch.setattr(PostgresInvestigationStore,'seal_stop',unavailable)
    seed,request,gw,_,_=scenario(engine)
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        assert result.persistence=='NOT_STORED' and result.answer is None
        assert result.delivery_error=='ORCHESTRATION_PERSISTENCE_FAILED' and result.status.recovery_required
        assert result.status.overall_status=='RUNNING' and 'SECRET_DB_VALUE' not in result.model_dump_json()
        with transaction(engine) as db:assert db.get(m.AgentRun,result.context.logical_investigation_id).finished_at is None
    finally:gw.close()


@pytest.mark.parametrize('mode',['required_partial','blocked','ambiguous'])
def test_essential_partial_blocked_or_ambiguous_stops_downstream(engine,mode):
    from app.orchestration.service import InvestigationOrchestrator
    seed,request,gw,_,_=scenario(engine,mode)
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        assert result.answer.integration_status=='REPLAN_REQUIRED'
        assert result.status.overall_status=='INCOMPLETE'
        assert result.context.verification_run_id is None and result.context.analysis_run_id is None
        assert result.answer.agent_run_references==(result.context.investigation_run_id,)
        if mode=='blocked':
            trace=InvestigationOrchestrator(engine,gw).get_trace(result.context.logical_investigation_id,actor=seed.actor)
            assert trace.agent_runs[0].task_statuses['blocked_child']=='BLOCKED'
    finally:gw.close()


def test_real_gate_rejects_missing_source_artifact_and_answer_has_no_facts(engine,monkeypatch):
    from app.orchestration.service import InvestigationOrchestrator
    from app.orchestration.adapters import AgentServices
    from uuid import uuid4
    from copy import deepcopy
    seed,request,gw,_,_=scenario(engine);original=AgentServices.integrate;saved={}
    def changed(self,request,actor):
        with transaction(engine) as db:
            row=db.get(m.AgentRun,request.investigation.run_id);saved['id']=row.id;saved['details']=deepcopy(row.details)
            raw=deepcopy(row.details);raw['runtime_v1']['artifacts'][request.investigation.task_id]['artifact_id']=str(uuid4());row.details=raw
        return original(self,request,actor)
    monkeypatch.setattr(AgentServices,'integrate',changed)
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        assert result.answer.integration_status=='FAILED' and result.answer.answer_status=='FAILED'
        assert not result.answer.verified_claims and result.answer.risk_assessment is None
        assert result.answer.agent_run_references==(result.context.investigation_run_id,result.context.verification_run_id,result.context.analysis_run_id)
        assert result.answer.accepted_source_run_references==()
        assert IntegrationService(engine).read(result.context.integration_result_id,actor=seed.actor).status=='FAILED'
    finally:
        if saved:
            with transaction(engine) as db:db.get(m.AgentRun,saved['id']).details=saved['details']
        gw.close()


@pytest.mark.parametrize('mode',['cancel','deadline'])
def test_active_investigation_control_reaps_actual_windows_process_tree(engine,monkeypatch,tmp_path,mode):
    import time,json,sys
    from pathlib import Path
    from app.runtime.process import ProcessSupervisor,process_alive
    from app.orchestration.contracts import InvestigationPolicy
    from app.orchestration.service import InvestigationOrchestrator
    fixture=Path(__file__).parents[1]/'runtime/fixtures/slow_worker.py'
    monkeypatch.setenv('AEGIS_RUNTIME_TEST_FOLDER',str(tmp_path))
    monkeypatch.setattr(ProcessSupervisor,'_command',lambda self:[sys.executable,str(fixture)])
    seed,request,gw,_,_=scenario(engine)
    policy=InvestigationPolicy(timeout_seconds=3 if mode=='deadline' else 30,poll_seconds=.02)
    svc=InvestigationOrchestrator(engine,gw,policy=policy)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(svc.investigate,request,actor=seed.actor)
            until=time.monotonic()+10
            while not (tmp_path/'pids.json').exists() and time.monotonic()<until:time.sleep(.02)
            assert (tmp_path/'pids.json').exists()
            with transaction(engine) as db:id=db.scalar(select(m.AgentRun.id).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==seed.actor))
            if mode=='cancel':svc.cancel(id,actor=seed.actor)
            result=future.result(timeout=10)
        assert result.context.error_code==('CANCELLED' if mode=='cancel' else 'DEADLINE_EXCEEDED')
        assert result.context.investigation_run_id and result.context.verification_run_id is None and result.context.analysis_run_id is None
        assert all(not process_alive(pid) for pid in json.loads((tmp_path/'pids.json').read_text()))
        assert not (tmp_path/'late.txt').exists()
        assert svc.get_trace(id,actor=seed.actor).error_code==result.context.error_code
    finally:gw.close()


def test_cancel_at_verification_boundary_creates_no_verification_run(engine,monkeypatch):
    from app.orchestration.service import InvestigationOrchestrator
    from app.orchestration.adapters import AgentServices
    entered=threading.Event();release=threading.Event();original=AgentServices.verify
    def paused(self,req,actor):entered.set();assert release.wait(10);return original(self,req,actor)
    monkeypatch.setattr(AgentServices,'verify',paused)
    seed,request,gw,_,_=scenario(engine);svc=InvestigationOrchestrator(engine,gw)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(svc.investigate,request,actor=seed.actor)
            assert entered.wait(20)
            with transaction(engine) as db:id=db.scalar(select(m.AgentRun.id).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==seed.actor))
            svc.cancel(id,actor=seed.actor);release.set();result=future.result(timeout=10)
        assert result.status.overall_status=='CANCELLED' and result.context.verification_run_id is None
    finally:release.set();gw.close()

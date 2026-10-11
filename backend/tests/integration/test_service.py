from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import threading,time
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from tests.integration.helpers import request

def service(engine):
    from app.integration.service import IntegrationService
    return IntegrationService(engine)

def test_actual_chain_persisted_receipt_and_trace_without_business_writes(engine,gate_chain):
    from tests.agents.analysis.test_end_to_end import counts
    c=gate_chain;svc=service(engine);before=counts(engine)
    got=svc.evaluate(request(c),actor=c.seed.actor)
    assert got.status=='PASS' and got.persistence=='STORED' and len(set(got.source_run_ids))==3
    assert svc.read(got.integration_id,actor=c.seed.actor)==got
    trace=svc.read_trace(got.integration_id,actor=c.seed.actor)
    assert trace.status=='PASS' and trace.integration_id==got.trace_id
    assert len({ch.gate for ch in trace.checks})==6 and trace.evidence_references
    assert counts(engine)==before
    from pathlib import Path
    import json
    out=Path(__file__).resolve().parents[3]/'work/integration'
    (out/'actual_chain_receipt.json').write_text(json.dumps({'synthetic_not_production':True,'integration':got.model_dump(mode='json'),
        'trace':trace.model_dump(mode='json'),'investigation_run':str(c.investigation.run_id),'verification_run':str(c.verification.run_id),
        'analysis_run':str(c.analysis.run_id),'business_counts_unchanged':before==counts(engine)},indent=2),encoding='utf-8')

def test_repeated_key_reuses_fixed_evaluation_time(engine,gate_chain):
    c=gate_chain;svc=service(engine);r=request(c)
    first=svc.evaluate(r,actor=c.seed.actor);second=svc.evaluate(r,actor=c.seed.actor)
    assert first==second and first.status=='PASS'
    with transaction(engine) as db:
        rows=list(db.scalars(select(m.AgentRun).where(m.AgentRun.agent_type=='integration-gate-v1',
            m.AgentRun.actor_principal==c.seed.actor,m.AgentRun.details['integration_v1']['request_key'].astext==r.request_key)))
        assert len(rows)==1

def test_concurrent_same_input_creates_one_result(engine,gate_chain):
    c=gate_chain;r=request(c);svc=service(engine)
    with ThreadPoolExecutor(max_workers=2) as pool:got=list(pool.map(lambda _:svc.evaluate(r,actor=c.seed.actor),range(2)))
    assert got[0]==got[1] and got[0].status=='PASS'

def test_changed_key_content_conflicts(engine,gate_chain):
    from app.assistant.storage import IdempotencyConflict
    c=gate_chain;r=request(c);svc=service(engine);svc.evaluate(r,actor=c.seed.actor)
    with pytest.raises(IdempotencyConflict):svc.evaluate(r.model_copy(update={'objective_profile':'overview_v1'}),actor=c.seed.actor)

def test_changed_snapshot_creates_new_revision_history_stays_fixed(engine,gate_chain):
    c=gate_chain;r=request(c);svc=service(engine);first=svc.evaluate(r,actor=c.seed.actor)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,c.analysis.run_id);old=deepcopy(row.context);row.context={**old,'test_metadata_revision':2}
    try:
        second=svc.evaluate(r,actor=c.seed.actor)
        assert second.status=='PASS' and second.input_hash!=first.input_hash and second.integration_id!=first.integration_id
        assert svc.read(first.integration_id,actor=c.seed.actor)==first
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,c.analysis.run_id).context=old

def test_foreign_actor_cannot_read_or_mix_sources(engine,gate_chain):
    c=gate_chain;svc=service(engine);got=svc.evaluate(request(c),actor=c.seed.actor)
    with pytest.raises(LookupError):svc.read(got.integration_id,actor='other')
    rejected=svc.evaluate(request(c),actor='other')
    assert rejected.status=='FAILED' and not rejected.evidence_references

def test_missing_stage_recorded_replan(engine,gate_chain):
    c=gate_chain;got=service(engine).evaluate(request(c,analysis=None),actor=c.seed.actor)
    assert got.status=='REPLAN_REQUIRED' and got.persistence=='STORED'

def test_invalid_read_is_recorded_without_mutating_original_agent(engine,gate_chain):
    c=gate_chain;svc=service(engine);r=request(c)
    r=r.model_copy(update={'analysis':r.analysis.model_copy(update={'artifact_id':uuid4()})})
    with transaction(engine) as db:before=deepcopy(db.get(m.AgentRun,c.analysis.run_id).details)
    got=svc.evaluate(r,actor=c.seed.actor)
    assert got.status=='FAILED' and got.persistence=='STORED'
    assert svc.read(got.integration_id,actor=c.seed.actor)==got
    with transaction(engine) as db:assert db.get(m.AgentRun,c.analysis.run_id).details==before

def test_history_tampering_rejected(engine,gate_chain):
    c=gate_chain;svc=service(engine);got=svc.evaluate(request(c),actor=c.seed.actor)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,got.integration_id);old=deepcopy(row.details);data=deepcopy(old)
        data['integration_v1']['result']['status']='PASS_WITH_WARNINGS';row.details=data
    try:
        with pytest.raises(ValueError):svc.read(got.integration_id,actor=c.seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,got.integration_id).details=old

@pytest.mark.parametrize('when',['before','after_capture','after_evaluation'])
def test_cancel_never_returns_cached_or_late_pass(engine,gate_chain,when,monkeypatch):
    from app.integration.service import GateControl
    c=gate_chain;svc=service(engine);event=threading.Event();control=GateControl(cancel_event=event)
    if when=='before':event.set()
    else:
        target=svc.loader if when=='after_capture' else svc.evaluator
        name='capture' if when=='after_capture' else 'evaluate';old=getattr(target,name)
        def wrapped(*args,**kwargs):
            result=old(*args,**kwargs);event.set();return result
        monkeypatch.setattr(target,name,wrapped)
    got=svc.evaluate(request(c),actor=c.seed.actor,control=control)
    assert got.status=='FAILED' and 'GATE_CANCELLED' in got.blocking_issues
    assert not got.final_result_references

def test_deadline_expiration_and_cancel_isolation(engine,gate_chain):
    from app.integration.service import GateControl
    c=gate_chain;svc=service(engine)
    late=svc.evaluate(request(c),actor=c.seed.actor,control=GateControl(deadline_monotonic=time.monotonic()-1))
    assert late.status=='FAILED' and 'GATE_DEADLINE_EXCEEDED' in late.blocking_issues
    assert svc.evaluate(request(c),actor=c.seed.actor).status=='PASS'

def test_db_failure_not_stored_and_no_secret_logging(engine,gate_chain,monkeypatch,caplog):
    c=gate_chain;svc=service(engine)
    def broken(*args,**kwargs):raise RuntimeError('password=DO_NOT_LOG_ME')
    monkeypatch.setattr(svc.store,'evaluate_once',broken)
    got=svc.evaluate(request(c),actor=c.seed.actor)
    assert got.status=='FAILED' and got.persistence=='NOT_STORED'
    assert 'DO_NOT_LOG_ME' not in caplog.text and str(got.integration_id) in caplog.text

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from datetime import timedelta
import pytest
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from app.assistant.storage import IdempotencyConflict
from app.orchestration.contracts import InvestigationRequest,StageEvent,TYPE
from tests.orchestration.test_contracts_scope import request


def store(engine):
    from app.orchestration.store import PostgresInvestigationStore
    return PostgresInvestigationStore(engine)


def test_same_key_same_scope_reuses_root(engine):
    service=store(engine);raw=request();actor='reuse-'+uuid4().hex
    first=service.claim(raw,actor=actor);second=service.claim(raw,actor=actor)
    assert first.fresh and not second.fresh and first.logical_id==second.logical_id
    assert second.worker_token is None
    with transaction(engine) as db:
        assert db.scalar(select(func.count()).select_from(m.AgentRun).where(m.AgentRun.actor_principal==actor,m.AgentRun.agent_type==TYPE))==1


def test_same_key_changed_version_conflicts(engine):
    service=store(engine);raw=request();actor='conflict-'+uuid4().hex
    service.claim(raw,actor=actor)
    value=raw.model_dump(mode='json');value['time_scope']={'window_days':3}
    with pytest.raises(IdempotencyConflict):service.claim(InvestigationRequest.model_validate(value),actor=actor)


def test_concurrent_claim_only_one_worker(engine):
    service=store(engine);raw=request();actor='concurrent-'+uuid4().hex
    with ThreadPoolExecutor(max_workers=6) as pool:
        got=list(pool.map(lambda _:service.claim(raw,actor=actor),range(6)))
    assert len({g.logical_id for g in got})==1 and sum(g.fresh for g in got)==1


def test_owners_and_read_types_are_isolated(engine):
    service=store(engine);raw=request();alice='a-'+uuid4().hex;bob='b-'+uuid4().hex
    a=service.claim(raw,actor=alice);b=service.claim(raw,actor=bob)
    assert a.logical_id!=b.logical_id
    with pytest.raises(LookupError):service.read(a.logical_id,actor=bob)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,a.logical_id);assert 'request_key' not in row.context
        row.agent_type='deterministic-orchestrator-v1'
    with pytest.raises(LookupError):service.read(a.logical_id,actor=alice)


def test_revision_and_worker_token_prevent_stale_writes(engine):
    service=store(engine);raw=request();actor='revision-'+uuid4().hex;owned=service.claim(raw,actor=actor)
    updated=service.advance(owned.logical_id,actor=actor,worker_token=owned.worker_token,
        expected_revision=0,event=StageEvent(stage='PLANNING',code='START'))
    assert updated.revision==1
    for token,revision in ((uuid4(),1),(owned.worker_token,0)):
        with pytest.raises(ValueError):
            service.advance(owned.logical_id,actor=actor,worker_token=token,expected_revision=revision,
                event=StageEvent(stage='INTEGRATING',code='BAD'))


def test_cancel_is_durable_and_does_not_restart(engine):
    service=store(engine);raw=request();actor='cancel-'+uuid4().hex;owned=service.claim(raw,actor=actor)
    status=service.request_cancel(owned.logical_id,actor=actor)
    assert status.cancel_requested and status.overall_status=='RUNNING'
    assert not service.claim(raw,actor=actor).fresh
    assert service.read(owned.logical_id,actor=actor).cancel_requested_at is not None


def test_expired_lease_is_recovery_required_without_takeover(engine):
    service=store(engine);raw=request();actor='orphan-'+uuid4().hex;owned=service.claim(raw,actor=actor)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,owned.logical_id);value=dict(row.details);ns=dict(value['orchestration_v1'])
        ns['lease_expires_at']=(owned.context.created_at-timedelta(seconds=1)).isoformat();value['orchestration_v1']=ns;row.details=value
    assert service.status(owned.logical_id,actor=actor).recovery_required
    assert not service.claim(raw,actor=actor).fresh


def test_history_detects_corrupt_context(engine):
    service=store(engine);raw=request();actor='hash-'+uuid4().hex;owned=service.claim(raw,actor=actor)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,owned.logical_id);value=dict(row.details);ns=dict(value['orchestration_v1'])
        content=dict(ns['context']);content['overall_status']='SUCCEEDED';ns['context']=content;value['orchestration_v1']=ns;row.details=value
    with pytest.raises(ValueError,match='AUDIT'):service.read(owned.logical_id,actor=actor)

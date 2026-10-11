import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from app.orchestration.contracts import TYPE
from tests.orchestration.fixtures import scenario


def test_process_quota_is_shared_across_service_instances_and_does_not_allocate_busy_root(engine,monkeypatch):
    from app.orchestration.service import InvestigationOrchestrator,InvestigationBusy
    from app.orchestration.adapters import AgentServices
    from app.orchestration.control import InvestigationAbort
    entered=[threading.Event(),threading.Event()];release=threading.Event();lock=threading.Lock();count=[0]
    def wait(self,*a,**k):
        with lock:index=count[0];count[0]+=1
        entered[index].set();assert release.wait(10);raise InvestigationAbort('SYNTHETIC_STOP')
    monkeypatch.setattr(AgentServices,'investigate',wait)
    contexts=[scenario(engine) for _ in range(3)]
    services=[InvestigationOrchestrator(engine,x[2]) for x in contexts]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(services[i].investigate,contexts[i][1],actor=contexts[i][0].actor) for i in range(2)]
            assert all(e.wait(10) for e in entered)
            with pytest.raises(InvestigationBusy):services[2].investigate(contexts[2][1],actor=contexts[2][0].actor)
            with transaction(engine) as db:assert db.scalar(select(func.count()).select_from(m.AgentRun).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==contexts[2][0].actor))==0
            release.set()
            assert all(f.result(timeout=10).status.overall_status=='FAILED' for f in futures)
    finally:
        release.set()
        for x in contexts:x[2].close()


def test_concurrent_same_key_during_planning_uses_one_chain_and_frozen_running_read(engine):
    from app.orchestration.service import InvestigationOrchestrator
    seed,request,gw,calls,_=scenario(engine);entered=threading.Event();release=threading.Event()
    original=gw.text_provider.generate_structured
    def wait(req,schema):entered.set();assert release.wait(10);return original(req,schema)
    gw.text_provider.generate_structured=wait
    svc=InvestigationOrchestrator(engine,gw)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(svc.investigate,request,actor=seed.actor)
            assert entered.wait(10)
            duplicate=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
            assert duplicate.status.overall_status=='RUNNING' and duplicate.answer is None
            release.set();result=future.result(timeout=30)
        assert result.context.logical_investigation_id==duplicate.context.logical_investigation_id and len(calls)==1
    finally:release.set();gw.close()


def test_old_api_and_business_source_hashes_are_unchanged():
    import json,hashlib
    from pathlib import Path
    root=Path(__file__).resolve().parents[3]
    baseline=json.loads((root/'work/orchestration/baseline_hashes.json').read_text(encoding='utf-8'))
    allowed={'backend/app/runtime/service.py','backend/app/agents/investigation/service.py','backend/app/runtime/process.py'}
    for path,digest in baseline.items():
        if path not in allowed:assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path

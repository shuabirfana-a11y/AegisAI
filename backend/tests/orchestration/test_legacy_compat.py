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
    # Baseline stays immutable; separately authorize exact Phase12D source digests.
    changes=json.loads((root/'docs/phase12d/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(changes)=={'backend/app/planner/schemas.py','backend/app/llm/config.py','backend/tests/agents/verification/test_rules.py','backend/tests/runtime/test_scheduler.py',
                         'backend/app/llm/providers/openai_compatible.py'}
    planner_changes=json.loads((root/'docs/phase12d1/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(planner_changes)=={'backend/app/agents/investigation/planner.py','backend/app/agents/investigation/planning.py',
                                 'backend/app/agents/investigation/roles.py','backend/tests/agents/investigation/test_planning.py'}
    asset_changes=json.loads((root/'docs/phase12d3/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    f2_changes=json.loads((root/'docs/phase13f2/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    f3_changes=json.loads((root/'docs/phase13f3/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes']
    assert set(f3_changes)=={'backend/app/agents/investigation/planner.py','backend/app/agents/investigation/planning.py',
        'backend/app/agents/investigation/roles.py','backend/tests/agents/investigation/test_planning.py'}
    assert set(f2_changes)=={'backend/app/agents/investigation/planner.py','backend/app/agents/investigation/planning.py',
        'backend/app/agents/investigation/roles.py','backend/tests/agents/investigation/test_planning.py',
        'backend/app/agents/verification/schemas.py','backend/app/agents/verification/snapshot.py',
        'backend/app/orchestration/handoff.py','backend/app/orchestration/service.py'}
    assert set(asset_changes)=={'backend/app/agents/analysis/schemas.py','backend/app/agents/analysis/snapshot.py',
        'backend/app/agents/verification/schemas.py','backend/app/agents/verification/snapshot.py',
        'backend/app/agents/verification/reader.py','backend/app/tooling/analysis.py','backend/app/tooling/verification.py'}
    allowed={'backend/app/runtime/service.py','backend/app/agents/investigation/service.py','backend/app/runtime/process.py',
             'backend/app/main.py'}
    for path,digest in baseline.items():
        if path in f3_changes:
            entry=f3_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['previous_sha256']==f2_changes[path]['current_sha256'],path
            assert entry['authorization']=='PHASE13F3_USER_AUTHORIZED_NORMALIZATION_AND_TASK_TEMPLATES',path
            assert hashlib.sha256((root/path).read_bytes()).hexdigest()==entry['current_sha256'],path
            continue
        if path in f2_changes:
            entry=f2_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['authorization']=='PHASE13F2_USER_AUTHORIZED_INPUT_PLANNER_AND_CONFLICT_HANDOFF',path
            assert hashlib.sha256((root/path).read_bytes()).hexdigest()==entry['current_sha256'],path
            continue
        if path in asset_changes:
            entry=asset_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['authorization']=='PHASE12D3_USER_AUTHORIZED_ASSET_HANDOFF_ADAPTERS',path
            assert hashlib.sha256((root/path).read_bytes()).hexdigest()==entry['current_sha256'],path
            continue
        if path in planner_changes:
            entry=planner_changes[path]
            assert entry['baseline_sha256']==digest,path
            assert entry['authorization']=='PHASE12D1_USER_AUTHORIZED_PLANNER_STABILITY',path
            assert hashlib.sha256((root/path).read_bytes()).hexdigest()==entry['current_sha256'],path
            continue
        if path in changes:
            assert changes[path]['baseline_sha256']==digest,path
            assert changes[path]['authorization'] in {'USER_APPROVED_SCHEMA_METADATA_ONLY','PHASE12D_MODEL_PROVIDER_CONFIGURATION','PHASE12D_TEST_CLOCK_ISOLATION','PHASE12D_TEST_MONOTONIC_CONCURRENCY'}
            assert hashlib.sha256((root/path).read_bytes()).hexdigest()==changes[path]['current_sha256'],path
            continue
        if path not in allowed:assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
    from fastapi.routing import APIRoute
    from app.main import create_app
    from app.api import routes,enrichment,assets,assistant,tools
    expected={(route.path,method):route.endpoint for module in (routes,enrichment,assets,assistant,tools)
              for route in module.router.routes if isinstance(route,APIRoute) for method in route.methods}
    def flat(routes):
        for route in routes:
            if hasattr(route,'original_router'):
                yield from flat(route.original_router.routes)
            else:yield route
    actual={(route.path,method):route.endpoint for route in flat(create_app().routes) if isinstance(route,APIRoute)
            and not route.path.startswith('/api/investigations') for method in route.methods}
    assert len(expected)==34
    assert actual==expected

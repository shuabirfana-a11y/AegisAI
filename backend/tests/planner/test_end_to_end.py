"""Real Gateway → PostgreSQL → existing process Runtime; model responses synthetic."""
import json
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from app.llm.providers.base import ProviderFailure
from app.planner.schemas import PlannerInput
from app.runtime.contracts import RuntimePolicy
from tests.planner.fixtures import valid_plan, task, cve_input
from tests.planner.test_validation import missing
from tests.planner.test_trace_service import service_for,counts

def seeded_input(seed,asset=False):
    return PlannerInput(query=cve_input(target=seed.cve,question=
        f'我的 vLLM 0.8.2 是否受到 {seed.cve}影响？' if asset else f'{seed.cve}是什么？',
        **({'asset_id':seed.asset_id} if asset else {})).query,
        component_id=seed.component_id if asset else None)

def seeded_plan(seed,asset=False):
    p=valid_plan();p['tasks'][0]['input_data']['steps'][0]['arguments']['target']=seed.cve
    if asset:p['tasks'] += [task('version_match','version','match_component_vulnerabilities',
        {'component_id':str(seed.component_id)},['lookup']),
        task('patch_analysis','patch','find_patch_candidates',{'target':seed.cve},['version']),
        task('risk_analysis','risk','get_asset_risks',{'asset_id':str(seed.asset_id)},['patch'])]
    return p

def test_user1_simple_lookup_with_real_receipt(engine,runtime_seed):
    svc,gw,calls,records=service_for(engine,[seeded_plan(runtime_seed)])
    s=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
    tr=svc.runtime.read_trace(s.runtime_run_id,runtime_seed.actor)
    assert s.planning_status=='VALIDATED' and s.runtime_status=='COMPLETED'
    assert tr.artifacts[0].result['outputs'][0]['data']['canonical_id']==runtime_seed.cve
    assert tr.tasks[0].tools_called[0]['record_id'] and tr.artifacts[0].confidence is None
    assert tr.tasks[0].model_called==[];gw.close()

def test_user2_four_stage_asset_chain_keeps_uncertainty(engine,runtime_seed):
    svc,gw,calls,records=service_for(engine,[seeded_plan(runtime_seed,True)],RuntimePolicy(permissions={'READ_ONLY','WRITE'}))
    s=svc.plan_and_run(seeded_input(runtime_seed,True),runtime_seed.actor)
    tr=svc.runtime.read_trace(s.runtime_run_id,runtime_seed.actor)
    assert [t.tools_called[0]['tool_name'] for t in tr.tasks]==[
        'get_vulnerability','match_component_vulnerabilities','find_patch_candidates','get_asset_risks']
    assert all(tr.tasks[j].start_time>=tr.tasks[j-1].end_time for j in (1,2,3))
    assert tr.artifacts[1].result['outputs'][0]['data'][0]['match_status']=='UNCERTAIN'
    assert s.runtime_status=='WAITING_REVIEW';gw.close()

def test_user3_unknown_task_rejected_before_runtime(engine):
    p=valid_plan();p['tasks'][0]['type']='unknown_task'
    svc,gw,calls,records=service_for(engine,[p]);before=counts(engine);actor='owner-'+uuid4().hex
    s=svc.plan_and_run(cve_input(),actor)
    assert s.planning_status=='PLANNING_FAILED' and not s.runtime_run_id and counts(engine)==before
    assert len(calls)==2 and svc.read_trace(s.planner_run_id,actor).attempts[0].diagnostic
    gw.close()

def test_user4_illegal_tool_rejected_before_runtime(engine):
    p=valid_plan();p['tasks'][0].update(allowed_tools=['get_system_status'],input_data={'steps':[{'name':'get_system_status','arguments':{}}]})
    svc,gw,calls,records=service_for(engine,[p]);before=counts(engine);actor='owner-'+uuid4().hex
    s=svc.plan_and_run(cve_input(),actor);tr=svc.read_trace(s.planner_run_id,actor)
    assert s.planning_status=='PLANNING_FAILED' and counts(engine)==before
    assert tr.error[0].code=='TASK_TOOL_FORBIDDEN';gw.close()

def test_user5_gateway_failure_recovers_in_two_calls(engine,runtime_seed):
    svc,gw,calls,records=service_for(engine,[ProviderFailure('TIMEOUT',retryable=True),seeded_plan(runtime_seed)])
    s=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
    tr=svc.read_trace(s.planner_run_id,runtime_seed.actor)
    assert s.runtime_run_id and len(calls)==2 and tr.retry_count==1
    assert tr.attempts[0].raw_unavailable_reason=='NO_TEXT_RESPONSE';gw.close()

def test_missing_version_inputs_block_patch_and_risk(engine,runtime_seed):
    p=seeded_plan(runtime_seed);p['tasks'] += [missing('version_match','version',['component_id','write_authorization'],['lookup']),
        task('patch_analysis','patch','find_patch_candidates',{'target':runtime_seed.cve},['version']),
        missing('risk_analysis','risk',['asset_id'],['patch'])]
    svc,gw,calls,records=service_for(engine,[p])
    i=cve_input(target=runtime_seed.cve,question=f'我的 vLLM 0.6.0 是否受到 {runtime_seed.cve}影响？')
    s=svc.plan_and_run(i,runtime_seed.actor);tr=svc.runtime.read_trace(s.runtime_run_id,runtime_seed.actor)
    assert [t.status for t in tr.tasks]==['SUCCESS','WAITING_REVIEW','BLOCKED','BLOCKED']
    assert all(not t.tools_called for t in tr.tasks[1:]);gw.close()

def test_no_fake_asset_analysis_from_only_epss(engine,runtime_seed):
    p=seeded_plan(runtime_seed,True)
    p['tasks'][3]=task('risk_analysis','risk','get_epss',{'target':runtime_seed.cve},['patch'])
    svc,gw,calls,records=service_for(engine,[p],RuntimePolicy(permissions={'READ_ONLY','WRITE'}))
    before=counts(engine);s=svc.plan_and_run(seeded_input(runtime_seed,True),runtime_seed.actor)
    assert s.planning_status=='PLANNING_FAILED' and not s.runtime_run_id and counts(engine)==before
    gw.close()

def test_concurrent_pending_request_calls_model_once(engine,runtime_seed,monkeypatch):
    svc,gw,calls,records=service_for(engine,[seeded_plan(runtime_seed)]);i=seeded_input(runtime_seed)
    entered=Event();release=Event();old=gw.generate_structured
    def held(*a,**k):
        entered.set();assert release.wait(15);return old(*a,**k)
    monkeypatch.setattr(gw,'generate_structured',held)
    with ThreadPoolExecutor(2) as pool:
        first=pool.submit(svc.plan_and_run,i,runtime_seed.actor)
        assert entered.wait(5)
        try:second=svc.plan_and_run(i,runtime_seed.actor)
        finally:release.set()
        finished=first.result(timeout=20)
    assert second.planning_status=='PLANNING' and second.planner_run_id==finished.planner_run_id and len(calls)==1
    gw.close()

def test_authenticated_get_compatibility_and_private_trace(engine,runtime_seed,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    svc,gw,calls,records=service_for(engine,['PRIVATE_RAW_FAILURE',seeded_plan(runtime_seed)])
    s=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
    monkeypatch.setenv('AEGIS_ASSET_TOKEN','SYNTHETIC-PLANNER-TOKEN');monkeypatch.setenv('AEGIS_ASSET_OWNER',runtime_seed.actor)
    with TestClient(create_app(engine)) as client:
        headers={'Authorization':'Bearer SYNTHETIC-PLANNER-TOKEN'}
        for id in [s.planner_run_id,s.runtime_run_id]:
            url='/api/v1/assistant/runs/'+str(id)
            assert client.get(url).status_code==401
            for suffix in ['', '/tasks','/trace']:
                r=client.get(url+suffix,headers=headers)
                assert r.status_code==200 and 'PRIVATE_RAW_FAILURE' not in r.text
        assert client.get('/api/v1/assistant/runs/'+str(s.runtime_run_id),headers=headers).json()['result']['generation_calls']==2
    gw.close()

def test_late_concurrent_duplicate_does_not_regress_status(engine,runtime_seed,monkeypatch):
    svc,gw,calls,records=service_for(engine,[seeded_plan(runtime_seed)]);i=seeded_input(runtime_seed)
    created=Event();release_execution=Event();duplicate_waiting=Event();completed=Event()
    old_create=svc.runtime.store.create_run;old_link=svc.store.link_runtime
    def hold_new_execution(*args,**kwargs):
        snapshot,fresh=old_create(*args,**kwargs)
        if fresh:
            created.set();assert release_execution.wait(15)
        return snapshot,fresh
    def delay_duplicate_link(id,actor,runtime):
        if runtime.status in ('PLANNING','RUNNING'):
            duplicate_waiting.set();assert completed.wait(20)
        return old_link(id,actor,runtime)
    monkeypatch.setattr(svc.runtime.store,'create_run',hold_new_execution)
    monkeypatch.setattr(svc.store,'link_runtime',delay_duplicate_link)
    with ThreadPoolExecutor(2) as pool:
        first=pool.submit(svc.plan_and_run,i,runtime_seed.actor)
        assert created.wait(10)
        second=pool.submit(svc.plan_and_run,i,runtime_seed.actor)
        try:
            assert duplicate_waiting.wait(10)
            release_execution.set();a=first.result(timeout=20)
        finally:
            release_execution.set();completed.set()
        b=second.result(timeout=20)
    assert a.runtime_status==b.runtime_status=='COMPLETED'
    assert svc.read_trace(a.planner_run_id,runtime_seed.actor).runtime_status=='COMPLETED'
    assert a.runtime_run_id==b.runtime_run_id and len(calls)==1
    gw.close()

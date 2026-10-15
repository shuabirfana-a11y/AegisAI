"""Real HTTP/Runtime/tools/Gate, with only the slow external model doubled."""
import json
import time
import threading
from datetime import timedelta
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.db import models as m
from app.db.session import transaction
from tests.investigation_api.test_multi_asset_database import setup_batch
from tests.agents.investigation.test_end_to_end import plan_for
from tests.planner.fixtures import task,gateway_with_responses

HEADERS={'Authorization':'Bearer SYNTHETIC-batch-token'}


def plans(seed,second_version='0.7.0'):
    values=[]
    for asset_id,version in sorted([(seed.asset_id,'0.6.0'),(seed.second_asset_id,second_version)],key=lambda x:str(x[0])):
        s=SimpleNamespace(**vars(seed));s.asset_id=asset_id
        s.component={**seed.component,'name':seed.component['package_name'],'version':version}
        value=plan_for(s,'version')
        value['tasks'].append(task('asset_lookup','asset','get_asset',{'asset_id':str(asset_id)}))
        values.append(value)
    return values


def wait(client,id,timeout=60):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        response=client.get(f'/api/investigations/batches/{id}',headers=HEADERS)
        assert response.status_code==200,response.text
        result=response.json()
        if result['execution_status'] in ('COMPLETED','FAILED','CANCELLED','TIMED_OUT'):return result
        time.sleep(.08)
    raise AssertionError('Batch did not reach terminal coverage state')


def configure(monkeypatch,seed):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN','SYNTHETIC-batch-token')
    monkeypatch.setenv('AEGIS_ASSET_OWNER',seed.actor)


def test_two_versions_actual_chain_produce_independent_verdicts_and_persist(engine,monkeypatch):
    seed,old=setup_batch(engine);old.close();gw,calls,_=gateway_with_responses(plans(seed));configure(monkeypatch,seed)
    key='HTTP-batch-'+uuid4().hex
    body={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id),str(seed.asset_id)],'idempotency_key':key}
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            response=client.post('/api/investigations/batches',json=body,headers=HEADERS)
            assert response.status_code==202,response.text
            id=response.json()['batch_id'];result=wait(client,id)
            assert result['execution_status']=='COMPLETED',result
            assets={i['snapshot']['asset_id']:i for i in result['items']}
            a,b=assets[str(seed.asset_id)],assets[str(seed.second_asset_id)]
            assert (a['impact'],a['risk_level'],a['priority'])==('AFFECTED','HIGH','P2'),result
            assert (b['impact'],b['risk_level'],b['priority'])==('NOT_AFFECTED','LOW','DEFER'),result
            assert a['investigation_id']!=b['investigation_id']
            assert a['gate_status']=='PASS' and b['gate_status'] in ('PASS','PASS_WITH_WARNINGS')
            assert all(i['citations'] and len(i['artifact_references'])==3 for i in assets.values())
            assert result['summary']['actionable_asset_ids']==[str(seed.asset_id)]
            assert result['duplicate_asset_count']==1 and len(calls)==2
            before=deepcopy(result)
            with transaction(engine) as db:
                c=db.get(m.AssetComponent,seed.component_id);c.version='8.0.0';c.inventory_revision+=1
            repeated=client.post('/api/investigations/batches',json=body,headers=HEADERS)
            assert repeated.status_code==202 and repeated.json()['reused'] is True
            assert repeated.json()['items']==before['items'] and len(calls)==2
            historical=next(i for i in repeated.json()['items'] if i['snapshot']['asset_id']==str(seed.asset_id))
            assert historical['historical_snapshot'] is True and historical['current_safety_evaluated'] is False
            assert historical['snapshot']['components'][0]['version']=='0.6.0' and historical['risk_level']=='HIGH'
            summary=client.get(f'/api/investigations/batches/{id}/summary',headers=HEADERS).json()
            assert summary==before
            repo=client.app.state.multi_asset.repo
            def forged(record):
                affected=next(i for i in record.response.items if i.snapshot.asset_id==seed.asset_id)
                affected.impact='NOT_AFFECTED';affected.risk_level='LOW';affected.priority='DEFER'
            pristine=repo.read(id,seed.actor)
            repo.mutate(id,seed.actor,forged)  # Deliberately recomputes hash and summary.
            assert client.get(f'/api/investigations/batches/{id}',headers=HEADERS).status_code==500
            repo.mutate(id,seed.actor,lambda record:setattr(record,'response',pristine.response))
            def forged_bypass(record):
                affected=next(i for i in record.response.items if i.snapshot.asset_id==seed.asset_id)
                affected.error_code='CHILD_RESULT_UNAVAILABLE';affected.impact='NOT_AFFECTED'
                affected.risk_level='LOW';affected.priority='DEFER'
            repo.mutate(id,seed.actor,forged_bypass)
            assert client.get(f'/api/investigations/batches/{id}',headers=HEADERS).status_code==500
            repo.mutate(id,seed.actor,lambda record:setattr(record,'response',pristine.response))
            def erased_refs(record):
                it=record.response.items[0];it.artifact_references=();it.integration_result_id=None;it.answer_id=None
            repo.mutate(id,seed.actor,erased_refs)
            assert client.get(f'/api/investigations/batches/{id}',headers=HEADERS).status_code==500
            repo.mutate(id,seed.actor,lambda record:setattr(record,'response',pristine.response))
            before=client.get(f'/api/investigations/batches/{id}',headers=HEADERS).json()
            monkeypatch.setenv('AEGIS_ASSET_OWNER','SYNTHETIC-other-owner')
            assert client.get(f'/api/investigations/batches/{id}',headers=HEADERS).status_code==404
            assert client.get(f'/api/investigations/{a["investigation_id"]}/answer',headers=HEADERS).status_code==404
            monkeypatch.setenv('AEGIS_ASSET_OWNER',seed.actor)
        # A new service reads persisted results without starting children again.
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            assert client.get(f'/api/investigations/batches/{id}/summary',headers=HEADERS).json()==before
            assert len(calls)==2
    finally:gw.close()


def test_missing_version_stays_unknown_while_complete_sibling_runs(engine,monkeypatch):
    seed,old=setup_batch(engine);old.close()
    with transaction(engine) as db:db.get(m.AssetComponent,seed.second_component_id).version=None
    plan=next(p for p in plans(seed) if any(t['input_data']['steps'][0]['arguments'].get('asset_id')==str(seed.asset_id) for t in p['tasks']))
    gw,calls,_=gateway_with_responses([plan]);configure(monkeypatch,seed)
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            response=client.post('/api/investigations/batches',headers={**HEADERS,'Idempotency-Key':uuid4().hex},
                json={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)]})
            assert response.status_code==202,response.text
            result=wait(client,response.json()['batch_id'])
            a,b=({i['snapshot']['asset_id']:i for i in result['items']}[str(x)] for x in (seed.asset_id,seed.second_asset_id))
            assert a['impact']=='AFFECTED',result
            assert b['execution_status']=='NEED_CONTEXT' and b['missing_fields']==['version']
            assert b['investigation_id'] is None and b['risk_level']=='UNKNOWN'
            assert result['summary']['unresolved_asset_ids']==[str(seed.second_asset_id)] and len(calls)==1
    finally:gw.close()


@pytest.mark.parametrize('stop',['cancel','deadline','inventory_change'])
def test_stop_and_snapshot_drift_prevent_new_child_admission(engine,monkeypatch,stop):
    seed,old=setup_batch(engine);old.close();values=plans(seed)
    gw,calls,_=gateway_with_responses(values);configure(monkeypatch,seed)
    entered,release=threading.Event(),threading.Event()
    original=gw.text_provider.generate_structured
    def slow(request,schema):
        entered.set();assert release.wait(15)
        return original(request,schema)
    gw.text_provider.generate_structured=slow
    ids=sorted([seed.asset_id,seed.second_asset_id],key=str)
    second_component=seed.component_id if ids[1]==seed.asset_id else seed.second_component_id
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            body={'vulnerability_id':seed.cve,'asset_ids':[str(x) for x in ids],'timeout_seconds':30 if stop=='deadline' else 120}
            key=uuid4().hex
            response=client.post('/api/investigations/batches',json=body,headers={**HEADERS,'Idempotency-Key':key})
            assert response.status_code==202,response.text
            id=response.json()['batch_id'];assert entered.wait(10)
            # Concurrent duplicates must never start another batch or child.
            with ThreadPoolExecutor(max_workers=2) as pool:
                duplicates=list(pool.map(lambda _:client.post('/api/investigations/batches',json=body,
                    headers={**HEADERS,'Idempotency-Key':key}),range(2)))
            assert all(x.status_code==202 and x.json()['batch_id']==id and x.json()['reused'] for x in duplicates)
            if stop=='cancel':
                acknowledged=client.post(f'/api/investigations/batches/{id}/cancel',json={},headers=HEADERS)
                assert acknowledged.status_code==200 and acknowledged.json()['cancel_requested_at']
                assert acknowledged.json()['cancellation_observed'] is False
            elif stop=='deadline':
                import app.investigation_api.multi_asset_service as batch_module
                from app.utils.time import utcnow
                expired=utcnow()+timedelta(seconds=31)
                monkeypatch.setattr(batch_module,'utcnow',lambda:expired)
            else:
                with transaction(engine) as db:
                    c=db.get(m.AssetComponent,second_component);c.version='9.0.0';c.inventory_revision+=1
            release.set();result=wait(client,id)
            assert result['items'][1]['investigation_id'] is None,result
            if stop=='inventory_change':
                assert result['items'][1]['execution_status']=='NEED_CONTEXT'
                assert result['items'][1]['snapshot_valid'] is False
            else:
                assert result['execution_status'] in ('CANCELLED','TIMED_OUT')
                assert result['items'][1]['execution_status']=='NOT_EXECUTED'
            assert len(calls)==1
    finally:release.set();gw.close()


def test_planner_failure_of_one_asset_does_not_remove_or_stop_sibling(engine,monkeypatch):
    seed,old=setup_batch(engine);old.close();values=plans(seed)
    gw,calls,_=gateway_with_responses([{'tasks':[]},{'tasks':[]},values[1]]);configure(monkeypatch,seed)
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            created=client.post('/api/investigations/batches',headers={**HEADERS,'Idempotency-Key':uuid4().hex},
                json={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)]})
            assert created.status_code==202,created.text
            result=wait(client,created.json()['batch_id'])
            assert result['execution_status']=='COMPLETED'
            a,b=result['items']
            assert a['execution_status']=='FAILED' and a['risk_level']=='UNKNOWN'
            assert b['execution_status']=='COMPLETED' and b['gate_status'] in ('PASS','PASS_WITH_WARNINGS'),result
            assert result['summary']['counts']['failed']==1 and result['summary']['counts']['total']==2
            assert len(calls)==3
    finally:gw.close()


@pytest.mark.parametrize('mode,gate',[('insufficient','REPLAN_REQUIRED'),('conflict','HUMAN_REVIEW_REQUIRED')])
def test_graph_path_and_conflict_do_not_become_batch_impact_proof(engine,monkeypatch,mode,gate):
    seed,old=setup_batch(engine,mode);old.close();gw,calls,_=gateway_with_responses(plans(seed));configure(monkeypatch,seed)
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            response=client.post('/api/investigations/batches',headers={**HEADERS,'Idempotency-Key':uuid4().hex},
                json={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)]})
            assert response.status_code==202,response.text
            result=wait(client,response.json()['batch_id'])
            assert len(result['items'])==2 and all(x['relations']['node_ids'] for x in result['items'])
            assert all(x['gate_status']==gate and x['impact']=='UNKNOWN' and x['risk_level']=='UNKNOWN' for x in result['items']),result
            assert result['summary']['actionable_asset_ids']==[] and len(result['summary']['unresolved_asset_ids'])==2
            if mode=='conflict':assert all(x['evidence_observations'] for x in result['items'])
    finally:gw.close()


def test_delayed_creation_ack_is_tracked_and_cancelled_without_starting_sibling(engine,monkeypatch):
    from app.investigation_api.service import InvestigationApiService
    from app.orchestration.store import PostgresInvestigationStore
    import app.main as main
    seed,old=setup_batch(engine);old.close();gw,calls,_=gateway_with_responses(plans(seed));configure(monkeypatch,seed)
    entered,release=threading.Event(),threading.Event()
    claim=PostgresInvestigationStore.claim
    def delayed(self,request,*,actor):
        entered.set();assert release.wait(15)
        return claim(self,request,actor=actor)
    monkeypatch.setattr(PostgresInvestigationStore,'claim',delayed)
    monkeypatch.setattr(main,'InvestigationApiService',lambda e,g:InvestigationApiService(e,g,ack_timeout=.05))
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            created=client.post('/api/investigations/batches',headers={**HEADERS,'Idempotency-Key':uuid4().hex},
                json={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)]})
            assert created.status_code==202,created.text
            id=created.json()['batch_id'];assert entered.wait(10)
            time.sleep(.15)
            pending=client.get(f'/api/investigations/batches/{id}',headers=HEADERS).json()
            assert pending['items'][0]['execution_status']=='RUNNING'
            assert pending['items'][1]['execution_status']=='NOT_STARTED'
            assert client.post(f'/api/investigations/batches/{id}/cancel',headers=HEADERS).status_code==200
            release.set();result=wait(client,id)
            assert result['items'][0]['investigation_id'] is not None,result
            assert result['items'][1]['execution_status']=='NOT_EXECUTED' and not calls
            assert result['cancellation_observed'] is True
    finally:release.set();gw.close()


def test_cancel_ack_does_not_claim_stop_and_late_child_is_reconciled(engine,monkeypatch):
    from app.investigation_api.multi_asset_service import MultiAssetService
    import app.main as main
    seed,old=setup_batch(engine);old.close();gw,calls,_=gateway_with_responses(plans(seed));configure(monkeypatch,seed)
    entered,release=threading.Event(),threading.Event();original=gw.text_provider.generate_structured
    def slow(request,schema):
        entered.set();assert release.wait(15)
        return original(request,schema)
    gw.text_provider.generate_structured=slow
    monkeypatch.setattr(main,'MultiAssetService',lambda e,s:MultiAssetService(e,s,cancel_grace=.05,poll_seconds=.02))
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            created=client.post('/api/investigations/batches',headers={**HEADERS,'Idempotency-Key':uuid4().hex},
                json={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)]})
            assert created.status_code==202,created.text
            id=created.json()['batch_id'];assert entered.wait(10)
            client.post(f'/api/investigations/batches/{id}/cancel',headers=HEADERS)
            pending=wait(client,id)
            assert pending['execution_status']=='CANCELLED' and pending['cancellation_observed'] is False
            assert pending['recovery_required'] and pending['items'][1]['execution_status']=='NOT_EXECUTED'
            release.set()
            end=time.monotonic()+15
            while time.monotonic()<end:
                result=client.get(f'/api/investigations/batches/{id}',headers=HEADERS).json()
                if result['cancellation_observed']:break
                time.sleep(.1)
            assert result['cancellation_observed'] and result['items'][0]['execution_status']!='RUNNING',result
            assert len(calls)==1
    finally:release.set();gw.close()


def test_post_commit_ack_projection_exception_does_not_orphan_child(engine,monkeypatch):
    from app.investigation_api.service import InvestigationApiService
    seed,old=setup_batch(engine);old.close();gw,calls,_=gateway_with_responses(plans(seed));configure(monkeypatch,seed)
    original=InvestigationApiService._created;attempts=[]
    def fail_once(self,*args):
        attempts.append(1)
        if len(attempts)==1:raise RuntimeError('SYNTHETIC post-commit ACK projection read failure')
        return original(self,*args)
    monkeypatch.setattr(InvestigationApiService,'_created',fail_once)
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            created=client.post('/api/investigations/batches',headers={**HEADERS,'Idempotency-Key':uuid4().hex},
                json={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)]})
            assert created.status_code==202,created.text
            result=wait(client,created.json()['batch_id'])
            assert all(x['execution_status']=='COMPLETED' and x['investigation_id'] for x in result['items']),result
            assert len(calls)==2
    finally:gw.close()


def test_known_pre_admission_busy_does_not_leave_an_orphan_intent(engine,monkeypatch):
    from app.orchestration.service import InvestigationBusy
    seed,old=setup_batch(engine);old.close();gw,calls,_=gateway_with_responses([]);configure(monkeypatch,seed)
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            def busy(*args,**kwargs):raise InvestigationBusy('INVESTIGATION_BUSY')
            monkeypatch.setattr(client.app.state.investigations,'create',busy)
            created=client.post('/api/investigations/batches',headers={**HEADERS,'Idempotency-Key':uuid4().hex},
                json={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)]})
            assert created.status_code==202,created.text
            result=wait(client,created.json()['batch_id'])
            assert all(x['execution_status']=='FAILED' and x['error_code']=='INVESTIGATION_BUSY' for x in result['items'])
            assert not calls and result['summary']['counts']['failed']==2
    finally:gw.close()


def test_temporary_sealed_inventory_drift_cannot_be_published_as_frozen_risk(engine,monkeypatch):
    from app.agents.analysis.snapshot import AnalysisSnapshotReader
    seed,old=setup_batch(engine);old.close()
    plan=next(p for p in plans(seed) if any(t['input_data']['steps'][0]['arguments'].get('asset_id')==str(seed.asset_id) for t in p['tasks']))
    gw,calls,_=gateway_with_responses([plan]);configure(monkeypatch,seed)
    original=AnalysisSnapshotReader.read
    def drift(self,*args,**kwargs):
        inputs=original(self,*args,**kwargs);asset=inputs.asset
        return inputs.model_copy(update={'asset':asset.model_copy(update={
            'exposure':'internal' if asset.exposure!='internal' else 'internet'})})
    monkeypatch.setattr(AnalysisSnapshotReader,'read',drift)
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            created=client.post('/api/investigations/batches',headers={**HEADERS,'Idempotency-Key':uuid4().hex},
                json={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id)]})
            assert created.status_code==202,created.text
            result=wait(client,created.json()['batch_id']);item=result['items'][0]
            assert item['snapshot_valid'] is False and item['impact']=='UNKNOWN' and item['risk_level']=='UNKNOWN'
            assert result['summary']['actionable_asset_ids']==[]
    finally:gw.close()

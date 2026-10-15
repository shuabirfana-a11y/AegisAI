"""Owned TCP/HTTP and batch scopes. Synthetic source facts, never Benchmark."""
import time
from uuid import UUID,uuid4
from sqlalchemy import select,func
from fastapi.testclient import TestClient
import pytest
from app.db import models as m
from app.db.session import transaction
from app.main import create_app
from tests.orchestration.test_supplement import hidden_range_evidence
from tests.investigation_api.test_tcp_chain import tcp_client,TOKEN,bound_case

def finished(client,id,headers=None):
    end=time.monotonic()+100
    while time.monotonic()<end:
        response=client.get('/api/investigations/'+id+'/status',headers=headers)
        assert response.status_code==200,response.text
        if response.json()['processing_complete']:return response.json()
        time.sleep(.05)
    raise AssertionError('Supplement did not finish in bounded HTTP budget')

@pytest.mark.parametrize('enabled',[False,True])
def test_tcp_automatic_supplement_versions_and_read_only_history(engine,monkeypatch,enabled):
    seed,request,gw,calls,_=hidden_range_evidence(engine)
    monkeypatch.setenv('AEGIS_ASSET_TOKEN',TOKEN);monkeypatch.setenv('AEGIS_ASSET_OWNER',seed.actor)
    monkeypatch.setenv('AEGIS_EVIDENCE_SUPPLEMENT_ENABLED','1' if enabled else '0')
    try:
        with tcp_client(create_app(engine,investigation_gateway=gw)) as client:
            body=bound_case(seed,request)['request'].model_dump(mode='json')
            response=client.post('/api/investigations',json=body)
            assert response.status_code==202,response.text
            id=response.json()['investigation_id'];state=finished(client,id)
            assert state['result_version']==(2 if enabled else 1),state
            answer=client.get('/api/investigations/'+id+'/answer').json()
            original=client.get('/api/investigations/'+id+'/answer?version=1').json()
            assert original['integration_status']=='REPLAN_REQUIRED'
            # HTTP version metadata must remain outside the immutable domain
            # envelope without changing the existing evaluation projection.
            import sys
            from pathlib import Path
            sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
            from evaluation.bench.http_investigation import project_answer
            from evaluation.bench.schema import Question
            q=Question(id='SYNTHETIC_SUPPLEMENT_HTTP_NOT_GOLD',question=request.user_query,
                category='risk',origin='TEST_FIXTURE',source_ids=['SYNTHETIC_NOT_BENCHMARK'],input_context={})
            assert project_answer(q,original).status=='SUCCEEDED'
            assert project_answer(q,answer).status=='SUCCEEDED'
            with pytest.raises(ValueError):project_answer(q,{**answer,'result_version':99})
            if enabled:
                assert state['supplement']['status']=='COMPLETED',state
                assert state['supplement']['new_evidence_ids'] and state['supplement']['resolved_claim_ids']
                assert answer['answer_id']!=original['answer_id']
                assert answer['integration_status'] in ('PASS','PASS_WITH_WARNINGS')
                assert client.get('/api/investigations/'+id+'/answer?version=2').json()==answer
            else:assert client.get('/api/investigations/'+id+'/answer?version=2').status_code==409
            with transaction(engine) as db:before=db.scalar(select(func.count()).select_from(m.ToolCallRecord))
            for op in ('trace','artifacts','integration','answer'):
                assert client.get('/api/investigations/'+id+'/'+op+'?version=1').status_code==200
                assert client.get('/api/investigations/'+id+'/'+op).status_code==200
            assert client.get('/api/investigations/history').json()['items'][0]['answer_id']==answer['answer_id']
            assert client.get('/api/investigations/'+id+'/answer?version=3').status_code==422
            assert client.post('/api/investigations',json=body).json()['reused']
            assert len(calls)==1
            with transaction(engine) as db:assert db.scalar(select(func.count()).select_from(m.ToolCallRecord))==before
            monkeypatch.setenv('AEGIS_ASSET_OWNER','other-synthetic-owner')
            assert client.get('/api/investigations/'+id+'/answer?version=1').status_code==404
            monkeypatch.setenv('AEGIS_ASSET_OWNER',seed.actor)
    finally:gw.close()

def test_http_cancel_between_first_gate_and_acquisition_preserves_v1(engine,monkeypatch):
    from threading import Event
    from app.orchestration.supplement.runtime import SupplementRuntime
    seed,request,gw,_,_=hidden_range_evidence(engine)
    entered,release=Event(),Event();old=SupplementRuntime.run_fixed
    def pause(self,actor):
        entered.set();assert release.wait(10)
        return old(self,actor)
    monkeypatch.setattr(SupplementRuntime,'run_fixed',pause)
    monkeypatch.setenv('AEGIS_ASSET_TOKEN',TOKEN);monkeypatch.setenv('AEGIS_ASSET_OWNER',seed.actor)
    monkeypatch.setenv('AEGIS_EVIDENCE_SUPPLEMENT_ENABLED','1')
    try:
        with tcp_client(create_app(engine,investigation_gateway=gw)) as client:
            response=client.post('/api/investigations',json=bound_case(seed,request)['request'].model_dump(mode='json'))
            assert response.status_code==202,response.text
            id=response.json()['investigation_id'];assert entered.wait(40)
            assert client.post('/api/investigations/'+id+'/cancel').status_code==200
            release.set();state=finished(client,id)
            assert state['supplement']['status']=='CANCELLED',state
            assert state['result_version']==1
            assert client.get('/api/investigations/'+id+'/answer').json()['integration_status']=='REPLAN_REQUIRED'
            assert state['supplement']['extra_acquisition_calls']==0
    finally:release.set();gw.close()

def test_two_eligible_assets_share_one_round_and_cannot_reuse_version_or_answer(engine,monkeypatch):
    from tests.investigation_api.test_multi_asset_chain import plans,configure,HEADERS,wait
    from tests.planner.fixtures import gateway_with_responses
    seed,_,old,_,_=hidden_range_evidence(engine);old.close()
    with transaction(engine) as db:
        a=m.Asset(name='SYNTHETIC independent second asset',asset_type='service',owner_principal=seed.actor,is_demo=True,
            environment='production',exposure='internet')
        db.add(a);db.flush()
        c=m.AssetComponent(asset_id=a.id,package_identifier_id=seed.package_id,raw_package_name=seed.component['package_name'],
            version='0.7.0',ecosystem='PyPI',identity_status='resolved',inventory_revision=1)
        db.add(c);db.flush();seed.second_asset_id=a.id;seed.second_component_id=c.id
    gw,calls,_=gateway_with_responses(plans(seed));configure(monkeypatch,seed)
    monkeypatch.setenv('AEGIS_EVIDENCE_SUPPLEMENT_ENABLED','1')
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            reply=client.post('/api/investigations/batches',headers=HEADERS,json={'vulnerability_id':seed.cve,
                'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)],'idempotency_key':uuid4().hex})
            assert reply.status_code==202,reply.text
            bid=reply.json()['batch_id'];deadline=time.monotonic()+240
            while time.monotonic()<deadline:
                response=client.get('/api/investigations/batches/'+bid,headers=HEADERS)
                assert response.status_code==200,response.text
                result=response.json()
                if result['execution_status'] in ('COMPLETED','FAILED','CANCELLED','TIMED_OUT'):break
                time.sleep(.5)
            assert result['execution_status']=='COMPLETED',result
            summaries=[]
            for item in result['items']:
                status=client.get('/api/investigations/'+item['investigation_id']+'/status',headers=HEADERS).json()
                summaries.append(status['supplement'])
                assert item['result_version']==status['result_version']
                assert item['supplement']==status['supplement']
                answer=client.get('/api/investigations/'+item['investigation_id']+'/answer',headers=HEADERS).json()
                assert item['answer_id']==answer['answer_id']
                for asset in answer['affected_assets']:
                    assert asset['asset_id']==item['snapshot']['asset_id']
                    assert asset['deployed_version']==item['snapshot']['components'][0]['version']
            assert sum(s['eligible'] for s in summaries)==1,summaries
            assert sum(s['extra_acquisition_calls'] for s in summaries)<=3
            assert any(s['reason']=='BATCH_SUPPLEMENT_BUDGET_EXHAUSTED' for s in summaries)
            assert len(calls)==2
            assert len({i['answer_id'] for i in result['items']})==2
    finally:gw.close()

def test_client_cannot_raise_supplement_budget_or_task_permissions(monkeypatch):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN',TOKEN)
    client=TestClient(create_app())
    # Dependency resolution happens before body validation; no database/model
    # service is needed or invoked by an invalid input request.
    client.app.state.investigations=object()
    body={'user_query':'query','idempotency_key':'synthetic','options':{'supplement_budget':99}}
    assert client.post('/api/investigations',json=body,headers={'Authorization':'Bearer '+TOKEN}).status_code==422

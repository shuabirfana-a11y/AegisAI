from uuid import uuid4
import pytest

def query(key='SYNTHETIC'):
    from app.assistant.contracts import QueryRequest
    return QueryRequest(question='CVE-2099-9999001',request_key=key)

def test_run_idempotency_is_server_owner_scoped_and_body_bound(db):
    from app.assistant.storage import create_run,owned_run,IdempotencyConflict
    a,new=create_run(db,query(),'owner-a');assert new
    b,new=create_run(db,query(),'owner-a');assert not new and b.id==a.id
    c,new=create_run(db,query(),'owner-b');assert new and c.id!=a.id
    with pytest.raises(LookupError):owned_run(db,a.id,'owner-b')
    changed=query();changed.question='changed'
    with pytest.raises(IdempotencyConflict):create_run(db,changed,'owner-a')

def test_tool_audit_records_full_envelope_but_no_credentials(db):
    from app.assistant.storage import create_run,record_tool
    from app.tooling.contracts import ToolEnvelope
    from app.db import models as m
    r,_=create_run(db,query(),'owner')
    output=ToolEnvelope(tool='get_vulnerability',status='no_result',trace_id=r.details['trace_id'],duration_ms=3)
    row=record_tool(db,r.id,1,'get_vulnerability',{'target':'CVE-2099-9999001'},output,1)
    db.flush();assert row.status=='succeeded' and row.output_summary['status']=='no_result'
    assert db.get(m.ToolCallRecord,row.id).agent_run_id==r.id

def test_assistant_api_auth_extra_fields_and_owner_reads(engine,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    class Stub:
        def start(self,request,actor):return {'run_id':str(uuid4()),'status':'PLANNING','trace_id':'SYNTHETIC'}
        def read(self,id,actor):raise LookupError('Run not found')
    monkeypatch.setenv('AEGIS_ASSET_TOKEN','SYNTHETIC-TEST-TOKEN')
    monkeypatch.setenv('AEGIS_ASSET_OWNER','test-analyst')
    with TestClient(create_app(engine)) as client:
        client.app.state.assistant=Stub()
        assert client.post('/api/v1/assistant/query',json=query().model_dump(mode='json')).status_code==401
        h={'Authorization':'Bearer SYNTHETIC-TEST-TOKEN'}
        assert client.post('/api/v1/assistant/query',headers=h,json={**query().model_dump(mode='json'),'actor':'other'}).status_code==422
        assert client.post('/api/v1/assistant/query',headers=h,json=query().model_dump(mode='json')).status_code==202
        assert client.get('/api/v1/assistant/runs/'+str(uuid4()),headers=h).status_code==404
        contracts=client.get('/api/v1/tools/contracts',headers=h);assert contracts.status_code==200
        assert all('input_schema' in t and 'permission' in t for t in contracts.json()['tools'])

def test_human_review_links_reuse_tasks_and_hide_other_owners(db,seed):
    from app.assistant.storage import review_links
    from app.db import models as m
    private=m.ReviewTask(claim_id=seed.claim.id,review_type='ASSET_MATCH_REVIEW',reason='TEST',details={'owner_principal':'other-owner','asset_id':str(seed.asset.id)})
    db.add(private);db.flush()
    result={'gate':{'status':'HUMAN_REVIEW_REQUIRED'},'artifacts':[{'claims':[{'id':str(seed.claim.id)}]}],'asset_candidates':[]}
    links=review_links(db,result,'test-analyst')
    assert str(seed.review.id) in [r['id'] for r in links]
    assert str(private.id) not in [r['id'] for r in links]

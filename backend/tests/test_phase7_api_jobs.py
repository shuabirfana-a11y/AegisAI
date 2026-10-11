from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.db import models as m
from app.main import create_app
from app.api.dependencies import get_session
from test_api import BoundEngine
from conftest import NOW

def factory(db):
    conn=db.connection()
    @contextmanager
    def tx():
        with Session(conn,join_transaction_mode='create_savepoint') as s:
            with s.begin():yield s
    return tx

class Empty:
    name='poc';depends_on=();sources=('GITHUB',)
    def investigate(self,ctx,session,acq):
        from app.enrichment.enrichers.base import WorkOutcome
        return WorkOutcome(status='NO_RESULT',checked=[{'source':'GITHUB','checked_at':NOW.isoformat()}])

class Broken(Empty):
    name='vendor'
    def investigate(self,*args):raise TimeoutError('TEST external failure')

def test_jobs_persist_no_result_and_repeat_history(db,seed):
    from app.enrichment.service import EnrichmentService
    service=EnrichmentService(factory(db),enrichers=[Empty()])
    a=service.run(seed.vuln.id);b=service.run(seed.vuln.id)
    assert a[0].status==b[0].status=='NO_RESULT' and a[0].task_id!=b[0].task_id
    rows=list(db.scalars(select(m.EnrichmentJob)))
    assert len(rows)==2 and all(r.finished_at and r.result['sources_checked'] for r in rows)

def test_failed_enricher_does_not_skip_other_steps(db,seed):
    from app.enrichment.service import EnrichmentService
    results=EnrichmentService(factory(db),enrichers=[Broken(),Empty()]).run(seed.vuln.id)
    assert [r.status for r in results]==['FAILED','NO_RESULT'] and results[0].errors

def test_job_emits_structured_trace_log(db,seed,caplog):
    import json,logging
    from app.enrichment.service import EnrichmentService
    with caplog.at_level(logging.INFO,logger='aegis.ingestion'):
        result=EnrichmentService(factory(db),enrichers=[Empty()]).run(seed.vuln.id)[0]
    logs=[json.loads(r.message) for r in caplog.records if r.name=='aegis.ingestion']
    row=next(r for r in logs if r['event']=='enrichment.finished')
    assert row['task_id']==str(result.task_id) and row['trace_id']==str(result.trace_id) and row['target_id']==str(seed.vuln.id)
    assert row['status']=='NO_RESULT' and row['duration_ms']>=0 and 'error_code' in row

def test_scheduler_does_not_duplicate_pending_jobs(db,seed):
    from app.enrichment.scheduler import schedule_due
    a=schedule_due(db,[seed.vuln.id],now=NOW);b=schedule_due(db,[seed.vuln.id],now=NOW)
    assert len(a)==6 and b==[]
    assert db.scalar(select(func.count()).select_from(m.EnrichmentJob))==6

def app_client(db):
    app=create_app(BoundEngine(db.connection()))
    def session():yield db
    app.dependency_overrides[get_session]=session
    return TestClient(app)

@pytest.mark.parametrize('path',['enrichment','claims','evidence','pocs','patches','timeline'])
def test_phase7_target_read_routes(db,seed,path):
    with app_client(db) as c:
        response=c.get('/api/v1/vulnerabilities/'+seed.vuln.canonical_id+'/'+path)
        assert response.status_code==200 and 'items' in response.json()
        assert c.get('/api/v1/vulnerabilities/unknown/'+path).status_code==404
        assert c.get('/api/v1/vulnerabilities/'+seed.vuln.canonical_id+'/'+path,params={'limit':0}).status_code==422

def test_aggregate_keeps_phase6_and_adds_trusted_data(db,seed):
    with app_client(db) as c:
        data=c.get('/api/v1/vulnerabilities/'+seed.vuln.canonical_id).json()
        assert 'source_variants' in data and 'claims' in data and 'evidence' in data and 'timeline' in data and 'epss' in data
        assert c.get('/api/v1/reviews').json()['items']
        assert c.get('/api/v1/reviews/'+str(seed.review.id)).status_code==200
        evidence=c.get('/api/v1/evidence/'+str(seed.evidence[0].id)).json()
        assert evidence['content_trust_level']=='UNTRUSTED_EXTERNAL_CONTENT'
        assert evidence['claim_verification_status']=='PENDING' and evidence['source_key']=='TEST_CVE'

def decision(seed):return {'expected_revision':1,'expected_claim_revision':1,'request_key':'API-TEST','status':'CONFIRMED',
    'value':seed.claim.value_json,'reason':'TEST analyst reason','evidence_ids':[str(seed.evidence[0].id)]}

def test_review_write_disabled_without_server_secret(db,seed,monkeypatch):
    monkeypatch.delenv('AEGIS_REVIEW_TOKEN',raising=False)
    with app_client(db) as c:assert c.post('/api/v1/reviews/'+str(seed.review.id)+'/resolve',json=decision(seed)).status_code==503

def test_review_token_actor_idempotency_and_stale_revision(db,seed,monkeypatch):
    monkeypatch.setenv('AEGIS_REVIEW_TOKEN','TEST-only-token');monkeypatch.setenv('AEGIS_REVIEW_ACTOR','TEST-server-analyst')
    with app_client(db) as c:
        url='/api/v1/reviews/'+str(seed.review.id)+'/resolve';body=decision(seed)
        assert c.post(url,json=body).status_code==401
        headers={'Authorization':'Bearer TEST-only-token'}
        r=c.post(url,json=body,headers=headers);assert r.status_code==200 and r.json()['actor']=='TEST-server-analyst'
        assert c.post(url,json=body,headers=headers).json()['id']==r.json()['id']
        assert c.post(url,json={**body,'request_key':'OTHER'},headers=headers).status_code==409
        assert c.post(url,json={**body,'actor':'body-forged'},headers=headers).status_code==422

def test_review_confirmation_without_support_rejected(db,seed,monkeypatch):
    monkeypatch.setenv('AEGIS_REVIEW_TOKEN','TEST-only-token')
    with app_client(db) as c:
        body={**decision(seed),'evidence_ids':[]}
        assert c.post('/api/v1/reviews/'+str(seed.review.id)+'/resolve',json=body,headers={'Authorization':'Bearer TEST-only-token'}).status_code==422

import json
import pytest
from sqlalchemy import select,func
from fastapi.testclient import TestClient
from app.db import models as m
from app.main import create_app
from app.api.dependencies import get_session
from conftest import NOW
from test_phase8_matching import confirmed_range
from test_phase8_units import cdx

@pytest.fixture
def asset_client(db,engine,monkeypatch):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN','TEST-LOCAL-SECRET');monkeypatch.setenv('AEGIS_ASSET_OWNER','test-analyst')
    application=create_app(engine)
    application.dependency_overrides[get_session]=lambda:db
    with TestClient(application) as client:yield client

HEAD={'Authorization':'Bearer TEST-LOCAL-SECRET'}

def test_assets_default_closed_and_owner_scoped(asset_client,seed,monkeypatch):
    assert asset_client.get('/api/v1/assets').status_code==401
    assert asset_client.get('/api/v1/assets',headers=HEAD).json()['total']==1
    monkeypatch.setenv('AEGIS_ASSET_OWNER','different-owner')
    assert asset_client.get('/api/v1/assets',headers=HEAD).json()['total']==0
    assert asset_client.get('/api/v1/assets/'+str(seed.asset.id),headers=HEAD).status_code==404
    monkeypatch.delenv('AEGIS_ASSET_TOKEN')
    assert asset_client.get('/api/v1/assets',headers=HEAD).status_code==503

def test_manual_sbom_upgrade_and_read_risks_through_api(asset_client,seed):
    confirmed_range(asset_client.app.dependency_overrides[get_session](),seed)
    a=asset_client.post('/api/v1/assets',headers=HEAD,json={'name':'API demo','is_demo':True,'request_key':'api-create'});assert a.status_code==201
    aid=a.json()['id']
    c=asset_client.post(f'/api/v1/assets/{aid}/components',headers=HEAD,json={'name':'vllm','ecosystem':'PyPI','version':'0.8.2','request_key':'api-component'});assert c.status_code==201
    cid=c.json()['id'];risks=asset_client.get(f'/api/v1/assets/{aid}/risks',headers=HEAD).json()
    assert risks['items'][0]['match_status']=='AFFECTED' and risks['items'][0]['evidence_refs']
    patch=asset_client.patch(f'/api/v1/assets/{aid}/components/{cid}',headers=HEAD,json={'version':'0.8.4','expected_revision':1,'request_key':'api-upgrade'});assert patch.status_code==200
    assert asset_client.get(f'/api/v1/assets/{aid}/risks',headers=HEAD).json()['items'][0]['match_status']=='NOT_AFFECTED'
    assert asset_client.get(f'/api/v1/assets/{aid}/risk-changes',headers=HEAD).json()['total']>=2
    r=asset_client.post(f'/api/v1/assets/{aid}/sbom',headers={**HEAD,'X-Request-Key':'api-sbom','Content-Type':'application/json'},content=json.dumps(cdx()))
    assert r.status_code==200 and r.json()['added']==1
    assert asset_client.get('/api/v1/assets/overview',headers=HEAD).json()['assets']==2

def test_invalid_asset_body_and_repeated_keys_are_explicit(asset_client,seed):
    assert asset_client.post('/api/v1/assets',headers=HEAD,json={'name':'x','owner_principal':'someone','request_key':'k'}).status_code==422
    a=asset_client.post('/api/v1/assets',headers=HEAD,json={'name':'one','request_key':'dup'});assert a.status_code==201
    assert asset_client.post('/api/v1/assets',headers=HEAD,json={'name':'two','request_key':'dup'}).status_code==409
    assert asset_client.get('/api/v1/assets?limit=1001',headers=HEAD).status_code==422

def test_atomic_sbom_failure_leaves_inventory_unchanged(asset_client,db,seed):
    before=db.scalar(select(func.count()).select_from(m.AssetComponent))
    doc=cdx();doc['components'].append({'type':'library','name':'oops','purl':'pkg:pypi/torch@2.0','version':'3.0'})
    r=asset_client.post('/api/v1/assets/'+str(seed.asset.id)+'/sbom',headers={**HEAD,'X-Request-Key':'bad-sbom'},content=json.dumps(doc))
    assert r.status_code==422
    assert db.scalar(select(func.count()).select_from(m.AssetComponent))==before

def test_intelligence_event_queue_targets_only_related_assets_once(db,seed):
    from app.assets.events import dispatch_events
    confirmed_range(db,seed)
    other=m.Asset(name='unrelated',asset_type='service',owner_principal='test-analyst',is_demo=True);db.add(other);db.flush()
    event=m.IntelligenceEvent(event_key='phase8-test-event',vulnerability_id=seed.vuln.id,event_type='KEV_ADDED',detected_at=NOW,summary='SYNTHETIC event')
    db.add(event);db.flush()
    jobs=dispatch_events(db,50);assert len(jobs)==1 and jobs[0].asset_id==seed.asset.id
    assert dispatch_events(db,50)==[]

def test_production_review_dedup_and_private_public_review_separation(db,seed,asset_client):
    from app.assets.risk import RiskService
    confirmed_range(db,seed);seed.asset.environment='production';seed.component.version='custom';db.flush()
    RiskService.recompute(db,seed.asset.id);RiskService.recompute(db,seed.asset.id)
    rows=list(db.scalars(select(m.ReviewTask).where(m.ReviewTask.review_type=='ASSET_MATCH_REVIEW')));assert len(rows)==1
    public=asset_client.get('/api/v1/reviews').json()
    assert all(x['review_type']!='ASSET_MATCH_REVIEW' for x in public['items'])
    assert asset_client.get('/api/v1/reviews/'+str(rows[0].id)).status_code==404

def test_worker_processes_queued_asset_and_retry_is_bounded(db,seed):
    from app.assets.events import run_job
    confirmed_range(db,seed)
    job=m.AssetRecomputeJob(asset_id=seed.asset.id,job_key='TEST-JOB');db.add(job);db.flush()
    run_job(db,job);assert job.status=='succeeded' and job.attempt==1
    assert db.scalar(select(func.count()).select_from(m.AssetRiskSnapshot))==1
    run_job(db,job);assert job.attempt==1

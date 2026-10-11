from fastapi.testclient import TestClient
from app.main import create_app
from app.repositories.ingestion import persist_record
from app.normalizers import osv
from app.db import models as m
from app.db.persistence import store_raw
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
import json

class BoundEngine:
    def __init__(self,conn):self.conn=conn
    @contextmanager
    def connect(self):yield self.conn
    def dispose(self):pass

def setup(db):
    source=m.Source(source_key='OSV',name='OSV fixture',source_type='test',category='test',authority_level='official',authority_scope='test',acquisition_method='fixture',base_url='https://api.osv.dev',status='failed')
    db.add(source);db.flush()
    data=(Path(__file__).parent/'fixtures/source_records/osv.json').read_bytes();payload=json.loads(data)
    now=datetime.now(timezone.utc)
    raw=store_raw(db,source_id=source.id,external_id=payload['id'],source_url='https://api.osv.dev/v1/vulns/'+payload['id'],retrieved_at=now,content_type='application/json',raw_payload=data,publisher='test')
    persist_record(db,source,raw,osv.normalize(payload,raw.id,now));db.flush()
    app=create_app(BoundEngine(db.connection()))
    from app.api.dependencies import get_session
    def session():yield db
    app.dependency_overrides[get_session]=session
    return app

def test_api_health_is_not_down_for_source_failure(db):
    app=setup(db)
    with TestClient(app) as c:
        r=c.get('/health'); assert r.status_code==200 and r.json()['database']=='up'
        assert r.json()['application']=='up'

def test_api_source_status_and_known_gaps(db):
    app=setup(db)
    with TestClient(app) as c:
        r=c.get('/api/v1/sources'); assert r.status_code==200
        row=r.json()['items'][0]
        assert row['source_key']=='OSV' and row['last_success_at'] is None and row['status']=='failed'
        assert 'latest_error' in row and 'records' in row

def test_api_vulnerability_list_filters_and_detail_provenance(db):
    app=setup(db)
    with TestClient(app) as c:
        r=c.get('/api/v1/vulnerabilities',params={'q':'CVE-2025-32434','source':'OSV','ai_relevance':'relevant','limit':1})
        assert r.status_code==200 and r.json()['total']==1
        row=r.json()['items'][0]; detail=c.get('/api/v1/vulnerabilities/'+row['canonical_id'])
        assert detail.status_code==200
        d=detail.json(); assert d['canonical_id']=='CVE-2025-32434'
        assert d['products'] and d['affected_versions'] and d['cvss_assessments'] and d['source_documents']
        assert d['source_documents'][0]['raw_document_id'] and d['source_documents'][0]['content_hash']
        assert d['source_variants'][0]['source']=='OSV' and d['source_variants'][0]['verification_status']=='pending'
        assert c.get('/api/v1/vulnerabilities',params={'offset':1}).json()['items']==[]
        assert c.get('/api/v1/vulnerabilities',params={'source':'NOT_APPROVED'}).status_code==422
        assert c.get('/api/v1/vulnerabilities',params={'ai_relevance':'false'}).status_code==422

def test_api_invalid_id_and_bounds(db):
    app=setup(db)
    with TestClient(app) as c:
        assert c.get('/api/v1/vulnerabilities/unknown').status_code==404
        assert c.get('/api/v1/vulnerabilities',params={'limit':0}).status_code==422
        assert c.get('/api/v1/vulnerabilities',params={'limit':1001}).status_code==422
        assert c.get('/api/v1/sync-runs').status_code==200

def test_api_kev_product_without_version_range_is_visible(db):
    app=setup(db)
    from app.normalizers import cisa_kev
    source=m.Source(source_key='CISA_KEV',name='KEV fixture',source_type='test',category='test',authority_level='official',authority_scope='test',acquisition_method='fixture',base_url='https://example.invalid')
    db.add(source);db.flush()
    payload=json.loads((Path(__file__).parent/'fixtures/source_records/cisa_kev.json').read_bytes())
    payload['vulnerabilities'][0]['product']='Unknown KEV Product';payload['vulnerabilities'][0]['vendorProject']='Test Vendor'
    body=json.dumps(payload).encode();now=datetime.now(timezone.utc)
    raw=store_raw(db,source_id=source.id,external_id='catalog',source_url=source.base_url,retrieved_at=now,content_type='application/json',raw_payload=body,publisher='test')
    record=cisa_kev.normalize({'catalog':payload,'index':0},raw.id,now)
    persist_record(db,source,raw,record);db.flush()
    with TestClient(app) as c:
        detail=c.get('/api/v1/vulnerabilities/'+record.external_id).json()
        assert any(p['canonical_name']=='Unknown KEV Product' for p in detail['products'])

def test_health_returns_503_when_database_is_unavailable():
    class Unavailable:
        def connect(self):raise ConnectionError('test database unavailable')
    with TestClient(create_app(Unavailable())) as c:
        response=c.get('/health')
        assert response.status_code==503 and response.json()['database']=='down'

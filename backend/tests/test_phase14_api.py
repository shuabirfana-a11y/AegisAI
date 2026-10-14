from fastapi.testclient import TestClient
from app.main import create_app
from app.api.dependencies import get_session

def test_intelligence_api_exposes_typed_safe_projection_and_404(db,seed,engine):
    app=create_app(engine);app.dependency_overrides[get_session]=lambda:db
    with TestClient(app) as c:
        response=c.get('/api/v1/intelligence/vulnerabilities/'+str(seed.vuln.id))
        assert response.status_code==200
        body=response.json();assert body['cve_id']==seed.vuln.canonical_id and body['poc_status']=='POC_CANDIDATE'
        assert 'raw_payload' not in str(body) and 'owner_principal' not in str(body)
        assert c.get('/api/v1/intelligence/vulnerabilities/CVE-2099-00009999').status_code==404
        page=c.get('/api/v1/intelligence?type=vulnerability&limit=1').json()
        assert page['total']==1 and len(page['items'])==1
        assert c.get('/api/v1/intelligence?limit=101').status_code==422

def test_intelligence_assets_require_auth_and_keep_actor_scope(db,seed,engine,monkeypatch):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN','phase14-test-fixture-only');monkeypatch.setenv('AEGIS_ASSET_OWNER','another-actor')
    app=create_app(engine);app.dependency_overrides[get_session]=lambda:db
    with TestClient(app) as c:
        path='/api/v1/intelligence/vulnerabilities/'+str(seed.vuln.id)+'/assets'
        assert c.get(path).status_code==401
        response=c.get(path,headers={'Authorization':'Bearer phase14-test-fixture-only'})
        assert response.status_code==200 and response.json()['items']==[]

def test_intelligence_openapi_schema_documents_source_and_poc_states():
    schema=create_app().openapi()
    route=schema['paths'].get('/api/v1/intelligence/vulnerabilities/{id}')
    assert route is not None and route['get']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('SecurityIntelligenceObject')
    dto=schema['components']['schemas']['SecurityIntelligenceObject']
    assert set(dto['properties']['poc_status']['enum'])=={'POC_CANDIDATE','VERIFIED_EXPLOIT','NO_EVIDENCE'}
    assert {'source','references','affected_version','published_time','status'}<=set(dto['properties'])

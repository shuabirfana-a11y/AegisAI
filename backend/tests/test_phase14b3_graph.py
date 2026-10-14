"""Synthetic SQL/HTTP knowledge graph tests; no live model or benchmark scoring."""
import importlib
from uuid import uuid4
import pytest
from sqlalchemy import select, func, event
from fastapi.testclient import TestClient
from app.db import models as m
from app.main import create_app
from app.api.dependencies import get_session


def module():
    try:return importlib.import_module('app.knowledge.security_graph')
    except ModuleNotFoundError:pytest.fail('Phase14-B3 knowledge association projection is missing')


def graph(db, seed, **options):
    return module().build_security_graph(db,seed.vuln.canonical_id,'test-analyst',**options)


def test_existing_relations_create_typed_nodes_and_traceable_edges(db,seed):
    value=graph(db,seed)
    assert {'VULNERABILITY','COMPONENT','VERSION','EVIDENCE'} <= {n.type for n in value.nodes}
    assert {'AFFECTS_COMPONENT','HAS_AFFECTED_RANGE','HAS_EVIDENCE'} <= {e.type for e in value.edges}
    assert all(e.source_records for e in value.edges)
    assert 'ASSET' not in {n.type for n in value.nodes}
    assert not any(n.type=='RISK' for n in value.nodes)


def test_deployed_version_is_distinct_from_an_affected_range(db,seed):
    value=graph(db,seed,include_assets=True)
    versions=[n for n in value.nodes if n.type=='VERSION']
    assert any(n.data.get('version_kind')=='DEPLOYED' and n.data['version']=='0.8.2' for n in versions)
    assert any(n.data.get('version_kind')=='AFFECTED_RANGE' for n in versions)
    assert any(e.type=='DEPLOYED_ON' for e in value.edges)
    assert not any(e.type=='HAS_RISK' for e in value.edges)


def test_unknown_deployed_version_is_retained_and_not_called_safe(db,seed):
    seed.component.version=None;db.flush()
    value=graph(db,seed,include_assets=True)
    versions=[n for n in value.nodes if n.data.get('version_kind')=='DEPLOYED']
    assert len(versions)==1 and versions[0].data['version'] is None
    assert versions[0].data['status']=='UNKNOWN'
    assert not any(n.type=='RISK' and n.data.get('level')=='LOW' for n in value.nodes)


def test_other_owner_assets_are_not_exposed(db,seed):
    seed.asset.owner_principal='private-other-owner';db.flush()
    value=graph(db,seed,include_assets=True)
    assert not any(n.type=='ASSET' for n in value.nodes)
    assert str(seed.asset.id) not in value.model_dump_json()
    with pytest.raises(LookupError):graph(db,seed,asset_id=seed.asset.id)


def test_deleted_inventory_is_not_exposed(db,seed):
    from app.utils.time import utcnow
    seed.asset.deleted_at=utcnow();db.flush()
    assert not any(n.type=='ASSET' for n in graph(db,seed,include_assets=True).nodes)


def test_private_claim_evidence_does_not_leak_into_public_graph(db,seed):
    seed.claim.range_id=None;seed.claim.asset_component_id=seed.component.id;db.flush()
    value=graph(db,seed)
    assert str(seed.claim.id) not in value.model_dump_json()
    assert not any(n.type=='EVIDENCE' for n in value.nodes)


def test_conflicting_claim_does_not_become_confirmed_relation(db,seed):
    seed.claim.verification_status='conflict';db.flush()
    value=graph(db,seed)
    assert any(e.status=='CONFLICT' and str(seed.claim.id) in e.claim_ids for e in value.edges)
    assert not any(e.status=='CONFIRMED' and str(seed.claim.id) in e.claim_ids for e in value.edges)


def test_damaged_evidence_hash_is_omitted(db,seed):
    original=seed.evidence[0]
    fields={col.key:getattr(original,col.key) for col in m.Evidence.__table__.columns if col.key not in ('id','created_at')}
    fields.update(excerpt_hash='0'*64,locator_key='damaged-graph-proof-'+uuid4().hex)
    damaged=m.Evidence(**fields);db.add(damaged);db.flush()
    value=graph(db,seed)
    assert not any(n.data.get('evidence_id')==str(damaged.id) for n in value.nodes)
    assert any('EVIDENCE_INTEGRITY' in w for w in value.warnings)


def test_confirmed_label_without_existing_trust_attestation_is_not_confirmed(db,seed):
    seed.claim.verification_status='confirmed';seed.claim.adopted=False;db.flush()
    value=graph(db,seed)
    assert not any(e.status=='CONFIRMED' for e in value.edges)


def test_component_query_uses_exact_package_and_ecosystem_relationship(db,seed):
    seed.vuln.primary_severity='high';db.flush()
    result=module().query_security_graphs(db,'test-analyst',component='vllm',ecosystem='PyPI',minimum_severity='HIGH')
    assert result.total==1 and result.items[0].vulnerability_id==str(seed.vuln.id)
    assert module().query_security_graphs(db,'test-analyst',component='llm',ecosystem='PyPI').total==0
    assert module().query_security_graphs(db,'test-analyst',component='vllm',ecosystem='npm').total==0


def test_query_pagination_and_scope_do_not_infer_asset_risk(db,seed):
    result=module().query_security_graphs(db,'test-analyst',component='vllm',offset=1,limit=1)
    assert result.total==1 and result.items==()
    assert 'SOURCE_SEVERITY_IS_NOT_ASSET_RISK' in result.limitations


def test_high_severity_query_uses_stored_cvss_when_primary_label_is_unknown(db,seed):
    db.add(m.CvssAssessment(vulnerability_id=seed.vuln.id,source_id=seed.sources[0].id,observation_id=seed.observations[0].id,
        version='3.1',base_score=9.8,severity='critical',provider='SYNTHETIC',scope_key='graph-score-synthetic'))
    db.flush()
    value=module().query_security_graphs(db,'test-analyst',component='vllm',minimum_severity='HIGH')
    assert value.total==1
    assert not any(n.type=='RISK' for n in value.items[0].nodes)


def test_insufficient_claim_is_a_supported_graph_state(db,seed):
    seed.claim.verification_status='insufficient';db.flush()
    value=graph(db,seed)
    assert any(n.type=='EVIDENCE' and n.data['verification_status']=='INSUFFICIENT_EVIDENCE' for n in value.nodes)


def test_graph_projection_does_not_write_business_records(db,seed):
    db.flush();statements=[]
    bind=db.connection()
    def record(conn,cursor,statement,parameters,context,many):statements.append(statement.strip().split()[0].upper())
    event.listen(bind,'before_cursor_execute',record)
    try:graph(db,seed,include_assets=True)
    finally:event.remove(bind,'before_cursor_execute',record)
    assert statements and set(statements)<={'SELECT','SHOW'}
    assert db.scalar(select(func.count()).select_from(m.AssetRiskSnapshot))==0


def test_absent_or_deleted_vulnerability_is_rejected(db,seed):
    with pytest.raises(LookupError):module().build_security_graph(db,'CVE-2099-99999999','test-analyst')
    from app.utils.time import utcnow
    seed.vuln.deleted_at=utcnow();db.flush()
    with pytest.raises(LookupError):graph(db,seed)


def test_graph_budget_is_explicit_and_has_no_dangling_edges():
    schemas=importlib.import_module('app.knowledge.graph_schemas')
    from pydantic import ValidationError
    with pytest.raises(ValidationError):schemas.KnowledgeGraph(vulnerability_id='x',nodes=(),edges=(
        schemas.KnowledgeEdge(id='edge',type='HAS_EVIDENCE',source='missing',target='other',status='CANDIDATE',source_records=('synthetic:source',)),))


def test_openapi_graph_and_query_are_typed():
    schema=create_app().openapi()
    for path in ['/api/v1/intelligence/vulnerabilities/{id}/graph','/api/v1/intelligence/graph/query']:
        assert path in schema['paths']
        assert '$ref' in schema['paths'][path]['get']['responses']['200']['content']['application/json']['schema']
    assert set(schema['components']['schemas']['KnowledgeNode']['properties']['type']['enum'])=={'VULNERABILITY','COMPONENT','VERSION','ASSET','EVIDENCE','RISK'}


def test_graph_http_authorization_validation_and_404(db,seed,engine,monkeypatch):
    monkeypatch.setenv('AEGIS_ASSET_TOKEN','synthetic-graph-access-only');monkeypatch.setenv('AEGIS_ASSET_OWNER','test-analyst')
    app=create_app(engine);app.dependency_overrides[get_session]=lambda:db
    with TestClient(app) as c:
        path='/api/v1/intelligence/vulnerabilities/'+seed.vuln.canonical_id+'/graph'
        assert c.get(path).status_code==401
        headers={'Authorization':'Bearer synthetic-graph-access-only'}
        response=c.get(path,headers=headers);assert response.status_code==200
        assert response.json()['vulnerability_id']==str(seed.vuln.id)
        assert c.get(path,headers=headers,params={'asset_id':str(uuid4())}).status_code==404
        assert c.get(path,headers=headers,params={'asset_id':'invalid'}).status_code==422
        assert c.get('/api/v1/intelligence/graph/query?limit=11',headers=headers).status_code==422


def test_linked_graph_rejects_a_different_investigation_target(db,seed):
    linked={'vulnerability_id':str(uuid4()),'canonical_id':'CVE-2099-11111'}
    with pytest.raises(ValueError,match='TARGET'):graph(db,seed,linked=linked)


@pytest.mark.parametrize('kind,value',[('FIXED_VERSION',{'version':'0.8.4','ecosystem':'PyPI'}),('AFFECTS_VERSION',{'raw_expression':'<0.1','ecosystem':'PyPI'})])
def test_range_does_not_borrow_confirmation_from_a_different_assertion(db,seed,monkeypatch,kind,value):
    seed.claim.range_id=None;seed.claim.package_identifier_id=seed.packages[0].id
    seed.claim.claim_type=kind;seed.claim.value_json=value;db.flush()
    monkeypatch.setattr(module(),'trusted_claim',lambda *a,**k:True)
    value=graph(db,seed)
    assert not any(e.type=='HAS_AFFECTED_RANGE' and e.status=='CONFIRMED' for e in value.edges)


def test_evidence_budget_prevents_unbounded_existing_trust_traversal(db,seed,monkeypatch):
    original=seed.evidence[0]
    fields={col.key:getattr(original,col.key) for col in m.Evidence.__table__.columns if col.key not in ('id','created_at')}
    for _ in range(35):db.add(m.Evidence(**{**fields,'locator_key':'budget-'+uuid4().hex}))
    db.flush()
    def forbidden(*a,**k):raise AssertionError('Unbounded evidence traversal reached')
    monkeypatch.setattr(module(),'current_evidence',forbidden)
    monkeypatch.setattr(module(),'trusted_claim',forbidden)
    value=graph(db,seed)
    assert value.truncated and any('EVIDENCE_BUDGET' in w for w in value.warnings)
    assert not any(e.status=='CONFIRMED' for e in value.edges)


def test_large_source_arrays_yield_an_explicitly_truncated_graph(db,seed):
    original=seed.ranges[0]
    fields={col.key:getattr(original,col.key) for col in m.AffectedVersionRange.__table__.columns if col.key not in ('id','created_at')}
    fields.update(raw_expression='1.0,'*12000,explicit_versions=['1.0.'+str(i) for i in range(12000)],events=None)
    db.add(m.AffectedVersionRange(**fields));db.flush()
    value=graph(db,seed)
    assert value.truncated and len(value.model_dump_json().encode())<=128*1024
    page=module().query_security_graphs(db,'test-analyst',component='vllm')
    assert page.items and page.items[0].truncated


@pytest.mark.parametrize('invalid_reason',['stale','value_mismatch','none'])
def test_confirmed_range_requires_the_same_intact_fresh_reviewed_support(db,seed,monkeypatch,invalid_reason):
    from datetime import timedelta
    from app.utils.time import utcnow
    from hashlib import sha256
    # Separate the range assertion from the original intentionally conflicting fixture.
    seed.claim.range_id=None;seed.claim.product_id=seed.products[1].id
    claim=m.Claim(claim_key='graph-review-'+uuid4().hex,vulnerability_id=seed.vuln.id,
        range_id=seed.ranges[0].id,claim_type='AFFECTS_VERSION',predicate='is_affected',
        value_json={'raw_expression':seed.ranges[0].raw_expression,'ecosystem':'PyPI'},
        scope_key='graph-review-'+uuid4().hex,verification_status='confirmed',adopted=True)
    db.add(claim);db.flush();now=utcnow()
    text=seed.raws[0].raw_payload.decode()
    fields={col.key:getattr(seed.evidence[0],col.key) for col in m.Evidence.__table__.columns if col.key not in ('id','created_at')}
    fields.update(claim_id=claim.id,scope_key=claim.scope_key,excerpt=text,excerpt_hash=sha256(text.encode()).hexdigest(),
        locator={'text_span':[0,len(text)]},observed_value=claim.value_json,retrieved_at=now)
    good=m.Evidence(**{**fields,'locator_key':'reviewed-intact',
        'retrieved_at':now-timedelta(days=60) if invalid_reason=='stale' else now,
        'observed_value':{'raw_expression':'<0.1','ecosystem':'PyPI'} if invalid_reason=='value_mismatch' else claim.value_json})
    bad=m.Evidence(**{**fields,'locator_key':'reviewed-damaged','excerpt_hash':'0'*64})
    db.add_all([good,bad]);db.flush()
    attestation=m.VerificationResult(claim_id=claim.id,claim_revision=claim.revision,status='confirmed',
        verification_method='SYNTHETIC_REVIEW',reason_summary='Synthetic graph intersection test',verified_at=now,
        verified_by_type='human',verified_by_id='synthetic-reviewer',decision_key=uuid4().hex,
        details={'observed_evidence_ids':[str(good.id),str(bad.id)]})
    db.add(attestation);db.flush()
    # Isolate projection checks from existing trust rules. They must independently intersect proofs.
    monkeypatch.setattr(module(),'trusted_claim',lambda *a,**k:True)
    value=graph(db,seed)
    ranges=[e for e in value.edges if e.type=='HAS_AFFECTED_RANGE' and str(claim.id) in e.claim_ids]
    assert ranges
    if invalid_reason=='none':
        assert ranges[0].status=='CONFIRMED'
        assert any(n.data.get('evidence_id')==str(good.id) and n.data['verification_status']=='CONFIRMED' for n in value.nodes)
    else:
        assert ranges[0].status!='CONFIRMED'
        assert not any(n.data.get('claim_id')==str(claim.id) and n.data['verification_status']=='CONFIRMED' for n in value.nodes)

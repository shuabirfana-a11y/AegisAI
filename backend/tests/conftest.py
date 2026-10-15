import os
from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.db import models as m
from app.db.session import make_engine

NOW=datetime(2026,10,3,8,0,tzinfo=timezone.utc)
REPORTS=[]

def pytest_runtest_logreport(report):
    if report.when=='call' or (report.failed and report.when!='call'):
        REPORTS.append({'test':report.nodeid,'phase':report.when,'outcome':report.outcome})

def pytest_sessionfinish(session,exitstatus):
    import json,datetime
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    (root/'work/database_test_report.json').write_text(json.dumps({'kind':'REAL POSTGRESQL / SCHEMA CONTRACT TESTS; NOT BENCHMARK','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_status':int(exitstatus),'passed':sum(r['outcome']=='passed' for r in REPORTS),'failed':sum(r['outcome']=='failed' for r in REPORTS),'skipped':sum(r['outcome']=='skipped' for r in REPORTS),'tests':REPORTS},indent=2),encoding='utf-8')

@pytest.fixture(scope='session')
def engine():
    url=os.environ.get('AEGIS_TEST_DATABASE_URL')
    if not url: pytest.fail('AEGIS_TEST_DATABASE_URL required; database tests must not be silently skipped')
    if make_url(url).database!='aegis_phase5_test': pytest.fail('Only dedicated aegis_phase5_test database is permitted')
    runtime_url=os.environ.get('AEGIS_RUNTIME_TEST_DATABASE_URL')
    if runtime_url:
        root_db=make_url(url);runtime_db=make_url(runtime_url)
        local={'localhost','127.0.0.1','::1'}
        root_host='loopback' if root_db.host in local else root_db.host
        runtime_host='loopback' if runtime_db.host in local else runtime_db.host
        if (root_host,root_db.port or 5432,root_db.database)==(runtime_host,runtime_db.port or 5432,runtime_db.database):
            pytest.fail('DISTINCT_TEST_DATABASES_REQUIRED: committed Runtime fixtures cannot share rollback fixtures')
    engine=make_engine(url)
    yield engine
    engine.dispose()

@pytest.fixture
def db(engine):
    with engine.connect() as conn:
        tx=conn.begin()
        with Session(conn,join_transaction_mode='create_savepoint') as session:
            yield session
        tx.rollback()

@pytest.fixture
def seed(db):
    """Synthetic relational fixture, never a real CVE assertion or benchmark gold."""
    sources=[]; raws=[]; observations=[]
    for index,key in enumerate(['TEST_CVE','TEST_OSV','TEST_VENDOR']):
        s=m.Source(source_key=key,name='Synthetic '+key,source_type='fixture',category='vulnerability',authority_level='community',authority_scope='TEST ONLY',acquisition_method='fixture',base_url='https://example.invalid/'+key,details={'is_test':True})
        db.add(s); db.flush(); sources.append(s)
        payload=f'SYNTHETIC fixture {index}'.encode()
        r=m.RawDocument(source_id=s.id,external_id='CVE-2099-9999001',source_url=s.base_url,published_at=NOW,retrieved_at=NOW,content_type='text/plain',raw_payload=payload,content_hash=sha256(payload).hexdigest(),publisher=key,completeness='complete',details={'is_test':True})
        db.add(r); db.flush(); raws.append(r)
        o=m.SourceObservation(source_id=s.id,raw_document_id=r.id,external_id=r.external_id,record_type='vulnerability',retrieved_at=NOW,http_status=200,lineage_key='original-test-publisher' if index<2 else 'independent-test-vendor',publisher=key,parse_status='parsed',normalizer_version='TEST-1')
        db.add(o); db.flush(); observations.append(o)
    vuln=m.Vulnerability(canonical_id='CVE-2099-9999001',title='SYNTHETIC database fixture',status='published',details={'is_test':True})
    db.add(vuln); db.flush()
    products=[]; packages=[]
    for key,name,package in [('test-vllm','vLLM','vllm'),('test-pytorch','PyTorch','torch')]:
        product=m.Product(canonical_key=key,canonical_name=name,details={'is_test':True})
        db.add(product); db.flush(); products.append(product)
        pkg=m.PackageIdentifier(product_id=product.id,ecosystem='PyPI',package_name=package,purl='pkg:pypi/'+package)
        db.add(pkg); db.flush(); packages.append(pkg)
    ranges=[]
    for i,pkg in enumerate(packages):
        vr=m.AffectedVersionRange(vulnerability_id=vuln.id,product_id=products[i].id,package_identifier_id=pkg.id,source_id=sources[0].id,observation_id=observations[0].id,introduced='0.8.0' if i==0 else '2.5.0',fixed='0.8.4' if i==0 else '2.5.2',range_type='ECOSYSTEM',raw_expression='>=0.8.0,<0.8.4' if i==0 else '>=2.5.0,<2.5.2',scope_key='test-vllm' if i==0 else 'test-torch',parse_status='parsed',parser_version='TEST-1')
        db.add(vr); db.flush(); ranges.append(vr)
    claim=m.Claim(claim_key='TEST-VLLM-RANGE',vulnerability_id=vuln.id,range_id=ranges[0].id,claim_type='affected_version',predicate='is_affected',value_json={'raw_expression':ranges[0].raw_expression},scope_key='test-vllm')
    db.add(claim); db.flush()
    evidence=[]
    for index,stance in enumerate(['support','neutral','contradict']):
        e=m.Evidence(claim_id=claim.id,source_id=sources[index].id,raw_document_id=raws[index].id,observation_id=observations[index].id,scope_key='test-vllm',evidence_type='source_excerpt',stance=stance,excerpt='SYNTHETIC range '+str(index),excerpt_hash=sha256(('SYNTHETIC range '+str(index)).encode()).hexdigest(),source_url=raws[index].source_url,published_at=NOW,retrieved_at=NOW,locator={'text_span':[0,19]},locator_key='test-span',observed_value={'range':'<0.8.4' if index<2 else '<=0.8.5'},publisher=sources[index].source_key,lineage_key=observations[index].lineage_key)
        db.add(e); db.flush(); evidence.append(e)
    poc=m.PocCandidate(vulnerability_id=vuln.id,source_id=sources[0].id,observation_id=observations[0].id,url='https://example.invalid/poc',canonical_url='https://example.invalid/poc',candidate_type='repository',first_seen_at=NOW,last_seen_at=NOW)
    db.add(poc); db.flush()
    asset=m.Asset(name='Synthetic inference service',asset_type='service',owner_principal='test-analyst',is_demo=True)
    db.add(asset); db.flush()
    component=m.AssetComponent(asset_id=asset.id,product_id=products[0].id,package_identifier_id=packages[0].id,version='0.8.2',identity_status='confirmed')
    db.add(component); db.flush()
    review=m.ReviewTask(claim_id=claim.id,review_type='version_conflict',reason='SYNTHETIC same-scope disagreement')
    db.add(review); db.flush()
    return SimpleNamespace(vuln=vuln,sources=sources,raws=raws,observations=observations,products=products,packages=packages,ranges=ranges,claim=claim,evidence=evidence,poc=poc,asset=asset,component=component,review=review)

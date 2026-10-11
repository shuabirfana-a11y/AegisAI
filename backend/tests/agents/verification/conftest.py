"""Committed SYNTHETIC inputs for actual Investigation and tool subprocesses."""
import hashlib
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from app.utils.time import utcnow
from tests.runtime.conftest import engine  # Dedicated runtime database only.


@pytest.fixture(scope='session')
def verification_seed(engine):
    suffix=uuid4().hex
    cve='CVE-2099-'+str(uuid4().int)[:12]
    now=utcnow()
    mark={'is_test':True,'fixture':'PHASE11B2_SYNTHETIC_NOT_BENCHMARK'}
    with transaction(engine) as db:
        source=m.Source(source_key='VERIFY_TEST_'+suffix,name='SYNTHETIC vendor',source_type='vendor_advisory',
            category='vulnerability',authority_level='official',authority_scope='vulnerability affected versions',
            acquisition_method='fixture',base_url='https://example.invalid/SYNTHETIC/'+suffix,details=mark)
        db.add(source);db.flush()
        payload=b'SYNTHETIC official vendor: affected >=0.5.0,<0.7.0; fixed version 0.7.0. Not a real advisory.'
        raw=m.RawDocument(source_id=source.id,external_id=cve,source_url=source.base_url,
            published_at=now,retrieved_at=now,content_type='text/plain',raw_payload=payload,
            content_hash=hashlib.sha256(payload).hexdigest(),publisher='SYNTHETIC vendor',details=mark)
        db.add(raw);db.flush()
        observation=m.SourceObservation(source_id=source.id,raw_document_id=raw.id,external_id=cve,
            record_type='vulnerability',retrieved_at=now,parse_status='parsed',lineage_key='synthetic-vendor:'+suffix,
            publisher='SYNTHETIC vendor',normalizer_version='TEST',normalized_payload={
                'canonical_id':cve,'external_id':cve,'title':'SYNTHETIC vLLM vulnerability',
                'description':'SYNTHETIC official vendor fixture'},details=mark)
        db.add(observation);db.flush()
        vuln=m.Vulnerability(canonical_id=cve,title='SYNTHETIC vLLM vulnerability',status='published',details=mark)
        product=m.Product(canonical_key='verification-vllm-'+suffix,canonical_name='SYNTHETIC vLLM',details=mark)
        db.add_all([vuln,product]);db.flush()
        package=m.PackageIdentifier(product_id=product.id,ecosystem='PyPI',package_name='vllm-verify-'+suffix,
            purl='pkg:pypi/vllm-verify-'+suffix,details=mark)
        db.add(package);db.flush()
        scope='PyPI:'+package.package_name
        value={'ecosystem':'PyPI','package':package.package_name,'raw_expression':'>=0.5.0,<0.7.0'}
        vr=m.AffectedVersionRange(vulnerability_id=vuln.id,product_id=product.id,package_identifier_id=package.id,
            source_id=source.id,observation_id=observation.id,introduced='0.5.0',fixed='0.7.0',
            range_type='ECOSYSTEM',raw_expression=value['raw_expression'],scope_key=scope,
            parse_status='parsed',parser_version='TEST',details=mark)
        claim=m.Claim(claim_key='verification:'+suffix,vulnerability_id=vuln.id,package_identifier_id=package.id,
            claim_type='AFFECTS_VERSION',predicate='AFFECTS_VERSION',scope_key=scope,value_json=value,details=mark)
        db.add_all([vr,claim]);db.flush()
        excerpt='affected >=0.5.0,<0.7.0'
        evidence=m.Evidence(claim_id=claim.id,source_id=source.id,raw_document_id=raw.id,observation_id=observation.id,
            scope_key=scope,evidence_type='official_vendor_advisory',stance='support',excerpt=excerpt,
            excerpt_hash=hashlib.sha256(excerpt.encode()).hexdigest(),source_url=raw.source_url,
            published_at=now,retrieved_at=now,locator={'line':1},locator_key='affected',observed_value=value,
            publisher='SYNTHETIC vendor',lineage_key=observation.lineage_key,details={**mark,'explicit':True})
        db.add(evidence)
        db.add(m.AiRelevanceAssessment(vulnerability_id=vuln.id,observation_id=observation.id,method='rule',
            result='relevant',reason_summary='SYNTHETIC only',evaluated_at=now))
        db.flush()
        saved=SimpleNamespace(cve=cve,actor='verification-owner-'+suffix,vulnerability_id=vuln.id,
            package_id=package.id,source_id=source.id,observation_id=observation.id,raw_id=raw.id,
            claim_id=claim.id,evidence_id=evidence.id,component={'name':'vllm','ecosystem':'PyPI',
                'package_name':package.package_name,'version':'0.6.0'})
    return saved


@pytest.fixture(scope='session')
def investigation_source(engine,verification_seed):
    from tests.agents.investigation.test_end_to_end import run
    svc,saved,_,_=run(engine,verification_seed,'version')
    artifact=svc.read_results(saved.runtime_run_id,verification_seed.actor).artifacts[0]
    return SimpleNamespace(service=svc,run=saved,artifact=artifact,seed=verification_seed)

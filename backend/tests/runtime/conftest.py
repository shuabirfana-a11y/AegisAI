"""Committed, explicitly synthetic data needed by real separate tool processes."""
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4
import os
import pytest


@pytest.fixture(scope='session')
def engine():
    from sqlalchemy.engine import make_url
    from app.db.session import make_engine
    url=os.environ.get('AEGIS_RUNTIME_TEST_DATABASE_URL') or os.environ.get('AEGIS_TEST_DATABASE_URL')
    if not url or make_url(url).database!='aegis_phase5_test':
        pytest.fail('Runtime tests require the dedicated aegis_phase5_test database')
    configured=make_engine(url)
    yield configured
    configured.dispose()


@pytest.fixture(scope='session')
def runtime_seed(engine):
    from app.db import models as m
    from app.db.session import transaction
    from app.utils.time import utcnow
    suffix=uuid4().hex
    cve='CVE-2099-'+str(uuid4().int)[:12]
    actor='runtime-synthetic-'+suffix
    label={'is_test':True,'fixture':'PHASE10A_SYNTHETIC_NOT_BENCHMARK'}
    now=utcnow()
    with transaction(engine) as db:
        source=m.Source(source_key='RUNTIME_TEST_'+suffix,name='SYNTHETIC source',
            source_type='fixture',category='vulnerability',authority_level='community',
            authority_scope='SYNTHETIC ONLY',acquisition_method='fixture',
            base_url='https://example.invalid/runtime/'+suffix,details=label)
        db.add(source);db.flush()
        payload=b'SYNTHETIC runtime advisory; not a real CVE'
        raw=m.RawDocument(source_id=source.id,external_id=cve,source_url=source.base_url,
            published_at=now,retrieved_at=now,content_type='text/plain',raw_payload=payload,
            content_hash=sha256(payload).hexdigest(),publisher='SYNTHETIC',details=label)
        db.add(raw);db.flush()
        observation=m.SourceObservation(source_id=source.id,raw_document_id=raw.id,external_id=cve,
            record_type='vulnerability',retrieved_at=now,http_status=200,lineage_key='test:'+suffix,
            publisher='SYNTHETIC',parse_status='parsed',normalizer_version='TEST',details=label)
        db.add(observation);db.flush()
        vuln=m.Vulnerability(canonical_id=cve,title='SYNTHETIC runtime CVE fixture',status='published',details=label)
        db.add(vuln);db.flush()
        product=m.Product(canonical_key='runtime-vllm-'+suffix,canonical_name='Synthetic vLLM',details=label)
        db.add(product);db.flush()
        name='vllm-runtime-test-'+suffix
        package=m.PackageIdentifier(product_id=product.id,ecosystem='PyPI',package_name=name,
                                     purl='pkg:pypi/'+name,details=label)
        db.add(package);db.flush()
        vr=m.AffectedVersionRange(vulnerability_id=vuln.id,product_id=product.id,
            package_identifier_id=package.id,source_id=source.id,observation_id=observation.id,
            introduced='0.8.0',fixed='0.8.4',range_type='ECOSYSTEM',raw_expression='>=0.8.0,<0.8.4',
            scope_key='PyPI:'+name,parse_status='parsed',parser_version='TEST',details=label)
        db.add(vr);db.flush()
        claim=m.Claim(claim_key='runtime-test:'+suffix,vulnerability_id=vuln.id,
            package_identifier_id=package.id,claim_type='AFFECTS_VERSION',predicate='AFFECTS_VERSION',
            scope_key='PyPI:'+name,value_json={'ecosystem':'PyPI','package':name,
                'raw_expression':'>=0.8.0,<0.8.4'},details=label)
        db.add(claim);db.flush()
        excerpt='SYNTHETIC unverified range'
        evidence=m.Evidence(claim_id=claim.id,source_id=source.id,raw_document_id=raw.id,
            observation_id=observation.id,scope_key=claim.scope_key,evidence_type='source_excerpt',
            stance='support',excerpt=excerpt,excerpt_hash=sha256(excerpt.encode()).hexdigest(),
            source_url=raw.source_url,published_at=now,retrieved_at=now,
            locator={'json_pointer':'/synthetic/range'},locator_key='synthetic-range',
            observed_value=claim.value_json,publisher='SYNTHETIC',lineage_key=observation.lineage_key,details=label)
        db.add(evidence);db.flush()
        poc=m.PocCandidate(vulnerability_id=vuln.id,source_id=source.id,observation_id=observation.id,
            url=source.base_url+'/poc',canonical_url=source.base_url+'/poc',candidate_type='repository',
            first_seen_at=now,last_seen_at=now,details=label)
        patch=m.PatchCandidate(vulnerability_id=vuln.id,product_id=product.id,source_id=source.id,
            observation_id=observation.id,patch_type='fixed_version',identity_key='test:'+suffix,
            release_version='0.8.4',first_seen_at=now,details=label)
        db.add_all([poc,patch]);db.flush()
        asset=m.Asset(name='SYNTHETIC vLLM service',asset_type='service',owner_principal=actor,is_demo=True,details=label)
        db.add(asset);db.flush()
        component=m.AssetComponent(asset_id=asset.id,product_id=product.id,package_identifier_id=package.id,
            version='0.8.2',raw_package_name=name,identity_status='confirmed',details=label)
        db.add(component);db.flush()
        result=SimpleNamespace(cve=cve,actor=actor,asset_id=asset.id,component_id=component.id)
    return result

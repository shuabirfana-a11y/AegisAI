"""Synthetic maintainer records: whole-package unions must keep their witnesses."""
from copy import deepcopy
import pytest
from app.enrichment.parsing import parse_advisory
from app.enrichment.enrichers import vendor
from app.enrichment.versions import contains, canonical_value
from app.enrichment.version_scope import VersionScopeNormalizer

def record():
    return {'cve_id':'CVE-2099-9000001','ghsa_id':'GHSA-test-test-test','state':'published',
        'vulnerabilities':[
            {'package':{'ecosystem':'pip','name':'synthetic-lib'},'vulnerable_version_range':'>= 4.0, < 4.2','patched_versions':'4.2'},
            {'package':{'ecosystem':'pip','name':'synthetic-lib'},'vulnerable_version_range':'< 3.8','patched_versions':'3.8'}]}

def unions(p):
    parsed=parse_advisory(p,'synthetic/repository',p['cve_id'],[p['ghsa_id']])
    return vendor.record_union_assertions(p,parsed['claims'])

def test_complete_record_produces_one_bound_union_without_losing_entries():
    p=record(); before=deepcopy(p); rows=unions(p)
    assert p==before and len(rows)==1
    u=rows[0]; assert len(u['value']['ranges'])==2
    assert contains(u['value'],'4.1') is True
    assert contains(u['value'],'3.9') is False
    assert contains(u['value'],'3.8') is False
    proof=VersionScopeNormalizer().normalize('AFFECTS_VERSION',u['value'],document=p,
        locator={'json_pointer':u['locator']},evidence_id='E1',raw_document_id='R1',integrity_verified=True)
    assert proof is not None and proof.coverage=='RECORD_UNION' and len(proof.entries)==2
    old={'ecosystem':'PyPI','package':'synthetic-lib','ranges':[
        {'events':[{'introduced':'4.0'},{'fixed':'4.2'}]},
        {'events':[{'introduced':'0'},{'fixed':'3.8'}]}]}
    assert canonical_value('AFFECTS_VERSION',u['value'])==canonical_value('AFFECTS_VERSION',old)

@pytest.mark.parametrize('mutation',['foreign_package','foreign_ecosystem','unsupported','conditional'])
def test_no_partial_or_cross_identity_union(mutation):
    p=record()
    if mutation=='foreign_package':p['vulnerabilities'][1]['package']['name']='other-lib'
    elif mutation=='foreign_ecosystem':p['vulnerabilities'][1]['package']['ecosystem']='npm'
    elif mutation=='unsupported':p['vulnerabilities'][1]['vulnerable_version_range']='any vulnerable release'
    else:p['vulnerabilities'][1]['platform']='downstream-only'
    assert unions(p)==[]

def test_vendor_package_identity_is_not_a_product_alias():
    from app.enrichment.context import EnrichmentContext
    ctx=EnrichmentContext(None,'SYNTHETIC',packages=[{'name':'torch','ecosystem':'PyPI'}])
    assert ctx.package('torch')['name']=='torch'
    assert ctx.package('pytorch') is None

def test_vendor_union_reuses_existing_claim_and_keeps_bound_evidence(db,seed):
    from types import SimpleNamespace
    from app.enrichment.context import EnrichmentContext
    from app.enrichment.repository import ClaimStore
    from app.enrichment.verification import VerificationService
    from app.enrichment.version_scope import stored_scope
    from app.db import models as m
    from sqlalchemy import select
    from app.utils.time import utcnow
    from tests.test_version_scope_storage_c2 import observation
    p=record();p['cve_id']=seed.vuln.canonical_id
    for entry in p['vulnerabilities']:entry['package']['name']='vllm'
    source=m.Source(source_key='VENDOR_VLLM',name='Synthetic vendor',source_type='api',
        category='enrichment',authority_level='official',authority_scope='vllm-project/vllm',
        acquisition_method='fixture',base_url='https://api.github.com/repos/vllm-project/vllm/security-advisories/GHSA-test-test-test')
    db.add(source);db.flush();raw,obs=observation(db,source,p,utcnow())
    package={'name':'vllm','ecosystem':'PyPI','package_id':seed.packages[0].id,'repository':'vllm-project/vllm'}
    ctx=EnrichmentContext(seed.vuln.id,p['cve_id'],aliases=[p['ghsa_id']],packages=[package])
    old={'ecosystem':'PyPI','package':'vllm','ranges':[{'range':'>=4.0,<4.2'},{'range':'<3.8'}]}
    existing=ClaimStore.add(db,ctx.target_id,'AFFECTS_VERSION','PyPI:vllm',old,
        subject={'package_identifier_id':seed.packages[0].id})
    doc=SimpleNamespace(payload=p,observation_id=obs.id,source_id=source.id,raw_id=raw.id)
    acq=SimpleNamespace(checked=[],fetch=lambda *args:doc)
    result=vendor.VendorEnricher().investigate(ctx,db,acq)
    assert existing.id in result.claims
    evidence=db.scalar(select(m.Evidence).where(m.Evidence.claim_id==existing.id,m.Evidence.source_id==source.id))
    assert evidence is not None and evidence.details['normalization']=='source-record-union-v1'
    assert len(evidence.details['member_locators'])==2
    proof=stored_scope(db,evidence,'AFFECTS_VERSION')
    assert proof.coverage=='RECORD_UNION' and len(proof.entries)==2
    verified=VerificationService.verify(db,existing)
    assert verified.status=='confirmed'
    assert db.get(m.Evidence,evidence.id).raw_document_id==raw.id


"""Primary advisory assertions must survive source acquisition, without trust shortcuts."""
from copy import deepcopy
import pytest
from app.enrichment.parsing import parse_advisory

VECTOR='CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:C/C:H/I:L/A:N'

def advisory():
    return {'ghsa_id':'GHSA-test-test-test','cve_id':'CVE-2099-9999001','state':'published',
        'cvss_severities':{'cvss_v3':{'vector_string':VECTOR,'score':7.3},'cvss_v4':{'vector_string':None,'score':None}},
        'vulnerabilities':[{'package':{'name':' package-name','ecosystem':'pip'},
                            'vulnerable_version_range':'<3.0.1','patched_versions':'3.0.1'}]}

def parsed(data):return parse_advisory(data,'langchain-ai/langgraph','CVE-2099-9999001',['GHSA-test-test-test'])

def test_primary_cvss_has_exact_field_locator_and_vector_checked_score():
    c=next(x for x in parsed(advisory())['claims'] if x['type']=='CVSS_SCORE')
    assert c['value']=={'score':7.3,'vector':VECTOR,'version':'3.1','severity':'high'}
    assert c['scope']=='CVE-2099-9999001:3.1' and c['locator']=='/cvss_severities/cvss_v3'

def test_advisory_package_whitespace_does_not_create_a_new_distribution():
    claims=[c for c in parsed(advisory())['claims'] if c['type']=='AFFECTS_PRODUCT']
    assert claims[0]['value']['package']=='package-name'

@pytest.mark.parametrize('score',[True,0,11,float('nan')])
def test_inconsistent_primary_cvss_is_not_emitted_and_is_reported(score):
    data=advisory();data['cvss_severities']['cvss_v3']['score']=score
    out=parsed(data)
    assert not any(c['type']=='CVSS_SCORE' for c in out['claims'])
    assert 'CVSS_UNUSABLE:cvss_v3' in out.get('unresolved',[])

def test_primary_source_mapping_is_exact_and_not_a_generic_github_trust_grant():
    from app.enrichment.acquisition import VENDORS,validate_enrichment_url
    from app.enrichment.parsing import OFFICIAL_REPOS
    assert VENDORS['VENDOR_LANGGRAPH']=='langchain-ai/langgraph'
    assert OFFICIAL_REPOS['langgraph-checkpoint-sqlite']=='langchain-ai/langgraph'
    validate_enrichment_url('https://api.github.com/repos/langchain-ai/langgraph/security-advisories/GHSA-test-test-test')
    assert 'unrelated-package' not in OFFICIAL_REPOS

@pytest.mark.parametrize('change',[{'cve_id':'CVE-2099-9999002'},{'state':'draft'},{'withdrawn_at':'2099-01-01T00:00:00Z'}])
def test_wrong_or_unpublished_advisory_cannot_supply_primary_evidence(change):
    data=advisory();data.update(change);assert parsed(data)['claims']==[]

def test_parser_does_not_modify_original_source():
    data=advisory();before=deepcopy(data);parsed(data);assert data==before

def test_vendor_enricher_persists_cvss_without_a_package_subject(db,seed):
    import httpx,json
    from sqlalchemy import select
    from app.db import models as m
    from app.enrichment.enrichers.vendor import VendorEnricher
    from tests.test_phase7_enrichers import acquire,context
    data=advisory();data['cve_id']=seed.vuln.canonical_id
    data['vulnerabilities'][0]['package']['name']=' vllm'
    out=VendorEnricher().investigate(context(db,seed),db,acquire(db,lambda _:httpx.Response(200,json=data)))
    claim=db.scalar(select(m.Claim).where(m.Claim.claim_type=='CVSS_SCORE'))
    assert out.status=='SUCCESS' and claim is not None and claim.package_identifier_id is None
    ev=db.scalar(select(m.Evidence).where(m.Evidence.claim_id==claim.id))
    assert ev.evidence_type=='official_vendor_advisory'
    assert ev.locator=={'json_pointer':'/cvss_severities/cvss_v3'}
    assert json.loads(db.get(m.RawDocument,ev.raw_document_id).raw_payload)['cve_id']==seed.vuln.canonical_id

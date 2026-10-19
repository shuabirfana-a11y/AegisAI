"""SYNTHETIC source-contract cases, never benchmark answers."""
from types import SimpleNamespace
import pytest
from app.enrichment.acquisition import VENDORS, validate_enrichment_url
from app.enrichment.parsing import OFFICIAL_REPOS, parse_advisory
from app.agents.verification.snapshot import scope_supported
from app.enrichment.version_scope import VersionScopeNormalizer, compare_scopes

REPO='langchain-ai/langchain'

def test_maintainer_source_and_component_route_are_registered():
    assert VENDORS.get('VENDOR_LANGCHAIN')==REPO
    assert OFFICIAL_REPOS.get('langchain-core')==REPO
    assert OFFICIAL_REPOS.get('unrelated-langchain-sounding-package') is None

def test_registered_primary_scope_requires_exact_repository_url():
    c=SimpleNamespace(claim_type='FIXED_VERSION',value={'package':'langchain-core'},
                      scope_key='PyPI:langchain-core',vulnerability_id='synthetic-vulnerability')
    good='https://api.github.com/repos/'+REPO+'/security-advisories/GHSA-test-test-test'
    assert scope_supported(REPO,c,source_key='VENDOR_LANGCHAIN',reference={'url':good})
    for bad in [good.replace(REPO,'other/project'),good.replace('https:','http:'),
                good.replace('api.github.com','127.0.0.1'),good.replace('api.github.com','api.github.com.evil.invalid')]:
        assert not scope_supported(REPO,c,source_key='VENDOR_LANGCHAIN',reference={'url':bad})

@pytest.mark.parametrize('url',[
    'https://127.0.0.1/repos/langchain-ai/langchain/security-advisories/GHSA-test-test-test',
    'https://api.github.com.evil.invalid/repos/langchain-ai/langchain/security-advisories/GHSA-test-test-test',
    'http://api.github.com/repos/langchain-ai/langchain/security-advisories/GHSA-test-test-test',
    'https://api.github.com/repos/langchain-ai/../security-advisories/GHSA-test-test-test',
])
def test_source_registration_does_not_expand_url_permissions(url):
    with pytest.raises(ValueError):validate_enrichment_url(url)

def advisory():
    return {'cve_id':'CVE-2099-9999001','ghsa_id':'GHSA-test-test-test','state':'published',
        'vulnerabilities':[
            {'package':{'ecosystem':'pip','name':'langchain-core'},'vulnerable_version_range':'< 4.2.5, >= 4.0.0','patched_versions':'4.2.5'},
            {'package':{'ecosystem':'pip','name':'langchain-core'},'vulnerable_version_range':'< 3.8.1','patched_versions':'3.8.1'}]}

def test_primary_parser_preserves_two_distinct_maintenance_entries():
    p=advisory();out=parse_advisory(p,REPO,p['cve_id'],[p['ghsa_id']])
    assert out['association']=='MATCHED'
    affected=[x for x in out['claims'] if x['type']=='AFFECTS_VERSION']
    fixed=[x for x in out['claims'] if x['type']=='FIXED_VERSION']
    assert [x['value']['range'] for x in affected]==['< 4.2.5, >= 4.0.0','< 3.8.1']
    assert [x['value']['version'] for x in fixed]==['4.2.5','3.8.1']
    assert [x['locator'] for x in fixed]==['/vulnerabilities/0/patched_versions','/vulnerabilities/1/patched_versions']
    assert all(x['value']['package']=='langchain-core' for x in affected+fixed)
    scopes=[]
    for x in fixed:
        s=VersionScopeNormalizer().normalize('FIXED_VERSION',x['value'],document=p,locator={'json_pointer':x['locator']},
            evidence_id='E'+x['value']['version'],raw_document_id='R1',raw_hash='original-hash',integrity_verified=True)
        assert s is not None
        scopes.append(s)
    result=compare_scopes({'type':'FIXED_VERSION','value':fixed[0]['value'],'version_scopes':[scopes[0].model_dump(mode='json')]},
                          {'type':'FIXED_VERSION','value':fixed[1]['value'],'version_scopes':[scopes[1].model_dump(mode='json')]})
    assert result.result=='BRANCH_DIFFERENCE'

def test_primary_parser_rejects_wrong_identity_and_withdrawal():
    p=advisory()
    assert parse_advisory(p,REPO,'CVE-2099-9999002',[p['ghsa_id']])['association']=='UNRESOLVED'
    p['withdrawn_at']='2099-01-02T00:00:00Z'
    assert parse_advisory(p,REPO,p['cve_id'],[p['ghsa_id']])['association']=='UNRESOLVED'

def test_package_name_from_external_advisory_is_not_silently_rewritten():
    p=advisory();p['vulnerabilities']=p['vulnerabilities'][:1]
    p['vulnerabilities'][0]['package']['name']='pytorch'
    rows=parse_advisory(p,'pytorch/pytorch',p['cve_id'],[p['ghsa_id']])['claims']
    assert all(x['value']['package']=='pytorch' for x in rows if x['type'] in ('AFFECTS_PRODUCT','AFFECTS_VERSION','FIXED_VERSION'))
    assert OFFICIAL_REPOS.get('pytorch') is None

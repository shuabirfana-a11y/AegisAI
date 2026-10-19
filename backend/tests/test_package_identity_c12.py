"""Synthetic identity contracts, never CVE-specific aliases."""
import pytest
from app.enrichment.context import EnrichmentContext

def ctx(packages=None):
    return EnrichmentContext(None,'SYNTHETIC',packages=packages or [
        {'name':'sample-lib','ecosystem':'PyPI','package_id':'pkg1','product_id':'product1','repository':'sample/project'}])

@pytest.mark.parametrize('name,eco,repo,status',[
    ('sample-lib','PyPI',None,'EXACT_MATCH'),
    ('Sample_Lib','PyPI',None,'VERIFIED_ALIAS'),
    ('sample-lib','Debian',None,'IDENTITY_CONFLICT'),
    ('sample-lib','npm',None,'IDENTITY_CONFLICT'),
    ('sample-libs','PyPI',None,'IDENTITY_UNKNOWN'),
    ('sample-product','PyPI','sample/project','RELATED_PACKAGE'),
    (None,'PyPI',None,'IDENTITY_UNKNOWN'),
    ('sample-lib',None,None,'IDENTITY_UNKNOWN'),
])
def test_identity_status_and_basis_are_explicit(name,eco,repo,status):
    result=ctx().resolve_package(name,eco,repository=repo)
    assert result['status']==status
    assert result['original_name']==name and result['original_ecosystem']==eco
    assert result['method'] and result['reason']
    if status=='VERIFIED_ALIAS':
        assert result['normalized_name']=='sample-lib' and result['basis_reference'].startswith('https://packaging.python.org/')
    if status not in ('EXACT_MATCH','VERIFIED_ALIAS'):assert result['package'] is None

def test_legacy_package_lookup_does_not_choose_ambiguous_ecosystems():
    c=ctx([{'name':'shared','ecosystem':'PyPI'},{'name':'shared','ecosystem':'npm'}])
    assert c.package('shared') is None
    assert c.package('shared',ecosystem='PyPI')['ecosystem']=='PyPI'

def test_product_name_is_not_a_distribution_alias():
    c=ctx([{'name':'torch','ecosystem':'PyPI','repository':'pytorch/pytorch'}])
    result=c.resolve_package('pytorch','PyPI',repository='pytorch/pytorch')
    assert result['status']=='RELATED_PACKAGE' and result['package'] is None


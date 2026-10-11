import pytest
from sqlalchemy import select, func
from app.db import models as m
from app.tooling.gateway import ToolGateway, ToolContext
from app.tooling.adapters import execute_local

def invoke(db,seed,version='0.6.0',**overrides):
    pkg=db.scalar(select(m.PackageIdentifier).where(m.PackageIdentifier.id==seed.packages[0].id))
    args={'target':seed.vuln.canonical_id,'name':'vLLM','ecosystem':pkg.ecosystem,
          'package_name':pkg.package_name,'version':version,**overrides}
    gateway=ToolGateway(executor=lambda name,args,ctx:execute_local(db,name,args,ctx.actor))
    return gateway.invoke('inspect_component_version',args,ToolContext(actor='SYNTHETIC-version-test'))

def test_version_tool_registered_read_only():
    from app.tooling.contracts import REGISTRY
    assert 'inspect_component_version' in REGISTRY
    assert REGISTRY['inspect_component_version'].permission=='READ_ONLY'

def test_vllm_060_version_results_use_existing_comparator(db,seed):
    got=invoke(db,seed)
    assert got.status=='success'
    assert got.data['component']['version']=='0.6.0'
    assert got.data['source_range_results']
    assert all(r['range_result'] in ('IN_RANGE','OUT_OF_RANGE','UNKNOWN') for r in got.data['source_range_results'])
    assert all(r['verified'] is False for r in got.data['source_range_results'])

@pytest.mark.parametrize('version',['0.8.0','0.8.4','invalid-version'])
def test_version_boundaries_and_unknown_are_not_guessed(db,seed,version):
    got=invoke(db,seed,version)
    assert got.status=='success'
    results=got.data['source_range_results']
    if version=='invalid-version':assert all(r['range_result']=='UNKNOWN' for r in results)
    assert all('comparison' in r for r in results)

def test_unknown_identity_is_explicit(db,seed):
    got=invoke(db,seed,package_name='SYNTHETIC-nonexistent-package')
    assert got.status=='success' and got.data['identity_resolution']['status']=='UNRESOLVED'
    assert got.data['source_range_results']==[] and got.data['uncertainties']

def test_version_tool_does_not_mutate_business_tables(db,seed):
    models=[m.Claim,m.Evidence,m.VerificationResult,m.Asset,m.AssetRiskSnapshot,m.PocCandidate,m.PatchCandidate]
    counts=lambda:[db.scalar(select(func.count()).select_from(model)) for model in models]
    before=counts(); got=invoke(db,seed); assert got.status=='success'
    assert counts()==before

def test_evidence_authority_is_metadata_not_verification(db,seed):
    gateway=ToolGateway(executor=lambda name,args,ctx:execute_local(db,name,args,ctx.actor))
    got=gateway.invoke('get_vulnerability',{'target':seed.vuln.canonical_id},ToolContext(actor='SYNTHETIC'))
    assert got.status=='success' and got.evidence_refs
    assert all('authority_level' in r and 'authority_scope' in r for r in got.evidence_refs)
    assert all('is_current' in r for r in got.evidence_refs)
    assert not any(r.get('verified') for r in got.evidence_refs)

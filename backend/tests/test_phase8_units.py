"""Synthetic rule fixtures; these are not human benchmark labels."""
import json,random
import pytest
from packaging.version import Version

def test_purl_resolves_exact_package_not_display_fuzzy(db,seed):
    from app.assets.identity import resolve_component
    r=resolve_component(db,{'name':'Display','purl':'pkg:pypi/vllm@0.8.2','version':'0.8.2'})
    assert r['status']=='RESOLVED' and r['package_identifier_id']==seed.packages[0].id
    assert r['method']=='PURL_EXACT'

def test_explicit_alias_uses_one_product(db,seed):
    from app.assets.identity import resolve_component
    r=resolve_component(db,{'name':'PyTorch','version':'2.6.0'})
    assert r['status']=='RESOLVED' and r['package_identifier_id']==seed.packages[1].id
    assert r['method']=='PRODUCT_ALIAS'

@pytest.mark.parametrize('value',[{'name':'vllm','ecosystem':'npm'},{'name':'vllm-awesome','ecosystem':'PyPI'},{'name':'unknown'}])
def test_wrong_ecosystem_and_similar_name_never_merge(db,seed,value):
    from app.assets.identity import resolve_component
    assert resolve_component(db,value)['status']=='UNRESOLVED'

@pytest.mark.parametrize('extra',[{'ecosystem':'npm'},{'package_name':'torch'},{'version':'0.8.3'}])
def test_purl_contradiction_not_alias_fallback(db,seed,extra):
    from app.assets.identity import resolve_component
    with pytest.raises(ValueError,match='mismatch'):
        resolve_component(db,{'name':'vllm','purl':'pkg:pypi/vllm@0.8.2',**extra})

def test_multiple_confirmed_aliases_are_ambiguous(db,seed):
    from app.assets.identity import resolve_component
    from app.db import models as m
    for p in seed.products:
        db.add(m.ProductAlias(product_id=p.id,source_id=seed.sources[0].id,alias='shared',normalized_alias='shared',alias_type='product',namespace='global',verification_status='confirmed'))
    db.flush()
    assert resolve_component(db,{'name':'shared'})['status']=='AMBIGUOUS'

@pytest.mark.parametrize('raw,normalized',[('v0.8.2','0.8.2'),('0.8.2+cu124','0.8.2+cu124'),('2.6.0.dev','2.6.0.dev0'),('1.2rc1','1.2rc1')])
def test_pep440_normalization_preserves_semantics(raw,normalized):
    from app.assets.versions import normalize_version
    r=normalize_version(raw,'PyPI')
    assert r['status']=='NORMALIZED' and r['normalized']==normalized

@pytest.mark.parametrize('raw,eco',[('0.8.2-custom','PyPI'),('4.x','PyPI'),('abcdef','Git'),('1.2.3+build','npm'),(None,'PyPI')])
def test_unsupported_versions_stay_unknown(raw,eco):
    from app.assets.versions import normalize_version
    assert normalize_version(raw,eco)['status']=='UNKNOWN'

@pytest.mark.parametrize('v,want',[('0.8.2',True),('0.8.4',False),('0.8.2+cu124',True),('0.8.4+cu124',False),('0.8.4rc1',True),('nonsense',None)])
def test_deterministic_boundary(v,want):
    from app.assets.versions import compare_version
    r=compare_version(v,{'ecosystem':'PyPI','raw_expression':'<0.8.4'})
    assert r['affected'] is want
    if want is not None:assert r['comparisons']

def test_generated_normalization_idempotence_and_exclusive_endpoint():
    from app.assets.versions import normalize_version,compare_version
    # Generates valid ordered releases; checks invariants, not mirrored comparator code.
    rng=random.Random(808)
    for _ in range(250):
        v='.'.join(str(rng.randrange(100)) for _ in range(3))
        n=normalize_version('v'+v,'PyPI')['normalized']
        assert normalize_version(n,'PyPI')['normalized']==n
        assert compare_version(n,{'ecosystem':'PyPI','raw_expression':'<'+n})['affected'] is False
        assert compare_version(n,{'ecosystem':'PyPI','raw_expression':'<='+n})['affected'] is True

def cdx(components=None):
    return {'bomFormat':'CycloneDX','specVersion':'1.6','version':1,'components':components or [
        {'type':'library','bom-ref':'vllm','name':'vllm','version':'0.8.2','purl':'pkg:pypi/vllm@0.8.2'}]}

def test_cyclonedx_official_schema_extracts_component():
    from app.assets.sbom import parse_sbom
    r=parse_sbom(json.dumps(cdx()).encode())
    assert r['format']=='CycloneDX' and r['components'][0]['purl']=='pkg:pypi/vllm@0.8.2'
    assert r['components'][0]['source_ref']=='vllm'

def test_spdx_23_external_purl_extracts_component():
    from app.assets.sbom import parse_sbom
    doc={'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':'demo','documentNamespace':'https://example.invalid/demo','creationInfo':{'creators':['Tool: AegisAI-test'],'created':'2026-10-03T00:00:00Z'},'packages':[{'name':'vllm','SPDXID':'SPDXRef-vllm','downloadLocation':'NOASSERTION','versionInfo':'0.8.2','externalRefs':[{'referenceCategory':'PACKAGE-MANAGER','referenceType':'purl','referenceLocator':'pkg:pypi/vllm@0.8.2'}]}]}
    r=parse_sbom(json.dumps(doc).encode());assert r['format']=='SPDX' and r['components'][0]['version']=='0.8.2'

@pytest.mark.parametrize('data',[b'{',b'{"x":NaN}',b'{"bomFormat":"CycloneDX","specVersion":"1.6","version":1,"version":2}',json.dumps(cdx([{'type':'library','name':42}])).encode(),b'['*60+b'0'+b']'*60,b'x'*(2*1024*1024+1)],ids=['malformed','nan','duplicate-key','invalid-schema','depth','size'])
def test_sbom_invalid_input_is_bounded_and_rejected(data):
    from app.assets.sbom import parse_sbom
    with pytest.raises(ValueError):parse_sbom(data)

def test_path_like_bom_refs_never_access_files():
    from app.assets.sbom import parse_sbom
    doc=cdx();doc['components'][0]['bom-ref']='../../private'
    r=parse_sbom(json.dumps(doc).encode())
    assert r['components'][0]['source_ref']=='../../private'
    assert r['content_trust_level']=='UNTRUSTED_EXTERNAL_CONTENT'

def test_conflicting_same_bom_ref_rejected():
    from app.assets.sbom import parse_sbom
    one=cdx()['components'][0];two={**one,'version':'0.8.3','purl':'pkg:pypi/vllm@0.8.3'}
    with pytest.raises(ValueError,match='duplicate'):
        parse_sbom(json.dumps(cdx([one,two])).encode())

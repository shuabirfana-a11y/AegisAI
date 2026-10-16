"""Business counterexamples for source-bound scope normalization, no benchmark labels."""
import json
from copy import deepcopy
from uuid import uuid4
import pytest
from tests.agents.verification.helpers import claim,evidence,context
from app.agents.verification.rules import evaluate_snapshot
from app.assets.versions import compare_version

def normalize(cs,es):
    from app.agents.verification.impact_normalization import normalize_bundle
    return normalize_bundle(tuple(cs),tuple(es),source_artifact_id=uuid4())

def patched(identifier='F1',expression='>= 2.4.3',**changes):
    value={'ecosystem':'PyPI','package':'vllm','version':None,'raw_expression':expression}
    c=claim(identifier,claim_type='FIXED_VERSION',value=value,evidence_ids=('E-'+identifier,))
    e=evidence('E-'+identifier,identifier,observed_value=deepcopy(value),content=json.dumps(expression),
        reference={'url':'https://example.invalid/SYNTHETIC','locator':{'json_pointer':'/vulnerabilities/0/patched_versions'}},**changes)
    return c,e

def test_explicit_inclusive_patched_constraint_reaches_confirmed_claim():
    c,e=patched();before=(c.model_dump_json(),e.model_dump_json())
    cs,es=normalize([c],[e]);assert cs[0].value['version']=='2.4.3'
    assert cs[0].impact_scope.fixed_version=='2.4.3'
    assert es[0].details['source_claim_id']==c.claim_id
    assert evaluate_snapshot(context(cs,es)).claims[0].status=='CONFIRMED'
    assert before==(c.model_dump_json(),e.model_dump_json())

@pytest.mark.parametrize('expression',['> 2.4.3','>= nonsense','< 2.4.3','2.4.x','>= 2.4.3, < 2.5.0'])
def test_no_invented_fixed_release_from_ambiguous_constraint(expression):
    c,e=patched(expression=expression);cs,es=normalize([c],[e])
    assert cs[0].value['version'] is None
    assert evaluate_snapshot(context(cs,es)).claims[0].status!='CONFIRMED'

@pytest.mark.parametrize('change',[
 {'content':'"other version"'},
 {'reference':{'url':'https://example.invalid/SYNTHETIC','locator':{'json_pointer':'/vulnerabilities/0/vulnerable_version_range'}}},
 {'integrity_status':'INVALID'},
])
def test_fixed_constraint_requires_bound_source_field(change):
    c,e=patched();e=e.model_copy(update=change);cs,es=normalize([c],[e])
    assert cs[0].value['version'] is None

def test_equivalent_normalized_claims_keep_original_binding_and_primary_evidence():
    c,e=patched('vendor')
    value={'ecosystem':'PyPI','package':'vllm','version':'2.4.3'}
    other=claim('index',claim_type='FIXED_VERSION',value=value,evidence_ids=('E-index',))
    indexed=evidence('E-index','index',observed_value=value,authority_level='authoritative',
        evidence_type='normalized_version',source_type='normalized_version')
    cs,es=normalize([other,c],[indexed,e]);assert len(cs)==1 and len(es)==2
    assert set(cs[0].impact_scope.source_claim_ids)=={'vendor','index'}
    assert {x.details['source_claim_id'] for x in es}=={'vendor','index'}
    assert {x.evidence_id for x in es}=={'E-vendor','E-index'}
    assert evaluate_snapshot(context(cs,es)).verification_status=='CONFIRMED'

def test_different_ranges_are_not_coalesced_or_voted_away():
    a=claim('A','<2.4.3',evidence_ids=('EA',));b=claim('B','<2.4.4',evidence_ids=('EB',))
    ea=evidence('EA','A','<2.4.3');eb=evidence('EB','B','<2.4.4')
    cs,es=normalize([a,b],[ea,eb]);assert len(cs)==2
    got=evaluate_snapshot(context(cs,es));assert got.verification_status=='CONFLICT'
    assert got.conflicts and len(got.conflicting_evidence)==2

def test_one_upstream_reprint_does_not_gain_confirmation():
    c=claim('A','<2.4.3',evidence_ids=('EA','EB'))
    es=[evidence(id,'A','<2.4.3',authority_level='authoritative',evidence_type='normalized_version',
        source_type='normalized_version',lineage_key='same-original') for id in ('EA','EB')]
    cs,es=normalize([c],es)
    got=evaluate_snapshot(context(cs,es))
    assert got.claims[0].status=='INSUFFICIENT_EVIDENCE'
    assert got.verification_status in ('PENDING','INSUFFICIENT_EVIDENCE')

@pytest.mark.parametrize(('version','affected'),[('2.4.1',True),('2.4.4',False),('2.4.3',False),('1.10.0',True),(None,None)])
def test_normalized_scope_reuses_version_math_and_retains_unknown(version,affected):
    c=claim('A','<2.4.3');e=evidence('E1','A','<2.4.3');cs,es=normalize([c],[e])
    assert compare_version(version,cs[0].value)['affected'] is affected
    assert cs[0].impact_scope.affected_version_range

def test_unknown_range_is_not_safe_or_confirmed():
    c=claim('A','some old versions');e=evidence('E1','A','some old versions');cs,es=normalize([c],[e])
    assert compare_version('2.4.1',cs[0].value)['affected'] is None
    assert evaluate_snapshot(context(cs,es)).claims[0].status=='INSUFFICIENT_EVIDENCE'

def test_different_package_and_branch_are_not_coalesced():
    a=claim('A','<2.4.3');b=claim('B','<2.4.3',package_identifier_id='other-package',branch='branch-one')
    cs,es=normalize([a,b],[evidence('E1','A','<2.4.3')]);assert len(cs)==2

def test_unsupported_platform_qualification_stays_unconfirmed():
    c=claim('A','<2.4.3');c=c.model_copy(update={'value':{**c.value,'platform':'linux'}})
    e=evidence('E1','A','<2.4.3',observed_value=c.value);cs,es=normalize([c],[e])
    assert cs[0].impact_scope.platform=='linux'
    assert evaluate_snapshot(context(cs,es)).verification_status!='CONFIRMED'

def test_qualification_is_not_shared_with_an_unqualified_claim():
    a=claim('A','<2.4.3')
    b=claim('B','<2.4.3',value={**a.value,'platform':'linux'})
    cs,es=normalize([a,b],[evidence('EA','A','<2.4.3'),evidence('EB','B','<2.4.3',observed_value=b.value)])
    assert len(cs)==2
    statuses={x.claim.claim_id:x.status for x in evaluate_snapshot(context(cs,es)).claims}
    assert statuses['B']!='CONFIRMED'

def test_large_explicit_version_set_does_not_crash_or_truncate_scope():
    c=claim('A',value={'ecosystem':'PyPI','package':'vllm','explicit_versions':[f'1.{i}.0' for i in range(130)]})
    e=evidence('E1','A',observed_value=c.value)
    cs,es=normalize([c],[e])
    assert cs[0].impact_scope.normalization_state=='UNSUPPORTED'
    assert not cs[0].impact_scope.affected_version_range
    assert len(cs[0].value['explicit_versions'])==130
    assert evaluate_snapshot(context(cs,es)).claims[0].status!='CONFIRMED'

@pytest.mark.parametrize('version',['not-a-version','>= 0.7.0',3])
def test_invalid_prepopulated_fixed_value_cannot_be_confirmed(version):
    c=claim('bad',claim_type='FIXED_VERSION',value={'ecosystem':'PyPI','package':'vllm','version':version})
    e=evidence('E1','bad',observed_value=c.value)
    cs,es=normalize([c],[e])
    assert cs[0].value==c.value
    assert cs[0].impact_scope.normalization_state=='UNSUPPORTED'
    assert cs[0].impact_scope.fixed_version is None
    assert evaluate_snapshot(context(cs,es)).claims[0].status!='CONFIRMED'

def test_version_order_does_not_use_lexicographic_comparison():
    c=claim('A','<1.9');e=evidence('E1','A','<1.9')
    cs,es=normalize([c],[e])
    assert compare_version('1.10',cs[0].value)['affected'] is False

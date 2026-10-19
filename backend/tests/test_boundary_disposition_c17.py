"""Generic boundary audit guards; synthetic versions are not vulnerability facts."""
from copy import deepcopy
import pytest
from packaging.version import Version
from app.enrichment.versions import contains, intervals
from app.enrichment.version_scope import compare_scopes, VersionScopeNormalizer
from app.enrichment.rules import compare_claims
from app.assets.versions import compare_version


def source(expression, fixed='4.2.1', package='audit-engine'):
    return {'vulnerabilities': [{'package': {'ecosystem': 'pip', 'name': package},
        'vulnerable_version_range': expression, 'first_patched_version': fixed}]}


def claim(expression, *, fixed='4.2.1', package='audit-engine'):
    return {'scope': 'PyPI:'+package, 'type': 'AFFECTS_VERSION',
        'value': {'ecosystem': 'PyPI', 'package': package, 'range': expression},
        'version_source_contexts': [{'document': source(expression, fixed, package),
            'locator': {'json_pointer': '/vulnerabilities/0'}, 'integrity_verified': True,
            'evidence_id': 'synthetic-evidence', 'raw_document_id': 'synthetic-raw'}]}


@pytest.mark.parametrize('version,expected', [('4.2.0', True), ('4.2.1', False)])
def test_point_agreement_does_not_prove_full_scope_equivalence(version, expected):
    a,b=claim('<4.2.1'),claim('<=4.2.0')
    assert contains(a['value'],version) is expected
    assert contains(b['value'],version) is expected
    assert compare_scopes(a,b).result == 'BOUNDARY_DIFFERENCE'
    assert compare_claims(a,b) == 'VERSION_CONFLICT'


@pytest.mark.parametrize('witness', ['4.2.0.post1', '4.2.0.1'])
def test_universal_equivalence_has_a_valid_version_order_counterexample(witness):
    assert Version('4.2.0') < Version(witness) < Version('4.2.1')
    assert contains(claim('<4.2.1')['value'],witness) is True
    assert contains(claim('<=4.2.0')['value'],witness) is False


def test_actual_equivalent_zero_padding_is_not_a_conflict():
    a,b=claim('<4.2.1'),claim('<4.2.1.0')
    assert compare_scopes(a,b).result == 'SAME_SCOPE'
    assert compare_claims(a,b) is None


def test_last_affected_is_not_a_guessed_successor_fix():
    a,b=claim('<=4.2.0',fixed=None),claim('<4.2.1')
    assert compare_scopes(a,b).result == 'BOUNDARY_DIFFERENCE'
    ctx=a['version_source_contexts'][0]
    scope=VersionScopeNormalizer().normalize(a['type'],a['value'],**ctx)
    assert scope.fixed_version is None and tuple(scope.entries[0]['fixed_versions']) == ()


def test_common_fixed_release_does_not_make_affected_ranges_equal():
    a,b=claim('<4.2.1'),claim('<=4.2.0')
    assert a['version_source_contexts'][0]['document']['vulnerabilities'][0]['first_patched_version']=='4.2.1'
    assert compare_scopes(a,b).result == 'BOUNDARY_DIFFERENCE'


def test_same_upstream_metadata_is_not_a_permission_to_override_events():
    a=claim('<4.2.1')
    a['version_source_contexts'][0]['document']['database_specific']={'last_known_affected_version_range':'<=4.2.0'}
    before=deepcopy(a)
    assert compare_scopes(a,claim('<=4.2.0')).result == 'BOUNDARY_DIFFERENCE'
    assert a == before


def test_timestamp_order_is_not_proof_of_supersession():
    a,b=claim('<4.2.1'),claim('<=4.2.0')
    a['version_source_contexts'][0]['document']['modified']='2026-10-17T00:00:00Z'
    b['version_source_contexts'][0]['document']['modified']='2020-01-01T00:00:00Z'
    assert compare_claims(a,b)=='VERSION_CONFLICT'


@pytest.mark.parametrize('identity', ['product','package','ecosystem'])
def test_identity_difference_cannot_be_normalized_into_agreement(identity):
    a,b=claim('<4.2.1'),claim('<=4.2.0')
    a['value'][identity]='first';b['value'][identity]='different'
    assert compare_scopes(a,b).result=='NOT_COMPARABLE'


def test_unbound_source_is_not_a_valid_equivalence_proof():
    a,b=claim('<4.2.1'),claim('<=4.2.0')
    b['version_source_contexts'][0]['locator']={'json_pointer':'/unrelated'}
    assert compare_scopes(a,b).result=='INSUFFICIENT_CONTEXT'
    assert compare_claims(a,b)=='VERSION_CONFLICT'


def test_raw_expressions_and_source_identity_survive_normalization():
    a=claim('<=4.2.0');before=deepcopy(a);s=VersionScopeNormalizer().normalize(a['type'],a['value'],**a['version_source_contexts'][0])
    assert a==before and s.raw_expression=='<=4.2.0'
    assert s.evidence_id=='synthetic-evidence' and s.raw_document_id=='synthetic-raw'


def test_multiple_assets_keep_independent_membership_and_unknown():
    value=claim('<4.2.1')['value']
    results=[compare_version(v,value)['affected'] for v in ['4.2.0','4.2.1','unknown']]
    assert results==[True,False,None]
    assert intervals(value)!=intervals(claim('<=4.2.0')['value'])

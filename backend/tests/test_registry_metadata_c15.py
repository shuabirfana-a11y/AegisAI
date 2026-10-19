"""Synthetic registry metadata: distribution identity is not CVE affectedness."""
import pytest
from app.enrichment.acquisition import validate_enrichment_url
from app.enrichment.package_registry import registry_snapshot


def payload(name='sample-lib'):
    return {'info': {'name': name, 'version': '4.2.0',
        'project_urls': {'Repository': 'https://github.com/example/project'}},
        'releases': {'4.1.0': [{'filename': 'sample.whl',
            'upload_time_iso_8601': '2025-01-02T00:00:00Z', 'yanked': False}],
            '4.2.0': []}, 'vulnerabilities': []}


def test_metadata_keeps_explicit_project_identity_and_releases_without_impact():
    out = registry_snapshot(payload(), 'sample-lib')
    assert out['package'] == 'sample-lib' and out['ecosystem'] == 'PyPI'
    assert out['registry_version'] == '4.2.0'
    assert out['project_repository'] == 'example/project'
    assert out['release_versions'] == ['4.1.0', '4.2.0']
    assert out['scope'] == 'IDENTITY_AND_RELEASES_ONLY'
    assert not {'affected', 'range', 'fixed_version', 'version', 'status'} & out.keys()
    assert out['metadata_updated_at'] is None


def test_name_normalization_is_only_pep503_and_not_product_aliasing():
    assert registry_snapshot(payload('Sample_Lib'), 'sample-lib')['original_name'] == 'Sample_Lib'
    with pytest.raises(ValueError): registry_snapshot(payload('sample-product'), 'sample-lib')


@pytest.mark.parametrize('p', [{}, {'info': {}}, {'info': {'name': 'sample-lib'}},
    {'info': {'name': 'sample-lib', 'version': 'not-a-version'}, 'releases': {}},
    {'info': {'name': 'sample-lib', 'version': '4.2.0'}, 'releases': []}])
def test_incomplete_or_invalid_metadata_is_not_an_identity_witness(p):
    with pytest.raises(ValueError): registry_snapshot(p, 'sample-lib')


@pytest.mark.parametrize('url', [
    'http://pypi.org/pypi/torch/json',
    'https://pypi.org.evil.invalid/pypi/torch/json',
    'https://user:password@pypi.org/pypi/torch/json',
    'https://pypi.org:444/pypi/torch/json',
    'https://pypi.org/pypi/../json',
    'https://pypi.org/pypi/torch/../../json',
    'https://pypi.org/pypi/torch/json?redirect=http://127.0.0.1',
    'https://pypi.org/pypi/torch/json#fragment',
    'https://pypi.org/pypi/torch%2fother/json',
    'https://pypi.org/simple/torch/',
    'https://files.pythonhosted.org/packages/torch.whl',
])
def test_metadata_policy_does_not_authorize_arbitrary_urls_or_wheels(url):
    with pytest.raises(ValueError): validate_enrichment_url(url)


def test_only_exact_metadata_endpoint_is_allowed():
    validate_enrichment_url('https://pypi.org/pypi/sample-lib/json')


def test_repository_urls_are_descriptive_not_redirects_or_alias_proofs():
    p = payload(); p['info']['project_urls']['Repository'] = 'https://github.com.evil.invalid/example/project'
    assert registry_snapshot(p, 'sample-lib')['project_repository'] is None
    p['info']['project_urls'] = {'Homepage': 'https://example.invalid'}
    assert registry_snapshot(p, 'sample-lib')['project_repository'] is None


def test_empty_release_list_does_not_mean_not_affected_or_patch_applied():
    p = payload(); p['releases'] = {}
    out = registry_snapshot(p, 'sample-lib')
    assert out['release_versions'] == []
    assert not {'not_affected', 'patch_applied', 'fixed_versions'} & out.keys()

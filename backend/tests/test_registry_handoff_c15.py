"""Synthetic registry identity observations; no live sources or benchmark truth."""
import importlib
import json
from copy import deepcopy
from hashlib import sha256

import httpx
import pytest
from sqlalchemy import select

from app.db import models as m
from app.db.persistence import store_raw
from app.enrichment.enrichers.version import VersionEnricher
from app.utils.time import utcnow
from tests.test_phase7_enrichers import acquire, context


def metadata(name='vllm'):
    return {'info': {'name': name, 'version': '0.8.4',
                     'project_urls': {'Source': 'https://github.com/vllm-project/vllm'}},
            'releases': {'0.8.2': [], '0.8.4': []}}


def version_context(db, seed):
    """Use the existing real normalizer and relational test fixture."""
    from app.normalizers import osv
    now = utcnow()
    payload = {'id': 'GHSA-test-test-test', 'modified': now.isoformat(),
               'aliases': [seed.vuln.canonical_id], 'affected': [{
                   'package': {'ecosystem': 'PyPI', 'name': 'vllm'},
                   'ranges': [{'type': 'ECOSYSTEM',
                               'events': [{'introduced': '0'}, {'fixed': '0.8.4'}]}]}]}
    raw = store_raw(db, source_id=seed.sources[1].id, external_id=payload['id'],
                    source_url='https://example.invalid/SYNTHETIC-osv', retrieved_at=now,
                    content_type='application/json', raw_payload=json.dumps(payload).encode(),
                    publisher='SYNTHETIC')
    obs = m.SourceObservation(source_id=raw.source_id, raw_document_id=raw.id,
        external_id=payload['id'], record_type='vulnerability', retrieved_at=now,
        lineage_key='github:vllm-project/vllm', publisher='SYNTHETIC', parse_status='parsed',
        normalizer_version='SYNTHETIC',
        normalized_payload=osv.normalize(payload, raw.id, now).model_dump(mode='json'))
    db.add(obs)
    db.flush()
    ctx = context(db, seed)
    ctx.current_observation_ids = [obs.id]
    return ctx


def registry_rows(db):
    db.flush()
    return list(db.scalars(select(m.Evidence).join(m.Source).where(
        m.Source.source_key == 'PYPI_METADATA')))


def claim_snapshot(db, target):
    return {str(c.id): (c.claim_type, deepcopy(c.value_json), str(c.package_identifier_id))
            for c in db.scalars(select(m.Claim).where(m.Claim.vulnerability_id == target))}


def test_registry_contract_module_is_available():
    module = importlib.import_module('app.enrichment.package_registry')
    assert callable(module.registry_snapshot)
    assert callable(module.attach_registry_metadata)


def test_registry_enrichment_is_opt_in(db, seed, monkeypatch):
    monkeypatch.delenv('AEGIS_PYPI_METADATA_ENABLED', raising=False)
    def handler(request):
        raise AssertionError('Disabled registry metadata must not acquire remote data')
    out = VersionEnricher().investigate(version_context(db, seed), db, acquire(db, handler))
    assert out.claims
    assert not registry_rows(db)


def test_version_enricher_persists_original_registry_witnesses_without_new_claims(db, seed, monkeypatch):
    ctx = version_context(db, seed)
    monkeypatch.delenv('AEGIS_PYPI_METADATA_ENABLED', raising=False)
    VersionEnricher().investigate(ctx, db, acquire(db, lambda req: pytest.fail('Unexpected HTTP')))
    before = claim_snapshot(db, ctx.target_id)
    payload = metadata()
    original = deepcopy(payload)
    requests = []
    def handler(request):
        requests.append(str(request.url))
        assert request.url.host == 'pypi.org' and request.url.path == '/pypi/vllm/json'
        assert 'authorization' not in request.headers
        return httpx.Response(200, json=payload)
    monkeypatch.setenv('AEGIS_PYPI_METADATA_ENABLED', '1')
    out = VersionEnricher().investigate(ctx, db, acquire(db, handler))
    rows = registry_rows(db)
    assert len(requests) == 1 and rows
    assert claim_snapshot(db, ctx.target_id) == before
    assert payload == original
    assert any(x['source'] == 'PYPI_METADATA' for x in out.checked)
    local_raw_id = db.get(m.SourceObservation, ctx.current_observation_ids[0]).raw_document_id
    assert any(x.get('raw_document_id') == str(local_raw_id) for x in out.checked)
    for evidence in rows:
        claim = db.get(m.Claim, evidence.claim_id)
        raw = db.get(m.RawDocument, evidence.raw_document_id)
        obs = db.get(m.SourceObservation, evidence.observation_id)
        assert claim.claim_type in {'AFFECTS_PRODUCT', 'AFFECTS_VERSION', 'FIXED_VERSION'}
        assert claim.package_identifier_id == seed.packages[0].id
        assert evidence.stance == 'neutral' and evidence.details['explicit'] is False
        assert evidence.details['registry_scope'] == 'IDENTITY_AND_RELEASES_ONLY'
        assert evidence.observed_value['ecosystem'] == 'PyPI'
        assert evidence.observed_value['package'] == 'vllm'
        snapshot = evidence.details['metadata']
        assert snapshot['registry_version'] == '0.8.4'
        assert set(snapshot['release_versions']) == {'0.8.2', '0.8.4'}
        assert snapshot['project_repository'] == 'vllm-project/vllm'
        if evidence.locator['json_pointer'] == '/info':
            assert evidence.observed_value['original_name'] == 'vllm'
            assert evidence.observed_value['project_repository'] == 'vllm-project/vllm'
        else:
            assert evidence.locator['json_pointer'] == '/releases'
            assert set(evidence.observed_value['release_versions']) == {'0.8.2', '0.8.4'}
        assert not {'range', 'ranges', 'events', 'version', 'known_exploited'} & evidence.observed_value.keys()
        assert json.loads(raw.raw_payload) == original
        assert sha256(raw.raw_payload).hexdigest() == raw.content_hash
        assert obs.raw_document_id == raw.id and obs.source_id == evidence.source_id
        assert raw.source_url == 'https://pypi.org/pypi/vllm/json'


@pytest.mark.parametrize('case', ['wrong-package', 'malformed', 'http-failure', 'redirect'])
def test_invalid_registry_response_does_not_create_identity_evidence(db, seed, monkeypatch, case):
    monkeypatch.setenv('AEGIS_PYPI_METADATA_ENABLED', '1')
    requests = []
    def handler(request):
        requests.append(str(request.url))
        assert request.url.host == 'pypi.org'
        if case == 'wrong-package':
            return httpx.Response(200, json=metadata('different-distribution'))
        if case == 'malformed':
            return httpx.Response(200, content=b'not structured JSON')
        if case == 'redirect':
            return httpx.Response(302, headers={'Location': 'https://unrelated.invalid/metadata'})
        return httpx.Response(503, json={'error': 'SYNTHETIC unavailable'})
    out = VersionEnricher().investigate(version_context(db, seed), db, acquire(db, handler))
    assert out.claims
    assert not registry_rows(db)
    assert out.errors or out.unresolved or out.warnings
    assert len(requests) == 1


def test_registry_metadata_cannot_upgrade_existing_impact_verification(db, seed, monkeypatch):
    from app.enrichment.verification import VerificationService
    ctx = version_context(db, seed)
    monkeypatch.delenv('AEGIS_PYPI_METADATA_ENABLED', raising=False)
    baseline = VersionEnricher().investigate(ctx, db, acquire(db, lambda req: pytest.fail('Unexpected HTTP')))
    claims = [db.get(m.Claim, identifier) for identifier in baseline.claims]
    before = {c.id: VerificationService.verify(db, c).status for c in claims}
    assert all(status != 'confirmed' for status in before.values())
    payload = metadata()
    payload['vulnerabilities'] = [{'id': 'GHSA-test-test-test',
        'aliases': [ctx.canonical_id], 'fixed_in': ['0.8.4'], 'details': 'SYNTHETIC authoritative-looking text'}]
    monkeypatch.setenv('AEGIS_PYPI_METADATA_ENABLED', '1')
    VersionEnricher().investigate(ctx, db, acquire(db, lambda req: httpx.Response(200, json=payload)))
    assert registry_rows(db)
    for claim in claims:
        result = VerificationService.verify(db, claim)
        assert result.status == before[claim.id]
        neutral_ids = {str(e.id) for e in registry_rows(db) if e.claim_id == claim.id}
        assert not neutral_ids.intersection(result.details['supporting_evidence'])


def test_registry_has_no_reason_to_fetch_without_current_package_claims(db, seed, monkeypatch):
    monkeypatch.setenv('AEGIS_PYPI_METADATA_ENABLED', '1')
    ctx = context(db, seed)
    ctx.current_observation_ids = []
    def handler(request):
        raise AssertionError('No current output claim exists to bind registry metadata')
    result = VersionEnricher().investigate(ctx, db, acquire(db, handler))
    assert not result.claims and not registry_rows(db)


def test_registry_identity_does_not_rewrite_related_vendor_distribution(db, seed, monkeypatch):
    from app.enrichment.enrichers.vendor import VendorEnricher
    ctx = context(db, seed)
    ctx.packages = [{'name': 'torch', 'ecosystem': 'PyPI',
        'product_id': seed.products[1].id, 'package_id': seed.packages[1].id,
        'repository': 'pytorch/pytorch'}]
    payload = {'ghsa_id': ctx.aliases[0], 'cve_id': ctx.canonical_id, 'state': 'published',
        'vulnerabilities': [{'package': {'ecosystem': 'pip', 'name': 'pytorch'},
            'vulnerable_version_range': '< 9.0', 'patched_versions': '9.0'}]}
    monkeypatch.setenv('AEGIS_PYPI_METADATA_ENABLED', '1')
    before = claim_snapshot(db, ctx.target_id)
    out = VendorEnricher().investigate(ctx, db, acquire(db, lambda req: httpx.Response(200, json=payload)))
    added = {identifier: data for identifier, data in claim_snapshot(db, ctx.target_id).items()
             if identifier not in before}
    assert all(data[0] not in {'AFFECTS_PRODUCT', 'AFFECTS_VERSION', 'FIXED_VERSION'} for data in added.values())
    assert any(row['status'] == 'RELATED_PACKAGE' for row in out.artifacts['package_identity'])
    assert ctx.resolve_package('pytorch', 'PyPI', repository='pytorch/pytorch')['package'] is None


def test_real_tool_refs_and_verification_snapshot_retain_neutral_registry_observation(db, seed, monkeypatch):
    from app.agents.verification.snapshot import _claim, _evidence
    from app.enrichment import queries
    from app.tooling.adapters import execute_local
    monkeypatch.setenv('AEGIS_PYPI_METADATA_ENABLED', '1')
    ctx = version_context(db, seed)
    VersionEnricher().investigate(ctx, db, acquire(db, lambda req: httpx.Response(200, json=metadata())))
    stored_rows = registry_rows(db)
    assert stored_rows
    response = execute_local(db, 'get_vulnerability', {'target': ctx.canonical_id}, 'test-analyst')
    refs = {ref['evidence_id']: ref for ref in response['evidence_refs'] if ref.get('evidence_id')}
    serialized = {str(row['id']): row for row in response['data']['intelligence']['evidence']}
    for stored in stored_rows:
        ref = refs[str(stored.id)]
        assert ref['stance'] == 'neutral' and ref['verified'] is False and ref['is_current'] is True
        claim = db.get(m.Claim, stored.claim_id)
        canonical = _claim(queries.serialize(claim), 'SYNTHETIC-lookup', str(ctx.target_id))
        assert canonical is not None
        ref = {**ref, 'source_key': serialized[str(stored.id)]['source_key']}
        evidence = _evidence(db, stored, canonical, ref, utcnow())
        assert evidence.integrity_status == 'VALID'
        assert evidence.stance == 'neutral' and evidence.directness == 'mention'
        assert evidence.raw_document_id == stored.raw_document_id
        assert evidence.observation_id == stored.observation_id
        assert evidence.details['registry_scope'] == 'IDENTITY_AND_RELEASES_ONLY'
        assert 'normalized_version_scope' not in evidence.details


@pytest.mark.parametrize('changing_metadata', [False, True], ids=['identical-bytes', 'changed-bytes'])
def test_registry_refreshes_preserve_impact_support_and_historical_observations(db, seed, monkeypatch, changing_metadata):
    from app.tooling.adapters import execute_local
    ctx = version_context(db, seed)
    monkeypatch.delenv('AEGIS_PYPI_METADATA_ENABLED', raising=False)
    baseline = VersionEnricher().investigate(ctx, db, acquire(db, lambda req: pytest.fail('Unexpected HTTP')))
    claim_ids = {str(identifier) for identifier in baseline.claims}
    before = execute_local(db, 'get_vulnerability', {'target': ctx.canonical_id}, 'test-analyst')
    impact_support = {ref['evidence_id'] for ref in before['evidence_refs']
                      if ref.get('claim_id') in claim_ids and ref.get('stance') == 'support'}
    assert len(impact_support) == 3
    monkeypatch.setenv('AEGIS_PYPI_METADATA_ENABLED', '1')
    for iteration in range(17):
        payload = metadata()
        if changing_metadata:
            payload['info']['version'] = '0.8.4.post' + str(iteration)
            payload['releases'][payload['info']['version']] = []
        VersionEnricher().investigate(ctx, db, acquire(db, lambda req: httpx.Response(200, json=payload)))
    history = registry_rows(db)
    assert len(history) == 102
    assert len({row.raw_document_id for row in history}) == (17 if changing_metadata else 1)
    assert len({row.observation_id for row in history}) == 17
    response = execute_local(db, 'get_vulnerability', {'target': ctx.canonical_id}, 'test-analyst')
    refs = {ref['evidence_id']: ref for ref in response['evidence_refs'] if ref.get('evidence_id')}
    assert impact_support <= refs.keys(), 'Registry history must not evict current impact support at the Tool limit'
    newest = db.scalar(select(m.SourceObservation).where(
        m.SourceObservation.id.in_([row.observation_id for row in history])).order_by(
            m.SourceObservation.retrieved_at.desc(), m.SourceObservation.created_at.desc(),
            m.SourceObservation.id.desc()).limit(1))
    current_neutral_ids = {str(row.id) for row in history if row.observation_id == newest.id}
    assert len(current_neutral_ids) == 6
    assert {str(row.id) for row in history} & refs.keys() == current_neutral_ids
    assert all(refs[identifier]['stance'] == 'neutral' and refs[identifier]['is_current'] is True
               for identifier in current_neutral_ids)
    current_context = [row for row in response['data']['intelligence']['evidence']
                        if row['source_key'] == 'PYPI_METADATA']
    assert len(current_context) == 6, 'Obsolete registry metadata must not inflate bounded Tool payloads'
    from app.enrichment import queries
    assert queries.page(db, ctx.target_id, 'evidence', limit=1)['total'] >= 105
    assert len(registry_rows(db)) == 102  # Full immutable history remains queryable outside Tool context.

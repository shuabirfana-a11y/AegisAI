"""Synthetic stored witnesses crossing the real read-only Tool adapter."""
from copy import deepcopy
from datetime import timedelta
import pytest
from app.enrichment.evidence import EvidenceService
from app.tooling.adapters import evidence_refs
from app.tooling.investigation import decorate_evidence
from tests.test_version_scope_storage_c2 import material, observation

def refs_for(db,seed,*,time_case=None):
    now,v,document,claims=material(db,seed)
    when=now-timedelta(days=31) if time_case=='stale' else now-timedelta(days=1) if time_case=='after_retrieval' else now
    published=now+timedelta(days=1) if time_case=='future' else now if time_case=='after_retrieval' else when
    raw,obs=observation(db,seed.sources[0],document,when,published=published)
    for i,c in enumerate(claims):
        EvidenceService.add(db,c,obs,c.value_json,{'json_pointer':f'/vulnerabilities/{i}/first_patched_version'})
    refs=evidence_refs(db,v.id)
    return raw,claims,refs

def test_real_read_adapter_exports_bound_scope_without_changing_verification(db,seed):
    raw,claims,refs=refs_for(db,seed)
    before=[r['verified'] for r in refs]
    decorated=decorate_evidence(db,refs)
    assert [r['verified'] for r in decorated]==before
    assert len(decorated)==2
    for ref in decorated:
        scope=ref['normalized_version_scope']
        assert scope['evidence_id']==ref['evidence_id']
        assert scope['raw_document_id']==str(raw.id)
        assert scope['raw_hash']==ref['hash']==raw.content_hash
        assert scope['coverage']=='SOURCE_ENTRY'

@pytest.mark.parametrize('time_case',['stale','future','after_retrieval'])
def test_invalid_time_cannot_supply_comparability_proof(db,seed,time_case):
    _,_,refs=refs_for(db,seed,time_case=time_case)
    assert all('normalized_version_scope' not in ref for ref in decorate_evidence(db,refs))

def test_corrupted_raw_and_injected_metadata_cannot_supply_scope(db,seed):
    from sqlalchemy.orm.attributes import set_committed_value
    raw,_,refs=refs_for(db,seed)
    # Simulate corrupt materialized input; immutable database history stays untouched.
    set_committed_value(raw,'raw_payload',b'{"invalid":"SYNTHETIC changed bytes"}')
    for ref in refs:ref['normalized_version_scope']={'injected':True}
    assert all('normalized_version_scope' not in ref for ref in decorate_evidence(db,refs))

def test_wrong_claim_revision_cannot_supply_scope(db,seed):
    _,_,refs=refs_for(db,seed)
    for ref in refs:ref['claim_revision']-=1
    assert all('normalized_version_scope' not in ref for ref in decorate_evidence(db,refs))

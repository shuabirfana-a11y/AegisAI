"""Conflict source records are immutable observations, never trust verdicts."""
import pytest
from tests.agents.verification.helpers import context,claim,evidence


def test_conflict_artifact_links_exact_sources_and_stable_parent():
    from app.agents.verification.conflict_evidence import conflict_artifacts
    c=context(claims=[claim(),claim('C2',expression='<0.7')],evidence_items=[evidence(),evidence('E2','C2','<0.7')])
    original={'artifact_id':str(c.snapshot.source_artifact_id),'run_id':str(c.snapshot.source_run_id),'task_id':'lookup',
        'conflicts':[{'claim_a_id':'C1','claim_b_id':'C2','conflict_type':'VERSION_CONFLICT','scope_key':'PyPI:vllm'}]}
    arts=conflict_artifacts(original,c.snapshot.evidence)
    assert len(arts)==1 and arts[0].type=='CONFLICT_EVIDENCE'
    assert {s.evidence_id for s in arts[0].sources}=={'E1','E2'}
    assert arts[0].source_artifact.artifact_id==c.snapshot.source_artifact_id
    assert arts[0].information_status=='CANDIDATE'
    assert conflict_artifacts(original,c.snapshot.evidence)==arts
    with pytest.raises(ValueError):arts[0].conflict_reason='silently replaced'


def test_conflict_without_source_does_not_invent_evidence():
    from app.agents.verification.conflict_evidence import conflict_artifacts
    c=context();original={'artifact_id':str(c.snapshot.source_artifact_id),'run_id':str(c.snapshot.source_run_id),
        'task_id':'lookup','conflicts':[{'claim_a_id':'missing-a','claim_b_id':'missing-b','conflict_type':'VERSION_CONFLICT'}]}
    art=conflict_artifacts(original,c.snapshot.evidence)[0]
    assert art.sources==() and art.unresolved_items


def test_source_snapshot_rejects_changed_conflict_reference():
    from app.agents.verification.conflict_evidence import conflict_artifacts
    from app.agents.verification.schemas import VerificationSourceSnapshot
    c=context();raw=c.snapshot.model_dump(mode='python')
    raw['artifact'].update(artifact_id=str(c.snapshot.source_artifact_id),run_id=str(c.snapshot.source_run_id),task_id='lookup',
        conflicts=[{'claim_a_id':'C1','conflict_type':'VERSION_CONFLICT'}])
    raw['conflict_evidence_artifacts']=conflict_artifacts(raw['artifact'],c.snapshot.evidence)
    saved=VerificationSourceSnapshot.model_validate(raw)
    assert saved.conflict_evidence_artifacts
    raw['conflict_evidence_artifacts']=(saved.conflict_evidence_artifacts[0].model_copy(update={'conflict_reason':'invented'}),)
    with pytest.raises(ValueError):VerificationSourceSnapshot.model_validate(raw)


def snapshot_with_conflict(conflict):
    from app.agents.verification.conflict_evidence import conflict_artifacts
    from app.agents.verification.schemas import VerificationSourceSnapshot
    c=context();raw=c.snapshot.model_dump(mode='python')
    raw['artifact'].update(artifact_id=str(c.snapshot.source_artifact_id),run_id=str(c.snapshot.source_run_id),
        task_id='lookup',conflicts=[conflict])
    raw['conflict_evidence_artifacts']=conflict_artifacts(raw['artifact'],c.snapshot.evidence)
    return VerificationSourceSnapshot.model_validate(raw)


def test_conflict_snapshot_survives_jsonb_key_reordering():
    import json
    from app.agents.verification.schemas import VerificationSourceSnapshot
    saved=snapshot_with_conflict({'claim_a_id':'C1','conflict_type':'VERSION_CONFLICT','details':{'z':1,'a':2}})
    reloaded=VerificationSourceSnapshot.model_validate_json(json.dumps(saved.model_dump(mode='json'),sort_keys=True))
    assert reloaded.conflict_evidence_artifacts==saved.conflict_evidence_artifacts


def test_large_legal_conflict_uses_reference_without_copying_payload():
    from app.agents.contracts import fingerprint
    conflict={'claim_a_id':'C1','conflict_type':'VERSION_CONFLICT','details':{'source_excerpt':'x'*70000}}
    saved=snapshot_with_conflict(conflict)
    derived=saved.conflict_evidence_artifacts[0]
    assert derived.conflict_sha256==fingerprint(conflict)
    assert derived.conflict_index==0
    assert len(derived.model_dump_json())<2000


def test_many_conflicts_do_not_duplicate_large_evidence_references():
    from itertools import combinations
    from app.agents.verification.conflict_evidence import conflict_artifacts
    from app.agents.verification.schemas import VerificationSourceSnapshot
    claims=[claim(f'C{i}') for i in range(8)]
    refs=[evidence(f'E{i}-{j}',f'C{i}',reference={'url':'https://example.invalid/SYNTHETIC',
        'locator':{'excerpt':'x'*2200}}) for i in range(8) for j in range(16)]
    c=context(claims=claims,evidence_items=refs);raw=c.snapshot.model_dump(mode='python')
    raw['artifact'].update(artifact_id=str(c.snapshot.source_artifact_id),run_id=str(c.snapshot.source_run_id),
        task_id='lookup',conflicts=[{'claim_a_id':a.claim_id,'claim_b_id':b.claim_id,
            'conflict_type':'VERSION_CONFLICT'} for a,b in combinations(claims,2)])
    raw['conflict_evidence_artifacts']=conflict_artifacts(raw['artifact'],c.snapshot.evidence)
    saved=VerificationSourceSnapshot.model_validate(raw)
    assert len(saved.conflict_evidence_artifacts)==28
    assert len(saved.evidence)==128 and len(saved.model_dump_json())<1000000

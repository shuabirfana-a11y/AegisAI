from types import SimpleNamespace
import importlib
import pytest


def test_invalid_evidence_cannot_inherit_confirmed_claim_status():
    from app.agents.asset_observations import ImpactVersionEvidence
    module=importlib.import_module('app.agents.verification.asset_snapshot')
    bind=getattr(module,'bind_impact_verdicts',None)
    assert callable(bind),'Missing evidence-specific verdict binding'
    ref=ImpactVersionEvidence(id='excluded',vulnerability_id='v',claim_id='claim',source='official',reference={})
    checked=SimpleNamespace(claim=SimpleNamespace(claim_id='claim'),status='CONFIRMED',
        supporting_evidence_ids=('valid-other-evidence',),conflicting_evidence_ids=())
    assert bind((ref,),(checked,))[0].status=='INSUFFICIENT_EVIDENCE'


def test_verification_output_cannot_change_sealed_observation():
    module=importlib.import_module('app.agents.verification.asset_snapshot')
    check=getattr(module,'validate_observation_handoff',None)
    assert callable(check),'Missing observation handoff verification'
    original=SimpleNamespace(version_observations=('source-version',),impact_version_evidence=())
    output=SimpleNamespace(version_observations=('invented-version',),impact_version_evidence=(),partial_result=False,claims=())
    with pytest.raises(ValueError):check(output,original)


def test_complete_output_must_include_original_observation():
    module=importlib.import_module('app.agents.verification.asset_snapshot')
    check=getattr(module,'validate_observation_handoff',None)
    assert callable(check),'Missing observation handoff verification'
    original=SimpleNamespace(version_observations=('source-version',),impact_version_evidence=())
    output=SimpleNamespace(version_observations=(),impact_version_evidence=(),partial_result=False,claims=())
    with pytest.raises(ValueError):check(output,original)

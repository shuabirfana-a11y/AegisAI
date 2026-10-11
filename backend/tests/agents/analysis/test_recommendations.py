"""Breaks caught: invented fixes, cross-branch applicability and availability-as-mitigation."""
from tests.agents.analysis.helpers import context,verified,module
from tests.agents.analysis.test_rules import severity


def actions(value):
    r=module('rules').assess_risk(value)
    return module('recommendations').build_actions(value,asset_match=r.asset_match_result,
        version_match=r.version_match_result,risk_level=r.risk_level,priority=r.priority)


def test_confirmed_fix_action_references_exact_claim():
    fix=verified('FIXED_VERSION','fix',{'version':'0.7.0','ecosystem':'PyPI','package':'vllm'})
    result=actions(context([verified(),severity(),fix]))
    upgrade=next(a for a in result if a.action_type=='UPGRADE_VERIFIED_RELEASE')
    assert upgrade.fixed_version=='0.7.0' and upgrade.claim_ids==('fix',)
    assert upgrade.evidence_ids==('E-fix',) and upgrade.applicability=='CONFIRMED'
    assert upgrade.category=='IMMEDIATE'


def test_candidate_fix_or_wrong_branch_no_exact_upgrade():
    for change in ({'status':'PENDING'},{'branch':'other'}):
        fix=verified('FIXED_VERSION','fix',{'version':'9.9.9','ecosystem':'PyPI','package':'vllm'},**change)
        assert not any(a.fixed_version for a in actions(context([verified(),severity(),fix])))


def test_fixed_release_still_in_affected_range_rejected():
    fix=verified('FIXED_VERSION','fix',{'version':'0.6.5','ecosystem':'PyPI','package':'vllm'})
    assert not any(a.fixed_version for a in actions(context([verified(),severity(),fix])))


def test_unknown_patch_applicability_only_inspects_reference():
    patch=verified('PATCH_EXISTS','patch',{'url':'https://github.com/vendor/project/commit/'+'a'*40},package=None)
    result=actions(context([verified(),severity(),patch]))
    inspect=next(a for a in result if a.action_type=='INSPECT_PATCH_REFERENCE')
    assert inspect.applicability=='UNKNOWN' and inspect.patch_reference==patch.claim.value['url']
    assert not any(a.action_type=='APPLY_VERIFIED_PATCH' for a in result)


def test_patch_availability_does_not_lower_risk_or_imply_deployed():
    base=context([verified(),severity()])
    fixed=context([verified(),severity(),verified('FIXED_VERSION','fix',{'version':'0.7.0','ecosystem':'PyPI','package':'vllm'})])
    r=module('rules').assess_risk(fixed)
    assert (r.risk_level,r.priority)==('HIGH','P1')
    assert r.patch_availability.applied=='UNKNOWN' and not r.mitigating_factors


def test_missing_fix_keeps_absence_unknown_and_requires_followup():
    result=actions(context([verified(),severity()],patch_candidates=[{'release_version':'9.9.9','status':'CONFIRMED'}]))
    assert not any(a.fixed_version for a in result)
    assert any(a.action_type=='TRACK_REMEDIATION' for a in result)
    assert all(a.action_provenance=='GENERAL_PRECAUTION' for a in result)


def test_unknown_returns_review_directions_without_mutation():
    result=actions(context(verification_status='CONFLICT'))
    assert any(a.action_type=='REQUEST_REVIEW' for a in result)
    assert all(a.category in ('FURTHER_INVESTIGATION','LONG_TERM_HARDENING') for a in result)

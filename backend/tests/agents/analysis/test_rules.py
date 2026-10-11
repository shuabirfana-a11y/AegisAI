"""Breaks caught: bypassing verification, candidate promotion and score-only risk."""
import pytest
from tests.agents.analysis.helpers import context,verified,module


def assess(value):return module('rules').assess_risk(value)


def kev():return verified('KNOWN_EXPLOITED','kev',{'known_exploited':True},package=None)
def severity(band='critical'):
    score={'critical':9.8,'high':8.1,'medium':6.5,'low':2.0,'info':0.0}[band]
    return verified('CVSS_SCORE','severity',{'score':score,'version':'3.1','severity':band},package=None)


@pytest.mark.parametrize('exposure,level,priority',[('internet','CRITICAL','P0'),('internal','HIGH','P0'),('unknown','HIGH','P0')])
def test_confirmed_kev_priorities_and_risk_are_independent(exposure,level,priority):
    result=assess(context([verified(),kev(),severity()],exposure=exposure))
    assert result.risk_level==level and result.priority==priority and result.affected is True
    assert result.exploitation_signal.status=='KNOWN_EXPLOITED'
    assert result.exploitation_signal.usability=='NOT_EVALUATED'


def test_critical_cvss_without_exploit_is_high_p1():
    result=assess(context([verified(),severity()]))
    assert result.risk_level=='HIGH' and result.priority=='P1'
    assert result.exploitation_signal.status=='UNKNOWN'


@pytest.mark.parametrize('state',['PENDING','CONFLICT','INSUFFICIENT_EVIDENCE','REJECTED'])
def test_nonconfirmed_verification_never_definite(state):
    result=assess(context([verified(),kev(),severity()],verification_status=state))
    assert result.risk_level=='UNKNOWN' and result.priority=='REVIEW_REQUIRED'
    assert result.affected is None and result.verification_status==state
    assert result.exploitation_signal.status=='KNOWN_EXPLOITED'  # Warning signal retained, verdict withheld.


@pytest.mark.parametrize('change',[{'partial':True},{'coverage':False},{'asset_status':'MISSING'},
    {'asset_status':'AMBIGUOUS'},{'execution_status':'FAILED'},{'verification_task':'conflict_detection'}])
def test_incomplete_or_failed_input_abstains(change):
    result=assess(context([verified(),kev()],**change))
    assert result.risk_level=='UNKNOWN' and result.priority=='REVIEW_REQUIRED' and result.affected is None


def test_selected_claim_cannot_hide_omitted_impact():
    first=verified();counter=verified(identifier='counter',value={'ecosystem':'PyPI','package':'vllm','range':'<0.8'})
    result=assess(context([first,kev()],source_claims=[first.claim,counter.claim]))
    assert result.affected is None and result.risk_level=='UNKNOWN'
    assert any('UNCHECKED' in x for x in result.unresolved_items)


def test_static_poc_candidate_never_verified_exploit():
    result=assess(context([verified(),severity('medium')],candidates=[{'url':'https://example.invalid/SYNTHETIC','status':'CONFIRMED'}]))
    assert result.risk_level=='MEDIUM' and result.priority=='P3'
    assert result.exploitation_signal.status=='POC_CANDIDATE'
    assert not next(f for f in result.risk_factors if f.code=='POC_CANDIDATE').influences_decision


def test_confirmed_static_association_keeps_usability_not_evaluated():
    poc=verified('POC_ASSOCIATION','poc',{'url':'https://example.invalid/SYNTHETIC'},package=None)
    result=assess(context([verified(),poc]))
    assert result.risk_level=='HIGH' and result.priority=='P2'
    assert result.exploitation_signal.status=='VERIFIED_POC_ASSOCIATION'
    assert result.exploitation_signal.usability=='NOT_EVALUATED'


def test_epss_only_remains_source_asserted():
    value=context([verified(),severity('medium')],epss=[{'score':0.99,'score_date':'2099-01-01','raw_document_id':'SYNTHETIC'}])
    result=assess(value)
    assert result.risk_level=='MEDIUM' and result.priority=='P3'
    assert result.exploitation_signal.epss[0]['status']=='STALE_OR_INVALID'
    assert all(not f.influences_decision for f in result.risk_factors if f.code=='EPSS_SOURCE_ASSERTION')


def test_unknown_cvss_preserves_impact_but_requires_review():
    result=assess(context([verified()]))
    assert result.affected is True and result.version_match_status=='AFFECTED'
    assert result.risk_level=='UNKNOWN' and result.priority=='REVIEW_REQUIRED'


def test_rejected_impact_is_not_a_safety_proof():
    result=assess(context([verified(status='REJECTED')]))
    assert result.affected is None and result.risk_level=='UNKNOWN'


def test_unknown_gate_invariant_exhaustive_matrix():
    for state in ('PENDING','CONFLICT','INSUFFICIENT_EVIDENCE','REJECTED'):
        for version in ('0.5.0','0.7.0',None,'custom','99.0'):
            for exposure in ('internet','internal','unknown'):
                result=assess(context([verified(),kev(),severity()],verification_status=state,version=version,exposure=exposure))
                assert result.affected is None and (result.risk_level,result.priority)==('UNKNOWN','REVIEW_REQUIRED')

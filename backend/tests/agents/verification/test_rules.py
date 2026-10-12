"""Breaks caught: source-only confirmation, hidden contradictions and false independence."""
import importlib
from datetime import timedelta
import pytest
from app.utils.time import utcnow
from tests.agents.verification.helpers import claim,evidence,context


def evaluate(value,**kwargs):
    try:mod=importlib.import_module('app.agents.verification.rules')
    except ModuleNotFoundError:pytest.fail('Snapshot verification rules are missing')
    return mod.evaluate_snapshot(value,**kwargs)


def test_explicit_official_affected_range_is_confirmed():
    got=evaluate(context())
    assert got.verification_status=='CONFIRMED'
    assert got.claims[0].status=='CONFIRMED' and got.confidence==0.95
    assert got.claims[0].supporting_evidence_ids==('E1',)


def test_weak_blog_has_lower_confidence_and_cannot_confirm():
    official=evaluate(context())
    weak=evaluate(context(evidence_items=[evidence(source_type='blog',authority_level='community',
        evidence_type='source_excerpt',directness='mention',details={'explicit':False})]))
    assert weak.confidence<official.confidence
    assert weak.verification_status!='CONFIRMED'
    assert weak.claims[0].confidence<=0.05


@pytest.mark.parametrize('separate_claim',[False,True])
def test_conflicting_current_version_ranges_are_not_hidden_by_authority(separate_claim):
    claims=[claim()]
    second_id='C2' if separate_claim else 'C1'
    if separate_claim:claims.append(claim('C2','<=0.7',evidence_ids=('E2',)))
    got=evaluate(context(claims,evidence_items=[evidence(),evidence('E2',second_id,'<=0.7',
        authority_level='community',lineage_key='blog-two',evidence_type='source_excerpt')]))
    assert got.verification_status=='CONFLICT'
    assert got.confidence<=0.49
    assert got.conflicts[0].conflict_type=='VERSION_CONFLICT'
    assert {e.evidence_id for e in got.conflicting_evidence}=={'E1','E2'}


def test_no_evidence_requires_abstention_and_zero_score():
    got=evaluate(context(evidence_items=[]))
    assert got.verification_status=='INSUFFICIENT_EVIDENCE' and got.confidence==0


@pytest.mark.parametrize('change',[{'integrity_status':'INVALID'}, {'is_current':False},
    {'retrieved_at':lambda: utcnow()-timedelta(days=31)}, {'retrieved_at':lambda: utcnow()+timedelta(minutes=8)},
    {'published_at':lambda: utcnow()+timedelta(days=1)}, {'hash':None}, {'scope_key':'other-package'},
    {'vulnerability_id':'CVE-2099-0000'}, {'observed_value':{'ecosystem':'PyPI','package':'other','raw_expression':'<=0.6'}}])
def test_invalid_old_future_or_unrelated_evidence_never_confirms(change):
    change={key:value() if callable(value) else value for key,value in change.items()}
    got=evaluate(context(evidence_items=[evidence(**change)]))
    assert got.verification_status=='INSUFFICIENT_EVIDENCE'
    assert got.confidence==0


def test_correlated_mirrors_do_not_count_as_independent_confirmations():
    evs=[evidence(evidence_type='structured_source',authority_level='authoritative',lineage_key='github:vendor/repo'),
         evidence('E2',evidence_type='structured_source',authority_level='authoritative',lineage_key='github:vendor/repo')]
    got=evaluate(context(evidence_items=evs))
    assert got.verification_status!='CONFIRMED'
    independent=evaluate(context(evidence_items=[evs[0],evs[1].model_copy(update={'lineage_key':'vendor-independent'})]))
    assert independent.verification_status=='CONFIRMED'


def test_equivalent_ranges_historical_and_cross_scope_do_not_conflict():
    a=claim(expression='<=0.6');b=claim('C2','<=0.6.0',evidence_ids=('E2',))
    got=evaluate(context([a,b],[evidence(),evidence('E2','C2','<=0.6.0',lineage_key='other')]))
    assert not got.conflicts and got.verification_status=='CONFIRMED'
    b=b.model_copy(update={'value':{'raw_expression':'<=0.7','ecosystem':'PyPI','package':'other'},'scope_key':'PyPI:other','package_identifier_id':'other'})
    got=evaluate(context([a,b],[evidence(),evidence('E2','C2','<=0.7',scope_key='PyPI:other',
        observed_value=b.value,lineage_key='other')]))
    assert not got.conflicts


def test_selected_claim_cannot_omit_current_counterevidence():
    got=evaluate(context([claim(),claim('C2','<=0.7',evidence_ids=('E2',))],
        [evidence(),evidence('E2','C2','<=0.7',lineage_key='other')]),claim_ids=('C1',))
    assert len(got.claims)==1 and got.claims[0].status=='CONFLICT'


def test_explicit_rejection_and_absent_kev_are_different():
    c=claim(claim_type='POC_ASSOCIATION',value={'url':'https://example.invalid/list'})
    ev=evidence(observed_value=c.value,details={'classification':'REJECTED','explicit':True})
    got=evaluate(context([c],[ev]))
    assert got.verification_status=='REJECTED' and got.confidence==0
    kev=claim(claim_type='KNOWN_EXPLOITED',value={'known_exploited':False})
    got=evaluate(context([kev],[evidence(observed_value=kev.value,evidence_type='kev_record')]))
    assert got.verification_status!='CONFIRMED'


def test_poc_static_confirmation_never_asserts_runtime_usability():
    c=claim(claim_type='POC_ASSOCIATION',value={'url':'https://example.invalid/poc'})
    ev=evidence(observed_value=c.value,evidence_type='repository_readme',details={'classification':'CONFIRMED','explicit':True})
    got=evaluate(context([c],[ev,evidence('E2',observed_value=c.value,lineage_key='independent',details={'classification':'CONFIRMED','explicit':True})]))
    assert got.verification_status=='CONFIRMED'
    assert any('NOT_EXECUTED' in w for w in got.warnings)


def test_conflict_only_task_cannot_certify_unchecked_claims():
    got=evaluate(context(task_type='conflict_detection'))
    assert got.verification_status=='PENDING'
    assert got.claims[0].status=='PENDING'

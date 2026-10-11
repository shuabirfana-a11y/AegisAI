"""Independent final-review findings; each failed before its Phase 11-B3 fix."""
import hashlib
from uuid import uuid4
from types import SimpleNamespace
import pytest
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import fingerprint
from tests.agents.analysis.helpers import context,verified,module,request
from tests.agents.analysis.test_rules import kev


def test_source_only_cvss_band_cannot_promote_confirmed_score():
    ctx=context([verified(),verified('CVSS_SCORE','score',{'score':9.8,'version':'3.1'},package=None)])
    original=ctx.inputs.investigation.model_copy(update={'cvss':[{'base_score':9.8,'version':'3.1','severity':'critical'}]})
    got=module('rules').assess_risk(ctx.model_copy(update={'inputs':ctx.inputs.model_copy(update={'investigation':original})}))
    assert got.risk_level=='UNKNOWN' and got.priority=='REVIEW_REQUIRED' and got.affected is True


@pytest.mark.parametrize('value',[{'score':999,'severity':'critical','version':'3.1'},
    {'score':'invalid','severity':'high','version':'3.1'},
    {'score':9.8,'vector':'CVSS:3.1/INVALID','version':'3.1'},
    {'score':0.1,'severity':'critical','version':'3.1'},
    {'score':False,'severity':'info','version':'3.1'},
    {'score':9.8,'severity':'critical','version':'unsupported'},
    {'score':9.8,'vector':'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H','version':'3.0'},
    {'score':1.0,'vector':'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H','version':'3.1'}])
def test_invalid_or_contradictory_cvss_abstains_without_exception(value):
    got=module('rules').assess_risk(context([verified(),verified('CVSS_SCORE','score',value,package=None)]))
    assert got.risk_level=='UNKNOWN' and got.affected is True and got.priority=='REVIEW_REQUIRED'
    assert any('CVSS' in warning for warning in got.warnings)


def test_valid_verified_vector_uses_original_calculator():
    value={'score':9.8,'version':'3.1','vector':'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'}
    got=module('rules').assess_risk(context([verified(),verified('CVSS_SCORE','score',value,package=None)]))
    assert got.risk_level=='HIGH' and got.priority=='P1' and got.affected is True


def test_bad_cvss_does_not_erase_valid_kev_decision():
    got=module('rules').assess_risk(context([verified(),kev(),verified('CVSS_SCORE','score',
        {'score':999,'severity':'critical','version':'3.1'},package=None)]))
    assert got.risk_level=='CRITICAL' and got.priority=='P0' and got.affected is True
    assert any('CVSS' in warning for warning in got.warnings)


@pytest.mark.parametrize('value',[{'version':'0.7.0','ecosystem':'npm','package':'unrelated'},
    {'version':'0.7.0','ecosystem':'PyPI','package':'unrelated'},
    {'version':'0.7.0','ecosystem':'PyPI','package':'vllm','namespace':'different'}])
def test_fixed_release_value_identity_must_match_resolved_asset(value):
    from app.tooling.analysis import base_assessment
    result=base_assessment(context([verified(),kev(),verified('FIXED_VERSION','fix',value)]))
    assert not any(a.fixed_version for a in result.recommended_actions)
    assert result.patch_availability.status!='CONFIRMED_PRESENT'
    assert result.risk_level=='CRITICAL'


@pytest.mark.parametrize('kind',['POC_EXISTS','POC_ASSOCIATION'])
@pytest.mark.parametrize('scope',[{'package':'pkg-other'},{'branch':'stable'}])
def test_poc_for_other_package_never_decides_selected_asset(kind,scope):
    got=module('rules').assess_risk(context([verified(),verified(kind,'poc',{'url':'https://example.invalid/SYNTHETIC'},**scope)]))
    assert got.risk_level=='UNKNOWN' and got.priority=='REVIEW_REQUIRED'
    assert got.exploitation_signal.status=='UNKNOWN'


def test_inspect_patch_action_keeps_corresponding_evidence_reference():
    from app.tooling.analysis import base_assessment
    ctx=context([verified(),kev(),verified('PATCH_EXISTS','patch',{'url':'https://example.invalid/SYNTHETIC'},package=None)])
    result=base_assessment(ctx);action=next(a for a in result.recommended_actions if a.patch_reference)
    assert set(action.evidence_ids)<=set(e['evidence_id'] for e in result.evidence_refs)


def test_unselected_same_name_claim_without_package_id_prevents_low():
    first=verified();missing=verified(identifier='unchecked',package=None,
        value={'ecosystem':'PyPI','package':'vllm','raw_expression':'<0.8.0'})
    got=module('rules').assess_risk(context([first],source_claims=[first.claim,missing.claim],version='0.7.5'))
    assert got.affected is None and got.risk_level=='UNKNOWN' and got.priority=='REVIEW_REQUIRED'
    assert any('unchecked' in item for item in got.unresolved_items)


@pytest.mark.parametrize('name,expected',[('vllm','UNKNOWN'),('unrelated','LOW')])
def test_unchecked_other_id_requires_noncontradictory_distribution(name,expected):
    first=verified();other=verified(identifier='unchecked',package='pkg-other',
        value={'ecosystem':'PyPI','package':name,'raw_expression':'<0.8.0'})
    got=module('rules').assess_risk(context([first],source_claims=[first.claim,other.claim],version='0.7.5'))
    assert got.risk_level==expected
    assert got.affected is (False if expected=='LOW' else None)


def conflicting_source(engine):
    from app.utils.time import utcnow
    from tests.agents.verification.conftest import verification_seed
    from tests.agents.verification.test_end_to_end import source_for
    from tests.agents.verification.test_snapshot import request as verification_request
    from app.agents.verification.service import EvidenceVerificationService
    seed=verification_seed.__wrapped__(engine);now=utcnow();suffix=uuid4().hex
    with transaction(engine) as db:
        base=db.get(m.Claim,seed.claim_id)
        source=m.Source(source_key='ANALYSIS_CONFLICT_'+suffix,name='SYNTHETIC second vendor',
            source_type='vendor_advisory',category='vulnerability',authority_level='official',
            authority_scope='vulnerability affected versions',acquisition_method='fixture',
            base_url='https://example.invalid/SYNTHETIC/'+suffix,details={'is_test':True})
        db.add(source);db.flush();payload=b'SYNTHETIC affected <=0.8.0. Not a real advisory.'
        raw=m.RawDocument(source_id=source.id,external_id=seed.cve,source_url=source.base_url,
            published_at=now,retrieved_at=now,content_type='text/plain',raw_payload=payload,
            content_hash=hashlib.sha256(payload).hexdigest(),publisher=source.name)
        db.add(raw);db.flush()
        obs=m.SourceObservation(source_id=source.id,raw_document_id=raw.id,external_id=seed.cve,
            record_type='vulnerability',retrieved_at=now,parse_status='parsed',lineage_key='SYNTHETIC-second:'+suffix,
            publisher=source.name,normalizer_version='TEST',normalized_payload={'canonical_id':seed.cve})
        db.add(obs);db.flush();value={**base.value_json,'raw_expression':'<=0.8.0'}
        claim=m.Claim(claim_key='SYNTHETIC-conflict:'+suffix,vulnerability_id=seed.vulnerability_id,
            package_identifier_id=seed.package_id,claim_type='AFFECTS_VERSION',predicate='AFFECTS_VERSION',
            scope_key=base.scope_key,value_json=value)
        db.add(claim);db.flush();quote='affected <=0.8.0'
        db.add(m.Evidence(claim_id=claim.id,source_id=source.id,raw_document_id=raw.id,observation_id=obs.id,
            scope_key=base.scope_key,evidence_type='official_vendor_advisory',stance='support',excerpt=quote,
            excerpt_hash=hashlib.sha256(quote.encode()).hexdigest(),source_url=raw.source_url,
            published_at=now,retrieved_at=now,locator={'line':1},locator_key='affected',observed_value=value,
            publisher=source.name,lineage_key=obs.lineage_key,details={'is_test':True,'explicit':True}))
    src=source_for(engine,seed);verifier=EvidenceVerificationService(engine)
    saved=verifier.run(verification_request(src),actor=seed.actor)
    art=verifier.read_results(saved.run_id,actor=seed.actor).artifacts[0]
    assert art.verification_status=='CONFLICT' and art.conflicts
    return SimpleNamespace(seed=seed,investigation=src.artifact,verification=art,asset_id=None,component_id=None)


@pytest.fixture(scope='module')
def conflicted(engine):return conflicting_source(engine)


def test_real_cross_claim_conflict_handoff_remains_inspectable(engine,conflicted):
    src=conflicted;svc=module('service').SecurityAnalysisService(engine)
    saved=svc.run(request(src),actor=src.seed.actor)
    result=svc.read_results(saved.run_id,actor=src.seed.actor).artifacts[0]
    assert result.verification_status=='CONFLICT' and result.risk_level=='UNKNOWN' and result.affected is None
    ids={e['evidence_id'] for e in result.evidence_refs}
    assert {e.evidence_id for e in src.verification.conflicting_evidence}<=ids
    assert result.claim_dispositions and all(c['status']=='CONFLICT' for c in result.claim_dispositions)


@pytest.mark.parametrize('part',['content','missing_relationship','unknown_evidence'])
def test_cross_claim_support_still_rejects_unbound_or_changed_evidence(engine,conflicted,monkeypatch,part):
    src=conflicted;reader=module('snapshot').VerificationReader
    actual=src.verification
    if part=='content':
        items=actual.conflicting_evidence
        actual=actual.model_copy(update={'conflicting_evidence':(items[0].model_copy(update={'content':'forged'}),*items[1:])})
    if part=='missing_relationship':actual=actual.model_copy(update={'conflicts':()})
    if part=='unknown_evidence':
        checked=actual.claims[0].model_copy(update={'conflicting_evidence_ids':('unknown',)})
        actual=actual.model_copy(update={'claims':(checked,*actual.claims[1:])})
    # Fault injection at the existing Reader boundary; the real sealed DB input stays unchanged.
    monkeypatch.setattr(reader,'read',lambda *args,**kwargs:SimpleNamespace(artifacts=(actual,)))
    with pytest.raises(ValueError,match='INVALID_INPUT_ARTIFACT'):
        module('context_store').AnalysisContextStore(engine).capture(request(src),actor=src.seed.actor)

"""Sealed source metadata and currentness, through actual receipt-backed inputs."""
from datetime import timedelta
from types import SimpleNamespace
import pytest
from app.db import models as m
from app.db.session import transaction
from app.utils.time import utcnow
from app.agents.verification.snapshot import _claim,_quoted,InvestigationSnapshotReader
from app.agents.verification.context_store import VerificationContextStore
from app.agents.verification.rules import evaluate_snapshot
from tests.agents.verification.conftest import verification_seed
from tests.agents.verification.test_end_to_end import source_for
from tests.agents.verification.test_snapshot import request


def test_claim_preserves_scoring_subject_and_supersession_from_receipt():
    cve='CVE-2099-9999001'
    value={'id':'C1','vulnerability_id':cve,'claim_type':'CVSS_SCORE','scope_key':'cvss',
        'value_json':{'score':9.1},'cvss_version':'3.1','assessment_kind':'primary',
        'metadata':{'superseded':True},'revision':2}
    got=_claim(value,'lookup',cve)
    assert got.related_entities['cvss_version']=='3.1'
    assert got.related_entities['assessment_kind']=='primary'
    assert got.related_entities['superseded'] is True


@pytest.mark.parametrize('locator,quote,valid',[
    ({'line':1},'affected <=0.6',True),({'line':2},'affected <=0.6',False),
    ({'line':1},'unrelated invented quote',False),({},'affected <=0.6',False)])
def test_literal_quote_requires_matching_locator(locator,quote,valid):
    assert _quoted(SimpleNamespace(raw_payload=b'affected <=0.6\nother'),
        SimpleNamespace(locator=locator,excerpt=quote)) is valid


def test_new_observation_invalidates_new_context_but_not_saved_result(engine):
    seed=verification_seed.__wrapped__(engine);src=source_for(engine,seed)
    store=VerificationContextStore(engine);old=store.capture(request(src),actor=seed.actor)
    assert evaluate_snapshot(old).verification_status=='CONFIRMED'
    with transaction(engine) as db:
        obs=db.get(m.SourceObservation,seed.observation_id)
        db.add(m.SourceObservation(source_id=obs.source_id,raw_document_id=obs.raw_document_id,
            external_id=obs.external_id,record_type=obs.record_type,retrieved_at=utcnow()+timedelta(seconds=1),
            parse_status='parsed',lineage_key=obs.lineage_key,publisher=obs.publisher,
            normalizer_version='SYNTHETIC-new-edition',normalized_payload=obs.normalized_payload,
            details={'is_test':True}))
    new=store.capture(request(src),actor=seed.actor)
    ev=next(e for e in new.snapshot.evidence if e.evidence_id==str(seed.evidence_id))
    assert not ev.is_current
    assert evaluate_snapshot(new).verification_status=='INSUFFICIENT_EVIDENCE'
    assert store.read(old.context_id,actor=seed.actor)==old
    assert evaluate_snapshot(old).verification_status=='CONFIRMED'


def test_receipt_pointer_source_reconstructs_claims_from_formal_receipts(engine,investigation_source,monkeypatch):
    import app.agents.investigation.normalize as projection
    src=investigation_source
    # Force the original, legitimate size fallback; retain untouched formal receipts.
    monkeypatch.setattr(projection,'ARTIFACT_LIMIT',1)
    pointer=src.service.read_results(src.artifact.run_id,src.seed.actor).artifacts[0]
    assert pointer.evidence_storage=='tool_receipts' and pointer.vulnerability_id is None
    snapshot=InvestigationSnapshotReader(engine).read(request(src),actor=src.seed.actor)
    assert any(c.claim_id==str(src.seed.claim_id) for c in snapshot.claims)
    assert any(e.evidence_id==str(src.seed.evidence_id) for e in snapshot.evidence)
    assert snapshot.receipt_references and snapshot.artifact['evidence_storage']=='tool_receipts'

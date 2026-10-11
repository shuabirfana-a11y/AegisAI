"""Breaks caught: live data overwrite, cross-owner reads and unverified source links."""
import copy
import importlib
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import fingerprint
from app.agents.verification.schemas import VerificationRequest


def reader(engine):
    try:
        return importlib.import_module('app.agents.verification.snapshot').InvestigationSnapshotReader(engine)
    except ModuleNotFoundError:
        pytest.fail('Owner-scoped investigation snapshot reader is missing')


def request(source,**change):
    return VerificationRequest(source_run_id=source.artifact.run_id,source_task_id=source.artifact.task_id,
        source_artifact_id=source.artifact.artifact_id,request_key='snapshot-'+uuid4().hex,**change)


def test_snapshot_binds_stored_claim_evidence_and_preserves_source(engine,investigation_source):
    source=investigation_source
    before=source.artifact.model_dump(mode='json')
    value=reader(engine).read(request(source),actor=source.seed.actor)
    claim=next(c for c in value.claims if c.claim_id==str(source.seed.claim_id))
    evidence=next(e for e in value.evidence if e.evidence_id==str(source.seed.evidence_id))
    assert claim.value['raw_expression'] == '>=0.5.0,<0.7.0'
    assert claim.claim_type == 'AFFECTS_VERSION' and claim.claim_revision == 1
    assert evidence.integrity_status == 'VALID' and evidence.directness == 'direct'
    assert evidence.hash and evidence.excerpt_hash and evidence.authority_level == 'official'
    assert value.receipt_references[0]['record_id']
    assert before == source.service.read_results(source.artifact.run_id,source.seed.actor).artifacts[0].model_dump(mode='json')


def test_snapshot_rejects_foreign_owner_and_artifact_id(engine,investigation_source):
    source=investigation_source
    instance=reader(engine)
    with pytest.raises(LookupError):instance.read(request(source),actor='different-owner')
    forged=request(source).model_copy(update={'source_artifact_id':uuid4()})
    with pytest.raises(LookupError):instance.read(forged,actor=source.seed.actor)


def test_live_claim_and_authority_changes_do_not_replace_original_values(engine,investigation_source):
    source=investigation_source
    instance=reader(engine)
    with transaction(engine) as db:
        claim=db.get(m.Claim,source.seed.claim_id);old_value=copy.deepcopy(claim.value_json)
        live=db.get(m.Source,source.seed.source_id);old_level=live.authority_level
        claim.value_json={'raw_expression':'<=99'};live.authority_level='community'
    try:
        got=instance.read(request(source),actor=source.seed.actor)
        saved=next(c for c in got.claims if c.claim_id==str(source.seed.claim_id))
        ev=next(e for e in got.evidence if e.evidence_id==str(source.seed.evidence_id))
        assert saved.value['raw_expression'] == '>=0.5.0,<0.7.0'
        assert ev.authority_level == 'official'
    finally:
        with transaction(engine) as db:
            db.get(m.Claim,source.seed.claim_id).value_json=old_value
            db.get(m.Source,source.seed.source_id).authority_level=old_level


def test_snapshot_rejects_tampered_receipt_identity(engine,investigation_source):
    source=investigation_source
    instance=reader(engine)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,source.artifact.run_id);original=copy.deepcopy(row.details)
        edited=copy.deepcopy(original)
        edited['runtime_v1']['artifacts'][source.artifact.task_id]['tool_calls'][0]['sequence_no']+=800
        row.details=edited
    try:
        with pytest.raises(ValueError):instance.read(request(source),actor=source.seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,source.artifact.run_id).details=original

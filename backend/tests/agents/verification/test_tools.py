"""Breaks caught: unregistered/write tools, cross-owner access and business mutation."""
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from app.tooling.contracts import REGISTRY
from app.tooling.gateway import ToolGateway,ToolContext
from tests.agents.verification.test_snapshot import request

TOOLS=['evaluate_evidence_snapshot','validate_claim_snapshot','compare_claim_snapshot']


@pytest.mark.parametrize('name',TOOLS)
def test_verification_tools_are_typed_read_only(name):
    assert name in REGISTRY, 'Read-only verification adapter is missing'
    assert REGISTRY[name].permission=='READ_ONLY'
    with pytest.raises(ValueError):REGISTRY[name].input.model_validate({'context_id':str(uuid4()),'sql':'DROP TABLE claims'})


def test_tool_gateway_returns_receipt_backed_result_without_business_writes(engine,investigation_source,monkeypatch):
    assert TOOLS[0] in REGISTRY,'Verification tool registration is missing'
    from app.agents.verification.context_store import VerificationContextStore
    src=investigation_source
    captured=VerificationContextStore(engine).capture(request(src),actor=src.seed.actor)
    monkeypatch.setenv('AEGIS_DATABASE_URL',engine.url.render_as_string(hide_password=False))
    watched=(m.Claim,m.Evidence,m.VerificationResult,m.VerificationEvidence,m.ConflictRecord,m.ReviewTask)
    def state():
        with transaction(engine) as db:
            return [db.scalar(select(func.count()).select_from(table)) for table in watched]+[
                db.get(m.Claim,src.seed.claim_id).revision,db.get(m.Claim,src.seed.claim_id).adopted]
    before=state()
    ctx=ToolContext(actor=src.seed.actor,permissions={'READ_ONLY'},max_calls=1)
    out=ToolGateway().invoke(TOOLS[0],{'context_id':str(captured.context_id)},ctx)
    assert out.status=='success' and out.data['assessment']['verification_status']=='CONFIRMED'
    assert out.evidence_refs[0]['raw_document_id'] and out.evidence_refs[0]['verified'] is False
    assert before==state()
    foreign=ToolGateway().invoke(TOOLS[0],{'context_id':str(captured.context_id)},
        ToolContext(actor='different-owner',permissions={'READ_ONLY'},max_calls=1))
    assert foreign.status=='failed' and foreign.errors[0]['code']=='NOT_FOUND'


def test_only_claim_validation_can_use_its_matching_semantics(engine,investigation_source,monkeypatch):
    assert TOOLS[0] in REGISTRY,'Verification tool registration is missing'
    from app.agents.verification.context_store import VerificationContextStore
    src=investigation_source
    captured=VerificationContextStore(engine).capture(request(src),actor=src.seed.actor)
    monkeypatch.setenv('AEGIS_DATABASE_URL',engine.url.render_as_string(hide_password=False))
    out=ToolGateway().invoke('compare_claim_snapshot',{'context_id':str(captured.context_id)},
        ToolContext(actor=src.seed.actor,permissions={'READ_ONLY'},max_calls=1))
    assert out.status=='failed' and out.errors[0]['code']=='INVALID_STATE'

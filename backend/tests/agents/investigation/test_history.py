from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.tooling.gateway import ToolGateway, ToolContext
from app.tooling.adapters import execute_local


def test_reused_raw_document_does_not_make_old_evidence_current(engine, investigation_seed):
    with transaction(engine) as db:
        old = db.scalar(select(m.Evidence).join(m.Claim, m.Evidence.claim_id == m.Claim.id).where(
            m.Claim.vulnerability_id == investigation_seed.vulnerability_id))
        assert old.observation_id != investigation_seed.observation_id
        gateway = ToolGateway(executor=lambda name, args, ctx: execute_local(db, name, args, ctx.actor))
        result = gateway.invoke('get_evidence', {'target': investigation_seed.cve},
            ToolContext(actor=investigation_seed.actor))
        ref = next(r for r in result.evidence_refs if r.get('evidence_id') == str(old.id))
        assert ref['observation_id'] == str(old.observation_id)
        assert ref['is_current'] is False
        assert ref['verified'] is False

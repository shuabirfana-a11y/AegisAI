"""Reuse existing current-evidence trust at the tool/persistence boundary."""
from datetime import timedelta
from sqlalchemy import select
from app.db import models as m
from app.assets.remediation import trusted_claim
from app.enrichment.evidence import current_evidence
from app.enrichment.versions import canonical_value
from app.utils.time import utcnow

def current_support_ids(session,claim):
    if not trusted_claim(session,claim):return set()
    result=session.scalar(select(m.VerificationResult).where(m.VerificationResult.claim_id==claim.id,
        m.VerificationResult.claim_revision==claim.revision,m.VerificationResult.status=='confirmed'))
    if result is None:return set()
    known={str(id) for id in session.scalars(select(m.VerificationEvidence.evidence_id).where(m.VerificationEvidence.verification_result_id==result.id))}
    known.update(result.details.get('observed_evidence_ids',[]))
    now=utcnow()
    return {e['id'] for e in current_evidence(session,claim) if e['id'] in known and e['is_current'] and e['stance']=='support'
        and now-timedelta(days=30)<=e['retrieved_at']<=now+timedelta(minutes=5)
        and canonical_value(claim.claim_type,e['value'] or {})==canonical_value(claim.claim_type,claim.value_json)}

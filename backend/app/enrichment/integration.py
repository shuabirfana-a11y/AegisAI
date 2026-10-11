from sqlalchemy import select
from app.db import models as m
from app.enrichment.evidence import current_evidence
from app.enrichment.rules import evaluate_claim
from app.enrichment.repository import lock,ensure_review
from app.utils.time import utcnow

class IntelligenceIntegrationService:
    @staticmethod
    def adopt(session,claim,result,*,now=None):
        now=now or utcnow();lock(session,'adoption:'+str(claim.vulnerability_id)+':'+claim.predicate+':'+claim.scope_key);lock(session,'claim:'+claim.claim_key)
        other=session.scalar(select(m.Claim).where(m.Claim.vulnerability_id==claim.vulnerability_id,m.Claim.predicate==claim.predicate,
            m.Claim.scope_key==claim.scope_key,m.Claim.adopted.is_(True),m.Claim.id!=claim.id).limit(1))
        decision=evaluate_claim(claim.claim_type,claim.value_json,current_evidence(session,claim),now)
        reasons=[]
        if result.claim_id!=claim.id or result.claim_revision!=claim.revision:reasons.append('REVISION_MISMATCH')
        if result.status!='confirmed':reasons.append('NOT_CONFIRMED')
        if not result.verified_by_type=='human' and decision['status']!='CONFIRMED':reasons.append('EVIDENCE_OR_FRESHNESS_GATE')
        if other:reasons.append('EXISTING_ADOPTED_VALUE')
        if claim.details.get('superseded'):reasons.append('SUPERSEDED_SOURCE_ASSERTION')
        conflict=session.scalar(select(m.ConflictRecord.id).where(m.ConflictRecord.status=='open',
            (m.ConflictRecord.claim_a_id==claim.id)|(m.ConflictRecord.claim_b_id==claim.id)).limit(1))
        if conflict:reasons.append('OPEN_CONFLICT')
        if reasons:
            if result.verified_by_type!='human':claim.adopted=False
            if other or conflict:ensure_review(session,claim,'SOURCE_CONFLICT','Integration gate requires analyst choice: '+','.join(reasons),now=now)
        else:claim.adopted=True
        session.flush()
        return {'adopted':claim.adopted,'gate_passed':not reasons,'reasons':reasons,'claim_id':str(claim.id),'claim_revision':claim.revision}

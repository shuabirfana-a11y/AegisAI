from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.enrichment.rules import evaluate_claim
from app.enrichment.evidence import current_evidence,evidence_fingerprint
from app.enrichment.contracts import DB_VERIFY
from app.enrichment.repository import digest,lock,emit,ensure_review
from app.utils.time import utcnow

class VerificationService:
    @staticmethod
    def verify(session,claim,*,now=None):
        now=now or utcnow();lock(session,'claim:'+claim.claim_key)
        previous=session.scalar(select(m.VerificationResult).where(m.VerificationResult.claim_id==claim.id)
            .order_by(m.VerificationResult.claim_revision.desc()).limit(1))
        evidence=current_evidence(session,claim)
        decision=evaluate_claim(claim.claim_type,claim.value_json,evidence,now)
        fingerprint=digest([claim.claim_type,claim.value_json,decision['status'],sorted(decision['considered'])])
        if previous and previous.verified_by_type=='human':
            known={UUID(x) for x in previous.details.get('observed_evidence_ids',[])} or set(session.scalars(select(m.VerificationEvidence.evidence_id).where(m.VerificationEvidence.verification_result_id==previous.id)))
            known_fingerprints={evidence_fingerprint(e) for e in session.scalars(select(m.Evidence).where(m.Evidence.id.in_(known)))}
            if any(e['fingerprint'] not in known_fingerprints for e in evidence if e['is_current']):
                ensure_review(session,claim,'SOURCE_CONFLICT','New evidence after a human decision; explicit recheck required',fingerprint=fingerprint,now=now)
            return previous
        if previous and previous.decision_key==fingerprint:return previous
        if previous:claim.revision+=1
        claim.verification_status=DB_VERIFY[decision['status']]
        result=m.VerificationResult(claim_id=claim.id,claim_revision=claim.revision,status=claim.verification_status,
            verification_method=decision['method'],reason_summary=decision['reason_summary'],verified_at=now,
            verified_by_type='system',verified_by_id='aegis-deterministic-v1',decision_key=fingerprint,
            adopted_value=claim.value_json if claim.verification_status=='confirmed' else None,
            details={'evaluated_value':claim.value_json,'abstention_reason':decision['abstention_reason'],'independent_groups':decision['independent_groups'],
                'supporting_evidence':decision['supporting_evidence'],'contradicting_evidence':decision['contradicting_evidence'],
                'sources_considered':sorted({e['source'] for e in evidence if e['id'] in decision['considered']})})
        session.add(result);session.flush()
        for id in decision['considered']:
            session.add(m.VerificationEvidence(claim_id=claim.id,verification_result_id=result.id,evidence_id=UUID(id)))
        emit(session,claim.vulnerability_id,'VERIFICATION_CHANGED',str(result.id),'Claim verification produced a new scoped result',
            claim=claim,payload={'status':decision['status'],'revision':claim.revision,'method':decision['method']},now=now)
        if result.status in ('conflict','insufficient') and claim.claim_type in ('AFFECTS_VERSION','FIXED_VERSION','POC_EXISTS','POC_ASSOCIATION','PATCH_EXISTS','FIX_COMMIT'):
            kind='SOURCE_CONFLICT' if result.status=='conflict' else {'POC_EXISTS':'POC_VERIFICATION','POC_ASSOCIATION':'POC_VERIFICATION','PATCH_EXISTS':'PATCH_VERIFICATION','FIX_COMMIT':'PATCH_VERIFICATION'}.get(claim.claim_type,'INSUFFICIENT_EVIDENCE')
            ensure_review(session,claim,kind,decision['reason_summary'],fingerprint=fingerprint,now=now)
        session.flush();return result

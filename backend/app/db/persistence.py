"""Narrow database transactions; no collectors, matching engine or verification AI."""
import hashlib, json, re
from sqlalchemy import select,text
from sqlalchemy.dialects.postgresql import insert
from app.db import models as m
from app.db.types import utcnow

class RevisionConflict(ValueError): pass
class IdempotencyConflict(ValueError): pass

def ensure_vulnerability(session,canonical_id,title):
    """Exact supplied identity only; does not infer aliases or merge advisories."""
    canonical_id=canonical_id.strip()
    if not canonical_id: raise ValueError('Canonical identity is required')
    if canonical_id.upper().startswith('CVE-'):
        canonical_id=canonical_id.upper()
        if not re.fullmatch(r'CVE-\d{4}-\d{4,}',canonical_id): raise ValueError('Invalid CVE identity syntax')
    created=session.scalar(insert(m.Vulnerability).values(canonical_id=canonical_id,title=title).on_conflict_do_nothing(index_elements=['canonical_id']).returning(m.Vulnerability.id))
    if created is not None: return session.get(m.Vulnerability,created)
    return session.scalar(select(m.Vulnerability).where(m.Vulnerability.canonical_id==canonical_id))

def store_raw(session,**values):
    payload=values['raw_payload']
    if not isinstance(payload,bytes): raise ValueError('Original entity bytes required')
    digest=hashlib.sha256(payload).hexdigest()
    if values.get('content_hash',digest)!=digest: raise ValueError('Content hash does not match original bytes')
    values['content_hash']=digest
    created=session.scalar(insert(m.RawDocument).values(**values).on_conflict_do_nothing(constraint='uq_raw_revision').returning(m.RawDocument.id))
    if created is not None: return session.get(m.RawDocument,created)
    return session.scalar(select(m.RawDocument).where(m.RawDocument.source_id==values['source_id'],m.RawDocument.external_id==values['external_id'],m.RawDocument.content_hash==digest))

def record_review(session,*,task_id,actor,expected_revision,expected_claim_revision,
                  request_key,status,value,reason,evidence_ids):
    """Caller authenticates/authorizes actor; caller owns commit or rollback."""
    if not actor.strip() or not reason.strip() or not request_key.strip(): raise ValueError('Actor, reason and request key required')
    if status not in {'confirmed','conflict','insufficient','pending','deferred','rejected'}: raise ValueError('Unsupported review decision')
    fingerprint={'task':str(task_id),'actor':actor,'expected_revision':expected_revision,
                 'expected_claim_revision':expected_claim_revision,'status':status,
                 'value':value,'reason':reason,'evidence':sorted(str(x) for x in set(evidence_ids))}
    request_hash=hashlib.sha256(json.dumps(fingerprint,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    # Serialize identical request keys even when they target different tasks.
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:request,0))'),{'request':actor+':'+request_key})
    existing=session.scalar(select(m.AuditLog).where(m.AuditLog.actor==actor,m.AuditLog.request_key==request_key))
    if existing:
        if existing.request_hash!=request_hash: raise IdempotencyConflict('Request key already used for another payload')
        return existing
    task=session.scalar(select(m.ReviewTask).where(m.ReviewTask.id==task_id).with_for_update().execution_options(populate_existing=True))
    if task is None: raise ValueError('Review task not found')
    claim=session.scalar(select(m.Claim).where(m.Claim.id==task.claim_id).with_for_update().execution_options(populate_existing=True))
    if task.revision!=expected_revision or claim.revision!=expected_claim_revision:
        raise RevisionConflict('Review or claim changed; reload before deciding')
    if task.status in {'resolved','cancelled'}: raise RevisionConflict('Task is already closed')
    evidence=list(session.scalars(select(m.Evidence).where(m.Evidence.id.in_(evidence_ids)))) if evidence_ids else []
    if len(evidence)!=len(set(evidence_ids)) or any(e.claim_id!=claim.id or e.scope_key!=claim.scope_key for e in evidence):
        raise ValueError('Evidence does not belong to this scoped claim')
    if status=='confirmed' and (value is None or not any(e.stance=='support' for e in evidence)):
        raise ValueError('Confirmation requires explicit value and supporting evidence')
    if status=='conflict' and not {'support','contradict'}<={e.stance for e in evidence}:
        raise ValueError('Conflict requires scoped supporting and contradicting evidence')
    before={'value':claim.value_json,'verification_status':claim.verification_status,'claim_revision':claim.revision,'review_status':task.status}
    now=utcnow(); verification=None
    if status!='deferred':
        claim.revision+=1
        if value is not None: claim.value_json=value
        claim.verification_status=status;claim.adopted=status=='confirmed'
        verification=m.VerificationResult(claim_id=claim.id,claim_revision=claim.revision,
            status=status,verification_method='human_review',reason_summary=reason,
            verified_at=now,verified_by_type='human',verified_by_id=actor,
            decision_key=actor+':'+request_key,adopted_value=claim.value_json if claim.adopted else None,
            details={'evaluated_value':claim.value_json,'observed_evidence_ids':[str(e) for e in session.scalars(select(m.Evidence.id).where(m.Evidence.claim_id==claim.id))]})
        session.add(verification);session.flush()
        for e in evidence: session.add(m.VerificationEvidence(claim_id=claim.id,verification_result_id=verification.id,evidence_id=e.id))
    task.status='deferred' if status=='deferred' else 'resolved'
    task.revision+=1;task.resolved_at=None if status=='deferred' else now
    task.resolution=status;task.resolution_note=reason
    after={'value':claim.value_json,'verification_status':claim.verification_status,'claim_revision':claim.revision,'review_status':task.status}
    task.before_state=before;task.after_state=after
    audit=m.AuditLog(actor=actor,action='review_decision',claim_id=claim.id,
        review_task_id=task.id,verification_result_id=verification.id if verification else None,
        before_state=before,after_state=after,reason=reason,occurred_at=now,
        request_key=request_key,request_hash=request_hash)
    session.add(audit);session.flush()
    return audit

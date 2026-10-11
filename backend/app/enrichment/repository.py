import hashlib,json
from sqlalchemy import select,text
from app.db import models as m
from app.repositories.ingestion import unique_row
from app.enrichment.versions import canonical_value
from app.enrichment.contracts import CONTENT_TRUST
from app.utils.time import utcnow

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def lock(session,key):session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,3))'),{'key':'enrichment:'+key})

def emit(session,target,kind,key,summary,*,claim=None,evidence=None,source_id=None,payload=None,occurred_at=None,now=None):
    return unique_row(session,m.IntelligenceEvent,{'event_key':'p7:'+kind+':'+digest([str(target),key])},
        {'vulnerability_id':target,'event_type':kind,'summary':summary,'detected_at':now or utcnow(),'occurred_at':occurred_at,
         'claim_id':claim.id if claim else None,'evidence_id':evidence.id if evidence else None,'source_id':source_id,'payload':payload})

class ClaimStore:
    @staticmethod
    def add(session,target,kind,scope,value,*,subject=None,details=None):
        key='p7:'+digest([str(target),kind,scope,canonical_value(kind,value)])
        lock(session,'claim:'+key)
        return unique_row(session,m.Claim,{'claim_key':key},{'vulnerability_id':target,'claim_type':kind,'predicate':kind,
            'scope_key':scope,'value_json':value,**(subject or {}),
            'details':{'content_trust_level':CONTENT_TRUST,**(details or {})}})

def ensure_review(session,claim,kind,reason,*,fingerprint='',now=None):
    lock(session,'review:'+str(claim.id))
    kinds=[kind]
    if kind=='SOURCE_CONFLICT':kinds+=['VERSION_CONFLICT','FIXED_VERSION_CONFLICT','SEVERITY_CONFLICT','POC_STATUS_CONFLICT','PATCH_STATUS_CONFLICT','KNOWN_EXPLOITATION_CONFLICT','VENDOR_THIRD_PARTY_CONFLICT']
    existing=session.scalar(select(m.ReviewTask).where(m.ReviewTask.claim_id==claim.id,m.ReviewTask.review_type.in_(kinds),
        m.ReviewTask.status.in_(['open','assigned','deferred'])).order_by(m.ReviewTask.created_at.desc()).limit(1))
    if existing:return existing
    task=m.ReviewTask(claim_id=claim.id,review_type=kind,reason=reason,
        details={'enrichment_fingerprint':fingerprint,'content_trust_level':CONTENT_TRUST})
    session.add(task);session.flush()
    emit(session,claim.vulnerability_id,'REVIEW_CREATED',str(task.id),'A claim requires analyst review',claim=claim,
        payload={'review_id':str(task.id),'review_type':kind},now=now)
    return task

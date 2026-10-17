from itertools import combinations
from datetime import timedelta
from sqlalchemy import select
from app.db import models as m
from app.enrichment.rules import compare_claims
from app.enrichment.version_scope import stored_scope,compare_scopes
from app.enrichment.evidence import EvidenceService,current_evidence
from app.enrichment.repository import digest,lock,ensure_review,emit
from app.repositories.ingestion import unique_row
from app.utils.time import utcnow

class ConflictDetectionService:
    @staticmethod
    def detect(session,target,*,now=None):
        now=now or utcnow();lock(session,'conflicts:'+str(target))
        claims=list(session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==target)))
        active=[c for c in claims if not c.details.get('superseded') and (c.claim_type!='FIXED_VERSION' or c.value_json.get('version')) and any(x['is_current'] and x['stance']=='support' and
            now-timedelta(days=30)<=x['retrieved_at']<=now+timedelta(minutes=5) for x in current_evidence(session,c))]
        active_ids={c.id for c in active}
        for obsolete in session.scalars(select(m.ConflictRecord).where(m.ConflictRecord.vulnerability_id==target,m.ConflictRecord.status=='open')):
            if obsolete.claim_a_id in active_ids and obsolete.claim_b_id in active_ids:continue
            obsolete.status='resolved';obsolete.resolution={'method':'system_current_evidence','reason':'Source assertion no longer current or supported'}
            obsolete.resolved_at=now;obsolete.resolved_by='system:current-evidence'
            task=session.get(m.ReviewTask,obsolete.review_task_id) if obsolete.review_task_id else None
            if task and task.status in ('open','assigned','deferred'):
                other=session.scalar(select(m.ConflictRecord.id).where(m.ConflictRecord.review_task_id==task.id,m.ConflictRecord.status=='open',m.ConflictRecord.id!=obsolete.id).limit(1))
                if not other:
                    before={'review_status':task.status,'revision':task.revision};task.status='cancelled';task.revision+=1;task.resolution_note='Source assertion no longer current; historical evidence retained'
                    session.add(m.AuditLog(actor='system:current-evidence',action='conflict_retired',claim_id=task.claim_id,review_task_id=task.id,
                        before_state=before,after_state={'review_status':'cancelled','revision':task.revision},reason=task.resolution_note,occurred_at=now,
                        request_key='retire:'+str(obsolete.id),request_hash=digest([str(obsolete.id),'inactive'])))
            emit(session,target,'CONFLICT_RETIRED',str(obsolete.id),'An obsolete source conflict was retired; history retained',payload={'conflict_id':str(obsolete.id)},now=now)
        results=[]
        assertions={}
        for c in active:
            scopes=[]
            if c.claim_type in ('AFFECTS_VERSION','FIXED_VERSION'):
                current_ids={x['id'] for x in current_evidence(session,c) if x['is_current'] and x['stance']=='support'
                             and now-timedelta(days=30)<=x['retrieved_at']<=now+timedelta(minutes=5)}
                for e in session.scalars(select(m.Evidence).where(m.Evidence.claim_id==c.id,m.Evidence.stance=='support')):
                    if e.published_at and (e.published_at>now+timedelta(minutes=5)
                        or e.published_at>e.retrieved_at+timedelta(minutes=5)):continue
                    if str(e.id) in current_ids and (scope:=stored_scope(session,e,c.claim_type)):
                        scopes.append(scope.model_dump(mode='json'))
            assertions[c.id]={'type':c.claim_type,'scope':c.scope_key,'value':c.value_json,'version_scopes':scopes}
        for a,b in combinations(active,2):
            kind=compare_claims(assertions[a.id],assertions[b.id])
            if not kind:
                if a.scope_key==b.scope_key and a.claim_type in ('AFFECTS_VERSION','FIXED_VERSION') and b.claim_type in ('AFFECTS_VERSION','FIXED_VERSION'):
                    comparison=compare_scopes(assertions[a.id],assertions[b.id])
                    if comparison.result in ('DIFFERENT_SCOPE','BRANCH_DIFFERENCE'):
                        for obsolete in session.scalars(select(m.ConflictRecord).where(m.ConflictRecord.vulnerability_id==target,
                            m.ConflictRecord.claim_a_id.in_([a.id,b.id]),m.ConflictRecord.claim_b_id.in_([a.id,b.id]),m.ConflictRecord.status=='open')):
                            obsolete.status='resolved';obsolete.resolved_at=now;obsolete.resolved_by='system:version-comparability-v1'
                            obsolete.resolution={'method':'source_entry_comparability','comparison':comparison.model_dump(mode='json'),
                                'history_and_evidence_retained':True}
                            emit(session,target,'CONFLICT_SCOPE_RECLASSIFIED',str(obsolete.id),'Bound source entries are compatible; historical evidence retained',
                                payload={'conflict_id':str(obsolete.id),'comparison':comparison.model_dump(mode='json')},now=now)
                continue
            if b.adopted and not a.adopted:a,b=b,a
            ordered=sorted([str(a.id),str(b.id)])
            fingerprint=digest(sorted(x['fingerprint'] for c in (a,b) for x in current_evidence(session,c) if x['is_current'] and x['stance']=='support'))
            key='p7:'+digest([str(target),kind,ordered,fingerprint])
            existing=session.scalar(select(m.ConflictRecord).where(m.ConflictRecord.conflict_key==key))
            if existing is None:
                open_pair=session.scalar(select(m.ConflictRecord).where(m.ConflictRecord.vulnerability_id==target,m.ConflictRecord.conflict_type==kind,
                    m.ConflictRecord.claim_a_id.in_([a.id,b.id]),m.ConflictRecord.claim_b_id.in_([a.id,b.id]),m.ConflictRecord.status=='open').limit(1))
                if open_pair:open_pair.conflict_key=key;open_pair.details={**open_pair.details,'evidence_fingerprint':fingerprint};existing=open_pair
            if existing and existing.status!='open':results.append(existing);continue
            task=ensure_review(session,a,kind,'Current same-scope source assertions disagree',fingerprint=key,now=now)
            conflict=unique_row(session,m.ConflictRecord,{'conflict_key':key},{'vulnerability_id':target,
                'claim_a_id':a.id,'claim_b_id':b.id,'scope_key':a.scope_key,'conflict_type':kind,'detected_at':now,'review_task_id':task.id,
                'details':{'evidence_fingerprint':fingerprint}})
            # Retain both source facts; each opposing raw supplies scoped contradictory evidence.
            for own,opposing in [(a,b),(b,a)]:
                current_ids={x['id'] for x in current_evidence(session,opposing) if x['is_current'] and x['stance']=='support'}
                for e in list(session.scalars(select(m.Evidence).where(m.Evidence.claim_id==opposing.id,m.Evidence.stance=='support'))):
                    if str(e.id) not in current_ids:continue
                    EvidenceService.add(session,own,session.get(m.SourceObservation,e.observation_id),e.observed_value,e.locator,
                        stance='contradict',evidence_type=e.evidence_type,explicit=e.details.get('explicit',False),details={'conflict_id':str(conflict.id)},excerpt=e.excerpt)
            emit(session,target,'CONFLICT_DETECTED',key,'Current structured assertions have a same-scope conflict',claim=a,
                payload={'conflict_id':str(conflict.id),'claim_a':str(a.id),'claim_b':str(b.id),'conflict_type':kind},now=now)
            results.append(conflict)
        session.flush();return results

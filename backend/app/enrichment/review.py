from sqlalchemy import select
from app.db import models as m
from app.db.persistence import record_review
from app.enrichment.repository import emit,lock,digest
from app.enrichment.versions import canonical_value

class ReviewWorkflow:
    @staticmethod
    def resolve(session,**values):
        with session.begin_nested():return ReviewWorkflow._resolve(session,**values)

    @staticmethod
    def _resolve(session,**values):
        task=session.get(m.ReviewTask,values['task_id'])
        existing=session.scalar(select(m.AuditLog).where(m.AuditLog.actor==values['actor'],m.AuditLog.request_key==values['request_key']))
        if task and values['status']=='confirmed' and not existing:
            claim=session.get(m.Claim,task.claim_id)
            lock(session,'adoption:'+str(claim.vulnerability_id)+':'+claim.predicate+':'+claim.scope_key)
            if claim.claim_type.isupper():
                evidence=list(session.scalars(select(m.Evidence).where(m.Evidence.id.in_(values['evidence_ids']),m.Evidence.claim_id==claim.id,m.Evidence.stance=='support')))
                if not any(canonical_value(claim.claim_type,e.observed_value or {})==canonical_value(claim.claim_type,values['value'] or {}) for e in evidence):
                    raise ValueError('Chosen typed value lacks matching supporting evidence')
            if task.revision==values['expected_revision'] and claim.revision==values['expected_claim_revision'] and task.status not in ('resolved','cancelled'):
                for prior in session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==claim.vulnerability_id,m.Claim.predicate==claim.predicate,
                    m.Claim.scope_key==claim.scope_key,m.Claim.adopted.is_(True),m.Claim.id!=claim.id).with_for_update()):
                    before={'adopted':True,'value':prior.value_json,'claim_revision':prior.revision}
                    prior.adopted=False;session.flush()
                    session.add(m.AuditLog(actor=values['actor'],action='claim_adoption_replaced',claim_id=prior.id,
                        review_task_id=task.id,before_state=before,after_state={**before,'adopted':False,'replacement_claim_id':str(claim.id)},
                        reason=values['reason'],occurred_at=__import__('app.utils.time',fromlist=['utcnow']).utcnow(),
                        request_key='replace:'+digest([values['request_key'],str(prior.id)]),request_hash=digest([values['actor'],values['request_key'],str(prior.id),str(claim.id)])))
        audit=record_review(session,**values)
        claim=session.get(m.Claim,audit.claim_id)
        if audit.after_state['review_status']=='resolved':
            for conflict in session.scalars(select(m.ConflictRecord).where(m.ConflictRecord.review_task_id==audit.review_task_id,m.ConflictRecord.status=='open')):
                conflict.status='resolved';conflict.resolution={'status':values['status'],'value':values['value'],'reason':values['reason']}
                conflict.resolved_at=audit.occurred_at;conflict.resolved_by=audit.actor
            emit(session,claim.vulnerability_id,'REVIEW_RESOLVED',str(audit.id),'An analyst resolved a review with an audited reason',
                claim=claim,payload={'review_id':str(audit.review_task_id),'audit_id':str(audit.id),'verification_result_id':str(audit.verification_result_id)},now=audit.occurred_at)
            if audit.verification_result_id:emit(session,claim.vulnerability_id,'VERIFICATION_CHANGED',str(audit.verification_result_id),
                'Human review appended a verification result',claim=claim,payload={'method':'human_review','status':audit.after_state['verification_status']},now=audit.occurred_at)
        session.flush();return audit

"""One atomic round claim; immutable parent, separately versioned publication."""
from copy import deepcopy
from contextlib import contextmanager
from uuid import UUID,uuid4,uuid5,NAMESPACE_URL
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from app.enrichment.repository import lock
from app.agents.contracts import fingerprint
from app.orchestration.contracts import InvestigationContext,InvestigationResult,InvestigationPolicy
from app.orchestration.store import PostgresInvestigationStore,status_snapshot
from app.orchestration.lifecycle import transition
from app.orchestration.supplement.contracts import (TYPE,NS,VERSION,SupplementRecord,SupplementSummary,TERMINAL)
from app.orchestration.supplement.policy import inventory,BatchRepository
from app.utils.time import utcnow

INTENT=TYPE+'-cancel'
DECISION=TYPE+'-decision'

def parent_lock(db,parent):
    lock(db,TYPE+':parent:'+str(parent))


def tool_count(db,ids):
    return db.scalar(select(func.count()).select_from(m.ToolCallRecord).where(m.ToolCallRecord.agent_run_id.in_(tuple(ids)))) if ids else 0

def runs(context):
    return tuple(x for x in (context.investigation_run_id,context.verification_run_id,context.analysis_run_id) if x)

class SupplementStore:
    def __init__(self,engine):self.engine=engine;self.policy=InvestigationPolicy()

    def _decode(self,row,actor):
        if row is None or row.actor_principal!=actor or row.agent_type!=TYPE:raise LookupError('Supplement unavailable')
        ns=row.details[NS];raw=deepcopy(ns['record'])
        if fingerprint(raw)!=ns['hash']:raise ValueError('SUPPLEMENT_INTEGRITY_INVALID')
        record=SupplementRecord.model_validate({**raw,'worker_token':ns['worker_token']})
        if (record.summary.supplement_id!=row.id or record.context.owner!=actor or
                record.original.context.owner!=actor or
                record.context.logical_investigation_id!=record.spec.parent_investigation_id or
                record.context.original_request!=record.original.context.original_request or
                record.context.resolved_scope!=record.original.context.resolved_scope or
                record.context.deadline_at!=record.original.context.deadline_at or
                record.context.investigation_run_id!=record.original.context.investigation_run_id or
                record.spec.parent_investigation_id!=record.original.context.logical_investigation_id):
            raise ValueError('SUPPLEMENT_BINDING_INVALID')
        return record

    def _save(self,db,row,record):
        record.summary=record.summary.model_copy(update={'heartbeat_at':utcnow()})
        raw=record.model_dump(mode='json');row.details={NS:{'record':raw,'hash':fingerprint(raw),'worker_token':str(record.worker_token)}}
        row.status='running' if record.summary.status not in TERMINAL else 'succeeded' if record.summary.status=='COMPLETED' else 'partial'
        row.finished_at=record.summary.finished_at;db.flush();return record

    def _row(self,db,parent,actor,locked=False):
        q=select(m.AgentRun).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==actor,
            m.AgentRun.details[NS]['record']['spec']['parent_investigation_id'].astext==str(parent))
        return db.scalar(q.with_for_update() if locked else q)

    def read(self,parent,actor):
        # Verify root ownership/integrity even if no supplement exists.
        original=PostgresInvestigationStore(self.engine).read(parent,actor=actor)
        with transaction(self.engine) as db:
            row=self._row(db,parent,actor)
            record=self._decode(row,actor) if row else None
            if record and record.original.context!=original:
                raise ValueError('SUPPLEMENT_PARENT_BINDING_INVALID')
            if record and record.summary.latest_result_version==2:
                from app.orchestration.answer_sources import AnswerSourcesLoader
                from app.orchestration.composer import AnswerComposer
                result=record.result
                if result is None or result.context!=record.context or record.summary.status!='COMPLETED':
                    raise ValueError('SUPPLEMENT_RESULT_BINDING_INVALID')
                source,gate,_=AnswerSourcesLoader(self.engine).load(result.context,actor=actor)
                expected=AnswerComposer().compose(result.context,source,gate,
                    answer_id=uuid5(NAMESPACE_URL,str(record.summary.supplement_id)+':answer-v2'))
                if expected!=result.answer or result.context.answer_id!=expected.answer_id:
                    raise ValueError('SUPPLEMENT_ANSWER_BINDING_INVALID')
            if record and record.summary.status not in TERMINAL and record.summary.heartbeat_at and (utcnow()-record.summary.heartbeat_at).total_seconds()>self.policy.lease_seconds:
                record.summary=record.summary.model_copy(update={'recovery_required':True})
            return record

    def cancelled(self,parent,actor):
        with transaction(self.engine) as db:
            return db.scalar(select(m.AgentRun.id).where(m.AgentRun.id==uuid5(NAMESPACE_URL,INTENT+':'+str(parent)),
                m.AgentRun.actor_principal==actor,m.AgentRun.agent_type==INTENT)) is not None

    def save_decision(self,summary,actor):
        parent=summary.parent_investigation_id
        PostgresInvestigationStore(self.engine).read(parent,actor=actor)
        with transaction(self.engine) as db:
            parent_lock(db,parent)
            id=uuid5(NAMESPACE_URL,DECISION+':'+str(parent));row=db.get(m.AgentRun,id)
            if row is None:
                raw=summary.model_dump(mode='json')
                db.add(m.AgentRun(id=id,actor_principal=actor,agent_type=DECISION,status='partial',
                    user_request='',context={'parent_investigation_id':str(parent)},started_at=utcnow(),finished_at=utcnow(),
                    details={'summary':raw,'hash':fingerprint(raw)}))

    def read_decision(self,parent,actor):
        PostgresInvestigationStore(self.engine).read(parent,actor=actor)
        with transaction(self.engine) as db:
            row=db.get(m.AgentRun,uuid5(NAMESPACE_URL,DECISION+':'+str(parent)))
            if row is None:return None
            if row.actor_principal!=actor or row.agent_type!=DECISION:raise PermissionError('DECISION_OWNER_MISMATCH')
            raw=row.details['summary']
            if fingerprint(raw)!=row.details['hash']:raise ValueError('DECISION_INTEGRITY_INVALID')
            return SupplementSummary.model_validate(raw)

    def _check_scope(self,record,actor):
        original=PostgresInvestigationStore(self.engine).read(record.spec.parent_investigation_id,actor=actor)
        if original.cancel_requested_at:raise ValueError('CANCELLED')
        if self.cancelled(record.spec.parent_investigation_id,actor):raise ValueError('CANCELLED')
        if original.integration_result_id!=record.spec.parent_integration_id:raise ValueError('PARENT_RESULT_CHANGED')
        if inventory(self.engine,original,actor).inventory_hash!=record.spec.inventory_hash:raise ValueError('INVENTORY_CHANGED')
        if record.spec.batch_id:
            batch=BatchRepository(self.engine).read(record.spec.batch_id,actor).response
            if batch.cancel_requested_at:raise ValueError('CANCELLED')
            if utcnow()>=batch.deadline_at:raise ValueError('DEADLINE_EXCEEDED')

    def claim(self,original,spec,actor):
        parent=spec.parent_investigation_id;id=uuid5(NAMESPACE_URL,str(parent)+':'+spec.gap_hash+':'+VERSION)
        with transaction(self.engine) as db:
            # Shared batch grant is more conservative: only one child obtains a round.
            lock(db,TYPE+':'+str(spec.batch_id or parent))
            parent_lock(db,parent)
            old=self._row(db,parent,actor,locked=True)
            if old:return self._decode(old,actor),False
            if spec.batch_id:
                used=db.scalar(select(m.AgentRun.id).where(m.AgentRun.agent_type==TYPE,
                    m.AgentRun.details[NS]['record']['spec']['batch_id'].astext==str(spec.batch_id)))
                if used:raise ValueError('BATCH_SUPPLEMENT_BUDGET_EXHAUSTED')
            now=utcnow();c=original.context
            value=c.model_dump(mode='python');value.update(current_stage='INVESTIGATING',overall_status='RUNNING',
                verification_run_id=None,analysis_run_id=None,artifact_references=(spec.source_artifact,),
                integration_result_id=None,gate_logical_investigation_id=None,gate_input_hash=None,objective_hash=None,
                answer_id=None,events=(),warnings=(),unresolved_items=(),finished_at=None,error_code=None,revision=c.revision,
                stage_keys={**c.stage_keys,'verification':f'supplement:{id}:verify','analysis':f'supplement:{id}:analysis',
                            'integration':f'supplement:{id}:integration'})
            context=InvestigationContext.model_validate(value)
            record=SupplementRecord(summary=SupplementSummary(supplement_id=id,parent_investigation_id=parent,
                parent_integration_id=spec.parent_integration_id,status='RUNNING',eligible=True,reason='TARGETED_EVIDENCE_LOOKUP',
                claim_ids=spec.claim_ids,started_at=now,deadline_at=c.deadline_at),spec=spec,original=original,
                context=context,worker_token=uuid4())
            self._check_scope(record,actor)
            if now>=c.deadline_at:raise ValueError('DEADLINE_EXCEEDED')
            if self._count(db,record)+len(spec.claim_ids)+2>32:raise ValueError('TOTAL_TOOL_BUDGET_EXHAUSTED')
            row=m.AgentRun(id=id,actor_principal=actor,agent_type=TYPE,user_request=c.original_request.user_query,
                context={'parent_investigation_id':str(parent)},started_at=now,status='running')
            db.add(row);return self._save(db,row,record),True

    def _count(self,db,record):
        ids=set(runs(record.original.context))|set(runs(record.context))
        if record.summary.acquisition_run_id:ids.add(record.summary.acquisition_run_id)
        if record.spec.batch_id:
            batch=BatchRepository(self.engine).read(record.spec.batch_id,record.context.owner).response
            for child in batch.items:
                if child.investigation_id:
                    ids.update(runs(PostgresInvestigationStore(self.engine).read(child.investigation_id,actor=record.context.owner)))
        return tool_count(db,ids)

    def guard(self,parent,actor,token,*,required_calls=0):
        record=self.read(parent,actor)
        if record is None or record.worker_token!=token:raise ValueError('WORKER_TOKEN_INVALID')
        if record.summary.status in TERMINAL:raise ValueError('ALREADY_TERMINAL')
        if record.summary.cancel_requested:raise ValueError('CANCELLED')
        if utcnow()>=record.context.deadline_at:raise ValueError('DEADLINE_EXCEEDED')
        self._check_scope(record,actor)
        with transaction(self.engine) as db:
            if self._count(db,record)+required_calls>32:raise ValueError('TOTAL_TOOL_BUDGET_EXHAUSTED')
        return record

    def mutate(self,parent,actor,token,fn):
        with transaction(self.engine) as db:
            parent_lock(db,parent)
            row=self._row(db,parent,actor,locked=True);record=self._decode(row,actor)
            if record.worker_token!=token:raise ValueError('WORKER_TOKEN_INVALID')
            fn(record);record.revision+=1
            return self._save(db,row,record)

    def cancel(self,parent,actor):
        PostgresInvestigationStore(self.engine).read(parent,actor=actor)
        with transaction(self.engine) as db:
            # Same boundary as Runtime creation: an admitted step commits before
            # cancellation, or its admission check observes committed cancellation.
            lock(db,TYPE+':creation:'+actor+':'+str(parent))
            parent_lock(db,parent)
            id=uuid5(NAMESPACE_URL,INTENT+':'+str(parent))
            if db.get(m.AgentRun,id) is None:
                db.add(m.AgentRun(id=id,actor_principal=actor,agent_type=INTENT,status='cancelled',
                    user_request='',context={'parent_investigation_id':str(parent)},started_at=utcnow(),finished_at=utcnow(),details={}))
            row=self._row(db,parent,actor,locked=True)
            if row:
                record=self._decode(row,actor)
                if record.summary.status not in TERMINAL:
                    record.summary=record.summary.model_copy(update={'cancel_requested':True})
                    return self._save(db,row,record)

    def stop(self,parent,actor,token,reason):
        def finish(r):
            if r.summary.status in TERMINAL:return
            cancelled=r.summary.cancel_requested or reason=='CANCELLED'
            error=reason in ('SUPPLEMENT_FAILED','ACCESS_DENIED','CONTROL_STORE_FAILED','WORKER_TOKEN_INVALID')
            r.summary=r.summary.model_copy(update={'status':'CANCELLED' if cancelled else 'FAILED' if error else 'STOPPED',
                'error_code':reason if error else None,
                'reason':'CANCELLED' if cancelled else reason,'finished_at':utcnow()})
        return self.mutate(parent,actor,token,finish)

    def publish(self,parent,actor,token,answer):
        self.guard(parent,actor,token)
        def finish(r):
            self._check_scope(r,actor)
            if r.summary.cancel_requested:raise ValueError('CANCELLED')
            if r.summary.status in TERMINAL or utcnow()>=r.context.deadline_at:raise ValueError('STALE_PUBLICATION')
            from app.orchestration.answer_sources import AnswerSourcesLoader
            source,gate,_=AnswerSourcesLoader(self.engine).load(r.context,actor=actor)
            from app.orchestration.composer import AnswerComposer
            expected=AnswerComposer().compose(r.context,source,gate,
                answer_id=uuid5(NAMESPACE_URL,str(r.summary.supplement_id)+':answer-v2'))
            if r.context.current_stage!='COMPOSING' or answer!=expected:
                raise ValueError('ANSWER_BINDING_INVALID')
            confirmed=tuple(a.claim.claim_id for a in source.verification.claims
                if a.status=='CONFIRMED' and a.claim.claim_id in r.spec.claim_ids and
                set(a.supporting_evidence_ids)&set(r.summary.new_evidence_ids))
            state={'COMPLETE':('COMPLETED','SUCCEEDED'),'COMPLETE_WITH_WARNINGS':('COMPLETED','SUCCEEDED_WITH_WARNINGS'),
                'INCOMPLETE':('COMPLETED','INCOMPLETE'),'REVIEW_REQUIRED':('WAITING_REVIEW','REVIEW_REQUIRED'),'FAILED':('FAILED','FAILED')}
            from app.orchestration.contracts import StageEvent
            stage,status=state[answer.answer_status]
            r.context=transition(r.context,StageEvent(stage=stage,code='SUPPLEMENT_ANSWER_STORED',overall_status=status))
            r.context=r.context.model_copy(update={'answer_id':answer.answer_id,'warnings':answer.warnings,'unresolved_items':answer.unresolved_items})
            r.result=InvestigationResult(context=r.context,status=status_snapshot(r.context,{'lease_expires_at':utcnow().isoformat()}),answer=answer)
            # Atomic publication: result body/refs and latest pointer share one commit.
            r.summary=r.summary.model_copy(update={'status':'COMPLETED','reason':'REVALIDATED_WITH_NEW_EVIDENCE',
                'resolved_claim_ids':confirmed,'latest_result_version':2,'result_version':2,'finished_at':utcnow()})
        return self.mutate(parent,actor,token,finish)

    @contextmanager
    def creation_guard(self,parent,actor):
        with transaction(self.engine) as db:
            lock(db,TYPE+':creation:'+actor+':'+str(parent))
            yield

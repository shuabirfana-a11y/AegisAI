"""One owner/type-bound root audit; short atomic claims, no business table writes."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime,timedelta
from uuid import UUID,uuid4
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.enrichment.repository import lock
from app.assistant.storage import IdempotencyConflict
from app.agents.contracts import fingerprint
from app.runtime.contracts import json_bytes
from app.utils.time import utcnow
from app.orchestration.contracts import (TYPE,NAMESPACE,InvestigationContext,InvestigationStatus,
    InvestigationPolicy,ClaimReceipt,capture_request,request_fingerprint,valid_actor,stage_key,TERMINAL_STAGES)
from app.orchestration.scope import resolve_scope
from app.orchestration.lifecycle import transition

LIMIT=2*1024*1024
UPDATES=frozenset({'planner_run_id','investigation_run_id','verification_run_id','analysis_run_id',
    'artifact_references','integration_result_id','gate_logical_investigation_id','gate_input_hash',
    'objective_hash','warnings','unresolved_items','cancel_observed_at','error_code','answer_id'})


def _row(db,id,actor,*,locked=False):
    valid_actor(actor)
    query=select(m.AgentRun).where(m.AgentRun.id==UUID(str(id)),m.AgentRun.actor_principal==actor,m.AgentRun.agent_type==TYPE)
    row=db.scalar(query.with_for_update() if locked else query)
    if row is None:raise LookupError('Investigation not available')
    return row


def decode(row,actor):
    ns=deepcopy(row.details.get(NAMESPACE) or {})
    context=InvestigationContext.model_validate(ns['context'])
    if (row.id!=context.logical_investigation_id or row.agent_type!=TYPE or
            row.actor_principal!=actor or context.owner!=actor):raise ValueError('ORCHESTRATION_AUDIT_IDENTITY_INVALID')
    if ns['context_hash']!=fingerprint(context.model_dump(mode='json')):raise ValueError('ORCHESTRATION_AUDIT_HASH_INVALID')
    if (ns['request_key']!=context.original_request.request_key or ns['request_hash']!=context.request_hash
        or ns['scope_hash']!=fingerprint(context.resolved_scope.model_dump(mode='json'))):
        raise ValueError('ORCHESTRATION_AUDIT_BINDING_INVALID')
    expected=resolve_scope(context.original_request,actor=actor)
    if fingerprint(expected.model_dump(mode='json'))!=ns['scope_hash']:raise ValueError('ORCHESTRATION_AUDIT_SCOPE_INVALID')
    return context,ns


def _save(row,context,ns):
    ns={**ns,'context':context.model_dump(mode='json'),'context_hash':fingerprint(context.model_dump(mode='json'))}
    details={NAMESPACE:ns};json_bytes(details,LIMIT);row.details=details
    row.status=({'SUCCEEDED':'succeeded','SUCCEEDED_WITH_WARNINGS':'succeeded','INCOMPLETE':'partial',
                 'REVIEW_REQUIRED':'partial','FAILED':'timeout' if context.error_code=='DEADLINE_EXCEEDED' else 'failed',
                 'CANCELLED':'cancelled'}.get(context.overall_status,'queued' if context.current_stage=='CREATED' else 'running'))
    row.finished_at=context.finished_at
    if context.finished_at:row.duration_ms=max(0,int((context.finished_at-context.created_at).total_seconds()*1000))
    row.result_summary=context.overall_status;row.error_summary=context.error_code


def status_snapshot(context,ns):
    orphan=context.current_stage not in TERMINAL_STAGES and datetime.fromisoformat(ns['lease_expires_at'])<utcnow()
    return InvestigationStatus(logical_investigation_id=context.logical_investigation_id,current_stage=context.current_stage,
        overall_status=context.overall_status,planner_run_id=context.planner_run_id,
        investigation_run_id=context.investigation_run_id,verification_run_id=context.verification_run_id,
        analysis_run_id=context.analysis_run_id,cancel_requested=context.cancel_requested_at is not None,
        recovery_required=orphan,warnings=context.warnings,error_code=context.error_code,
        revision=context.revision,updated_at=context.updated_at)


class PostgresInvestigationStore:
    def __init__(self,engine,*,policy=None):self.engine=engine;self.policy=policy or InvestigationPolicy()

    def claim(self,request,*,actor):
        valid_actor(actor);request=capture_request(request);rh=request_fingerprint(request)
        with transaction(self.engine) as db:
            lock(db,TYPE+':'+actor+':'+request.request_key)
            old=db.scalar(select(m.AgentRun).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==actor,
                m.AgentRun.details[NAMESPACE]['request_key'].astext==request.request_key))
            if old:
                context,ns=decode(old,actor)
                if rh!=ns['request_hash']:raise IdempotencyConflict('Investigation key has different request content')
                return ClaimReceipt(logical_id=context.logical_investigation_id,fresh=False,context=context)
            scope=resolve_scope(request,actor=actor);id=uuid4();token=uuid4();now=utcnow()
            duration=min(self.policy.timeout_seconds,request.investigation_options.timeout_seconds)
            context=InvestigationContext(logical_investigation_id=id,owner=actor,original_request=request,
                request_hash=rh,resolved_scope=scope,created_at=now,updated_at=now,deadline_at=now+timedelta(seconds=duration),
                stage_keys={stage:stage_key(id,stage) for stage in ('planner','verification','analysis','integration')})
            ns={'request_key':request.request_key,'request_hash':rh,'scope_hash':fingerprint(scope.model_dump(mode='json')),
                'worker_token':str(token),'lease_expires_at':(now+timedelta(seconds=self.policy.lease_seconds)).isoformat(),
                'heartbeat_at':now.isoformat(),'answer':None,'answer_hash':fingerprint(None)}
            row=m.AgentRun(id=id,actor_principal=actor,agent_type=TYPE,user_request=request.user_query,
                context={'audit_kind':TYPE,'logical_investigation_id':str(id)},status='queued',started_at=now)
            _save(row,context,ns);db.add(row);db.flush()
            return ClaimReceipt(logical_id=id,fresh=True,context=context,worker_token=token)

    def read(self,id,*,actor):
        with transaction(self.engine) as db:return decode(_row(db,id,actor),actor)[0]

    def read_audit(self,id,*,actor):
        with transaction(self.engine) as db:return decode(_row(db,id,actor),actor)

    def status(self,id,*,actor):
        context,ns=self.read_audit(id,actor=actor)
        return status_snapshot(context,ns)

    def advance(self,id,*,actor,worker_token,expected_revision,event,**updates):
        if set(updates)-UPDATES:raise ValueError('IMMUTABLE_CONTEXT_FIELD')
        with transaction(self.engine) as db:
            row=_row(db,id,actor,locked=True);ctx,ns=decode(row,actor)
            if ns['worker_token']!=str(worker_token):raise ValueError('WORKER_TOKEN_INVALID')
            if ctx.revision!=expected_revision:raise ValueError('STALE_REVISION')
            ctx=transition(ctx,event)
            value=ctx.model_dump(mode='python');value.update(updates);ctx=InvestigationContext.model_validate(value)
            _save(row,ctx,ns);return ctx

    @contextmanager
    def creation_guard(self,id,*,actor):
        # Cancel uses this same lock. Runtime creation commits before cancellation
        # or is rejected after cancellation; no row lock held across child sessions.
        with transaction(self.engine) as db:
            lock(db,TYPE+':creation:'+actor+':'+str(id))
            _row(db,id,actor)
            yield

    def request_cancel(self,id,*,actor):
        with transaction(self.engine) as db:
            lock(db,TYPE+':creation:'+actor+':'+str(id))
            row=_row(db,id,actor,locked=True);ctx,ns=decode(row,actor)
            if ctx.current_stage not in TERMINAL_STAGES and ctx.cancel_requested_at is None:
                value=ctx.model_dump(mode='json');now=utcnow()
                value.update(cancel_requested_at=now,updated_at=now,revision=ctx.revision+1)
                ctx=InvestigationContext.model_validate(value);_save(row,ctx,ns)
        return self.status(id,actor=actor)

    def heartbeat(self,id,*,actor,worker_token):
        with transaction(self.engine) as db:
            row=_row(db,id,actor,locked=True);ctx,ns=decode(row,actor)
            if ns['worker_token']!=str(worker_token):raise ValueError('WORKER_TOKEN_INVALID')
            if ctx.current_stage in TERMINAL_STAGES:return
            now=utcnow();ns.update(heartbeat_at=now.isoformat(),lease_expires_at=(now+timedelta(seconds=self.policy.lease_seconds)).isoformat())
            _save(row,ctx,ns)

    def seal(self,id,*,actor,worker_token,expected_revision,answer):
        """Publish answer and terminal state in one transaction; cancel wins first."""
        from app.orchestration.answer_contracts import AnswerEnvelope
        from app.orchestration.contracts import StageEvent
        answer=AnswerEnvelope.model_validate_json(answer.model_dump_json())
        with transaction(self.engine) as db:
            row=_row(db,id,actor,locked=True);ctx,ns=decode(row,actor)
            if ns['worker_token']!=str(worker_token):raise ValueError('WORKER_TOKEN_INVALID')
            if ctx.cancel_requested_at is not None:raise ValueError('CANCELLED')
            if utcnow()>=ctx.deadline_at:raise ValueError('DEADLINE_EXCEEDED')
            if ctx.revision!=expected_revision:raise ValueError('STALE_REVISION')
            if ctx.current_stage!='COMPOSING':raise ValueError('ANSWER_STAGE_INVALID')
            if (answer.logical_investigation_id!=ctx.logical_investigation_id or
                answer.integration_result_id!=ctx.integration_result_id or answer.original_question!=ctx.original_request.user_query):
                raise ValueError('ANSWER_IDENTITY_INVALID')
            mapping={'COMPLETE':('COMPLETED','SUCCEEDED'),'COMPLETE_WITH_WARNINGS':('COMPLETED','SUCCEEDED_WITH_WARNINGS'),
                'INCOMPLETE':('COMPLETED','INCOMPLETE'),'REVIEW_REQUIRED':('WAITING_REVIEW','REVIEW_REQUIRED'),'FAILED':('FAILED','FAILED')}
            stage,status=mapping[answer.answer_status]
            ctx=transition(ctx,StageEvent(stage=stage,code='ANSWER_STORED',overall_status=status))
            raw=ctx.model_dump(mode='json');raw.update(answer_id=answer.answer_id,warnings=answer.warnings,
                unresolved_items=answer.unresolved_items,error_code='GATE_FAILED' if status=='FAILED' else None)
            ctx=InvestigationContext.model_validate(raw)
            ns.update(answer=answer.model_dump(mode='json'),answer_hash=fingerprint(answer.model_dump(mode='json')))
            _save(row,ctx,ns);return ctx

    def seal_stop(self,id,*,actor,worker_token,code):
        from app.orchestration.composer import AnswerComposer
        from app.orchestration.contracts import StageEvent
        with transaction(self.engine) as db:
            row=_row(db,id,actor,locked=True);ctx,ns=decode(row,actor)
            if ns['worker_token']!=str(worker_token):raise ValueError('WORKER_TOKEN_INVALID')
            if ctx.current_stage in TERMINAL_STAGES:return ctx
            cancelled=ctx.cancel_requested_at is not None or code=='CANCELLED'
            code='CANCELLED' if cancelled else code
            ctx=transition(ctx,StageEvent(stage='CANCELLED' if cancelled else 'FAILED',code='STOP',
                overall_status='CANCELLED' if cancelled else 'FAILED'))
            raw=ctx.model_dump(mode='json');raw.update(error_code=code,cancel_observed_at=utcnow() if cancelled else None)
            ctx=InvestigationContext.model_validate(raw)
            answer=AnswerComposer().failure(ctx,code=code,cancelled=cancelled)
            ctx=InvestigationContext.model_validate({**ctx.model_dump(mode='json'),'answer_id':answer.answer_id})
            ns.update(answer=answer.model_dump(mode='json'),answer_hash=fingerprint(answer.model_dump(mode='json')))
            _save(row,ctx,ns);return ctx

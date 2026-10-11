"""Atomic acceptance of validated revisions, using the existing audit/lock.

All entry points must use this actor/key advisory lock. No database migration or
claim/asset/review write. Independent source sessions require fingerprint recheck.
Failed captures record each attempt; only validated equal inputs reuse a revision.
"""
import time
from uuid import UUID,uuid4,uuid5,NAMESPACE_URL
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.enrichment.repository import lock
from app.assistant.storage import IdempotencyConflict
from app.agents.contracts import fingerprint
from app.integration.contracts import IntegrationContext,IntegrationResult,IntegrationTrace,POLICY_VERSION
from app.integration.rules_common import check
from app.integration.trace import build_integration_trace
from app.runtime.contracts import json_bytes,METADATA_LIMIT
from app.utils.time import utcnow

TYPE='integration-gate-v1'

def failure_context(request,actor,code,*,id=None):
    now=utcnow();id=id or uuid4();oh=fingerprint(None)
    return IntegrationContext(integration_id=id,logical_investigation_id=uuid5(NAMESPACE_URL,fingerprint([actor,str(request.run_id),oh])),
        owner=actor,request=request,objective_hash=oh,evaluation_time=now,
        input_hash=fingerprint({'request':request.model_dump(mode='json'),'failure':code,'policy':POLICY_VERSION}),
        capture_checks=(check('integrity',code,'Acceptance stopped; no trusted business result','FATAL'),))

def decode(row,actor):
    ns=row.details['integration_v1'];context=IntegrationContext.model_validate(ns['context'])
    result=IntegrationResult.model_validate(ns['result']);trace=IntegrationTrace.model_validate(ns['trace'])
    if (context.owner!=actor or row.actor_principal!=actor or row.agent_type!=TYPE or
        context.integration_id!=row.id or result.integration_id!=row.id or trace.integration_id!=row.id or
        context.policy_version!=POLICY_VERSION or result.policy_version!=POLICY_VERSION or trace.rule_version!=POLICY_VERSION):raise ValueError('INTEGRATION_AUDIT_IDENTITY_INVALID')
    for key,value in (('context',context),('result',result),('trace',trace)):
        if ns[key+'_hash']!=fingerprint(value.model_dump(mode='json')):raise ValueError('INTEGRATION_AUDIT_HASH_INVALID')
    if (ns['request_hash']!=fingerprint(context.request.model_dump(mode='json')) or ns['input_hash']!=context.input_hash
        or ns['request_key']!=context.request.request_key or result.input_hash!=context.input_hash):raise ValueError('INTEGRATION_AUDIT_BINDING_INVALID')
    from app.integration.evaluator import IntegrationGateEvaluator
    expected=IntegrationGateEvaluator().evaluate(context)
    if expected!=result or build_integration_trace(context,result,trace.execution_time_ms)!=trace:raise ValueError('INTEGRATION_AUDIT_RESULT_INVALID')
    return context,result,trace

class PostgresIntegrationStore:
    def __init__(self,engine):self.engine=engine

    def evaluate_once(self,request,*,actor,loader,evaluator,control):
        started=time.monotonic();request_hash=fingerprint(request.model_dump(mode='json'))
        with transaction(self.engine) as db:
            lock(db,TYPE+':'+actor+':'+request.request_key)
            rows=list(db.scalars(select(m.AgentRun).where(m.AgentRun.agent_type==TYPE,m.AgentRun.actor_principal==actor,
                m.AgentRun.details['integration_v1']['request_key'].astext==request.request_key)))
            existing=[decode(row,actor) for row in rows]
            if any(fingerprint(c.request.model_dump(mode='json'))!=request_hash for c,_,_ in existing):raise IdempotencyConflict('Integration key has different request content')
            try:
                control.check()
                context=loader.capture(request,actor=actor)
                control.check()
                # Cache only after current formal receipts and input fingerprints
                # have been checked. New source versions produce a new revision.
                for old,result,_ in existing:
                    if old.input_hash==context.input_hash:
                        control.check();return result
                result=evaluator.evaluate(context)
                control.check()
                if loader.recheck(context)!=context.source_fingerprints:raise ValueError('SOURCE_CHANGED_DURING_EVALUATION')
                control.check()
            except IdempotencyConflict:raise
            except Exception as exc:
                from app.integration.service import GateAbort
                code=exc.code if isinstance(exc,GateAbort) else 'SOURCE_INPUT_INVALID' if isinstance(exc,(LookupError,ValueError,KeyError,TypeError)) else 'GATE_EXECUTION_FAILED'
                context=failure_context(request,actor,code)
                result=evaluator.evaluate(context)
            trace=build_integration_trace(context,result,int((time.monotonic()-started)*1000))
            ns={'request_key':request.request_key,'request_hash':request_hash,'input_hash':context.input_hash,
                'context':context.model_dump(mode='json'),'result':result.model_dump(mode='json'),'trace':trace.model_dump(mode='json')}
            for key in ('context','result','trace'):ns[key+'_hash']=fingerprint(ns[key])
            details={'integration_v1':ns};json_bytes(details,METADATA_LIMIT)
            row=m.AgentRun(id=result.integration_id,actor_principal=actor,agent_type=TYPE,user_request='Deterministic Integration Gate acceptance audit',
                context={'audit_kind':TYPE,'logical_investigation_id':str(result.logical_investigation_id)},
                status='succeeded' if result.status in ('PASS','PASS_WITH_WARNINGS') else 'partial' if result.status in ('REPLAN_REQUIRED','HUMAN_REVIEW_REQUIRED') else 'failed',
                started_at=context.evaluation_time,finished_at=utcnow(),duration_ms=trace.execution_time_ms,
                result_summary=result.status,error_summary=','.join(trace.error_codes) or None,details=details)
            db.add(row);db.flush()
            # This check is deliberately after flush: transaction rollback prevents
            # a late cancellation from committing a success receipt.
            if result.status in ('PASS','PASS_WITH_WARNINGS'):control.check()
        return result

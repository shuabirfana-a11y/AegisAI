"""Actor/type-scoped private Planner audit in existing AgentRun JSON namespace."""
from copy import deepcopy
from functools import wraps
from uuid import UUID, uuid4
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.enrichment.repository import digest, lock
from app.assistant.storage import IdempotencyConflict
from app.runtime.store import StoreFailure
from app.runtime.contracts import json_bytes, METADATA_LIMIT
from app.planner.schemas import (PlannerInput, PlannerSnapshot, PlannerRunTrace,
                                 PlannerAttempt, ModelIdentity)
from app.utils.time import utcnow

def safe(method):
    @wraps(method)
    def wrapped(*args,**kwargs):
        try:return method(*args,**kwargs)
        except (LookupError,IdempotencyConflict,StoreFailure):raise
        except Exception as exc:raise StoreFailure('STORE_FAILED: planner persistence failed') from exc
    return wrapped

def row_for(session,id,actor,locked=False):
    q=select(m.AgentRun).where(m.AgentRun.id==UUID(str(id)),m.AgentRun.agent_type=='planner-v1',
                              m.AgentRun.actor_principal==actor)
    row=session.scalar(q.with_for_update() if locked else q)
    if row is None:raise LookupError('Planner run not found')
    return row

def snapshot(row):
    ns=row.details['planner_v1']
    return PlannerSnapshot(planner_run_id=row.id,trace_id=row.details['trace_id'],
        planning_status=ns['validation_status'],runtime_run_id=ns.get('runtime_run_id'),
        runtime_status=ns.get('runtime_status'))

def save(row,details):
    json_bytes(details,METADATA_LIMIT)
    row.details=details

class PlannerTraceStore:
    def __init__(self,engine):self.engine=engine

    @safe
    def create(self,input,actor,policy,*,model_identity,prompt_version,registry_version):
        if not isinstance(actor,str) or not 1<=len(actor)<=150:raise ValueError('Authenticated actor required')
        captured=PlannerInput.model_validate_json(input.model_dump_json());key=captured.query.request_key
        fingerprint=digest({'input':captured.model_dump(mode='json'),'policy':policy.model_dump(mode='json'),
            'model':model_identity.model_dump(mode='json'),'prompt_version':prompt_version,'registry_version':registry_version})
        with transaction(self.engine) as db:
            lock(db,'planner-v1:'+actor+':'+key)
            old=db.scalar(select(m.AgentRun).where(m.AgentRun.agent_type=='planner-v1',m.AgentRun.actor_principal==actor,
                m.AgentRun.details['planner_v1']['request_key'].astext==key))
            if old:
                if old.details['planner_v1']['request_hash']!=fingerprint:raise IdempotencyConflict('Planner key has different content')
                return snapshot(old),False
            id=uuid4();trace_id=uuid4()
            details={'trace_id':str(trace_id),'ui_status':'PLANNING','events':[],'plan':[],'result':None,
                'planner_v1':{'request_key':key,'request_hash':fingerprint,'user_query':captured.query.question,
                    'model':model_identity.model_dump(mode='json'),'prompt_version':prompt_version,
                    'registry_version':registry_version,'validation_status':'PLANNING','generated_plan':None,
                    'retry_count':0,'latency':0.0,'error':[],'attempts':[],'validated_plan':None,
                    'runtime_run_id':None,'runtime_status':None}}
            row=m.AgentRun(id=id,agent_type='planner-v1',actor_principal=actor,user_request=captured.query.question,
                context={'planner_version':'planner-v1','planner_input_v1':captured.model_dump(mode='json'),
                         'planner_input_sha256':digest(captured.model_dump(mode='json'))},
                status='running',started_at=utcnow(),details=details)
            db.add(row);db.flush();return snapshot(row),True

    @safe
    def record_attempt(self,context,attempt):
        # Private diagnostics stay in planner_v1; never the legacy result/events.
        attempt=PlannerAttempt.model_validate_json(attempt.model_dump_json())
        with transaction(self.engine) as db:
            row=row_for(db,context.planner_run_id,context.actor,True)
            details=deepcopy(row.details);ns=details['planner_v1']
            if ns['validation_status']!='PLANNING':raise ValueError('Planning already terminal')
            if attempt.attempt_index!=len(ns['attempts'])+1:raise ValueError('Attempt order mismatch')
            if attempt.model_call['trace_id']!=str(context.trace_id) or row.details['trace_id']!=str(context.trace_id):
                raise ValueError('Attempt trace mismatch')
            ns['attempts'].append(attempt.model_dump(mode='json'))
            ns['retry_count']=len(ns['attempts'])-1
            ns['latency']=sum(a['model_call']['duration_ms'] for a in ns['attempts'])
            ns['error']=[e.model_dump(mode='json') for e in attempt.issues]
            save(row,details)

    @safe
    def complete(self,planner_id,actor,outcome):
        with transaction(self.engine) as db:
            row=row_for(db,planner_id,actor,True);details=deepcopy(row.details);ns=details['planner_v1']
            if ns['validation_status']!='PLANNING':return snapshot(row)
            attempts=[a.model_dump(mode='json') for a in outcome.attempts]
            if outcome.status=='VALIDATED' and attempts!=ns['attempts']:raise ValueError('Unsaved successful audit')
            if outcome.status=='PLANNING_FAILED' and len(attempts)>=len(ns['attempts']):ns['attempts']=attempts
            ns['validation_status']=outcome.status
            ns['validated_plan']=outcome.validated_plan.model_dump(mode='json') if outcome.validated_plan else None
            ns['generated_plan']=__import__('json').loads(outcome.validated_plan.candidate_json) if outcome.validated_plan else None
            ns['retry_count']=max(0,len(ns['attempts'])-1)
            ns['latency']=sum(a['model_call']['duration_ms'] for a in ns['attempts'])
            ns['error']=[e.model_dump(mode='json') for e in outcome.issues]
            details['ui_status']='COMPLETED' if outcome.status=='VALIDATED' else 'FAILED'
            row.status='succeeded' if outcome.status=='VALIDATED' else 'failed'
            row.finished_at=utcnow();row.duration_ms=int(max(0,(row.finished_at-row.started_at).total_seconds()*1000))
            row.error_summary=','.join(e.code for e in outcome.issues) or None
            save(row,details);db.flush();return snapshot(row)

    @safe
    def link_runtime(self,planner_id,actor,runtime):
        with transaction(self.engine) as db:
            row=row_for(db,planner_id,actor,True);details=deepcopy(row.details);ns=details['planner_v1']
            runtime_row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==runtime.run_id,
                m.AgentRun.actor_principal==actor,m.AgentRun.agent_type=='runtime-v1'))
            if runtime_row is None or ns['validation_status']!='VALIDATED':raise ValueError('Unowned or unvalidated Runtime')
            if ns['runtime_run_id'] and ns['runtime_run_id']!=str(runtime.run_id):raise ValueError('Runtime link conflict')
            # A concurrent retry may carry an older pending snapshot. The Runtime
            # row is authoritative; never copy that stale status over a terminal link.
            ns.update(runtime_run_id=str(runtime_row.id),runtime_status=runtime_row.details['ui_status'])
            save(row,details);db.flush();return snapshot(row)

    @safe
    def read(self,planner_id,actor):
        with transaction(self.engine) as db:
            row=row_for(db,planner_id,actor);ns=row.details['planner_v1']
            return PlannerRunTrace(planner_run_id=row.id,trace_id=row.details['trace_id'],
                **{k:ns[k] for k in PlannerRunTrace.model_fields if k not in ('planner_run_id','trace_id')})

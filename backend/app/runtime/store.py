"""Reuse existing tables with actor/type-scoped idempotency and atomic snapshots.

No nested JSON is mutated in place: a complete replacement is written under a
row lock. Independent Sessions let concurrently finished tasks safely merge.
"""
from copy import deepcopy
from functools import wraps
from typing import Protocol
from uuid import UUID, uuid4
from sqlalchemy import select

from app.db import models as m
from app.db.session import transaction
from app.enrichment.repository import lock, digest
from app.assistant.storage import record_tool, IdempotencyConflict
from app.runtime.contracts import (TaskTrace, TaskArtifact, RunSnapshot, TraceSnapshot,
                                   METADATA_LIMIT, INPUT_LIMIT, json_bytes)
from app.runtime.trace import project
from app.utils.time import utcnow


class StoreFailure(RuntimeError):
    pass


def _safe(method):
    @wraps(method)
    def call(*args, **kwargs):
        try:return method(*args, **kwargs)
        except (LookupError, IdempotencyConflict, StoreFailure):raise
        except Exception as exc:
            raise StoreFailure('STORE_FAILED: runtime persistence failed') from exc
    return call


class RuntimeStore(Protocol):
    def create_run(self, request_data, plan, actor, request_key):...
    def save_task(self, run_id, task, artifact, trace, receipts):...
    def finish_run(self, run_id, outcome):...
    def read_trace(self, run_id, actor):...


def _row(session, run_id, actor=None, *, locked=False):
    query = select(m.AgentRun).where(m.AgentRun.id==UUID(str(run_id)),
                                    m.AgentRun.agent_type=='runtime-v1')
    if actor is not None:query=query.where(m.AgentRun.actor_principal==actor)
    if locked:query=query.with_for_update()
    row = session.scalar(query)
    if row is None:raise LookupError('Run not found')
    return row


def _snapshot(row):
    return RunSnapshot(run_id=row.id, trace_id=row.details['trace_id'],
                       status=row.details['ui_status'], result=row.details.get('result'))


class PostgresRuntimeStore:
    def __init__(self, engine):
        self.engine = engine

    @_safe
    def create_run(self, request_data, plan, actor, request_key):
        if not isinstance(request_key,str) or not 1 <= len(request_key) <= 150:
            raise ValueError('Invalid request key')
        json_bytes(request_data, INPUT_LIMIT)
        planned=plan.model_dump(mode='json')
        fingerprint=digest({'request':request_data,'plan':planned})
        with transaction(self.engine) as session:
            lock(session,'runtime-v1:'+actor+':'+request_key)
            old=session.scalar(select(m.AgentRun).where(m.AgentRun.actor_principal==actor,
                m.AgentRun.agent_type=='runtime-v1',
                m.AgentRun.details['runtime_v1']['request_key'].astext==request_key))
            if old:
                if old.details['runtime_v1']['request_hash']!=fingerprint:
                    raise IdempotencyConflict('Runtime request key has different content')
                return _snapshot(old),False
            run_id=uuid4();trace_id=uuid4()
            traces={t.task_id:TaskTrace(run_id=run_id,task_id=t.task_id,task_type=t.task_type,
                dependencies=t.dependencies).model_dump(mode='json') for t in plan.tasks}
            details={'trace_id':str(trace_id),'runtime_v1':{
                'request_key':request_key,'request_hash':fingerprint,'plan':planned,
                'traces':traces,'artifacts':{},'next_sequence':0}}
            details=project(details,'queued');json_bytes(details,METADATA_LIMIT)
            row=m.AgentRun(id=run_id,actor_principal=actor,
                user_request=str(request_data.get('question','Structured runtime plan'))[:2000],
                agent_type='runtime-v1',context={'runtime_version':'runtime-v1','query':request_data},
                status='queued',started_at=utcnow(),details=details)
            session.add(row);session.flush()
            return _snapshot(row),True

    @_safe
    def save_task(self, run_id, task, artifact, trace, receipts):
        if trace.run_id!=UUID(str(run_id)) or trace.task_id!=task.task_id:
            raise ValueError('Task trace identity mismatch')
        if artifact and (artifact.run_id!=trace.run_id or artifact.task_id!=task.task_id):
            raise ValueError('Task artifact identity mismatch')
        with transaction(self.engine) as session:
            row=_row(session,run_id,locked=True)
            if row.finished_at is not None:raise ValueError('Run already terminal')
            details=deepcopy(row.details);ns=details['runtime_v1']
            if task.task_id not in ns['traces']:raise ValueError('Unplanned task')
            if task.task_id in ns['artifacts']:raise ValueError('Task already terminal')
            calls=[]
            for receipt in receipts:
                ns['next_sequence']+=1
                record=record_tool(session,row.id,ns['next_sequence'],receipt.name,
                                   receipt.arguments,receipt.envelope,1)
                calls.append({'record_id':str(record.id),'sequence_no':record.sequence_no,
                              'call_index':receipt.call_index,'tool_name':receipt.name,
                              'status':receipt.envelope.status,'duration_ms':receipt.envelope.duration_ms})
            traced=trace.model_copy(update={'tools_called':calls or trace.tools_called})
            ns['traces'][task.task_id]=traced.model_dump(mode='json')
            if artifact:
                ns['artifacts'][task.task_id]=artifact.model_copy(update={'tool_calls':calls}).model_dump(mode='json')
            details=project(details,'running');json_bytes(details,METADATA_LIMIT)
            row.details=details;row.status='running'

    @_safe
    def finish_run(self, run_id, outcome):
        if outcome.run_id!=UUID(str(run_id)):raise ValueError('Run outcome identity mismatch')
        with transaction(self.engine) as session:
            row=_row(session,run_id,locked=True)
            if row.finished_at is not None:return _snapshot(row)
            if outcome.status not in ('succeeded','partial','failed','timeout'):
                raise ValueError('Unknown run state')
            if set(row.details['runtime_v1']['artifacts']) != {t['task_id'] for t in row.details['runtime_v1']['plan']['tasks']}:
                raise ValueError('Cannot finish incomplete run')
            details=project(row.details,outcome.status);json_bytes(details,METADATA_LIMIT)
            row.details=details;row.status=outcome.status;row.finished_at=utcnow()
            row.duration_ms=max(0,int((row.finished_at-row.started_at).total_seconds()*1000))
            row.result_summary='Structured runtime completed; inspect artifacts and uncertainty'
            row.error_summary='Runtime task failed' if outcome.status in ('failed','timeout') else None
            session.flush();return _snapshot(row)

    @_safe
    def read_trace(self, run_id, actor):
        with transaction(self.engine) as session:
            row=_row(session,run_id,actor);ns=row.details['runtime_v1']
            order=[t['task_id'] for t in ns['plan']['tasks']]
            return TraceSnapshot(run_id=row.id,trace_id=row.details['trace_id'],
                tasks=[TaskTrace.model_validate(ns['traces'][key]) for key in order],
                artifacts=[TaskArtifact.model_validate(ns['artifacts'][key]) for key in order if key in ns['artifacts']])

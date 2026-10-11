"""Controlled internal trace projections; no raw prompts or external excerpts."""
from typing import ClassVar
from uuid import UUID
from pydantic import AwareDatetime,Field
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.integration.contracts import Sized,ArtifactRef,Status
from app.planner.trace import PlannerTraceStore
from app.runtime.store import PostgresRuntimeStore
from app.orchestration.contracts import StageEvent


class PlannerSummary(Sized):
    planner_run_id: UUID
    validation_status: str
    retry_count: int
    prompt_version: str
    task_ids: tuple[str,...]=()


class ToolSummary(Sized):
    record_id: UUID
    task_id: str
    tool: str
    status: str
    duration_ms: float
    evidence_ids: tuple[str,...]=()


class AgentTrace(Sized):
    run_id: UUID
    status: str
    artifact_references: tuple[ArtifactRef,...]
    task_statuses: dict[str,str]
    tool_calls: tuple[ToolSummary,...]=Field(default=(),max_length=32)


class InvestigationTrace(Sized):
    size_limit: ClassVar[int]=1024*1024
    schema_version: str='investigation-trace-v1'
    logical_investigation_id: UUID
    original_question: str
    planner: PlannerSummary|None
    events: tuple[StageEvent,...]
    agent_runs: tuple[AgentTrace,...]=Field(max_length=3)
    integration_result_id: UUID|None
    integration_status: Status|None
    answer_id: UUID|None
    warnings: tuple[str,...]
    unresolved_items: tuple[str,...]
    error_code: str|None
    historical_snapshot: bool=True


def build_trace(store,result,*,actor):
    c=result.context;planner=None
    if c.planner_run_id:
        p=PlannerTraceStore(store.engine).read(c.planner_run_id,actor)
        # Runtime creation precedes Planner.link_runtime. A missing link during
        # execution (or a later link-write failure) is legitimate only when the
        # actual, owned Runtime plan provides the exact inverse Planner link.
        if p.runtime_run_id is not None and p.runtime_run_id!=c.investigation_run_id:
            raise ValueError('TRACE_PLANNER_RUN_MISMATCH')
        if p.runtime_run_id is None and c.investigation_run_id is not None:
            with transaction(store.engine) as db:
                row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==c.investigation_run_id,
                    m.AgentRun.agent_type=='runtime-v1',m.AgentRun.actor_principal==actor))
                if row is None:raise LookupError('Trace not available')
                backlink=row.details.get('runtime_v1',{}).get('plan',{}).get('route',{}).get('planner_run_id')
                if backlink!=str(c.planner_run_id):raise ValueError('TRACE_PLANNER_RUN_MISMATCH')
        planner=PlannerSummary(planner_run_id=p.planner_run_id,validation_status=p.validation_status,retry_count=p.retry_count,
            prompt_version=p.prompt_version,task_ids=tuple(t['task_id'] for t in p.generated_plan.get('tasks',[]) if 'task_id' in t) if p.generated_plan else ())
    runs=[]
    for id in (c.investigation_run_id,c.verification_run_id,c.analysis_run_id):
        if id is None:continue
        snapshot=PostgresRuntimeStore(store.engine).read_trace(id,actor)
        with transaction(store.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==id,m.AgentRun.agent_type=='runtime-v1',m.AgentRun.actor_principal==actor))
            if row is None:raise LookupError('Trace not available')
            status=row.status
            calls=[]
            for task in snapshot.tasks:
                for ref in task.tools_called:
                    record=db.scalar(select(m.ToolCallRecord).where(m.ToolCallRecord.id==UUID(ref['record_id']),m.ToolCallRecord.agent_run_id==id))
                    if record is None or record.tool_name!=ref['tool_name']:raise ValueError('TRACE_TOOL_REFERENCE_INVALID')
                    ids=tuple(str(e['evidence_id']) for e in record.output_summary.get('evidence_refs',[]) if e.get('evidence_id'))
                    calls.append(ToolSummary(record_id=record.id,task_id=task.task_id,tool=record.tool_name,
                        status=ref['status'],duration_ms=ref['duration_ms'],evidence_ids=ids))
        refs=tuple(r for r in c.artifact_references if r.run_id==id)
        if any(not any(a.task_id==r.task_id and a.artifact_id==r.artifact_id for a in snapshot.artifacts) for r in refs):
            raise ValueError('TRACE_ARTIFACT_REFERENCE_INVALID')
        runs.append(AgentTrace(run_id=id,status=status,artifact_references=refs,task_statuses={t.task_id:t.status for t in snapshot.tasks},tool_calls=tuple(calls)))
    return InvestigationTrace(logical_investigation_id=c.logical_investigation_id,original_question=c.original_request.user_query,
        planner=planner,events=c.events,agent_runs=tuple(runs),integration_result_id=c.integration_result_id,
        integration_status=result.answer.integration_status if result.answer else None,answer_id=c.answer_id,
        warnings=c.warnings,unresolved_items=c.unresolved_items,error_code=c.error_code)

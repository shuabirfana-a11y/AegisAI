"""Rebuild business artifacts exclusively from actor-owned execution snapshots."""
from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import AgentBinding,AgentFrameworkError,fingerprint
from app.agents.artifacts import AgentArtifact
from app.agents.investigation.roles import IMPLEMENTATION_KEY,REGISTRY_VERSION
from app.agents.investigation.normalize import normalize_investigation
from app.agents.investigation.schemas import InvestigationRunResult,InvestigationTaskTrace
from app.runtime.contracts import TaskPlan,TaskTrace,TaskArtifact,ToolReceipt,WorkerContext,ExecutionOutcome,TaskState
from app.runtime.executor import validate_receipts,validate_outcome
from app.tooling.contracts import ToolEnvelope

class InvestigationReader:
    def __init__(self,engine):self.engine=engine
    def read(self,run_id,actor):
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(str(run_id)),
                m.AgentRun.agent_type=='runtime-v1',m.AgentRun.actor_principal==actor))
            if row is None:raise LookupError('Run not found')
            ns=row.details['runtime_v1'];plan=TaskPlan.model_validate(ns['plan'])
            professional=plan.route.get('professional_agents_v1')
            if not professional or professional['registry']['registry_version']!=REGISTRY_VERSION:
                raise AgentFrameworkError('INVESTIGATION_TRACE_NOT_AVAILABLE')
            if fingerprint(professional['registry'])!=professional['registry_fingerprint']:
                raise AgentFrameworkError('AGENT_TRACE_INVALID')
            bindings={key:AgentBinding.model_validate(value) for key,value in professional['bindings'].items()}
            artifacts={key:TaskArtifact.model_validate(value) for key,value in ns['artifacts'].items()}
            ctx=WorkerContext(run_id=row.id,trace_id=UUID(row.details['trace_id']),actor=actor,deadline=1.0)
            projected=[];traces=[];blocked=[];required=[]
            for task in plan.tasks:
                trace=TaskTrace.model_validate(ns['traces'][task.task_id]);artifact=artifacts.get(task.task_id)
                if trace.run_id!=row.id or trace.task_id!=task.task_id:raise AgentFrameworkError('AGENT_TRACE_INVALID')
                if task.task_type=='input_required':required.append(task.task_id);continue
                binding=bindings.get(task.task_id)
                if binding is None or binding.implementation_key!=IMPLEMENTATION_KEY or binding.task_fingerprint!=fingerprint(task.model_dump(mode='json')):
                    raise AgentFrameworkError('AGENT_TRACE_INVALID')
                attempted=trace.start_time is not None and trace.status!=TaskState.BLOCKED
                calls=[];receipts=[]
                if artifact:
                    if artifact.run_id!=row.id or artifact.task_id!=task.task_id or trace.artifact_id!=artifact.artifact_id or trace.status!=artifact.status:
                        raise AgentFrameworkError('AGENT_TRACE_INVALID')
                    for ref in artifact.tool_calls:
                        record=db.scalar(select(m.ToolCallRecord).where(m.ToolCallRecord.id==UUID(ref['record_id']),m.ToolCallRecord.agent_run_id==row.id))
                        if record is None or record.sequence_no!=ref['sequence_no'] or record.tool_name!=ref['tool_name']:
                            raise AgentFrameworkError('AGENT_TRACE_INVALID')
                        env=ToolEnvelope.model_validate(record.output_summary)
                        if env.trace_id!=str(ctx.trace_id) or env.tool!=record.tool_name or env.status!=ref['status']:
                            raise AgentFrameworkError('AGENT_TRACE_INVALID')
                        receipts.append(ToolReceipt(call_index=ref['call_index'],name=record.tool_name,arguments=record.input_summary,
                            started_at=record.started_at,finished_at=record.finished_at,envelope=env))
                        calls.append({**ref,'start_time':record.started_at.isoformat(),'end_time':record.finished_at.isoformat()})
                traces.append(InvestigationTaskTrace(task_id=task.task_id,tools_called=calls,start_time=trace.start_time,
                    end_time=trace.end_time,status=trace.status,artifact_id=trace.artifact_id,attempted=attempted))
                if trace.status==TaskState.BLOCKED:blocked.append(task.task_id);continue
                if artifact is None:continue
                validate_receipts(task,ctx,receipts)
                outcome=validate_outcome(task,ctx,ExecutionOutcome(artifact=artifact,receipts=receipts))
                dependencies=tuple(AgentArtifact.from_task_artifact(artifacts[key],bindings[key]) for key in task.dependencies)
                projected.append(normalize_investigation(task,outcome,dependencies))
            return InvestigationRunResult(run_id=row.id,runtime_status=row.details['ui_status'],artifacts=tuple(projected),
                blocked_tasks=tuple(blocked),input_required_tasks=tuple(required),traces=tuple(traces))

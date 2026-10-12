"""Project immutable formal receipts, never live intelligence, into verification views."""
from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import AgentBinding,AgentFrameworkError,fingerprint
from app.agents.artifacts import AgentArtifact
from app.agents.router import AgentRouter
from app.agents.verification.context_store import VerificationContextStore
from app.agents.verification.registry import create_verification_registry
from app.agents.verification.roles import ROLES,REGISTRY_VERSION
from app.agents.verification.runtime import verification_plan
from app.agents.verification.schemas import VerificationAssessment,VerificationArtifact,VerificationRun,VerificationRunResult
from app.runtime.contracts import TaskPlan,TaskTrace,TaskArtifact,WorkerContext,ToolReceipt,ExecutionOutcome,TaskState
from app.runtime.executor import validate_outcome
from app.tooling.contracts import ToolEnvelope


class VerificationReader:
    def __init__(self,engine):self.engine=engine

    def read(self,run_id,*,actor):
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(str(run_id)),
                m.AgentRun.agent_type=='runtime-v1',m.AgentRun.actor_principal==actor))
            if row is None:raise LookupError('Verification run not found')
            ns=row.details['runtime_v1'];plan=TaskPlan.model_validate(ns['plan'])
            route=plan.route.get('verification_v1');professional=plan.route.get('professional_agents_v1')
            if not route or not professional:raise AgentFrameworkError('VERIFICATION_TRACE_NOT_AVAILABLE')
            context=VerificationContextStore(self.engine).read(route['context_id'],actor=actor)
            expected=verification_plan(context)
            frozen=create_verification_registry().freeze()
            if (route!=expected.route['verification_v1'] or plan.tasks!=expected.tasks or
                professional['registry'].get('registry_version')!=REGISTRY_VERSION or
                professional['registry_fingerprint']!=frozen.fingerprint or
                fingerprint(professional['registry'])!=frozen.fingerprint or
                professional['semantic_types']!={'verify':context.request.task_type}):
                raise AgentFrameworkError('AGENT_TRACE_INVALID')
            task=plan.tasks[0]
            binding=AgentBinding.model_validate(professional['bindings']['verify'])
            if binding!=AgentRouter(frozen,task_registry=ROLES).route(task,context.request.task_type):
                raise AgentFrameworkError('AGENT_TRACE_INVALID')
            trace=TaskTrace.model_validate(ns['traces']['verify'])
            art=TaskArtifact.model_validate(ns['artifacts']['verify']) if 'verify' in ns['artifacts'] else None
            if trace.run_id!=row.id or trace.task_id!='verify':raise AgentFrameworkError('AGENT_TRACE_INVALID')
            if art is None:
                return VerificationRunResult(run_id=row.id,runtime_status=row.details['ui_status'])
            if art.run_id!=row.id or art.task_id!='verify' or trace.artifact_id!=art.artifact_id or trace.status!=art.status:
                raise AgentFrameworkError('AGENT_TRACE_INVALID')
            AgentArtifact.from_task_artifact(art,binding)
            ctx=WorkerContext(run_id=row.id,trace_id=UUID(row.details['trace_id']),actor=actor,deadline=1.0)
            receipts=[]
            for ref in art.tool_calls:
                record=db.get(m.ToolCallRecord,UUID(ref['record_id']))
                if (record is None or record.agent_run_id!=row.id or record.sequence_no!=ref['sequence_no']
                    or record.tool_name!=ref['tool_name']):raise AgentFrameworkError('AGENT_TRACE_INVALID')
                envelope=ToolEnvelope.model_validate(record.output_summary)
                if envelope.trace_id!=str(ctx.trace_id) or envelope.status!=ref['status'] or envelope.tool!=record.tool_name:
                    raise AgentFrameworkError('AGENT_TRACE_INVALID')
                receipts.append(ToolReceipt(call_index=ref['call_index'],name=record.tool_name,arguments=record.input_summary,
                    started_at=record.started_at,finished_at=record.finished_at,envelope=envelope))
            validate_outcome(task,ctx,ExecutionOutcome(artifact=art,receipts=receipts))
            result=None;checked=()
            if receipts and receipts[0].envelope.status in ('success','partial'):
                data=receipts[0].envelope.data
                if (data.get('context_id')!=str(context.context_id) or data.get('source_snapshot_hash')!=context.source_snapshot_hash
                    or data.get('source_run_id')!=str(context.snapshot.source_run_id)
                    or data.get('source_artifact_id')!=str(context.snapshot.source_artifact_id)
                    or data.get('evaluation_time')!=context.evaluation_time.isoformat()):
                    raise AgentFrameworkError('AGENT_TRACE_INVALID')
                result=VerificationAssessment.model_validate(data['assessment'])
                if context.request.asset_id:
                    from app.agents.verification.asset_snapshot import validate_observation_handoff
                    validate_observation_handoff(result,context.snapshot)
                checked=tuple(data.get('claims_checked',[c.claim.claim_id for c in result.claims]))
                expected_checked=tuple(c.claim_id for c in context.snapshot.claims
                    if not context.request.claim_ids or c.claim_id in context.request.claim_ids)
                if checked!=expected_checked:raise AgentFrameworkError('AGENT_TRACE_INVALID')
            if result is None:
                result=VerificationAssessment(verification_status='INSUFFICIENT_EVIDENCE',confidence=0,partial_result=True,
                    warnings=tuple(art.warnings),unresolved_items=('Verification tool did not return usable evidence; inspect canonical error receipts',))
            if art.status not in (TaskState.SUCCESS,TaskState.WAITING_REVIEW):
                result=result.model_copy(update={'verification_status':'CONFLICT' if result.verification_status=='CONFLICT' else 'INSUFFICIENT_EVIDENCE',
                    'confidence':0,'partial_result':True,'unresolved_items':(*result.unresolved_items,'RUNTIME_INCOMPLETE')})
            projected=VerificationArtifact(**result.model_dump(),artifact_id=art.artifact_id,task_id=art.task_id,run_id=row.id,
                source_run_id=context.snapshot.source_run_id,source_artifact_id=context.snapshot.source_artifact_id,
                source_snapshot_hash=context.source_snapshot_hash,evaluation_time=context.evaluation_time,
                execution_status=art.status,tool_calls=tuple(art.tool_calls))
            elapsed=max(0,int((trace.end_time-trace.start_time).total_seconds()*1000)) if trace.start_time and trace.end_time else 0
            used=tuple(sorted({e.evidence_id for e in (*result.supporting_evidence,*result.conflicting_evidence)}))
            audit=VerificationRun(run_id=row.id,task_id=task.task_id,input_artifact={
                'run_id':str(context.snapshot.source_run_id),'artifact_id':str(context.snapshot.source_artifact_id),
                'task_id':context.snapshot.source_task_id,'source_snapshot_hash':context.source_snapshot_hash,
                'original_status':context.snapshot.artifact.get('runtime_status'),
                'link_kind':'source_observation_not_success_dependency'},output_artifact=art.artifact_id,
                claims_checked=checked,evidence_used=used,
                verification_result=result.verification_status,confidence=result.confidence,execution_time=elapsed,
                start_time=trace.start_time,end_time=trace.end_time,status=trace.status,tools_called=tuple(art.tool_calls))
            return VerificationRunResult(run_id=row.id,runtime_status=row.details['ui_status'],artifacts=(projected,),traces=(audit,))

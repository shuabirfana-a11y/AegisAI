"""Project sealed inputs and formal receipts; never refresh live intelligence/inventory."""
from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import AgentBinding,AgentFrameworkError,fingerprint
from app.agents.artifacts import AgentArtifact
from app.agents.router import AgentRouter
from app.agents.analysis.context_store import AnalysisContextStore
from app.agents.analysis.registry import create_analysis_registry
from app.agents.analysis.roles import ROLES,REGISTRY_VERSION
from app.agents.analysis.runtime import analysis_plan
from app.agents.analysis.schemas import RiskAssessment,RiskAnalysisArtifact,AnalysisRun,AnalysisRunResult
from app.runtime.contracts import TaskPlan,TaskTrace,TaskArtifact,WorkerContext,ToolReceipt,ExecutionOutcome,TaskState
from app.runtime.executor import validate_outcome
from app.tooling.contracts import ToolEnvelope
from app.tooling.analysis import base_assessment,protected_decision,bounded_payload


class AnalysisReader:
    def __init__(self,engine):self.engine=engine

    def read(self,run_id,*,actor):
        with transaction(self.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(str(run_id)),
                m.AgentRun.agent_type=='runtime-v1',m.AgentRun.actor_principal==actor))
            if row is None:raise LookupError('Analysis run not found')
            try:return self._project(db,row,actor)
            except (ValueError,KeyError,TypeError,LookupError,AttributeError):
                raise AgentFrameworkError('AGENT_TRACE_INVALID') from None

    def _project(self,db,row,actor):
        ns=row.details['runtime_v1'];plan=TaskPlan.model_validate(ns['plan'])
        route=plan.route.get('analysis_v1');professional=plan.route.get('professional_agents_v1')
        if not route or not professional:raise ValueError('Analysis route missing')
        context=AnalysisContextStore(self.engine).read(route['context_id'],actor=actor)
        expected=analysis_plan(context);frozen=create_analysis_registry().freeze()
        if (route!=expected.route['analysis_v1'] or plan.tasks!=expected.tasks or
            professional['registry'].get('registry_version')!=REGISTRY_VERSION or
            professional['registry_fingerprint']!=frozen.fingerprint or
            fingerprint(professional['registry'])!=frozen.fingerprint or
            professional['semantic_types']!={'analyze':context.request.task_type}):
            raise ValueError('Analysis plan changed')
        task=plan.tasks[0];binding=AgentBinding.model_validate(professional['bindings']['analyze'])
        if binding!=AgentRouter(frozen,task_registry=ROLES).route(task,context.request.task_type):raise ValueError('Agent binding changed')
        trace=TaskTrace.model_validate(ns['traces']['analyze'])
        art=TaskArtifact.model_validate(ns['artifacts']['analyze']) if 'analyze' in ns['artifacts'] else None
        if trace.run_id!=row.id or trace.task_id!='analyze':raise ValueError('Trace identity changed')
        if art is None:return AnalysisRunResult(run_id=row.id,runtime_status=row.details['ui_status'])
        if (art.run_id!=row.id or art.task_id!='analyze' or trace.artifact_id!=art.artifact_id or
            trace.status!=art.status or trace.tools_called!=art.tool_calls):raise ValueError('Artifact/trace mismatch')
        AgentArtifact.from_task_artifact(art,binding)
        ctx=WorkerContext(run_id=row.id,trace_id=UUID(row.details['trace_id']),actor=actor,deadline=1.0)
        receipts=[]
        for ref in art.tool_calls:
            record=db.get(m.ToolCallRecord,UUID(ref['record_id']))
            if (record is None or record.agent_run_id!=row.id or record.sequence_no!=ref['sequence_no'] or
                record.tool_name!=ref['tool_name']):raise ValueError('Receipt reference changed')
            envelope=ToolEnvelope.model_validate(record.output_summary)
            if envelope.trace_id!=str(ctx.trace_id) or envelope.status!=ref['status'] or envelope.tool!=record.tool_name:
                raise ValueError('Envelope identity changed')
            receipts.append(ToolReceipt(call_index=ref['call_index'],name=record.tool_name,arguments=record.input_summary,
                started_at=record.started_at,finished_at=record.finished_at,envelope=envelope))
        validate_outcome(task,ctx,ExecutionOutcome(artifact=art,receipts=receipts))
        if art.status in (TaskState.SUCCESS,TaskState.WAITING_REVIEW):
            outputs=[{'tool':r.name,'status':r.envelope.status,'data':r.envelope.data} for r in receipts]
            if fingerprint(art.result.get('outputs'))!=fingerprint(outputs):raise ValueError('Formal Artifact output changed')
        result=None
        if receipts and receipts[0].envelope.status in ('success','partial'):
            data=receipts[0].envelope.data
            ids=[str(context.inputs.investigation.artifact_id),str(context.inputs.verification.artifact_id)]
            if (data.get('context_id')!=str(context.context_id) or data.get('input_snapshot_hash')!=context.input_snapshot_hash or
                data.get('input_artifact_ids')!=ids or data.get('evaluation_time')!=context.evaluation_time.isoformat()):
                raise ValueError('Sealed input changed')
            result=RiskAssessment.model_validate(data['assessment'])
            expected_output=bounded_payload(context,base_assessment(context))['data']['assessment']
            if protected_decision(result)!=protected_decision(RiskAssessment.model_validate(expected_output)):
                raise ValueError('Rule result changed')
            if receipts[0].envelope.evidence_refs!=list(result.evidence_refs):raise ValueError('Evidence references changed')
            if not context.request.model_assistance and (result.model_assist_status!='DISABLED' or result.model_assist_used or result.model_calls):
                raise ValueError('Unauthorized model call')
            if art.status==TaskState.SUCCESS and result.priority=='REVIEW_REQUIRED':raise ValueError('Unresolved analysis marked successful')
        if result is None or art.status not in (TaskState.SUCCESS,TaskState.WAITING_REVIEW):
            result=RiskAssessment(verification_status=context.inputs.verification.verification_status,
                asset_id=context.inputs.asset.asset_id,component=context.inputs.asset.component,
                version=context.inputs.asset.deployed_version,partial_result=True,
                warnings=tuple(art.warnings),unresolved_items=('RUNTIME_INCOMPLETE: inspect original error receipts',))
        projected=RiskAnalysisArtifact(**result.model_dump(),artifact_id=art.artifact_id,task_id=art.task_id,run_id=row.id,
            context_id=context.context_id,input_artifact_ids=(context.inputs.investigation.artifact_id,context.inputs.verification.artifact_id),
            input_snapshot_hash=context.input_snapshot_hash,evaluation_time=context.evaluation_time,
            source_verification_time=context.inputs.verification.evaluation_time,inventory_revision=context.inputs.asset.inventory_revision,
            execution_status=art.status,tool_calls=tuple(art.tool_calls))
        elapsed=max(0,int((trace.end_time-trace.start_time).total_seconds()*1000)) if trace.start_time and trace.end_time else 0
        audit=AnalysisRun(run_id=row.id,task_id=task.task_id,actor=actor,input_artifact_ids=projected.input_artifact_ids,
            input_snapshot_hash=context.input_snapshot_hash,asset_match_result=result.asset_match_result,
            version_match_result=result.version_match_result,verification_status=result.verification_status,
            claim_dispositions=result.claim_dispositions,risk_factors=result.risk_factors,mitigating_factors=result.mitigating_factors,
            risk_level=result.risk_level,priority=result.priority,rule_ids=result.rule_ids,
            model_assist_used=result.model_assist_used,model_assist_status=result.model_assist_status,
            output_artifact_id=art.artifact_id,execution_time=elapsed,start_time=trace.start_time,end_time=trace.end_time,
            status=trace.status,tools_called=tuple(art.tool_calls))
        return AnalysisRunResult(run_id=row.id,runtime_status=row.details['ui_status'],artifacts=(projected,),traces=(audit,))

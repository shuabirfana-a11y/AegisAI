"""Read original formal receipts through the existing actor-bound readers.

Multiple sessions are not an atomic source snapshot. Pre/post fingerprints detect
changes during capture; no live inventory/claim refresh or new domain evaluation.
"""
from datetime import datetime
from uuid import UUID,uuid4,uuid5,NAMESPACE_URL
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import fingerprint,AgentFrameworkError
from app.enrichment.repository import digest
from app.agents.investigation.reader import InvestigationReader
from app.agents.verification.reader import VerificationReader
from app.agents.analysis.reader import AnalysisReader
from app.agents.verification.context_store import VerificationContextStore
from app.agents.analysis.context_store import AnalysisContextStore
from app.runtime.contracts import TaskPlan,TaskTrace
from app.integration.contracts import IntegrationRequest,IntegrationContext,TaskExecution,GateCheck
from app.integration.objective import from_planner_input
from app.integration.profiles import REQUIREMENTS,minimum_outcomes
from app.utils.time import utcnow

def _owned(db,id,actor,kind):
    row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(str(id)),m.AgentRun.actor_principal==actor,m.AgentRun.agent_type==kind))
    if row is None:raise LookupError('Integration source not available')
    return row

def _row_hash(row):
    return fingerprint({'id':str(row.id),'actor':row.actor_principal,'type':row.agent_type,'status':row.status,
        'context':row.context,'details':row.details,'started_at':row.started_at.isoformat() if row.started_at else None,
        'finished_at':row.finished_at.isoformat() if row.finished_at else None})

def source_fingerprints(engine,ids,actor):
    """Also binds stored tool inputs/outputs, not only mutable Run JSON."""
    out={}
    with transaction(engine) as db:
        for id,kind in ids.items():out[str(id)]=_row_hash(_owned(db,id,actor,kind))
        for row in db.scalars(select(m.ToolCallRecord).where(m.ToolCallRecord.agent_run_id.in_(tuple(ids)))):
            out['receipt:'+str(row.id)]=fingerprint({'run_id':str(row.agent_run_id),'tool':row.tool_name,
                'sequence':row.sequence_no,'status':row.status,'input':row.input_summary,'output':row.output_summary,
                'start':row.started_at.isoformat() if row.started_at else None,'end':row.finished_at.isoformat() if row.finished_at else None})
    return out

class IntegrationSnapshotReader:
    def __init__(self,engine):self.engine=engine

    def recheck(self,context):
        ids={}
        with transaction(self.engine) as db:
            for key in context.source_fingerprints:
                if key.startswith('receipt:'):continue
                row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(key),m.AgentRun.actor_principal==context.owner))
                if row is None:raise ValueError('SOURCE_NO_LONGER_AVAILABLE')
                ids[row.id]=row.agent_type
        return source_fingerprints(self.engine,ids,context.owner)

    def capture(self,request,*,actor,integration_id=None,evaluation_time=None):
        if not isinstance(actor,str) or not 1<=len(actor)<=150:raise ValueError('Authenticated actor required')
        r=IntegrationRequest.model_validate_json(request.model_dump_json())
        try:return self._capture(r,actor,integration_id or uuid4(),evaluation_time or utcnow())
        except AgentFrameworkError:raise ValueError('SOURCE_RECEIPT_INVALID') from None

    def _capture(self,r,actor,id,now):
        root=r.investigation.run_id if r.investigation else r.run_id
        if r.run_id and root!=r.run_id:raise ValueError('SOURCE_ANCHOR_MISMATCH')
        ids={ref.run_id:'runtime-v1' for ref in (r.investigation,r.verification,r.analysis) if ref}
        if root:ids[root]='runtime-v1'
        routes={};runs={};trace_refs=[];planner_id=None;observed={}
        with transaction(self.engine) as db:
            for rid in tuple(ids):
                row=_owned(db,rid,actor,'runtime-v1');plan=TaskPlan.model_validate(row.details['runtime_v1']['plan'])
                observed[str(rid)]=_row_hash(row)
                runs[rid]=(row.status,plan,row.details['runtime_v1']);routes[rid]=plan.route;trace_refs.append(str(row.details['trace_id']))
            if root:
                planner_id=routes[root].get('planner_run_id')
                if not planner_id:raise ValueError('INVESTIGATION_PLANNER_LINK_MISSING')
            if r.planner_run_id and str(r.planner_run_id)!=str(planner_id):raise ValueError('PLANNER_LINK_MISMATCH')
            checks=[];objective=None
            if planner_id:
                planner=_owned(db,planner_id,actor,'planner-v1');ids[UUID(planner_id)]='planner-v1'
                observed[str(planner_id)]=_row_hash(planner)
                ns=planner.details['planner_v1']
                if ns['runtime_run_id']!=str(root) or ns['validation_status']!='VALIDATED':raise ValueError('PLANNER_REVERSE_LINK_MISMATCH')
                trace_refs.append(str(planner.details['trace_id']))
                if r.objective_source=='stored_planner_request':
                    raw=planner.context.get('planner_input_v1')
                    if raw is not None:
                        if digest(raw)!=planner.context.get('planner_input_sha256'):raise ValueError('PLANNER_INPUT_HASH_INVALID')
                        if raw.get('query',{}).get('question')!=ns['user_query']:raise ValueError('PLANNER_QUESTION_MISMATCH')
                        objective=from_planner_input(raw,r.objective_profile)
            if r.objective_source=='new_structured_request':
                objective=r.explicit_objective
                if not set(minimum_outcomes(r.objective_profile,objective.question))<=set(objective.required_outcomes):raise ValueError('OBJECTIVE_PROFILE_WEAKENED')
                checks.append(GateCheck(gate='objective',code='NEW_EXPLICIT_OBJECTIVE',outcome='WARNING',message='New bounded request; not recovered historical intent'))
            elif objective is None:
                checks.append(GateCheck(gate='objective',code='OBJECTIVE_CONTEXT_MISSING',outcome='BLOCKED',blocking='REPLAN',message='Original structured request was not captured'))
            vc=None;ac=None
            if r.verification:
                route=routes[r.verification.run_id].get('verification_v1')
                if not route:raise ValueError('VERIFICATION_ROUTE_MISSING')
                vc=VerificationContextStore(self.engine).read(route['context_id'],actor=actor);ids[vc.context_id]='verification-context-v1'
            if r.analysis:
                route=routes[r.analysis.run_id].get('analysis_v1')
                if not route:raise ValueError('ANALYSIS_ROUTE_MISSING')
                ac=AnalysisContextStore(self.engine).read(route['context_id'],actor=actor);ids[ac.context_id]='analysis-context-v1'
        before=source_fingerprints(self.engine,ids,actor)
        if any(before.get(key)!=value for key,value in observed.items()):raise ValueError('SOURCE_CHANGED_DURING_CAPTURE')
        def selected(ref,reader,keyword=True):
            if ref is None:return None
            result=reader.read(ref.run_id,actor=actor) if keyword else reader.read(ref.run_id,actor)
            art=next((a for a in result.artifacts if (a.task_id,a.artifact_id,a.schema_version)==(ref.task_id,ref.artifact_id,ref.schema_version)),None)
            if art is None:raise ValueError('ARTIFACT_REFERENCE_NOT_AVAILABLE')
            return art
        inv=selected(r.investigation,InvestigationReader(self.engine),False)
        ver=selected(r.verification,VerificationReader(self.engine))
        risk=selected(r.analysis,AnalysisReader(self.engine))
        if vc:
            if root!=vc.snapshot.source_run_id:raise ValueError('CROSS_RUN_INVESTIGATION_MISMATCH')
            if inv and ((vc.snapshot.source_task_id,vc.snapshot.source_artifact_id)!=(inv.task_id,inv.artifact_id)
                or fingerprint(vc.snapshot.artifact)!=fingerprint(inv.model_dump(mode='json'))):raise ValueError('VERIFICATION_HANDOFF_MISMATCH')
            if vc.source_snapshot_hash!=fingerprint(vc.snapshot.model_dump(mode='json')):raise ValueError('VERIFICATION_SNAPSHOT_HASH_INVALID')
        if ac:
            if root!=ac.inputs.investigation.run_id:raise ValueError('CROSS_RUN_ANALYSIS_MISMATCH')
            for actual,expected in ((inv,ac.inputs.investigation),(ver,ac.inputs.verification)):
                if actual and fingerprint(actual.model_dump(mode='json'))!=fingerprint(expected.model_dump(mode='json')):raise ValueError('ANALYSIS_HANDOFF_MISMATCH')
        tasks=[];optional={(o.run_id,o.task_id) for o in r.optional_tasks};seen_optional=set()
        required_selected={(ref.run_id,ref.task_id) for ref in (r.investigation,r.verification,r.analysis) if ref}
        for rid,(status,plan,ns) in runs.items():
            semantics=plan.route.get('professional_agents_v1',{}).get('semantic_types',{})
            ancestors=set()
            def include(tid):
                if tid in ancestors:return
                ancestors.add(tid)
                node=next(t for t in plan.tasks if t.task_id==tid)
                for dep in node.dependencies:include(dep)
            for owner,tid in required_selected:
                if owner==rid:include(tid)
            for task in plan.tasks:
                key=(rid,task.task_id);is_optional=key in optional
                if is_optional:
                    seen_optional.add(key)
                    if rid!=root or semantics.get(task.task_id)!='evidence_search' or task.task_id in ancestors or any(task.task_id in t.dependencies for t in plan.tasks):raise ValueError('ESSENTIAL_TASK_CANNOT_BE_OPTIONAL')
                trace=TaskTrace.model_validate(ns['traces'][task.task_id])
                if trace.run_id!=rid or trace.task_id!=task.task_id:raise ValueError('TASK_TRACE_IDENTITY_INVALID')
                artifact=ns.get('artifacts',{}).get(task.task_id)
                codes=tuple(str(e.get('code','UNKNOWN_ERROR')) for e in (artifact or {}).get('errors',()))
                tasks.append(TaskExecution(run_id=rid,task_id=task.task_id,status=trace.status,semantic_type=semantics.get(task.task_id,'unknown'),
                    run_status=status,dependencies=task.dependencies,required=not is_optional,error_codes=codes))
        if seen_optional!=optional:raise ValueError('OPTIONAL_TASK_NOT_FOUND')
        after=source_fingerprints(self.engine,ids,actor)
        if before!=after:raise ValueError('SOURCE_CHANGED_DURING_CAPTURE')
        # Context stores were read while discovering provenance, before the full
        # fingerprint set existed. Compare them again to close that early gap.
        for store,context in ((VerificationContextStore(self.engine),vc),(AnalysisContextStore(self.engine),ac)):
            if context and fingerprint(store.read(context.context_id,actor=actor).model_dump(mode='json'))!=fingerprint(context.model_dump(mode='json')):raise ValueError('SOURCE_CHANGED_DURING_CAPTURE')
        objective_hash=fingerprint(objective.model_dump(mode='json') if objective else None)
        input_hash=fingerprint({'request':r.model_dump(mode='json'),'objective_hash':objective_hash,'sources':after,'policy':r.policy_version})
        logical=uuid5(NAMESPACE_URL,fingerprint({'owner':actor,'root':str(root),'objective':objective_hash}))
        context=IntegrationContext(integration_id=id,logical_investigation_id=logical,owner=actor,request=r,objective=objective,
            objective_hash=objective_hash,evaluation_time=now,investigation=inv,verification=ver,analysis=risk,
            verification_source=vc.snapshot if vc else None,asset_snapshot=ac.inputs.asset if ac else None,
            tasks=tuple(tasks),source_run_ids=tuple(dict.fromkeys(ref.run_id for ref in (r.investigation,r.verification,r.analysis) if ref)),
            source_fingerprints=after,trace_references=tuple(trace_refs),capture_checks=tuple(checks),input_hash=input_hash)
        # The effective input also binds temporal validity. Crossing a freshness
        # boundary produces a new revision instead of returning an aged PASS.
        from app.integration.freshness import check_freshness
        temporal=[ch.model_dump(mode='json') for ch in check_freshness(context)]
        return context.model_copy(update={'input_hash':fingerprint({'source_input_hash':input_hash,'temporal_validity':temporal})})

"""Exact reference adapters and upper admission; no verification/risk algorithm."""
from typing import Literal
from pydantic import Field
from app.integration.contracts import Sized,ArtifactRef,OptionalTask,IntegrationRequest
from app.runtime.contracts import TaskInput,TaskPlan
from app.agents.investigation.schemas import InvestigationArtifact,InvestigationRunResult
from app.agents.verification.schemas import VerificationRequest
from app.agents.analysis.schemas import AnalysisRequest
from app.agents.asset_observations import InvestigationArtifactReference
from uuid import UUID


class ArtifactSelection(Sized):
    size_limit=1024*1024
    artifact: InvestigationArtifact | None = None
    admission: Literal['CONTINUE','VERIFY_ONLY','STOP']
    reasons: tuple[str,...] = ()
    optional_tasks: tuple[OptionalTask,...] = Field(default=(),max_length=16)
    supporting_artifacts: tuple[InvestigationArtifactReference,...] = ()
    asset_id: UUID | None = None
    component_id: UUID | None = None


def artifact_ref(artifact):
    return ArtifactRef(run_id=artifact.run_id,task_id=artifact.task_id,
                       artifact_id=artifact.artifact_id,schema_version=artifact.schema_version)


def select_investigation(result: InvestigationRunResult,scope,plan: TaskPlan):
    result=InvestigationRunResult.model_validate_json(result.model_dump_json())
    plan=TaskPlan.model_validate_json(plan.model_dump_json())
    if len(scope.targets)!=1:return ArtifactSelection(admission='STOP',reasons=('SINGLE_TARGET_SCOPE_REQUIRED',))
    target=scope.targets[0];by_id={t.task_id:t for t in plan.tasks};traces={t.task_id:t for t in result.traces}
    candidates=[]
    for art in result.artifacts:
        task=by_id.get(art.task_id)
        if task and art.canonical_id==target and any(s.name=='get_vulnerability' and s.arguments.get('target')==target
                for s in TaskInput.model_validate(task.input_data).steps):candidates.append(art)
    if len(candidates)!=1:
        return ArtifactSelection(admission='STOP',reasons=('AMBIGUOUS_INVESTIGATION_ARTIFACT' if candidates else 'INVESTIGATION_ARTIFACT_MISSING',))
    artifact=candidates[0];ancestors=set()
    def visit(id):
        if id in ancestors:return
        ancestors.add(id)
        for dep in by_id[id].dependencies:visit(dep)
    visit(artifact.task_id)
    semantics=plan.route.get('professional_agents_v1',{}).get('semantic_types',{})
    # Unit plans may not be bound yet; production plans always carry formal semantic bindings.
    optional=[]
    requested_evidence=any(token in scope.objective.question.casefold() for token in ('poc','证据','公告','论文','commit','补丁代码'))
    for task in plan.tasks:
        steps=TaskInput.model_validate(task.input_data).steps
        kind=semantics.get(task.task_id)
        if (not requested_evidence and kind=='evidence_search' and task.task_id not in ancestors and
            not task.dependencies and not any(task.task_id in child.dependencies for child in plan.tasks) and
            {s.name for s in steps}=={'semantic_search'}):
            optional.append(OptionalTask(run_id=result.run_id,task_id=task.task_id))
    optional_ids={t.task_id for t in optional};reasons=[]
    for task in plan.tasks:
        if task.task_id in optional_ids:continue
        trace=traces.get(task.task_id)
        # A conflict is a complete observation requiring an independent verifier.
        # This does not unlock any blocked node in the Investigation DAG.
        conflict_observation=(task.task_id==artifact.task_id and artifact.status=='CONFLICT' and
            not artifact.partial_result and not artifact.failed_tools and trace is not None and
            trace.status=='WAITING_REVIEW' and artifact.runtime_status=='WAITING_REVIEW')
        if trace is None or (trace.status!='SUCCESS' and not conflict_observation):
            reasons.append('REQUIRED_INVESTIGATION_TASK_INCOMPLETE:'+task.task_id)
    if artifact.partial_result or artifact.status=='PARTIAL' or artifact.runtime_status not in ('SUCCESS','WAITING_REVIEW'):
        reasons.append('REQUIRED_INVESTIGATION_ARTIFACT_INCOMPLETE')
    # Exact complete sibling/descendant outputs are supplementary facts, not a
    # replacement for the original selected Artifact or a new Runtime task.
    supporting=[]
    if scope.planner_input.query.asset_id:
        for art in result.artifacts:
            if art.task_id in optional_ids or art.artifact_id==artifact.artifact_id:continue
            if art.run_id!=result.run_id or art.canonical_id not in (None,target):
                reasons.append('SUPPORTING_ARTIFACT_SCOPE_MISMATCH:'+art.task_id);continue
            trace=traces.get(art.task_id)
            if art.partial_result or art.runtime_status!='SUCCESS' or trace is None or trace.status!='SUCCESS':
                reasons.append('SUPPORTING_ARTIFACT_INCOMPLETE:'+art.task_id);continue
            supporting.append(InvestigationArtifactReference(run_id=art.run_id,task_id=art.task_id,artifact_id=art.artifact_id))
    # A complete conflict observation is consumable by the independent verifier,
    # even if a dependent node remains blocked. This is not execution success:
    # preserve every reason/task state and do not admit risk analysis.
    verify_only=(bool(reasons) and artifact.status=='CONFLICT' and artifact.runtime_status=='WAITING_REVIEW'
        and not artifact.partial_result and not artifact.failed_tools and bool(artifact.conflicts)
        and traces.get(artifact.task_id) is not None and traces[artifact.task_id].status=='WAITING_REVIEW')
    return ArtifactSelection(artifact=artifact,admission='VERIFY_ONLY' if verify_only else 'STOP' if reasons else 'CONTINUE',
        reasons=tuple(reasons),optional_tasks=tuple(optional),supporting_artifacts=tuple(supporting),
        asset_id=scope.planner_input.query.asset_id,component_id=scope.planner_input.component_id)


def build_verification_request(selection,stage_key):
    if selection.admission not in ('CONTINUE','VERIFY_ONLY') or selection.artifact is None:raise ValueError('INVESTIGATION_NOT_ADMITTED')
    art=selection.artifact
    return VerificationRequest(source_run_id=art.run_id,source_task_id=art.task_id,
        source_artifact_id=art.artifact_id,request_key=stage_key,task_type='evidence_verification',model_assistance=False,
        supporting_artifacts=selection.supporting_artifacts,asset_id=selection.asset_id,component_id=selection.component_id)


def verification_admitted(result,investigation):
    if len(result.artifacts)!=1:return False
    art=result.artifacts[0]
    return (art.source_run_id==investigation.run_id and art.source_artifact_id==investigation.artifact_id
        and art.execution_status in ('SUCCESS','WAITING_REVIEW') and not art.partial_result and bool(art.tool_calls))


def build_analysis_request(selection,verification,scope,stage_key):
    inv=selection.artifact
    if inv is None or (verification.source_run_id,verification.source_artifact_id)!=(inv.run_id,inv.artifact_id):
        raise ValueError('VERIFICATION_HANDOFF_MISMATCH')
    p=scope.planner_input
    return AnalysisRequest(investigation_run_id=inv.run_id,investigation_task_id=inv.task_id,
        investigation_artifact_id=inv.artifact_id,verification_run_id=verification.run_id,
        verification_task_id=verification.task_id,verification_artifact_id=verification.artifact_id,
        asset_id=p.query.asset_id,component_id=p.component_id,request_key=stage_key,model_assistance=False)


def build_integration_request(context,refs,*,optional_tasks=()):
    by_schema={r.schema_version:r for r in refs};scope=context.resolved_scope
    return IntegrationRequest(request_key=context.stage_keys['integration'],run_id=context.investigation_run_id,
        planner_run_id=context.planner_run_id,objective_profile=scope.objective_profile,
        objective_source=scope.objective_source,
        explicit_objective=scope.objective if scope.objective_source=='new_structured_request' else None,
        investigation=by_schema.get('investigation-artifact-v1'),verification=by_schema.get('verification-artifact-v1'),
        analysis=by_schema.get('risk-analysis-artifact-v1'),optional_tasks=optional_tasks)

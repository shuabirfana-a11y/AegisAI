from uuid import uuid4
from app.runtime.contracts import TaskPlan,TaskContract,TaskState
from app.agents.investigation.schemas import InvestigationArtifact,InvestigationRunResult,InvestigationTaskTrace
from tests.orchestration.test_contracts_scope import request


def input_data():
    from app.orchestration.scope import resolve_scope
    id=uuid4();aid=uuid4()
    node=TaskContract(task_id='lookup',description='SYNTHETIC UNIT ONLY',allowed_tools=('get_vulnerability',),
        input_data={'steps':[{'name':'get_vulnerability','arguments':{'target':'CVE-2099-90001'}}]})
    artifact=InvestigationArtifact(run_id=id,artifact_id=aid,task_id='lookup',canonical_id='CVE-2099-90001',
        status='COMPLETE',runtime_status='SUCCESS')
    trace=InvestigationTaskTrace(task_id='lookup',status='SUCCESS',artifact_id=aid,attempted=True)
    result=InvestigationRunResult(run_id=id,runtime_status='COMPLETED',artifacts=(artifact,),traces=(trace,))
    return result,resolve_scope(request(),actor='alice'),TaskPlan(tasks=(node,))


def test_handoff_preserves_original_ids():
    from app.orchestration.handoff import select_investigation,build_verification_request
    result,scope,plan=input_data();selection=select_investigation(result,scope,plan)
    built=build_verification_request(selection,'stage-key')
    assert (built.source_run_id,built.source_task_id,built.source_artifact_id)==(
        result.run_id,'lookup',result.artifacts[0].artifact_id)
    assert not built.model_assistance and built.claim_ids==()


def test_ambiguous_lookup_does_not_select_first():
    from app.orchestration.handoff import select_investigation
    result,scope,plan=input_data();node=plan.tasks[0].model_copy(update={'task_id':'second'})
    art=result.artifacts[0].model_copy(update={'task_id':'second','artifact_id':uuid4()})
    trace=result.traces[0].model_copy(update={'task_id':'second','artifact_id':art.artifact_id})
    result=result.model_copy(update={'artifacts':(*result.artifacts,art),'traces':(*result.traces,trace)})
    selection=select_investigation(result,scope,TaskPlan(tasks=(*plan.tasks,node)))
    assert selection.admission=='STOP' and 'AMBIGUOUS_INVESTIGATION_ARTIFACT' in selection.reasons
    assert selection.artifact is None


def test_required_partial_does_not_pass_admission():
    from app.orchestration.handoff import select_investigation
    result,scope,plan=input_data()
    art=result.artifacts[0].model_copy(update={'status':'PARTIAL','partial_result':True,'runtime_status':TaskState.WAITING_REVIEW})
    result=result.model_copy(update={'artifacts':(art,),'traces':(result.traces[0].model_copy(update={'status':TaskState.WAITING_REVIEW}),)})
    selection=select_investigation(result,scope,plan)
    assert selection.admission=='STOP' and selection.artifact.artifact_id==art.artifact_id


def test_optional_task_with_dependent_child_remains_required():
    from app.orchestration.handoff import select_investigation
    result,scope,plan=input_data()
    extra=TaskContract(task_id='extra',description='SYNTHETIC',allowed_tools=('semantic_search',),
        input_data={'steps':[{'name':'semantic_search','arguments':{'query':scope.planner_input.query.question}}]})
    child=plan.tasks[0].model_copy(update={'task_id':'child','dependencies':('extra',)})
    result=result.model_copy(update={'traces':(*result.traces,
        InvestigationTaskTrace(task_id='extra',status='FAILED',attempted=True),
        InvestigationTaskTrace(task_id='child',status='BLOCKED',attempted=False)), 'blocked_tasks':('child',)})
    selection=select_investigation(result,scope,TaskPlan(tasks=(*plan.tasks,extra,child)))
    assert selection.admission=='STOP' and selection.optional_tasks==()

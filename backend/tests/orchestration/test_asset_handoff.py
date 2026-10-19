"""Business handoff regressions; SYNTHETIC inputs, never Benchmark answers."""
from uuid import uuid4
from app.runtime.contracts import TaskPlan,TaskContract,TaskState
from app.agents.investigation.schemas import InvestigationTaskTrace
from app.orchestration.handoff import select_investigation,build_verification_request
from tests.orchestration.test_handoff import input_data


def asset_case():
    result,scope,plan=input_data()
    asset_id=uuid4();component_id=uuid4()
    p=scope.planner_input
    scope=scope.model_copy(update={'planner_input':p.model_copy(update={
        'query':p.query.model_copy(update={'asset_id':asset_id}),'component_id':component_id})})
    version=TaskContract(task_id='version',description='SYNTHETIC version',dependencies=('lookup',),
        allowed_tools=('inspect_component_version',),input_data={'steps':[{'name':'inspect_component_version',
        'arguments':{'target':'CVE-2099-90001','name':'vllm','version':'0.6.0'}}]})
    asset=TaskContract(task_id='asset',description='SYNTHETIC inventory',allowed_tools=('get_asset',),
        input_data={'steps':[{'name':'get_asset','arguments':{'asset_id':str(asset_id)}}]})
    arts=tuple(result.artifacts[0].model_copy(update={'task_id':t.task_id,'artifact_id':uuid4()}) for t in (version,asset))
    traces=tuple(InvestigationTaskTrace(task_id=a.task_id,status='SUCCESS',artifact_id=a.artifact_id,attempted=True) for a in arts)
    return result.model_copy(update={'artifacts':(*result.artifacts,*arts),'traces':(*result.traces,*traces)}),scope,TaskPlan(tasks=(*plan.tasks,version,asset))


def test_later_version_and_independent_asset_are_handed_to_verifier():
    result,scope,plan=asset_case()
    selection=select_investigation(result,scope,plan)
    request=build_verification_request(selection,'asset-stage')
    assert {r.task_id for r in getattr(request,'supporting_artifacts',())}=={'version','asset'}
    assert request.source_artifact_id==result.artifacts[0].artifact_id
    assert request.asset_id==scope.planner_input.query.asset_id
    assert request.component_id==scope.planner_input.component_id


def test_incomplete_supporting_task_cannot_be_consumed():
    result,scope,plan=asset_case()
    bad=result.traces[-1].model_copy(update={'status':TaskState.FAILED})
    selected=select_investigation(result.model_copy(update={'traces':(*result.traces[:-1],bad)}),scope,plan)
    assert selected.admission=='STOP'


def test_overview_request_explicitly_selects_source_facts_without_changing_asset_scope():
    result,scope,plan=input_data()
    request=build_verification_request(select_investigation(result,scope,plan),'legacy')
    assert set(request.model_dump(mode='json'))=={'source_run_id','source_task_id','source_artifact_id',
        'task_type','claim_ids','request_key','model_assistance','include_source_facts'}
    assert request.include_source_facts is True
    result,scope,plan=asset_case()
    scope=scope.model_copy(update={'objective_profile':'asset_risk_v1'})
    request=build_verification_request(select_investigation(result,scope,plan),'asset-required-facts')
    assert not request.include_source_facts
    assert 'include_source_facts' not in request.model_dump(mode='json')

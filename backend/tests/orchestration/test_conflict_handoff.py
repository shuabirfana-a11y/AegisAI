"""A complete conflicting source may be verified without unblocking its DAG."""
from app.orchestration.handoff import select_investigation,build_verification_request
from app.runtime.contracts import TaskContract,TaskPlan,TaskState
from app.agents.investigation.schemas import InvestigationTaskTrace
from tests.orchestration.test_handoff import input_data
import pytest


def conflicting_case():
    result,scope,plan=input_data()
    art=result.artifacts[0].model_copy(update={'status':'CONFLICT','information_status':'CONFLICT',
        'runtime_status':TaskState.WAITING_REVIEW,'conflicts':[{'conflict_type':'VERSION_CONFLICT','scope_key':'PyPI:synthetic'}]})
    blocked=TaskContract(task_id='version',description='Unexecuted dependency',dependencies=('lookup',),
        allowed_tools=('inspect_component_version',),input_data={'steps':[{'name':'inspect_component_version',
        'arguments':{'target':'CVE-2099-90001','name':'synthetic','version':'1.0'}}]})
    traces=(result.traces[0].model_copy(update={'status':TaskState.WAITING_REVIEW}),
        InvestigationTaskTrace(task_id='version',status='BLOCKED',attempted=False))
    return result.model_copy(update={'artifacts':(art,),'traces':traces,'blocked_tasks':('version',)}),scope,TaskPlan(tasks=(*plan.tasks,blocked))


def test_conflict_enters_verification_only_and_preserves_blocked_reason():
    result,scope,plan=conflicting_case();selected=select_investigation(result,scope,plan)
    assert selected.admission=='VERIFY_ONLY'
    assert 'REQUIRED_INVESTIGATION_TASK_INCOMPLETE:version' in selected.reasons
    assert result.blocked_tasks==('version',) and result.traces[1].status=='BLOCKED'
    request=build_verification_request(selected,'conflict-source')
    assert request.source_artifact_id==result.artifacts[0].artifact_id
    assert not request.model_assistance


@pytest.mark.parametrize('change',[{'partial_result':True},{'status':'PARTIAL'},
    {'failed_tools':[{'tool':'get_vulnerability'}]},{'runtime_status':TaskState.FAILED}])
def test_partial_failed_or_non_conflict_never_uses_verification_only(change):
    result,scope,plan=conflicting_case()
    result=result.model_copy(update={'artifacts':(result.artifacts[0].model_copy(update=change),)})
    assert select_investigation(result,scope,plan).admission=='STOP'

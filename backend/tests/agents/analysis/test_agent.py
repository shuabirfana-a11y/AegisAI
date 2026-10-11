"""Breaks caught: default-chain replacement, unauthorized tools and cancel cross-talk."""
import pytest
from uuid import uuid4
from app.agents.artifacts import AgentExecutionRequest
from app.agents.router import AgentRouter
from app.runtime.contracts import TaskContract
from tests.agents.fixtures import context as worker_context,outcome
from tests.agents.analysis.helpers import module


def framework():
    cls=module('agent').SecurityAnalysisAgent
    return cls,module('roles').ROLES,module('registry').create_analysis_registry()


def task(name='analyze_risk_snapshot'):
    return TaskContract(task_id='analyze',description='SYNTHETIC analysis',max_tool_calls=1,
        allowed_tools=(name,),input_data={'steps':[{'name':name,'arguments':{'context_id':str(uuid4())}}]})


@pytest.mark.parametrize('kind,name',[('risk_analysis','analyze_risk_snapshot'),
    ('asset_impact_analysis','analyze_asset_impact_snapshot'),('remediation_prioritization','prioritize_remediation_snapshot')])
def test_three_tasks_route_to_security_analysis_agent(kind,name):
    _,roles,registry=framework();snapshot=registry.freeze()
    binding=AgentRouter(snapshot,task_registry=roles).route(task(name),kind)
    assert binding.agent_id=='security_analysis_agent' and binding.implementation_key=='security-analysis-v1'
    assert binding.artifact_type=='security_analysis_result'


def test_default_registry_and_planner_unchanged():
    from app.agents.registry import create_default_registry
    from app.planner.registry import TASK_REGISTRY
    framework()
    assert create_default_registry().freeze().get('security_analysis_agent').implementation is None
    assert 'asset_impact_analysis' not in TASK_REGISTRY
    assert TASK_REGISTRY['risk_analysis'].tools==frozenset({'get_asset_risks','explain_asset_risk','get_epss','get_known_exploitation'})


def test_forbidden_lookup_or_write_rejected_before_execution():
    cls,roles,registry=framework();router=AgentRouter(registry.freeze(),task_registry=roles)
    wrong=TaskContract(task_id='analyze',description='wrong',allowed_tools=('get_vulnerability',),max_tool_calls=1,
        input_data={'steps':[{'name':'get_vulnerability','arguments':{'target':'CVE-2099-9999113'}}]})
    with pytest.raises(ValueError):router.route(wrong,'risk_analysis')
    with pytest.raises(ValueError,match='AGENT_NOT_FOUND'):router.route(task(),'unknown_task')
    result=cls().analyze(AgentExecutionRequest(task=wrong,context=worker_context()))
    assert result.artifact.errors[0]['code']=='AGENT_TOOL_FORBIDDEN' and not result.receipts


def test_cancelled_instance_is_independent_of_new_run():
    cls,_,_=framework();prototype=cls();first=prototype.for_run(uuid4());second=prototype.for_run(uuid4())
    first.cancel_all()
    assert first is not second and first is not prototype
    assert not second._cancelled.is_set()
    result=first.analyze(AgentExecutionRequest(task=task(),context=worker_context(run_id=first._run_id)))
    assert result.artifact.errors[0]['code']=='RUN_CANCELLED'


def test_invalid_payload_keeps_original_formal_receipt():
    cls,_,_=framework();item=task();ctx=worker_context()
    got=outcome(item,ctx,response={'status':'success','data':{'context_id':'forged','assessment':{}},'evidence_refs':[]})
    class Supervisor:
        def execute(self,*args,**kwargs):return got
        def cancel_all(self):pass
    result=cls(supervisor_factory=Supervisor).analyze(AgentExecutionRequest(task=item,context=ctx))
    assert result.artifact.errors[0]['code']=='ANALYSIS_OUTPUT_INVALID'
    assert result.receipts[0].envelope.data['context_id']=='forged'

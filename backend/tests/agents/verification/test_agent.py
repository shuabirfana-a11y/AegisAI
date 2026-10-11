"""Breaks caught: wrong dispatch, implicit roles and unbounded agent execution."""
import importlib
from uuid import uuid4
import pytest
from app.agents.artifacts import AgentExecutionRequest
from app.agents.router import AgentRouter
from app.runtime.contracts import TaskContract,TaskPlan,RuntimePolicy
from tests.agents.fixtures import context


def framework():
    try:
        agent=importlib.import_module('app.agents.verification.agent').EvidenceVerificationAgent
        roles=importlib.import_module('app.agents.verification.roles').ROLES
        registry=importlib.import_module('app.agents.verification.registry').create_verification_registry()
        return agent,roles,registry
    except ModuleNotFoundError:pytest.fail('Verification Agent framework implementation is missing')


def task(name='evaluate_evidence_snapshot'):
    return TaskContract(task_id='verify',description='SYNTHETIC verification',max_tool_calls=1,
        allowed_tools=(name,),input_data={'steps':[{'name':name,'arguments':{'context_id':str(uuid4())}}]})


@pytest.mark.parametrize('kind,name', [('evidence_verification','evaluate_evidence_snapshot'),
    ('claim_validation','validate_claim_snapshot'),('conflict_detection','compare_claim_snapshot')])
def test_all_three_roles_route_to_concrete_verifier(kind,name):
    _,roles,registry=framework()
    frozen=registry.freeze()
    assert frozen.for_task(kind).contract.agent_id=='verification_agent'
    binding=AgentRouter(frozen,task_registry=roles).route(task(name),kind)
    assert binding.implementation_key=='evidence-verification-v1'
    assert binding.artifact_type=='verification_result'


def test_unknown_task_and_unauthorized_tool_are_rejected():
    _,roles,registry=framework();router=AgentRouter(registry.freeze(),task_registry=roles)
    with pytest.raises(ValueError,match='AGENT_NOT_FOUND'):router.route(task(),'unknown_task')
    wrong=TaskContract(task_id='write',description='SYNTHETIC forbidden',allowed_tools=('verify_claim',),max_tool_calls=1,
        input_data={'steps':[{'name':'verify_claim','arguments':{'claim_id':str(uuid4())}}]})
    with pytest.raises(ValueError):router.route(wrong,'evidence_verification')


def test_cancelled_agent_cannot_execute_and_run_identity_is_pinned():
    cls,roles,registry=framework();item=task();ctx=context()
    binding=AgentRouter(registry.freeze(),task_registry=roles).route(item,'evidence_verification')
    agent=cls().for_run(ctx.run_id);agent.cancel_all()
    result=agent.verify(AgentExecutionRequest(task=item,context=ctx,input_artifacts=()))
    assert result.artifact.status=='FAILED'
    assert result.artifact.errors[0]['code']=='RUN_CANCELLED'
    assert not result.receipts


def test_invalid_business_payload_preserves_formal_tool_receipt():
    from tests.agents.fixtures import outcome
    cls,_,_=framework();item=task();ctx=context()
    got=outcome(item,ctx,response={'status':'success','data':{'context_id':'forged','assessment':{}},'evidence_refs':[]})
    class Supervisor:
        def execute(self,*args,**kwargs):return got
        def cancel_all(self):pass
    agent=cls(supervisor_factory=Supervisor)
    result=agent.verify(AgentExecutionRequest(task=item,context=ctx))
    assert result.artifact.status=='FAILED' and result.artifact.errors[0]['code']=='VERIFICATION_OUTPUT_INVALID'
    assert len(result.receipts)==1 and result.receipts[0].envelope.data['context_id']=='forged'

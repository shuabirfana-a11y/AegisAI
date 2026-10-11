import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from app.runtime.contracts import TaskPlan, RuntimePolicy
from tests.agents.fixtures import task, context, outcome


def make_executor(*, action=None, process=False, timeout=30):
    from app.agents.executor import AgentExecutor
    from app.agents.router import AgentRouter
    registry=delegate_registry(action=action,process=process,timeout=timeout)
    snapshot=registry.freeze();item=task()
    bound=AgentRouter(snapshot).bind_plan(TaskPlan(tasks=[item]),{'lookup':'vulnerability_lookup'},RuntimePolicy())
    return AgentExecutor(bound,snapshot),item,registry


def delegate_registry(*, action=None, process=False, timeout=30, observations=None):
    from app.agents.interfaces import InvestigationAgent, VerificationAgent, SecurityAnalysisAgent
    from app.agents.registry import AgentRegistry, create_default_registry
    from app.agents.contracts import AgentContract
    from app.runtime.process import ProcessSupervisor
    observations=observations if observations is not None else []
    class Delegate:
        implementation_key='TEST_ONLY.delegate-v1'
        def __init__(self):self.supervisor=ProcessSupervisor()
        def for_run(self,run_id):return type(self)()
        def cancel_all(self):self.supervisor.cancel_all()
        def call(self,request,*,database_url=None):
            observations.append(request)
            if action:return action(request)
            deps={a.task_id:a.to_task_artifact() for a in request.input_artifacts}
            if process:return self.supervisor.execute(request.task,request.context,deps,database_url=database_url)
            return outcome(request.task,request.context,deps)
    class TestInvestigation(Delegate,InvestigationAgent):
        investigate=Delegate.call
    class TestVerification(Delegate,VerificationAgent):
        verify=Delegate.call
    class TestAnalysis(Delegate,SecurityAnalysisAgent):
        analyze=Delegate.call
    registry=AgentRegistry()
    classes={'investigation':TestInvestigation,'verification':TestVerification,'security_analysis':TestAnalysis}
    for entry in create_default_registry().freeze().entries:
        contract=AgentContract(**{**entry.contract.model_dump(),'timeout_seconds':timeout})
        registry.register(contract,entry.interface,classes[contract.agent_type]())
    return registry


def test_registered_abstract_agent_returns_not_implemented():
    from app.agents.executor import AgentExecutor
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    snapshot=create_default_registry().freeze();item=task()
    bound=AgentRouter(snapshot).bind_plan(TaskPlan(tasks=[item]),{'lookup':'vulnerability_lookup'},RuntimePolicy())
    got=AgentExecutor(bound,snapshot).execute(item,context(),{})
    assert got.artifact.status=='FAILED' and got.artifact.errors[0]['code']=='AGENT_NOT_IMPLEMENTED'
    assert got.receipts==()


def test_executor_calls_capability_and_validates_receipts():
    calls=[]
    def action(request):calls.append(request);return outcome(request.task,request.context)
    executor,item,_=make_executor(action=action)
    got=executor.execute(item,context(),{})
    assert got.artifact.status=='SUCCESS' and len(got.receipts)==1 and len(calls)==1
    assert calls[0].task==item and calls[0].input_artifacts==()


@pytest.mark.parametrize('mutation',['evidence','output','dependencies','extra_result','unverified_cleanup','nan'])
def test_executor_rejects_forged_success_or_evidence(mutation):
    def action(request):
        got=outcome(request.task,request.context)
        if mutation=='unverified_cleanup':return got.model_copy(update={'cleanup_verified':False})
        values=got.artifact.model_dump()
        if mutation=='evidence':values['evidence']=[{'fake':True}]
        if mutation=='output':values['result']['outputs']=[{'fake':True}]
        if mutation=='dependencies':values['result']['dependencies']={'fake':str(request.context.run_id)}
        if mutation=='extra_result':values['result']['facts']=['unverified conclusion']
        if mutation=='nan':values['result']['outputs'][0]['data']['bad']=float('nan')
        return got.model_copy(update={'artifact':got.artifact.model_copy(update=values)})
    executor,item,_=make_executor(action=action)
    got=executor.execute(item,context(),{})
    assert got.artifact.status=='FAILED' and got.artifact.errors[0]['code']=='AGENT_OUTPUT_INVALID'
    assert len(got.receipts)==1


def test_executor_failure_is_sanitized():
    def action(request):raise RuntimeError('PRIVATE database secret')
    executor,item,_=make_executor(action=action)
    got=executor.execute(item,context(),{})
    assert got.artifact.errors[0]['code']=='AGENT_EXECUTION_FAILED'
    assert 'PRIVATE' not in got.model_dump_json()


def test_task_changed_after_binding_is_rejected_before_agent():
    executor,item,_=make_executor(action=lambda r:pytest.fail('must not run'))
    got=executor.execute(item.model_copy(update={'description':'Changed'}),context(),{})
    assert got.artifact.errors[0]['code']=='AGENT_PLAN_INVALID'


def test_timeout_and_cancel_propagate_to_process_supervisor(monkeypatch,tmp_path):
    from app.runtime.process import ProcessSupervisor,process_alive
    import sys
    fixture=Path(__file__).parents[1]/'runtime/fixtures/slow_worker.py'
    monkeypatch.setenv('AEGIS_RUNTIME_TEST_FOLDER',str(tmp_path))
    monkeypatch.setattr(ProcessSupervisor,'_command',lambda self:[sys.executable,str(fixture)])
    executor,item,_=make_executor(process=True,timeout=1)
    got=executor.execute(item,context(),{})
    assert got.artifact.errors[0]['code']=='TASK_TIMEOUT' and got.cleanup_verified
    assert all(not process_alive(pid) for pid in json.loads((tmp_path/'pids.json').read_text()))
    assert not (tmp_path/'late.txt').exists()
    folder=tmp_path/'cancel';folder.mkdir();monkeypatch.setenv('AEGIS_RUNTIME_TEST_FOLDER',str(folder))
    executor,item,_=make_executor(process=True)
    with ThreadPoolExecutor(1) as pool:
        running=pool.submit(executor.execute,item,context(),{})
        until=time.monotonic()+5
        while not (folder/'pids.json').exists() and time.monotonic()<until:time.sleep(.01)
        assert (folder/'pids.json').exists()
        executor.cancel_all();got=running.result(timeout=5)
    assert got.artifact.errors[0]['code']=='RUN_CANCELLED' and got.cleanup_verified
    assert all(not process_alive(pid) for pid in json.loads((folder/'pids.json').read_text()))
    assert not (folder/'late.txt').exists()


def test_executor_is_bound_to_single_run():
    executor,item,_=make_executor()
    assert executor.execute(item,context(),{}).artifact.status=='SUCCESS'
    assert executor.execute(item,context(),{}).artifact.errors[0]['code']=='AGENT_RUN_MISMATCH'

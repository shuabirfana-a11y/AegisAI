import time
import threading
from uuid import uuid4
import pytest
from .test_contracts_plan import task
from .fakes import MemoryStore, InlineExecutor


def run(tasks, lowlevel=None, *, executor=None, **policy):
    from app.runtime.contracts import RunContext,RuntimePolicy,TaskPlan
    from app.runtime.graph import compile_graph
    from app.runtime.scheduler import Scheduler
    configured=RuntimePolicy(**policy)
    ctx=RunContext(run_id=uuid4(),trace_id=uuid4(),actor='test-owner',policy=configured,
                   permissions=configured.permissions,deadline=time.monotonic()+configured.run_timeout_seconds)
    store=MemoryStore()
    execution=executor or InlineExecutor(lowlevel or (lambda n,a,c:{'status':'success','data':{'synthetic':True}}))
    outcome=Scheduler(executor=execution).run(compile_graph(TaskPlan(tasks=tasks),configured),ctx,store)
    return outcome,store


def test_dependencies_finish_before_downstream_starts():
    outcome,stored=run([task(task_id='a'),task(task_id='b',dependencies=['a']),task(task_id='c',dependencies=['b'])])
    assert outcome.status=='succeeded' and len(outcome.artifacts)==3
    assert stored.traces['b'].start_time >= stored.traces['a'].end_time
    assert stored.traces['c'].start_time >= stored.traces['b'].end_time
    assert stored.artifacts['b'].result['dependencies']['a']==str(stored.artifacts['a'].artifact_id)
    assert all(t.status=='SUCCESS' for t in outcome.traces)


def test_poc_patch_ready_tasks_are_really_parallel():
    barrier=threading.Barrier(2)
    def tools(name,args,ctx):
        if name in ('find_poc_candidates','find_patch_candidates'):
            barrier.wait(timeout=2)
        return {'status':'success','data':{'items':[{'synthetic':True}]}}
    tasks=[task(task_id='root')]
    for id,name in [('poc','find_poc_candidates'),('patch','find_patch_candidates')]:
        tasks.append(task(task_id=id,dependencies=['root'],allowed_tools=[name],
                          input_data={'steps':[{'name':name,'arguments':{'target':'CVE-2099-9999001'}}]}))
    outcome,_=run(tasks,tools)
    assert outcome.status=='succeeded'
    traces={t.task_id:t for t in outcome.traces}
    assert max(traces['poc'].start_time,traces['patch'].start_time) < min(traces['poc'].end_time,traces['patch'].end_time)


def test_parallel_limit_is_enforced_with_more_than_three_roots():
    active=0;peak=0;guard=threading.Lock()
    def tools(name,args,ctx):
        nonlocal active,peak
        with guard:active+=1;peak=max(peak,active)
        time.sleep(.04)
        with guard:active-=1
        return {'status':'success','data':{'ok':True}}
    outcome,_=run([task(task_id=f't{i}') for i in range(7)],tools)
    assert outcome.status=='succeeded' and peak==3


@pytest.mark.parametrize('status,want', [('failed','failed'),('no_result','partial')])
def test_failed_or_review_branch_blocks_dependencies_but_not_independent_tasks(status,want):
    def tools(n,a,c):
        return {'status':status,'data':{},'errors':[{'code':'SYNTHETIC_ERROR'}]} if a['target']=='CVE-2099-9999001' else {'status':'success','data':{'ok':True}}
    independent=task(task_id='independent',input_data={'steps':[{'name':'get_vulnerability','arguments':{'target':'CVE-2099-2222'}}]})
    outcome,stored=run([task(task_id='bad'),task(task_id='blocked',dependencies=['bad']),independent],tools)
    assert outcome.status==want
    assert stored.artifacts['blocked'].status=='BLOCKED' and not stored.artifacts['blocked'].tool_calls
    assert stored.artifacts['independent'].status=='SUCCESS'
    assert stored.traces['blocked'].start_time is None


def test_exception_in_executor_does_not_escape_scheduler():
    class Broken:
        def execute(self,*args,**kwargs):raise RuntimeError('private')
    outcome,_=run([task()],executor=Broken())
    assert outcome.status=='failed' and outcome.artifacts[0].errors[0]['code']=='EXECUTOR_FAILURE'
    assert 'private' not in outcome.model_dump_json()


def test_run_timeout_stops_real_worker_and_does_not_launch_queued_tasks(monkeypatch,tmp_path):
    from .test_process import supervisor
    outcome,stored=run([task(task_id=f't{i}') for i in range(3)],executor=supervisor(monkeypatch,tmp_path),
                       run_timeout_seconds=1,max_parallel=1)
    assert outcome.status=='timeout'
    assert stored.artifacts['t0'].status=='FAILED'
    assert stored.artifacts['t1'].status==stored.artifacts['t2'].status=='BLOCKED'
    assert not stored.traces['t1'].tools_called and not stored.traces['t2'].tools_called


def test_reserved_global_call_budget_prevents_any_execution_when_exceeded():
    with pytest.raises(ValueError):
        run([task(task_id=f't{i}',max_tool_calls=8) for i in range(5)])

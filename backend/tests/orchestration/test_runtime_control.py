import threading
import time
from contextlib import nullcontext
from uuid import uuid4
import pytest
from app.runtime.service import RuntimeService
from app.runtime.contracts import TaskPlan,TaskContract,RunOutcome


def input_plan():
    return TaskPlan(tasks=(TaskContract(task_id='need',task_type='input_required',description='Need target',
        input_data={'required_fields':['target']},allowed_tools=(),max_tool_calls=0),))


def test_windows_job_zero_accounting_is_not_exit_confirmation():
    from app.runtime.process import _WindowsJob,_Accounting
    import ctypes
    class Kernel:
        pending={11:True,12:True}
        def QueryInformationJobObject(self,handle,kind,out,size,returned):
            ctypes.cast(out,ctypes.POINTER(_Accounting)).contents.active=0
            return True
        def WaitForSingleObject(self,handle,timeout):return 258 if self.pending[handle] else 0
    job=_WindowsJob.__new__(_WindowsJob);job.dll=Kernel();job.handle=99;job._process_handles=[11,12]
    assert not job.empty()
    job.dll.pending[11]=False
    assert not job.empty()
    job.dll.pending[12]=False
    assert job.empty()


def test_windows_job_wait_failure_cannot_claim_cleanup():
    from app.runtime.process import _WindowsJob,_Accounting
    import ctypes
    class Kernel:
        def QueryInformationJobObject(self,handle,kind,out,size,returned):
            ctypes.cast(out,ctypes.POINTER(_Accounting)).contents.active=0
            return True
        def WaitForSingleObject(self,handle,timeout):return 0xffffffff
    job=_WindowsJob.__new__(_WindowsJob);job.dll=Kernel();job.handle=99;job._process_handles=[11]
    with pytest.raises(OSError):job.empty()


def test_windows_job_closes_all_owned_process_handles():
    from app.runtime.process import _WindowsJob
    class Kernel:
        closed=[]
        def CloseHandle(self,handle):self.closed.append(handle);return True
    job=_WindowsJob.__new__(_WindowsJob);job.dll=Kernel();job.handle=99;job._process_handles=[11,12]
    job.close();job.close()
    assert job.dll.closed==[11,12,99]


def test_windows_job_captures_owned_handles_before_termination():
    from app.runtime.process import _WindowsJob
    from ctypes import cast,POINTER,c_ulong,c_size_t,Structure
    from ctypes import wintypes
    class Ids(Structure):
        _fields_=[('assigned',wintypes.DWORD),('count',wintypes.DWORD),('ids',c_size_t*256)]
    class Kernel:
        events=[]
        def QueryInformationJobObject(self,handle,kind,out,size,returned):
            data=cast(out,POINTER(Ids)).contents;data.assigned=2;data.count=2;data.ids[0]=11;data.ids[1]=12
            return True
        def OpenProcess(self,access,inherit,pid):self.events.append(('open',pid));return pid*10
        def IsProcessInJob(self,process,job,out):cast(out,POINTER(wintypes.BOOL)).contents.value=True;return True
        def TerminateJobObject(self,handle,code):self.events.append(('terminate',handle));return True
        def CloseHandle(self,handle):return True
    job=_WindowsJob.__new__(_WindowsJob);job.dll=Kernel();job.handle=99;job._process_handles=[]
    job.terminate()
    assert job._process_handles==[110,120]
    assert job.dll.events==[('open',11),('open',12),('terminate',99)]


class Control:
    def __init__(self):self.runs=[];self.executor=None;self.completed=[];self.detached=False;self.deadline=time.monotonic()+1
    def check_start(self):pass
    def creation_guard(self):return nullcontext()
    def effective_deadline(self,value):return min(value,self.deadline)
    def run_started(self,saved):self.runs.append(saved.run_id)
    def attach_executor(self,executor):self.executor=executor
    def run_finished(self,saved):self.completed.append(saved.run_id)
    def detach_executor(self):self.detached=True


def test_control_receives_actual_run_and_executor(engine):
    ctl=Control();svc=RuntimeService(engine);svc.bind_execution_control(ctl);actor='control-'+uuid4().hex
    saved=svc.run_plan(input_plan(),actor,'control-'+uuid4().hex)
    assert ctl.runs==[saved.run_id] and ctl.completed==[saved.run_id]
    assert ctl.executor is not None and ctl.detached
    assert svc.read_trace(saved.run_id,actor).run_id==saved.run_id


def test_control_cannot_increase_runtime_deadline(engine):
    from app.runtime.contracts import RuntimePolicy
    ctl=Control();ctl.deadline=time.monotonic()+1000
    seen=[]
    from app.runtime.scheduler import Scheduler
    class CaptureScheduler(Scheduler):
        def run(self,graph,context,store):
            seen.append(context.deadline);return super().run(graph,context,store)
    class Service(RuntimeService):
        def _make_scheduler(self,plan):return CaptureScheduler()
    started=time.monotonic();svc=Service(engine,policy=RuntimePolicy(run_timeout_seconds=1));svc.bind_execution_control(ctl)
    svc.run_plan(input_plan(),'deadline-'+uuid4().hex,'deadline-'+uuid4().hex)
    assert seen[0]<=started+1.5


def test_cancel_before_start_creates_no_run(engine):
    from sqlalchemy import select,func
    from app.db import models as m
    from app.db.session import transaction
    ctl=Control()
    def aborted():raise RuntimeError('CANCELLED')
    ctl.check_start=aborted;svc=RuntimeService(engine);svc.bind_execution_control(ctl);actor='no-run-'+uuid4().hex
    with pytest.raises(RuntimeError,match='CANCELLED'):svc.run_plan(input_plan(),actor,'cancel-'+uuid4().hex)
    with transaction(engine) as db:
        assert db.scalar(select(func.count()).select_from(m.AgentRun).where(m.AgentRun.actor_principal==actor))==0


def test_default_runtime_has_unchanged_behavior(engine):
    svc=RuntimeService(engine);actor='default-'+uuid4().hex;key='default-'+uuid4().hex
    first=svc.run_plan(input_plan(),actor,key);second=svc.run_plan(input_plan(),actor,key)
    assert first.run_id==second.run_id and first.status==second.status


def test_cancel_after_planning_prevents_runtime_creation(engine):
    from tests.agents.investigation.test_end_to_end import plan_for
    from tests.agents.investigation.conftest import investigation_seed
    from tests.planner.fixtures import gateway_with_responses,cve_input
    from app.agents.investigation.service import IntelligenceInvestigationService
    seed=investigation_seed.__wrapped__(engine);gw,_,_=gateway_with_responses([plan_for(seed)])
    ids=[]
    class Observer:
        def creation_guard(self):
            from contextlib import nullcontext
            return nullcontext()
        def before_planning(self):pass
        def planner_created(self,saved):ids.append(saved.planner_run_id)
        def planner_completed(self,saved):assert saved.planning_status=='VALIDATED'
        def before_runtime(self):raise RuntimeError('CANCELLED')
    try:
        svc=IntelligenceInvestigationService(engine,gw,observer=Observer())
        with pytest.raises(RuntimeError,match='CANCELLED'):svc.plan_and_run(cve_input(target=seed.cve),seed.actor)
        assert len(ids)==1 and svc.read_planner_trace(ids[0],seed.actor).validation_status=='VALIDATED'
        assert svc.read_planner_trace(ids[0],seed.actor).runtime_run_id is None
    finally:gw.close()


def test_durable_cancel_reaches_only_bound_executor_and_monitor_closes(engine):
    from app.orchestration.control import InvestigationControl,InvestigationAbort
    from app.orchestration.store import PostgresInvestigationStore
    from tests.orchestration.test_contracts_scope import request
    store=PostgresInvestigationStore(engine);actor='monitor-'+uuid4().hex;owned=store.claim(request(),actor=actor)
    cancelled=threading.Event();other=threading.Event()
    class Executor:
        def cancel_all(self):cancelled.set()
    second=store.claim(request(),actor='other-'+uuid4().hex)
    class OtherExecutor:
        def cancel_all(self):other.set()
    other_ctl=InvestigationControl(store,second);other_ctl.attach_executor(OtherExecutor());other_ctl.start()
    ctl=InvestigationControl(store,owned);ctl.attach_executor(Executor());ctl.start()
    try:
        store.request_cancel(owned.logical_id,actor=actor)
        assert cancelled.wait(3) and not other.is_set()
        with pytest.raises(InvestigationAbort,match='CANCELLED'):ctl.check_start()
    finally:ctl.close();other_ctl.close()
    assert not ctl.monitor_alive and not other_ctl.monitor_alive


def test_runtime_creation_and_cancel_have_atomic_order(engine):
    from app.orchestration.control import InvestigationControl
    from app.orchestration.store import PostgresInvestigationStore
    from tests.orchestration.test_contracts_scope import request
    store=PostgresInvestigationStore(engine);actor='order-'+uuid4().hex;owned=store.claim(request(),actor=actor)
    ctl=InvestigationControl(store,owned);entered=threading.Event();done=threading.Event()
    def cancel():
        entered.set();store.request_cancel(owned.logical_id,actor=actor);done.set()
    with ctl.creation_guard():
        thread=threading.Thread(target=cancel);thread.start();assert entered.wait(1)
        assert not done.wait(.15)
        ctl.check_start()
    thread.join(3);assert done.is_set()


def test_upper_deadline_blocks_new_stage(engine):
    from app.orchestration.control import InvestigationControl,InvestigationAbort
    from app.orchestration.store import PostgresInvestigationStore
    from tests.orchestration.test_contracts_scope import request
    store=PostgresInvestigationStore(engine);owned=store.claim(request(investigation_options={'timeout_seconds':1}),actor='timeout-'+uuid4().hex)
    ctl=InvestigationControl(store,owned)
    # Inject only the clock boundary; all stored state/control checks stay real.
    ctl.deadline=time.monotonic()-1
    with pytest.raises(InvestigationAbort,match='DEADLINE_EXCEEDED'):ctl.check_start()
def test_planner_creation_uses_same_cancel_guard_as_runtime(engine,monkeypatch):
    from contextlib import contextmanager
    import threading
    from app.planner.trace import PlannerTraceStore
    from app.orchestration.store import PostgresInvestigationStore
    from app.orchestration.service import InvestigationOrchestrator
    from tests.orchestration.fixtures import scenario
    state=threading.local();old_guard=PostgresInvestigationStore.creation_guard;old_create=PlannerTraceStore.create
    @contextmanager
    def guarded(self,*a,**k):
        with old_guard(self,*a,**k):
            state.guarded=True
            try:yield
            finally:state.guarded=False
    def create(self,*a,**k):
        assert getattr(state,'guarded',False),'Planner creation must linearize with cancel'
        return old_create(self,*a,**k)
    monkeypatch.setattr(PostgresInvestigationStore,'creation_guard',guarded)
    monkeypatch.setattr(PlannerTraceStore,'create',create)
    seed,request,gw,_,_=scenario(engine)
    try:assert InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor).status.overall_status=='SUCCEEDED'
    finally:gw.close()

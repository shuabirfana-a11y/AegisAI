"""Request-local cooperative control; delegates process cleanup to old executors."""
from threading import Event,Thread,RLock
import time
from app.orchestration.contracts import StageEvent,TERMINAL_STAGES
from app.utils.time import utcnow


class InvestigationAbort(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)


class InvestigationControl:
    def __init__(self,store,claim):
        self.store=store;self.id=claim.logical_id;self.actor=claim.context.owner;self.token=claim.worker_token
        self.policy=store.policy
        remaining=max(0,(claim.context.deadline_at-utcnow()).total_seconds())
        self.deadline=time.monotonic()+remaining
        self.cancel_event=Event();self._halt=Event();self._lock=RLock();self._executor=None;self._code=None
        self._monitor=None;self.model_calls=0
        self.last_context=claim.context

    def _remember(self,context):
        with self._lock:
            if context.revision>=self.last_context.revision:self.last_context=context
        return context

    @property
    def abort_code(self):
        with self._lock:return self._code

    @property
    def monitor_alive(self):return self._monitor is not None and self._monitor.is_alive()

    def _abort(self,code):
        with self._lock:
            if self._code is None:self._code=code
            self.cancel_event.set();executor=self._executor
        if executor is not None and hasattr(executor,'cancel_all'):executor.cancel_all()

    def check_start(self):
        if self.abort_code:raise InvestigationAbort(self.abort_code)
        if time.monotonic()>=self.deadline:
            self._abort('DEADLINE_EXCEEDED');raise InvestigationAbort(self.abort_code)
        try:context=self.store.read(self.id,actor=self.actor)
        except Exception:
            self._abort('CONTROL_STORE_FAILED');raise InvestigationAbort(self.abort_code) from None
        self._remember(context)
        if context.cancel_requested_at is not None:
            self._abort('CANCELLED');raise InvestigationAbort(self.abort_code)
        if context.current_stage in TERMINAL_STAGES:raise InvestigationAbort('ALREADY_TERMINAL')

    def creation_guard(self):return self.store.creation_guard(self.id,actor=self.actor)
    def effective_deadline(self,runtime_deadline):return min(runtime_deadline,self.deadline)

    def attach_executor(self,executor):
        with self._lock:
            self._executor=executor;aborted=self._code is not None
        if aborted and hasattr(executor,'cancel_all'):executor.cancel_all()
        else:
            try:self.check_start()
            except InvestigationAbort:
                # Let the original Scheduler/Executor record real cancelled tasks.
                # Do not bypass scheduling with fabricated task outcomes.
                if hasattr(executor,'cancel_all'):executor.cancel_all()

    def detach_executor(self):
        with self._lock:self._executor=None

    def event(self,stage,code,*,overall_status=None,**updates):
        for attempt in range(4):
            context=self.store.read(self.id,actor=self.actor)
            try:
                return self._remember(self.store.advance(self.id,actor=self.actor,worker_token=self.token,
                    expected_revision=context.revision,event=StageEvent(stage=stage,code=code,
                        overall_status=overall_status),**updates))
            except ValueError as exc:
                if str(exc)!='STALE_REVISION' or attempt==3:raise

    def planner_created(self,saved):
        self.event('PLANNING','PLANNER_CREATED',planner_run_id=saved.planner_run_id)

    def before_planning(self):self.check_start()

    def planner_completed(self,saved):
        self.event('PLANNING','PLANNER_'+saved.planning_status)

    def before_runtime(self):self.check_start()
    def for_stage(self,stage):return StageControl(self,stage)

    def start(self):
        if self._monitor is not None:raise ValueError('CONTROL_ALREADY_STARTED')
        self._monitor=Thread(target=self._watch,name='aegis-investigation-'+str(self.id),daemon=True)
        self._monitor.start()

    def _watch(self):
        heartbeat=time.monotonic()
        while not self._halt.wait(self.policy.poll_seconds):
            try:
                self.check_start()
                if time.monotonic()-heartbeat>=self.policy.heartbeat_seconds:
                    self.store.heartbeat(self.id,actor=self.actor,worker_token=self.token);heartbeat=time.monotonic()
            except InvestigationAbort as exc:
                if exc.code!='ALREADY_TERMINAL':self._abort(exc.code)
                return
            except Exception:
                self._abort('CONTROL_STORE_FAILED');return

    def close(self):
        self._halt.set()
        if self._monitor is not None:self._monitor.join(timeout=32)
        if self.monitor_alive:raise InvestigationAbort('CONTROL_CLEANUP_FAILED')
        self.detach_executor()


class StageControl:
    def __init__(self,parent,stage):
        if stage not in ('INVESTIGATING','VERIFYING','ANALYZING'):raise ValueError('INVALID_CONTROL_STAGE')
        self.parent=parent;self.stage=stage
    def creation_guard(self):return self.parent.creation_guard()
    def check_start(self):return self.parent.check_start()
    def effective_deadline(self,value):return self.parent.effective_deadline(value)
    def attach_executor(self,executor):return self.parent.attach_executor(executor)
    def detach_executor(self):return self.parent.detach_executor()
    def run_started(self,saved):
        field={'INVESTIGATING':'investigation_run_id','VERIFYING':'verification_run_id','ANALYZING':'analysis_run_id'}[self.stage]
        self.parent.event(self.stage,'RUN_CREATED',**{field:saved.run_id})
    def run_finished(self,saved):self.parent.event(self.stage,'RUN_'+saved.status)


class ControlledGateway:
    """Borrowed Gateway: check before each model attempt; cannot interrupt HTTP."""
    def __init__(self,gateway,control):self._gateway=gateway;self._control=control
    def __getattr__(self,name):return getattr(self._gateway,name)
    def generate_structured(self,*args,**kwargs):
        self._control.check_start()
        if self._control.model_calls>=2:raise InvestigationAbort('MODEL_BUDGET_EXCEEDED')
        self._control.model_calls+=1
        return self._gateway.generate_structured(*args,**kwargs)

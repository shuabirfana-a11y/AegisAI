"""Opt-in synchronous service; the existing Assistant POST remains unchanged.

Rules are replaceable only in a future approved phase. A supplied Model Gateway
is borrowed, not instantiated or called by these deterministic templates.
"""
import time
from contextlib import nullcontext
from uuid import UUID
from app.assistant.contracts import QueryRequest
from app.runtime.contracts import TaskPlan, RuntimePolicy, RunContext
from app.runtime.planning import build_plan
from app.runtime.graph import compile_graph
from app.runtime.scheduler import Scheduler
from app.runtime.store import PostgresRuntimeStore


class RuntimeService:
    def __init__(self, engine, *, policy=None, model_gateway=None):
        self.engine=engine
        self.policy=policy or RuntimePolicy()
        self.model_gateway=model_gateway
        self.store=PostgresRuntimeStore(engine)
        self.execution_control=None

    def bind_execution_control(self,control):
        """Bind only to a request-local service instance before execution."""
        self.execution_control=control

    def run(self, request: QueryRequest, actor: str):
        captured=QueryRequest.model_validate_json(request.model_dump_json())
        plan=build_plan(captured,self.policy)
        return self._run(plan,actor,captured.request_key,
                         captured.model_dump(mode='json',exclude={'request_key'}))

    def run_plan(self, plan: TaskPlan, actor: str, request_key: str):
        return self._run(plan,actor,request_key,{'question':'Structured runtime plan'})

    def _make_scheduler(self, plan: TaskPlan) -> Scheduler:
        """Compatibility seam; the default executor and scheduling stay intact."""
        return Scheduler()

    def _run(self, plan, actor, request_key, request_data):
        if not isinstance(actor,str) or not 1<=len(actor)<=150:
            raise ValueError('Valid authenticated actor required')
        control=self.execution_control
        with control.creation_guard() if control is not None else nullcontext():
            if control is not None:control.check_start()
            graph=compile_graph(plan,self.policy)
            deadline=time.monotonic()+self.policy.run_timeout_seconds
            if control is not None:deadline=min(deadline,control.effective_deadline(deadline))
            captured=TaskPlan.model_validate_json(graph.plan_json)
            snapshot,fresh=self.store.create_run(request_data,captured,actor,request_key)
            if control is not None:control.run_started(snapshot)
            if not fresh:return snapshot
        context=RunContext(run_id=snapshot.run_id,trace_id=snapshot.trace_id,actor=actor,
            policy=self.policy,permissions=self.policy.permissions,deadline=deadline,
            database_url=self.engine.url.render_as_string(hide_password=False))
        try:
            scheduler=self._make_scheduler(captured)
            if control is not None:control.attach_executor(scheduler.executor)
            outcome=scheduler.run(graph,context,self.store)
            saved=self.store.finish_run(snapshot.run_id,outcome)
            if control is not None:control.run_finished(saved)
            return saved
        finally:
            if control is not None:control.detach_executor()

    def read_trace(self, run_id: UUID, actor: str):
        return self.store.read_trace(run_id,actor)

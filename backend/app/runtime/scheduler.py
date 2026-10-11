"""Bounded ready-queue scheduling; only accepted SUCCESS unlocks dependencies."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import time
from app.runtime.contracts import (TaskState as S, TERMINAL, TaskTrace, TaskArtifact,
                                   WorkerContext, RunOutcome, ExecutionOutcome)
from app.runtime.executor import failure, validate_outcome
from app.runtime.process import ProcessSupervisor
from app.runtime.states import transition
from app.utils.time import utcnow


class Scheduler:
    def __init__(self, executor=None):
        self.executor=executor or ProcessSupervisor()

    def run(self, graph, context, store) -> RunOutcome:
        tasks={t.task_id:t for t in graph.tasks}
        traces={key:TaskTrace(run_id=context.run_id,task_id=key,task_type=t.task_type,
                              dependencies=t.dependencies) for key,t in tasks.items()}
        artifacts={};active={}
        def change(key,target):
            previous=traces[key]
            state=transition(previous.status,target)
            now=utcnow()
            data={'status':state,'transitions':[*previous.transitions,
                {'from':previous.status.value,'state':state.value,'at':now.isoformat()}]}
            if state==S.RUNNING:data['start_time']=now
            traces[key]=previous.model_copy(update=data)
        def persist(key,artifact=None,receipts=()):
            store.save_task(context.run_id,tasks[key],artifact,traces[key],receipts)
        def blocked(key,code):
            change(key,S.BLOCKED)
            artifact=TaskArtifact(run_id=context.run_id,task_id=key,status=S.BLOCKED,
                end_time=utcnow(),errors=[{'code':code,'message':'Task was not executed'}],
                unresolved_questions=['Required successful dependency or run budget unavailable'])
            finish(key,ExecutionOutcome(artifact=artifact),changed=True)
        def finish(key,outcome,changed=False):
            artifact=outcome.artifact
            if not changed:change(key,artifact.status)
            traces[key]=traces[key].model_copy(update={'end_time':artifact.end_time,
                'artifact_id':artifact.artifact_id,'error':artifact.errors,
                'tools_called':artifact.tool_calls})
            artifacts[key]=artifact
            persist(key,artifact,outcome.receipts)
        for key in tasks:
            change(key,S.PENDING);persist(key)
        pool=ThreadPoolExecutor(max_workers=context.policy.max_parallel,thread_name_prefix='aegis-runtime')
        try:
            while len(artifacts)<len(tasks):
                for key,task in tasks.items():
                    if traces[key].status not in (S.PENDING,S.READY):continue
                    if time.monotonic()>=context.deadline:
                        blocked(key,'RUN_TIMEOUT');continue
                    failed_deps=[dep for dep in task.dependencies if dep in artifacts and artifacts[dep].status!=S.SUCCESS]
                    if failed_deps:
                        blocked(key,'DEPENDENCY_BLOCKED');continue
                    if not all(dep in artifacts for dep in task.dependencies):continue
                    if traces[key].status==S.PENDING:
                        change(key,S.READY);persist(key)
                    if len(active)>=context.policy.max_parallel:continue
                    worker=WorkerContext(run_id=context.run_id,trace_id=context.trace_id,actor=context.actor,
                        permissions=context.permissions & context.policy.permissions,
                        deadline=min(context.deadline,time.monotonic()+task.timeout_seconds))
                    change(key,S.RUNNING);persist(key)
                    future=pool.submit(self.executor.execute,task,worker,
                        {dep:artifacts[dep] for dep in task.dependencies},database_url=context.database_url)
                    active[future]=(key,worker)
                if active:
                    completed,_=wait(active,timeout=.05,return_when=FIRST_COMPLETED)
                    for future in completed:
                        key,worker=active.pop(future)
                        try:
                            outcome=validate_outcome(tasks[key],worker,future.result())
                        except Exception:
                            outcome=ExecutionOutcome(artifact=failure(tasks[key],worker,'EXECUTOR_FAILURE',started=traces[key].start_time))
                        finish(key,outcome)
                elif len(artifacts)<len(tasks):
                    raise ValueError('Validated graph stalled')
        except Exception:
            if hasattr(self.executor,'cancel_all'):self.executor.cancel_all()
            raise
        finally:
            pool.shutdown(wait=True,cancel_futures=True)
        values=tuple(artifacts[key] for key in tasks)
        errors={e.get('code') for a in values for e in a.errors}
        status='timeout' if errors & {'TASK_TIMEOUT','RUN_TIMEOUT','TOOL_TIMEOUT'} else (
            'failed' if any(a.status==S.FAILED for a in values) else
            'partial' if any(a.status!=S.SUCCESS for a in values) else 'succeeded')
        return RunOutcome(run_id=context.run_id,artifacts=values,
                          traces=tuple(traces[key] for key in tasks),status=status)

import time
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from app.assistant.handoff import validate_handoff
from app.assistant.contracts import TaskArtifact
from app.utils.time import utcnow

def levels(tasks):
    if len(tasks)>16:raise ValueError('Graph exceeds task budget')
    by_id={t.task_id:t for t in tasks}
    if len(by_id)!=len(tasks):raise ValueError('Duplicate task identity')
    if any(dep not in by_id for t in tasks for dep in t.dependencies):raise ValueError('Unknown dependency')
    done=set();result=[]
    while len(done)<len(tasks):
        ready=[t for t in tasks if t.task_id not in done and set(t.dependencies)<=done]
        if not ready or len(result)>=8:raise ValueError('Cycle or graph depth limit')
        result.append(ready);done.update(t.task_id for t in ready)
    return result

def failed(task,trace,code):
    now=utcnow()
    return TaskArtifact(task_id=task.task_id,agent=task.task_type,status='blocked',result={},trace_id=trace,
        errors=[{'code':code,'message':'Task dependency or handoff was not accepted'}],started_at=now,finished_at=now)

def run_graph(tasks,execute,trace_id,*,deadline=None,initial=None,on_update=None,evidence_attested=None,claims_attested=frozenset()):
    accepted=dict(initial or {});outputs=dict(accepted);deadline=deadline or time.monotonic()+120
    for layer in levels(tasks):
        ready=[]
        for t in layer:
            if t.task_id in outputs:continue
            if time.monotonic()>=deadline or any(dep not in accepted for dep in t.dependencies):outputs[t.task_id]=failed(t,trace_id,'DEPENDENCY_BLOCKED')
            else:ready.append(t)
        if ready:
            pool=ThreadPoolExecutor(max_workers=3,thread_name_prefix='aegis-role')
            try:
                futures={pool.submit(execute,t,dict(accepted)):t for t in ready}
                expires={f:min(deadline,time.monotonic()+t.timeout) for f,t in futures.items()}
                pending=set(futures)
                while pending:
                    completed,_=wait(pending,timeout=max(0,min(expires[f] for f in pending)-time.monotonic()),return_when=FIRST_COMPLETED)
                    for future in list(pending):
                        t=futures[future]
                        if future in completed:
                            try:
                                value=future.result();outputs[t.task_id]=value
                                accepted[t.task_id]=validate_handoff(t,value,trace_id,accepted,evidence_attested=evidence_attested,claims_attested=claims_attested)
                            except Exception:outputs[t.task_id]=failed(t,trace_id,'HANDOFF_REJECTED')
                        elif time.monotonic()>=expires[future]:
                            future.cancel();outputs[t.task_id]=failed(t,trace_id,'TASK_TIMEOUT')
                        else:continue
                        pending.remove(future)
                        if on_update:on_update(t,outputs[t.task_id])
            finally:pool.shutdown(wait=False,cancel_futures=True)
    return [outputs[t.task_id] for t in tasks]

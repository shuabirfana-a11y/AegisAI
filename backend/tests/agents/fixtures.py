"""SYNTHETIC framework inputs. No production professional implementation."""
from uuid import uuid4
from app.runtime.contracts import TaskContract, WorkerContext
import time


def task(task_id='lookup', name='get_vulnerability', arguments=None, deps=(), **overrides):
    return TaskContract(task_id=task_id, description='SYNTHETIC framework protocol',
        input_data={'steps':[{'name':name,'arguments':arguments or {'target':'CVE-2099-9999001'}}]},
        allowed_tools=[name], dependencies=deps, max_tool_calls=1, **overrides)


def context(**values):
    return WorkerContext(**{'run_id':uuid4(),'trace_id':uuid4(), 'actor':'SYNTHETIC-agent-owner',
                            'deadline':time.monotonic()+30, **values})


def outcome(item=None, ctx=None, deps=None, *, response=None):
    from app.runtime.executor import WorkerExecutor
    from app.runtime.contracts import ToolReceipt, ExecutionOutcome
    from app.tooling.gateway import ToolGateway
    events=[];item=item or task();ctx=ctx or context()
    executor=WorkerExecutor(ToolGateway(executor=lambda name,args,tool_context: response or {
        'status':'success','data':{'SYNTHETIC':True},
        'evidence_refs':[{'source_url':'https://example.invalid/SYNTHETIC','verified':False}]}), events.append)
    artifact=executor.execute(item,ctx,deps or {})
    return ExecutionOutcome(artifact=artifact,receipts=[ToolReceipt.model_validate(e['receipt'])
        for e in events if e['kind']=='tool_finished'])

"""Test-only doubles; production defaults always supervise actual worker processes."""
from app.runtime.contracts import ExecutionOutcome, ToolReceipt
from app.runtime.executor import WorkerExecutor
from app.tooling.gateway import ToolGateway


class MemoryStore:
    def __init__(self):
        self.traces = {}
        self.artifacts = {}

    def save_task(self, run_id, task, artifact, trace, receipts):
        self.traces[task.task_id] = trace
        if artifact:self.artifacts[task.task_id] = artifact


class InlineExecutor:
    def __init__(self, tool_executor):
        self.tool_executor = tool_executor

    def execute(self, task, context, dependencies, *, database_url=None):
        events = []
        worker = WorkerExecutor(gateway=ToolGateway(executor=self.tool_executor), emit=events.append)
        artifact = worker.execute(task, context, dependencies)
        receipts = [ToolReceipt.model_validate(e['receipt']) for e in events if e['kind']=='tool_finished']
        return ExecutionOutcome(artifact=artifact,receipts=receipts)

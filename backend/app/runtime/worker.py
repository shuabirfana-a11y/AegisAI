"""Fixed JSONL task worker; no user code, shell, model SDK or dynamic tools."""
import json
import sys
from app.runtime.contracts import TaskContract, WorkerContext, TaskArtifact, WIRE_LIMIT
from app.runtime.executor import WorkerExecutor


def main():
    raw = sys.stdin.buffer.read(WIRE_LIMIT+1)
    if len(raw) > WIRE_LIMIT:
        raise ValueError('Input limit')
    request = json.loads(raw)
    task = TaskContract.model_validate(request['task'])
    context = WorkerContext.model_validate(request['context'])
    dependencies = {key: TaskArtifact.model_validate(value)
                    for key, value in request['dependencies'].items()}
    def emit(event):
        sys.stdout.write(json.dumps(event, ensure_ascii=True, allow_nan=False) + '\n')
        sys.stdout.flush()
    artifact = WorkerExecutor(emit=emit).execute(task, context, dependencies)
    emit({'kind': 'artifact', 'artifact': artifact.model_dump(mode='json')})


if __name__ == '__main__':
    main()

"""Controlled test subprocess only; no user-selected worker is accepted in production."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

request = json.loads(sys.stdin.buffer.read())
mode = request['task']['description']
folder = Path(os.environ['AEGIS_RUNTIME_TEST_FOLDER'])
if mode == 'oversize':
    sys.stdout.buffer.write(b'x' * (5 * 1024 * 1024));sys.stdout.flush()
    time.sleep(10)
elif mode == 'crash':
    raise SystemExit(3)
elif mode == 'malformed':
    print('{bad json', flush=True)
elif mode == 'evidence_oversize':
    from app.runtime.contracts import TaskContract,WorkerContext
    from app.runtime.executor import WorkerExecutor
    from app.tooling.gateway import ToolGateway
    def emit(event):print(json.dumps(event),flush=True)
    gateway=ToolGateway(executor=lambda n,a,c:{'status':'success','data':{'found':True},
        'evidence_refs':[{'raw_document_id':'00000000-0000-0000-0000-000000000001',
                         'locator':{'excerpt':'x'*600000},'verified':False}]})
    artifact=WorkerExecutor(gateway=gateway,emit=emit).execute(
        TaskContract.model_validate(request['task']),WorkerContext.model_validate(request['context']),{})
    emit({'kind':'artifact','artifact':artifact.model_dump(mode='json')})
else:
    child = subprocess.Popen([sys.executable, '-c',
        'import time,pathlib,sys;time.sleep(8);pathlib.Path(sys.argv[1]).write_text("late")',
        str(folder / 'late.txt')])
    # The final path is the readiness signal; publish only complete PID JSON.
    pending=folder / 'pids.pending'
    pending.write_text(json.dumps([os.getpid(), child.pid]))
    pending.replace(folder / 'pids.json')
    time.sleep(20)

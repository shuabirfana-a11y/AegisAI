"""Uses OS processes; no fake Future cancellation can satisfy these assertions."""
import os
from pathlib import Path
import time
import json
import pytest
from .test_contracts_plan import task
from .test_executor import context


def supervisor(monkeypatch, folder):
    from app.runtime.process import ProcessSupervisor
    fixture = Path(__file__).with_name('fixtures') / 'slow_worker.py'
    monkeypatch.setenv('AEGIS_RUNTIME_TEST_FOLDER', str(folder))
    monkeypatch.setattr(ProcessSupervisor, '_command', lambda self: [__import__('sys').executable, str(fixture)])
    return ProcessSupervisor()


def test_timeout_really_terminates_worker_and_child(monkeypatch, tmp_path):
    from app.runtime.process import process_alive
    instance = supervisor(monkeypatch, tmp_path)
    begin = time.monotonic()
    got = instance.execute(task(timeout_seconds=1), context(deadline=begin+1), {})
    assert got.artifact.status == 'FAILED'
    assert got.artifact.errors[0]['code'] == 'TASK_TIMEOUT'
    assert got.cleanup_verified and time.monotonic()-begin < 3.5
    pids = json.loads((tmp_path/'pids.json').read_text())
    assert len(pids) == 2 and all(not process_alive(pid) for pid in pids)
    assert not (tmp_path/'late.txt').exists()


@pytest.mark.parametrize('mode,code', [('oversize','WORKER_OUTPUT_LIMIT'), ('crash','WORKER_FAILED'), ('malformed','WORKER_PROTOCOL_ERROR')])
def test_worker_failure_is_explicit_and_reaped(mode, code, monkeypatch, tmp_path):
    got = supervisor(monkeypatch, tmp_path).execute(task(description=mode), context(), {})
    assert got.artifact.status == 'FAILED' and got.artifact.errors[0]['code'] == code
    assert got.cleanup_verified


def test_isolation_failure_does_not_run_uncontrolled_worker(monkeypatch, tmp_path):
    from app.runtime import process
    monkeypatch.setattr(process, 'create_isolation', lambda: (_ for _ in ()).throw(OSError('secret')))
    got = supervisor(monkeypatch, tmp_path).execute(task(), context(), {})
    assert got.artifact.errors[0]['code'] == 'TASK_ISOLATION_UNAVAILABLE'
    assert not (tmp_path/'pids.json').exists()
    assert 'secret' not in got.model_dump_json()


def test_supervisor_cancellation_terminates_active_process_tree(monkeypatch, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from app.runtime.process import process_alive
    instance = supervisor(monkeypatch,tmp_path)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(instance.execute,task(),context(),{})
        until=time.monotonic()+2
        while not (tmp_path/'pids.json').exists() and time.monotonic()<until:
            time.sleep(.01)
        assert (tmp_path/'pids.json').exists()
        instance.cancel_all()
        outcome=future.result(timeout=2)
    assert outcome.artifact.errors[0]['code']=='RUN_CANCELLED' and outcome.cleanup_verified
    assert all(not process_alive(pid) for pid in json.loads((tmp_path/'pids.json').read_text()))


def test_exit_observed_after_deadline_cannot_return_late_success(monkeypatch):
    """Deterministically reproduce an exit between deadline and poll observation."""
    import io
    from .test_executor import execute
    from app.runtime import process
    item=task()
    ctx=context()
    artifact,events=execute({'status':'success','data':{'found':True}},context_=ctx)
    wire=b''.join((json.dumps(event)+'\n').encode() for event in
        [*events,{'kind':'artifact','artifact':artifact.model_dump(mode='json')}])
    clock={'now':9.995}
    class Completed:
        returncode=None
        stdin=io.BytesIO()
        stdout=io.BytesIO(wire)
        stderr=io.BytesIO()
        def poll(self):
            clock['now']=10.009
            self.returncode=0
            return 0
        def wait(self,**kwargs):return 0
        def kill(self):self.returncode=-1
    class Isolated:
        def attach(self,p):pass
        def terminate(self):pass
        def empty(self):return True
        def close(self):pass
    monkeypatch.setattr(process,'create_isolation',Isolated)
    monkeypatch.setattr(process.subprocess,'Popen',lambda *a,**k:Completed())
    monkeypatch.setattr(process.time,'monotonic',lambda:clock['now'])
    got=process.ProcessSupervisor().execute(item,ctx.model_copy(update={'deadline':10.0}),{})
    assert got.artifact.status=='FAILED'
    assert got.artifact.errors[0]['code']=='TASK_TIMEOUT'
    assert len(got.receipts)==1 and got.cleanup_verified


def test_oversized_evidence_retains_complete_receipt_and_explicit_failure(monkeypatch,tmp_path):
    got=supervisor(monkeypatch,tmp_path).execute(task(description='evidence_oversize'),context(),{})
    assert got.artifact.status=='FAILED'
    assert got.artifact.errors[0]['code']=='ARTIFACT_SIZE_LIMIT'
    assert len(got.receipts)==1
    assert len(got.receipts[0].envelope.evidence_refs[0]['locator']['excerpt'])==600000
    assert got.artifact.result['evidence_storage']=='tool_receipts'
    assert got.artifact.result['evidence_count']==1
    assert got.cleanup_verified

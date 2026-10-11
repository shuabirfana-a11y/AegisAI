import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.runtime.process import ProcessSupervisor, process_alive
from app.agents.investigation.agent import IntelligenceInvestigationAgent
from tests.agents.investigation.test_agent import request


def isolated_agent(monkeypatch, folder):
    fixture=Path(__file__).parents[2]/'runtime'/'fixtures'/'slow_worker.py'
    monkeypatch.setenv('AEGIS_RUNTIME_TEST_FOLDER',str(folder))
    monkeypatch.setattr(ProcessSupervisor,'_command',lambda self:[__import__('sys').executable,str(fixture)])
    return IntelligenceInvestigationAgent()


def test_investigation_timeout_reaps_actual_process_tree(monkeypatch,tmp_path):
    a=isolated_agent(monkeypatch,tmp_path);req=request(timeout_seconds=1)
    got=a.investigate(req)
    assert got.artifact.status=='FAILED' and got.cleanup_verified
    assert got.artifact.errors[0]['code']=='TASK_TIMEOUT'
    assert all(not process_alive(pid) for pid in json.loads((tmp_path/'pids.json').read_text()))
    assert not (tmp_path/'late.txt').exists()


def test_investigation_cancel_reaps_actual_process_tree(monkeypatch,tmp_path):
    a=isolated_agent(monkeypatch,tmp_path);req=request()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(a.investigate,req)
        until=time.monotonic()+3
        while not (tmp_path/'pids.json').exists() and time.monotonic()<until:time.sleep(.01)
        assert (tmp_path/'pids.json').exists()
        a.cancel_all();got=future.result(timeout=3)
    assert got.artifact.errors[0]['code']=='RUN_CANCELLED' and got.cleanup_verified
    assert all(not process_alive(pid) for pid in json.loads((tmp_path/'pids.json').read_text()))


def test_shared_process_fixture_publishes_complete_readiness_atomically(monkeypatch,tmp_path):
    import io,runpy,sys,subprocess
    from types import SimpleNamespace
    fixture=Path(__file__).parents[2]/'runtime'/'fixtures'/'slow_worker.py'
    ready=tmp_path/'pids.json';original_write=Path.write_text
    def writing(path,content,*args,**kwargs):
        if path.name in ('pids.json','pids.pending'):
            with path.open('w',encoding='utf-8') as stream:
                # Simulate cancellation exactly between creation and content write.
                assert not ready.exists(),'Readiness published before complete PID JSON'
                return stream.write(content)
        return original_write(path,content,*args,**kwargs)
    monkeypatch.setenv('AEGIS_RUNTIME_TEST_FOLDER',str(tmp_path))
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(buffer=io.BytesIO(b'{"task":{"description":"SYNTHETIC"}}')))
    monkeypatch.setattr(subprocess,'Popen',lambda *args,**kwargs:SimpleNamespace(pid=12345))
    monkeypatch.setattr(time,'sleep',lambda seconds:None)
    monkeypatch.setattr(Path,'write_text',writing)
    runpy.run_path(str(fixture))
    assert len(json.loads(ready.read_text()))==2

"""Check actual worker/descendant PIDs, not merely Future cancellation."""
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from app.agents.artifacts import AgentExecutionRequest
from app.runtime.process import ProcessSupervisor,process_alive
from tests.agents.fixtures import context
from tests.agents.analysis.helpers import module
from tests.agents.analysis.test_agent import task


def isolated(monkeypatch,tmp_path):
    fixture=Path(__file__).parents[2]/'runtime/fixtures/slow_worker.py'
    monkeypatch.setenv('AEGIS_RUNTIME_TEST_FOLDER',str(tmp_path))
    monkeypatch.setattr(ProcessSupervisor,'_command',lambda self:[__import__('sys').executable,str(fixture)])
    return module('agent').SecurityAnalysisAgent()


def test_analysis_timeout_reaps_worker_and_descendant(monkeypatch,tmp_path):
    agent=isolated(monkeypatch,tmp_path)
    result=agent.analyze(AgentExecutionRequest(task=task().model_copy(update={'timeout_seconds':1}),
        context=context(deadline=time.monotonic()+1)))
    assert result.artifact.errors[0]['code']=='TASK_TIMEOUT' and result.cleanup_verified
    assert all(not process_alive(pid) for pid in json.loads((tmp_path/'pids.json').read_text()))
    assert not (tmp_path/'late.txt').exists()


@pytest.mark.parametrize('attempt',range(3))
def test_analysis_cancel_reaps_owned_tree_and_isolates_next_run(monkeypatch,tmp_path,attempt):
    prototype=isolated(monkeypatch,tmp_path);run_id=uuid4();agent=prototype.for_run(run_id)
    other=prototype.for_run(uuid4())
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(agent.analyze,AgentExecutionRequest(task=task(),context=context(run_id=run_id)))
        deadline=time.monotonic()+4
        while not (tmp_path/'pids.json').exists() and time.monotonic()<deadline:time.sleep(.01)
        assert (tmp_path/'pids.json').exists()
        pids=json.loads((tmp_path/'pids.json').read_text());assert all(process_alive(pid) for pid in pids)
        agent.cancel_all();result=future.result(timeout=4)
    assert result.artifact.errors[0]['code']=='RUN_CANCELLED' and result.cleanup_verified
    assert all(not process_alive(pid) for pid in pids)
    assert not other._cancelled.is_set() and not other.supervisor._cancelled.is_set()
    assert not (tmp_path/'late.txt').exists()


def test_malformed_worker_preserves_failure_not_safe(monkeypatch,tmp_path):
    agent=isolated(monkeypatch,tmp_path)
    result=agent.analyze(AgentExecutionRequest(task=task().model_copy(update={'description':'malformed'}),context=context()))
    assert result.artifact.status=='FAILED' and result.artifact.errors[0]['code']=='WORKER_PROTOCOL_ERROR'
    assert result.cleanup_verified

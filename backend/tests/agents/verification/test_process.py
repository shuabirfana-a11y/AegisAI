"""Actual OS processes must terminate; a Future cancellation is insufficient."""
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.agents.artifacts import AgentExecutionRequest
from app.agents.verification.agent import EvidenceVerificationAgent
from app.runtime.contracts import TaskContract
from uuid import uuid4
from app.runtime.process import ProcessSupervisor,process_alive
from tests.agents.verification.test_agent import task
from tests.agents.fixtures import context


def isolated(monkeypatch,tmp_path):
    fixture=Path(__file__).parents[2]/'runtime/fixtures/slow_worker.py'
    monkeypatch.setenv('AEGIS_RUNTIME_TEST_FOLDER',str(tmp_path))
    monkeypatch.setattr(ProcessSupervisor,'_command',lambda self:[__import__('sys').executable,str(fixture)])
    return EvidenceVerificationAgent()


def test_verifier_timeout_reaps_worker_and_descendant(monkeypatch,tmp_path):
    agent=isolated(monkeypatch,tmp_path)
    ctx=context(deadline=time.monotonic()+1)
    result=agent.verify(AgentExecutionRequest(task=task().model_copy(update={'timeout_seconds':1}),context=ctx))
    assert result.artifact.status=='FAILED' and result.cleanup_verified
    assert result.artifact.errors[0]['code']=='TASK_TIMEOUT'
    assert all(not process_alive(pid) for pid in json.loads((tmp_path/'pids.json').read_text()))
    assert not (tmp_path/'late.txt').exists()


def test_verifier_cancel_reaps_worker_and_descendant(monkeypatch,tmp_path):
    agent=isolated(monkeypatch,tmp_path)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(agent.verify,AgentExecutionRequest(task=task(),context=context()))
        deadline=time.monotonic()+3
        while not (tmp_path/'pids.json').exists() and time.monotonic()<deadline:time.sleep(.01)
        assert (tmp_path/'pids.json').exists()
        agent.cancel_all();result=future.result(timeout=3)
    assert result.artifact.errors[0]['code']=='RUN_CANCELLED' and result.cleanup_verified
    assert all(not process_alive(pid) for pid in json.loads((tmp_path/'pids.json').read_text()))


def test_verifier_rejects_unknown_tool_before_starting_process(monkeypatch,tmp_path):
    agent=isolated(monkeypatch,tmp_path)
    wrong=TaskContract(task_id='verify',description='SYNTHETIC forbidden write tool',max_tool_calls=1,
        allowed_tools=('verify_claim',),input_data={'steps':[{'name':'verify_claim','arguments':{'claim_id':str(uuid4())}}]})
    result=agent.verify(AgentExecutionRequest(task=wrong,context=context()))
    assert result.artifact.errors[0]['code']=='AGENT_TOOL_FORBIDDEN'
    assert not (tmp_path/'pids.json').exists()

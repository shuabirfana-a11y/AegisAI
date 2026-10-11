"""Follow-up regressions. Controlled fixtures are not real Dify acceptance."""
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from app.assistant.contracts import QueryRequest
from app.assistant.orchestrator import Orchestrator
from app.tooling.gateway import ToolContext, ToolGateway

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('aegis_dify_smoke', ROOT/'integrations/dify/smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def test_live_task_events_and_terminal_handoff_override(db, monkeypatch):
    from app.assistant import service, storage
    row, _ = storage.create_run(db, QueryRequest(question='TEST LIVE STATES', request_key='LIVE-STATES'), 'test')
    row.details = {**row.details, 'plan':[
        {'task_id':key, 'goal':key} for key in ('root','verify','analysis')],
        'events':[{'task_id':'root','state':'started'}, {'task_id':'root','state':'success'},
                  {'task_id':'verify','state':'started'}]}
    db.flush()

    @contextmanager
    def transaction(_):
        yield db
    monkeypatch.setattr(service, 'transaction', transaction)
    instance = service.AssistantService(None)
    try:
        states = {t['task_id']:t['status'] for t in instance.tasks(row.id,'test')['items']}
        assert states == {'root':'success','verify':'running','analysis':'pending'}
        row.details = {**row.details, 'result':{'artifacts':[{'task_id':'root','status':'blocked'}]}}
        db.flush()
        assert instance.tasks(row.id,'test')['items'][0]['status'] == 'blocked'
        audit = instance.trace(row.id,'test')
        assert audit['run_id'] == str(row.id) and audit['trace_id'] == row.details['trace_id']
        with pytest.raises(LookupError):
            instance.tasks(row.id,'other-owner')
    finally:
        instance.close()


@pytest.mark.parametrize('question', ['执行这个POC看看','运行一下 PoC','run this exploit','execute the proof-of-concept'])
def test_poc_execution_is_rejected_before_any_tool(question):
    def no_tool(*args):
        pytest.fail('Execution request reached a tool')
    result = Orchestrator(ToolContext(actor='test'),gateway=ToolGateway(no_tool)).run(
        QueryRequest(question=question,request_key='POC-REJECTION'))
    assert result['route']['blocked'] is True
    assert result['gate']['status'] == 'FAILED'
    assert result['artifacts'] == []


@pytest.mark.parametrize('question', ['分析这个 POC 是否可靠','如何判断公开 exploit 的证据可靠性？','CVE-2025-32434 有哪些 POC？'])
def test_poc_evidence_queries_remain_supported(question):
    from app.assistant.router import route
    assert route(question)['blocked'] is False


def test_dify_serializer_matches_backend_question_boundary():
    workflow = yaml.safe_load((ROOT/'integrations/dify/workflows/assistant-bridge.v1.yml').read_text(encoding='utf-8'))
    nodes = {n['id']:n['data'] for n in workflow['workflow']['graph']['nodes']}
    namespace = {}
    exec(nodes['serialize']['code'], namespace)
    args = {'mode':'auto','request_key':'BOUNDARY','realtime':'false'}
    payload = json.loads(namespace['main'](question='测'*2000,**args)['request_json'])
    assert QueryRequest.model_validate(payload).question == '测'*2000
    with pytest.raises(ValueError):
        namespace['main'](question='测'*2001,**args)


def final_fixture(status='COMPLETED',gate='PASS',path='deep'):
    run_id,trace_id,raw_id = map(str,(uuid4(),uuid4(),uuid4()))
    ref = {'raw_document_id':raw_id,'url':'https://example.invalid/fixture','locator':{'text_span':[0,4]}}
    run = {'run_id':run_id,'trace_id':trace_id,'status':status,'finished_at':'2026-10-06T00:00:00+00:00',
           'route':{'path':path},'result':{'gate':{'status':gate},'answer':'TEST FIXTURE',
           'plan':[{'task_id':'root'}], 'artifacts':[{'task_id':'root','trace_id':trace_id,'status':'success'}],
           'evidence_refs':[ref],'facts':[]}}
    tasks = {'items':[{'task_id':'root','status':'success'}]}
    trace = {'run_id':run_id,'trace_id':trace_id,'items':[{'id':str(uuid4()),'tool_name':'get_vulnerability','status':'succeeded','evidence_refs':[ref]}], 'events':[]}
    ticket = {'run_id':run_id,'trace_id':trace_id,'status':'PLANNING','result':None}
    return ticket,run,tasks,trace


def test_dify_202_ticket_is_not_a_completed_result():
    ticket,_,tasks,trace = final_fixture()
    with pytest.raises(ValueError):
        smoke.validate_assistant_final(ticket,ticket,tasks,trace,expected_mode='deep')


@pytest.mark.parametrize('status,gate', [('COMPLETED','PASS'),('COMPLETED','PASS_WITH_WARNINGS'),('WAITING_REVIEW','HUMAN_REVIEW_REQUIRED')])
def test_dify_final_validation_preserves_real_gate(status,gate):
    ticket,run,tasks,trace = final_fixture(status,gate)
    result = smoke.validate_assistant_final(ticket,run,tasks,trace,expected_mode='deep')
    assert result['gate_status'] == gate
    assert result['backend_status'] == status


@pytest.mark.parametrize('mutate', ['run_id','trace_id','unfinished','no_audit','missing_evidence','wrong_path','gate','task_trace','failed','audit_binding'])
def test_dify_final_validation_rejects_unverifiable_results(mutate):
    ticket,run,tasks,trace = final_fixture()
    if mutate in ('run_id','trace_id'):run[mutate] = str(uuid4())
    elif mutate == 'unfinished':run['finished_at'] = None
    elif mutate == 'no_audit':trace['items'] = []
    elif mutate == 'missing_evidence':trace['items'][0]['evidence_refs'] = []
    elif mutate == 'wrong_path':run['route']['path'] = 'fast'
    elif mutate == 'gate':run['result']['gate']['status'] = 'FAILED'
    elif mutate == 'task_trace':run['result']['artifacts'][0]['trace_id'] = str(uuid4())
    elif mutate == 'failed':run['status'] = 'FAILED'
    elif mutate == 'audit_binding':trace['run_id'] = str(uuid4())
    with pytest.raises(ValueError):
        smoke.validate_assistant_final(ticket,run,tasks,trace,expected_mode='deep')


def test_dify_poll_reads_only_ticket_bound_routes_and_waits_for_terminal():
    ticket,run,tasks,trace = final_fixture()
    calls = []
    states = iter([ticket,run])
    def fetch(path):
        calls.append(path)
        if path.endswith('/tasks'):return tasks
        if path.endswith('/trace'):return trace
        return next(states)
    accepted = smoke.await_assistant_final(ticket,fetch,expected_mode='deep',pause=lambda _:None)
    assert accepted['backend_status'] == 'COMPLETED'
    base = '/assistant/runs/'+ticket['run_id']
    assert calls == [base,base,base+'/tasks',base+'/trace']


def test_dify_poll_is_bounded_and_rejects_redirect_like_ticket():
    ticket,_,_,_ = final_fixture()
    clock = iter([0,0,2])
    with pytest.raises(TimeoutError):
        smoke.await_assistant_final(ticket,lambda _:ticket,timeout=1,now=lambda:next(clock),pause=lambda _:None)
    ticket['run_id'] = 'http://example.invalid/steal'
    with pytest.raises(ValueError):
        smoke.await_assistant_final(ticket,lambda _:pytest.fail('Invalid ticket reached network'))

"""Synthetic reproductions for interruption, stale reports, accounting and redaction."""
from types import SimpleNamespace
from uuid import uuid4
import json
import sys

import pytest
import scripts.probe_planner_stability as probe
from app.investigation_api.schemas import TraceResponse
from tests.planner.fixtures import valid_plan


def configure_main(monkeypatch, tmp_path):
    cases = tmp_path/'cases.json'
    cases.write_text(json.dumps({'cases':[{'case_id':str(i),'request':{'user_query':'SYNTHETIC'}} for i in range(3)]}))
    output = tmp_path/'report.json'
    output.write_text(json.dumps({'finished_at_utc':'old','models':[{'summary':{'success':1}}]}))
    monkeypatch.setattr(sys,'argv',['probe','--model','SYNTHETIC-model','--planner-stability',
        '--cases',str(cases),'--output',str(output),'--ollama-executable','SYNTHETIC-exe'])
    monkeypatch.setattr(probe,'make_engine',lambda:SimpleNamespace(dispose=lambda:None))
    cfg = SimpleNamespace(provider='openai_compatible',model='SYNTHETIC-model',structured_mode='json_object',
        reasoning_effort='none',timeout_seconds=20,max_output_tokens=4096)
    monkeypatch.setattr(probe.ModelConfig,'from_env',lambda env:cfg)
    monkeypatch.setattr(probe,'ModelGateway',lambda cfg:SimpleNamespace(close=lambda:None))
    return output, cases


@pytest.mark.parametrize('failure', ['warm','cases','config'])
def test_setup_failure_replaces_previous_success_report(monkeypatch,tmp_path,failure):
    output, cases = configure_main(monkeypatch,tmp_path)
    def broken(*args,**kwargs): raise RuntimeError('MODEL_NOT_INSTALLED')
    monkeypatch.setattr(probe,'prewarm_model',broken)
    if failure=='cases':cases.write_text('{broken')
    if failure=='config':monkeypatch.setattr(probe.ModelConfig,'from_env',broken)
    with pytest.raises((ValueError,RuntimeError)):
        probe.main()
    report=json.loads(output.read_text())
    assert report['status']=='FAILED'
    assert report.get('finished_at_utc')!='old'
    assert report['started_at_utc'] and report['error_code']
    assert not any(m.get('summary',{}).get('success') for m in report['models'])


def test_keyboard_interrupt_preserves_inflight_repetition_in_denominator(monkeypatch,tmp_path):
    output,_=configure_main(monkeypatch,tmp_path)
    monkeypatch.setattr(probe,'prewarm_model',lambda *a:None)
    count=0
    def measured(*args,**kwargs):
        nonlocal count
        count+=1
        if count==2:raise KeyboardInterrupt()
        return {'case_id':'0','elapsed_ms':1,'attempts':[],'planner_validated':True,
            'real_mode_confirmed':True,'chain_attempted':False,'full_chain_executed':False,
            'gate_accepted':False,'error_codes':[]}
    monkeypatch.setattr(probe,'run_planner_case',measured)
    with pytest.raises(KeyboardInterrupt):probe.main()
    report=json.loads(output.read_text())
    assert report['status']=='INTERRUPTED'
    entry=report['models'][0]
    assert len(entry['planner_receipts'])==2
    assert entry['planner_receipts'][1]['measurement_status']=='INTERRUPTED'
    assert entry['planner_summary']['logical_runs']==2
    assert entry['planner_summary']['runs']['task_legal_rate']==.5


def test_private_model_task_identifiers_are_redacted_in_receipts():
    private=valid_plan()
    sensitive='sk-'+'SYNTHETIC_REVIEW_ONLY_'+str(123456)
    private['tasks'][0]['task_id']=sensitive
    private['tasks'][0]['dependencies']=[sensitive]
    exported=probe.public_plan_tasks(private)
    assert sensitive not in json.dumps(exported)
    assert exported[0]['task_id']=='[REDACTED]'
    assert private['tasks'][0]['task_id']==sensitive


def test_http_timeout_recovers_already_persisted_owned_attempts(monkeypatch):
    id, planner_id=str(uuid4()),str(uuid4())
    monkeypatch.setattr(probe,'run_probe',lambda *a,**k:{
        'investigation_id':id,'error_code':'PROBE_POLL_TIMEOUT','endpoints':{}})
    trace=SimpleNamespace(planner=SimpleNamespace(planner_run_id=planner_id,
        prompt_version='investigation-plan-v4',validation_status='PLANNING_FAILED'))
    monkeypatch.setattr(TraceResponse,'model_validate',lambda value:trace)
    attempts=[SimpleNamespace(model_dump=lambda **kw: {'attempt_index':1,'validation_status':'REJECTED',
        'diagnostic':None,'issues':[],'model_call':{'is_mock':False,'provider':'openai_compatible','model':'SYNTHETIC'}})]
    reads=[]
    def read(owned_id):
        reads.append(owned_id)
        return SimpleNamespace(attempts=attempts,generated_plan=None,validation_status='PLANNING_FAILED')
    class Response:
        is_success=True
        def json(self):return {}
    class Client:
        posts=[]
        def post(self,path,**kwargs):self.posts.append(path);return Response()
        def get(self,path,**kwargs):return Response()
    client=Client()
    receipt=probe.run_stability_case(client,{'case_id':'case','request':{'user_query':'SYNTHETIC'}},read)
    assert reads==[planner_id] and len(receipt['attempts'])==1
    assert receipt['attempt_accounting_complete']
    assert client.posts==[f'/api/investigations/{id}/cancel']
    assert summarize_one(receipt)['provider_attempts']==1


def summarize_one(receipt):return probe.summarize([receipt])


def test_interrupted_planner_finalizes_only_its_owned_audit(monkeypatch):
    state={'status':'PLANNING'}
    id,trace_id=uuid4(),uuid4()
    class Store:
        def __init__(self,engine):pass
        def create(self,*a,**k):return SimpleNamespace(planner_run_id=id,trace_id=trace_id),True
        def read(self,owned_id,actor):
            assert owned_id==id and actor=='SYNTHETIC-owner'
            return SimpleNamespace(attempts=(),validation_status=state['status'],generated_plan=None,error=())
        def complete(self,owned_id,actor,outcome):
            assert owned_id==id and actor=='SYNTHETIC-owner'
            state['status']=outcome.status
    class Planner:
        prompt_version='investigation-plan-v4';registry_version='investigation-registry-v1';model_identity=None
        def __init__(self,*a):pass
        def plan(self,*a):raise KeyboardInterrupt()
    monkeypatch.setattr(probe,'PlannerTraceStore',Store)
    monkeypatch.setattr(probe,'InvestigationPlannerAdapter',Planner)
    receipt={}
    case={'case_id':'synthetic','request':{'user_query':'CVE-2099-9999001 information',
        'asset_scope':{'target':'CVE-2099-9999001'}}}
    with pytest.raises(KeyboardInterrupt):
        probe.run_planner_case(None,None,'SYNTHETIC-owner',case,receipt=receipt)
    assert state['status']=='PLANNING_FAILED'
    assert receipt['planner_run_id']==str(id)
    assert receipt['measurement_status']=='INTERRUPTED'
    assert not receipt['attempt_accounting_complete']


def test_offline_statistics_import_does_not_require_http_server_runtime():
    import subprocess
    code='''import sys, importlib.abc
class Offline(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "uvicorn":
            raise ModuleNotFoundError("SYNTHETIC server runtime not installed")
sys.meta_path.insert(0, Offline())
from scripts.probe_planner_stability import summarize
assert summarize([])["logical_runs"] == 0
'''
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr

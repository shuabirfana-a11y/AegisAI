from uuid import uuid4
import time
import pytest
from app.runtime.contracts import TaskContract,ToolReceipt,ExecutionOutcome
from app.runtime.executor import WorkerExecutor,validate_outcome
from app.tooling.gateway import ToolGateway
from app.agents.artifacts import AgentExecutionRequest
from tests.agents.fixtures import context
from tests.agents.investigation.helpers import source,detail,execution,CVE

class Supervisor:
    """Test seam drives real WorkerExecutor/Gateway; production uses ProcessSupervisor."""
    def __init__(self,responses):self.responses=responses;self.calls=[];self.cancelled=False;self.detail=detail()
    def cancel_all(self):self.cancelled=True
    def execute(self,item,ctx,deps,*,database_url=None):
        self.calls.append((item,ctx,deps)); events=[]
        def response(name,args,tool_context):
            value=self.responses.get(name,{'status':'success','data':self.detail,'evidence_refs':[source()]})
            if isinstance(value,Exception):raise value
            return value
        art=WorkerExecutor(ToolGateway(executor=response),events.append).execute(item,ctx,deps)
        return ExecutionOutcome(artifact=art,receipts=[ToolReceipt.model_validate(e['receipt']) for e in events if e['kind']=='tool_finished'])

def request(names=('get_vulnerability',),**changes):
    ctx=context(); item=TaskContract(task_id='investigate',description='SYNTHETIC',
        input_data={'steps':[{'name':n,'arguments':{'target':CVE}} for n in names]},
        allowed_tools=names,max_tool_calls=len(names),**changes)
    return AgentExecutionRequest(task=item,context=ctx)

def agent(supervisor):
    from app.agents.investigation.agent import IntelligenceInvestigationAgent
    return IntelligenceInvestigationAgent(supervisor_factory=lambda:supervisor)

def test_agent_returns_exact_original_receipt_result():
    req=request(); sup=Supervisor({}); got=agent(sup).investigate(req)
    assert got.artifact.status=='SUCCESS' and len(got.receipts)==1
    assert got.artifact.result=={'outputs':[{'tool':got.receipts[0].name,'status':'success','data':got.receipts[0].envelope.data}],'dependencies':{}}
    assert validate_outcome(req.task,req.context,got).artifact.artifact_id==got.artifact.artifact_id

def test_failed_step_does_not_prevent_next_independent_read():
    req=request(('get_vulnerability','get_evidence','relation_query'))
    sup=Supervisor({'get_evidence':RuntimeError('SYNTHETIC-private-error')})
    got=agent(sup).investigate(req)
    from app.agents.investigation.normalize import normalize_investigation
    result=normalize_investigation(req.task,got)
    assert len(sup.calls)==len(got.receipts)==3
    assert [r.call_index for r in got.receipts]==[1,2,3]
    assert got.artifact.status=='FAILED' and result.status=='PARTIAL'
    assert 'SYNTHETIC-private-error' not in result.model_dump_json()
    assert validate_outcome(req.task,req.context,got)

def test_all_tool_failures_return_partial_with_no_confirmation():
    from app.agents.investigation.normalize import normalize_investigation
    item,_,out=execution(data={},refs=[],statuses=['failed'])
    result=normalize_investigation(item,out)
    assert result.status=='PARTIAL' and result.information_status=='INSUFFICIENT_EVIDENCE'
    assert result.failed_tools and result.confidence is None

@pytest.mark.parametrize('name',['verify_claim','get_system_status','UNKNOWN_TOOL'])
def test_unapproved_tools_never_execute(name):
    req=request((name,));sup=Supervisor({});got=agent(sup).investigate(req)
    assert got.artifact.status=='FAILED' and sup.calls==[]

def test_insufficient_sources_downgrade_success_to_review():
    req=request();sup=Supervisor({'get_vulnerability':{'status':'success','data':detail(),
        'evidence_refs':[source(authority_level='community')]}})
    got=agent(sup).investigate(req)
    assert got.artifact.status=='WAITING_REVIEW' and got.artifact.unresolved_questions
    assert validate_outcome(req.task,req.context,got)

def test_conflict_cannot_unlock_dependency():
    data=detail();data['intelligence']['conflicts']=[{'status':'open','claim_a_id':'A','claim_b_id':'B'}]
    req=request();sup=Supervisor({'get_vulnerability':{'status':'success','data':data,'evidence_refs':[source()]}})
    assert agent(sup).investigate(req).artifact.status=='WAITING_REVIEW'

def test_cancelled_agent_never_calls_supervisor():
    req=request();sup=Supervisor({});a=agent(sup);a.cancel_all()
    assert a.investigate(req).artifact.status=='FAILED' and sup.cancelled and not sup.calls

def test_expired_context_never_calls_tool():
    req=request();req=req.model_copy(update={'context':req.context.model_copy(update={'deadline':time.monotonic()-.1})})
    sup=Supervisor({});got=agent(sup).investigate(req)
    assert got.artifact.errors[0]['code']=='TASK_TIMEOUT' and not sup.calls

def test_for_run_has_independent_supervisor_and_owner():
    from app.agents.investigation.agent import IntelligenceInvestigationAgent
    prototype=IntelligenceInvestigationAgent(supervisor_factory=lambda:Supervisor({}))
    a=prototype.for_run(uuid4());b=prototype.for_run(uuid4());a.cancel_all()
    assert a is not b and a.supervisor is not b.supervisor and not b.supervisor.cancelled
    assert prototype.implementation_key==a.implementation_key==b.implementation_key

def test_missing_receipt_stops_and_cannot_become_success():
    from app.runtime.executor import failure
    class Missing(Supervisor):
        def execute(self,item,ctx,deps,*,database_url=None):
            self.calls.append(item)
            return ExecutionOutcome(artifact=failure(item,ctx,'TASK_ISOLATION_UNAVAILABLE'))
    sup=Missing({});got=agent(sup).investigate(request(('get_vulnerability','get_evidence')))
    assert len(sup.calls)==1 and not got.receipts and got.artifact.status=='FAILED'

def test_substeps_share_deadline_and_do_not_multiply_budget():
    req=request(('get_vulnerability','relation_query'));sup=Supervisor({});got=agent(sup).investigate(req)
    assert len(got.receipts)<=req.task.max_tool_calls
    assert all(ctx.deadline<=req.context.deadline and not deps and len(item.input_data['steps'])==1 for item,ctx,deps in sup.calls)

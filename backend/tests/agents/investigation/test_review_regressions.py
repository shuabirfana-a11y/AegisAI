from uuid import uuid4
import pytest
from app.agents.artifacts import AgentExecutionRequest
from app.runtime.contracts import TaskContract,ToolReceipt,ExecutionOutcome
from app.runtime.executor import WorkerExecutor,validate_outcome
from app.tooling.gateway import ToolGateway
from tests.agents.fixtures import context
from tests.agents.investigation.helpers import CVE,detail,source,execution
from tests.agents.investigation.test_agent import request,Supervisor,agent
from tests.agents.investigation.test_planning import validate
from tests.planner.fixtures import valid_plan,cve_input,context_for


def observed(steps,responses):
    item=TaskContract(task_id='investigate',description='SYNTHETIC',input_data={'steps':steps},
        allowed_tools=[s['name'] for s in steps],max_tool_calls=len(steps))
    ctx=context();events=[]
    art=WorkerExecutor(ToolGateway(executor=lambda n,a,c:responses[n]),events.append).execute(item,ctx,{})
    receipts=[ToolReceipt.model_validate(e['receipt']) for e in events if e['kind']=='tool_finished']
    return item,ctx,ExecutionOutcome(artifact=art,receipts=receipts)


def project(item,out):
    from app.agents.investigation.normalize import normalize_investigation
    return normalize_investigation(item,out)


@pytest.mark.parametrize('conflict',[False,True])
def test_overflow_cannot_unlock_dependencies_or_hide_conflict(conflict):
    data=detail();data['affected_versions'][0]['fixed']='x'*270000
    if conflict:data['intelligence']['conflicts']=[{'status':'open','claim_a_id':'A','claim_b_id':'B'}]
    req=request();sup=Supervisor({'get_vulnerability':{'status':'success','data':data,'evidence_refs':[source()]}})
    out=agent(sup).investigate(req);got=project(req.task,out)
    assert out.artifact.status=='WAITING_REVIEW' and got.status=='PARTIAL'
    assert got.information_status==('CONFLICT' if conflict else 'CANDIDATE')
    assert got.evidence_storage=='tool_receipts' and got.receipt_references
    assert validate_outcome(req.task,req.context,out)


def test_unrelated_official_semantic_hit_cannot_bless_target():
    data=detail();target={'name':'relation_query','arguments':{'target':CVE}}
    semantic={'name':'semantic_search','arguments':{'query':CVE+'是什么？'}}
    ref=source(authority_level='community');unrelated=source(external_id='CVE-2099-1111111')
    item,_,out=observed([target,semantic],{'relation_query':{'status':'success','data':data,'evidence_refs':[ref]},
        'semantic_search':{'status':'success','data':{'items':[{'content':'SYNTHETIC unrelated advisory'}]},'evidence_refs':[unrelated]}})
    got=project(item,out)
    assert got.status=='INSUFFICIENT_EVIDENCE' and got.information_status!='CONFIRMED'
    assert unrelated in got.evidence


@pytest.mark.parametrize('name',['get_evidence','get_claims'])
def test_independent_evidence_task_is_complete_for_its_observations(name):
    ref=source();row={'id':str(uuid4()),'excerpt':'SYNTHETIC observed statement'}
    item,_,out=observed([{'name':name,'arguments':{'target':CVE}}],
        {name:{'status':'success','data':{'items':[row]},'evidence_refs':[ref]}})
    got=project(item,out)
    assert got.status=='COMPLETE' and got.evidence==[ref]
    assert got.information_status=='CANDIDATE'
    assert got.findings and row in [f['data'] for f in got.findings]


def test_tool_failure_takes_partial_priority_over_information_conflict():
    data=detail();data['intelligence']['conflicts']=[{'status':'open','claim_a_id':'A','claim_b_id':'B'}]
    item,_,out=execution(data=data,names=['get_vulnerability','get_evidence'],statuses=['success','failed'])
    got=project(item,out)
    assert got.status=='PARTIAL' and got.information_status=='CONFLICT'
    assert got.conflicts and got.failed_tools and got.runtime_status=='FAILED'


def test_component_without_version_requires_input_node():
    from app.planner.schemas import PlannerInput
    inp=cve_input(question='我的 vLLM 是否受 '+CVE+' 影响？')
    inp=PlannerInput(query=inp.query,component={'name':'vllm'})
    ctx=context_for(input=inp);value=valid_plan()
    with pytest.raises(ValueError,match='VERSION_INPUT_REQUIRED'):validate(value,ctx)
    value['tasks'].append({'type':'vulnerability_lookup','task_id':'version_input','description':'Version required',
        'task_type':'input_required','input_data':{'required_fields':['version']},'max_tool_calls':0,'allowed_tools':[]})
    assert validate(value,ctx)


def test_projection_reserves_persisted_receipt_identifier_overhead():
    # Exact edge: raw projection fits; formal receipt UUID/sequence expansion would not.
    data=detail();item,_,out=execution(data)
    lo,hi=200000,270000
    while lo+1<hi:
        mid=(lo+hi)//2;data['affected_versions'][0]['fixed']='x'*mid
        item,_,out=execution(data);got=project(item,out)
        if got.evidence_storage=='artifact':lo=mid
        else:hi=mid
    data['affected_versions'][0]['fixed']='x'*lo;item,_,out=execution(data);got=project(item,out)
    assert got.evidence_storage=='artifact'
    expanded=out.artifact.model_copy(update={'tool_calls':[{**c,'record_id':str(uuid4()),'sequence_no':32} for c in out.artifact.tool_calls]})
    stored=project(item,out.model_copy(update={'artifact':expanded}))
    assert stored.evidence_storage=='artifact','Acceptance did not reserve formal ToolCallRecord overhead'


def test_unrelated_dependency_claim_cannot_confirm_current_target():
    from app.agents.artifacts import AgentArtifact
    from app.agents.investigation.normalize import normalize_investigation
    from tests.agents.investigation.test_normalize import confirmed_claim
    claim,ref=confirmed_claim();other='CVE-2099-1111111';ref['external_id']=other
    _,_,prior=observed([{'name':'get_claims','arguments':{'target':other}}],
        {'get_claims':{'status':'success','data':{'items':[claim]},'evidence_refs':[ref]}})
    item,ctx,out=observed([{'name':'get_evidence','arguments':{'target':CVE}}],
        {'get_evidence':{'status':'success','data':{'items':[{'id':str(uuid4())}]},'evidence_refs':[source()]}})
    dep=AgentArtifact(**{**prior.artifact.model_dump(),'run_id':ctx.run_id,'task_id':'prior'},
        agent_id='investigation_agent',artifact_type='investigation_result',unresolved_items=())
    item=item.model_copy(update={'dependencies':('prior',)})
    got=normalize_investigation(item,out,(dep,))
    assert got.status=='COMPLETE' and got.information_status=='CANDIDATE'

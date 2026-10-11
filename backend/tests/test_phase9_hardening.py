"""Synthetic failure-injection cases; excluded from factual benchmark gold."""
import time
from uuid import uuid4
from app.assistant.contracts import TaskContract,TaskArtifact,QueryRequest
from app.tooling.gateway import ToolContext,ToolGateway
from app.utils.time import utcnow

def task(**changes):
    return TaskContract(task_id='test',goal='TEST FIXTURE',task_type='Investigation',inputs={},allowed_tools=[],**changes)

def artifact(t,**changes):
    now=utcnow()
    return TaskArtifact(task_id=t.task_id,agent=t.task_type,status='success',result={},trace_id='test',started_at=now,finished_at=now,**changes)

def test_confirmation_requires_matching_current_supporting_evidence():
    from app.assistant.gate import integrate
    claim={'id':str(uuid4()),'revision':2,'verification_status':'CONFIRMED','trusted':True}
    ref={'claim_id':claim['id'],'claim_revision':2,'verified':True,'stance':'support','raw_document_id':str(uuid4()),'url':'https://example.invalid/evidence','locator':{'json_pointer':'/test'}}
    for refs in [[],[{**ref,'claim_revision':1}],[{**ref,'stance':'contradict'}]]:
        assert integrate([artifact(task(),claims=[claim],evidence_refs=refs)])['status']=='FAILED'
    from app.tooling.attestation import claim_key,evidence_key
    ref['evidence_id']=str(uuid4())
    assert integrate([artifact(task(),claims=[claim],evidence_refs=[ref])],claims_attested={claim_key(claim)},evidence_attested={evidence_key(ref)})['status']=='PASS'

def test_graph_deadline_returns_without_waiting_for_slow_task():
    from app.assistant.graph import run_graph
    def slow(t,accepted):
        time.sleep(.3)
        return artifact(t)
    start=time.monotonic()
    outputs=run_graph([task()],slow,'test',deadline=start+.04)
    assert time.monotonic()-start<.2
    assert outputs[0].status=='blocked'
    assert outputs[0].errors[0]['code']=='TASK_TIMEOUT'

def test_one_failed_tool_preserves_successful_partial_results():
    from app.assistant.roles import InvestigationRole
    def execute(name,args,context):
        return {'status':'success','data':{'items':[{'value':'TEST FIXTURE'}]}} if name=='get_epss' else {'status':'failed','errors':[{'code':'SOURCE_TIMEOUT'}]}
    t=task();t.allowed_tools=['get_epss','get_known_exploitation'];t.inputs={'calls':[{'tool':name,'args':{'target':'CVE-2099-9999001'}} for name in t.allowed_tools]}
    result=InvestigationRole(ToolGateway(execute),ToolContext(actor='test',trace_id='test')).execute(t,{})
    assert result.status=='partial'
    assert result.result['tool_results'][0]['data']['items'][0]['value']=='TEST FIXTURE'
    assert result.errors[0]['code']=='SOURCE_TIMEOUT'

def test_live_failure_replans_to_cached_tool_and_preserves_original_failure():
    from app.assistant.roles import InvestigationRole
    requests=[]
    def execute(name,args,context):
        requests.append(args['refresh'])
        return {'status':'failed','errors':[{'code':'SOURCE_TIMEOUT'}],'retryable':False} if args['refresh'] else {'status':'success','data':{'cached':True}}
    t=task(failure_policy='replan');t.allowed_tools=['investigate_vulnerability'];t.inputs={'calls':[{'tool':'investigate_vulnerability','args':{'target':'CVE-2099-9999001','refresh':True}}]}
    ctx=ToolContext(actor='test',trace_id='test',permissions=frozenset({'READ_ONLY','WRITE','EXTERNAL_NETWORK'}))
    result=InvestigationRole(ToolGateway(execute),ctx).execute(t,{})
    assert requests==[True,False]
    assert result.status=='partial' and result.result['tool_results'][0]['data']['cached']
    assert result.result['replans'][0]['original_failure']['errors'][0]['code']=='SOURCE_TIMEOUT'

def test_deep_path_runs_real_semantic_adapter_alongside_structured_calls():
    from app.assistant.orchestrator import Orchestrator
    names=[]
    def execute(name,args,context):
        names.append(name)
        return {'status':'no_result','data':{'items':[]}}
    result=Orchestrator(ToolContext(actor='test'),gateway=ToolGateway(execute)).run(QueryRequest(question='调查 CVE-2099-9999001',request_key='TEST'))
    assert 'semantic_search' in names and 'get_vulnerability' in names and 'relation_query' in names
    assert result['route']['path']=='deep' and not result['facts']

def test_role_task_timeout_limits_worker_budget():
    from app.assistant.roles import InvestigationRole
    observed=[]
    def execute(name,args,ctx):
        observed.append(ctx.deadline-time.monotonic())
        return {'status':'no_result','data':{}}
    t=task(timeout=1);t.allowed_tools=['get_vulnerability'];t.inputs={'calls':[{'tool':'get_vulnerability','args':{'target':'CVE-2099-9999001'}}]}
    InvestigationRole(ToolGateway(execute),ToolContext(actor='test')).execute(t,{})
    assert 0<observed[0]<=1

def test_product_query_routes_to_structured_relations_instead_of_semantic_only():
    from app.assistant.router import route
    r=route('哪些漏洞影响 vLLM 并已有可靠 POC？')
    assert r['path']=='deep' and r['product']=='vllm'

def test_product_tool_filters_using_existing_package_relations(db,seed):
    from app.tooling.adapters import execute_local
    data=execute_local(db,'search_vulnerabilities',{'product':'torch','limit':10},'test')['data']
    assert str(seed.vuln.id) in [str(v['id']) for v in data['items']]
    data=execute_local(db,'search_vulnerabilities',{'product':'unrelated-test-product','limit':10},'test')['data']
    assert data['items']==[]

def test_asset_tool_includes_publication_time_for_requested_time_window(db,seed):
    from app.tooling.adapters import execute_local
    from app.assets.matching import AssetVulnerabilityMatcher
    from app.assets.risk import RiskService
    # Use a genuine existing deterministic match/evaluation; uncertainty is allowed.
    AssetVulnerabilityMatcher.match(db,seed.component)
    RiskService.recompute(db,seed.asset.id)
    rows=execute_local(db,'get_asset_risks',{'asset_id':str(seed.asset.id)},'test-analyst')['data']['items']
    assert rows and all('published_at' in row for row in rows)

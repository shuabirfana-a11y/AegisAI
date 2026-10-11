import json
from uuid import uuid4
import pytest
from app.runtime.contracts import TaskPlan, TaskContract, RuntimePolicy
from tests.planner.fixtures import valid_plan,task,cve_input,context_for,gateway_with_responses,MemorySink

def validate(value,ctx=None):
    from app.agents.investigation.planning import InvestigationPlan
    from app.agents.investigation.validation import validate_investigation_plan
    return validate_investigation_plan(InvestigationPlan.model_validate(value),ctx or context_for())

def test_exact_three_roles_eight_tools():
    from app.agents.investigation.roles import ROLES
    assert set(ROLES)=={'vulnerability_lookup','evidence_search','asset_lookup'}
    assert len(set().union(*(r.tools for r in ROLES.values())))==8

def test_registry_routes_evidence_to_investigation():
    from app.agents.investigation.registry import create_investigation_registry
    registry=create_investigation_registry().freeze()
    assert len(registry.entries)==1 and registry.for_task('evidence_search').contract.agent_id=='investigation_agent'

def test_asset_lookup_uses_existing_router_with_scoped_table():
    from app.agents.investigation.registry import create_investigation_registry
    from app.agents.investigation.roles import ROLES
    from app.agents.router import AgentRouter
    item=TaskContract.model_validate({k:v for k,v in task('asset_lookup','asset','get_asset',{'asset_id':str(uuid4())}).items() if k!='type'})
    bound=AgentRouter(create_investigation_registry().freeze(),task_registry=ROLES).bind_plan(
        TaskPlan(tasks=[item]),{'asset':'asset_lookup'},RuntimePolicy())
    assert bound.binding('asset').agent_id=='investigation_agent'

def test_legacy_planner_schema_and_registry_remain_five():
    from app.planner.schemas import PlannerPlan
    from app.planner.registry import TASK_REGISTRY
    value=valid_plan();value['tasks'][0]['type']='asset_lookup'
    with pytest.raises(ValueError):PlannerPlan.model_validate(value)
    assert len(TASK_REGISTRY)==5 and 'asset_lookup' not in TASK_REGISTRY

def test_component_question_requires_readonly_version_observation():
    from app.planner.schemas import PlannerInput
    i=cve_input(question='我的 vLLM 0.6.0 是否受CVE-2099-9999001影响？')
    ctx=context_for(input=i);value=valid_plan()
    with pytest.raises(ValueError,match='VERSION_OBSERVATION_REQUIRED'):validate(value,ctx)
    value['tasks'][0]['input_data']['steps'].append({'name':'inspect_component_version',
        'arguments':{'target':i.query.target,'name':'vllm','version':'0.6.0'}})
    value['tasks'][0]['allowed_tools'].append('inspect_component_version');value['tasks'][0]['max_tool_calls']=2
    got=validate(value,ctx)
    assert 'risk_analysis' not in json.loads(got.semantic_types_json).values()

@pytest.mark.parametrize('mutation,code',[
    ('scope','TARGET_SCOPE_MISMATCH'),('write','TASK_TOOL_FORBIDDEN'),('refresh','TOOL_INPUT_INVALID'),
    ('unknown','SCHEMA'),('no_exact','TASK_TOOL_FORBIDDEN')])
def test_illegal_plan_rejected(mutation,code):
    value=valid_plan()
    if mutation=='scope':value['tasks'][0]['input_data']['steps'][0]['arguments']['target']='CVE-2099-1111111'
    elif mutation=='write':value['tasks'][0]=task(name='verify_claim',arguments={'claim_id':str(uuid4())})
    elif mutation=='refresh':value['tasks'][0]['input_data']['steps'][0]['arguments']['refresh']=True
    elif mutation=='unknown':value['tasks'][0]['type']='risk_analysis'
    elif mutation=='no_exact':value['tasks'][0]=task(name='get_system_status',arguments={})
    with pytest.raises(ValueError):validate(value)

def test_asset_missing_id_requires_real_input():
    value=valid_plan();value['tasks'].append({'type':'asset_lookup','task_id':'asset','description':'Missing asset',
        'task_type':'input_required','input_data':{'required_fields':['asset_id']},'max_tool_calls':0,'allowed_tools':[]})
    assert validate(value)
    value['tasks'][-1]['input_data']['required_fields']=['write_authorization']
    with pytest.raises(ValueError):validate(value)

def test_adapter_uses_model_gateway_and_existing_attempt_protocol():
    from app.agents.investigation.planner import InvestigationPlannerAdapter
    gateway,calls,sink=gateway_with_responses(['INVALID_JSON',valid_plan()])
    planner=InvestigationPlannerAdapter(gateway,sink)
    try:
        got=planner.plan(cve_input(),context_for())
        assert got.status=='VALIDATED' and len(calls)==2 and len(sink.attempts)==2
        assert got.attempts[0].diagnostic['raw_output']=='INVALID_JSON'
        assert planner.prompt_version=='investigation-plan-v1'
    finally:gateway.close()

def test_candidate_cannot_request_dag_cycle():
    value=valid_plan();value['tasks'][0]['dependencies']=['lookup']
    with pytest.raises(ValueError):validate(value)

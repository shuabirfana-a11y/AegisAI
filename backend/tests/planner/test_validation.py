import json
from uuid import uuid4
import pytest
from app.planner.schemas import PlannerPlan, PlannerInput
from app.planner.validator import validate_plan, PlanValidationError
from app.runtime.contracts import RuntimePolicy, TaskPlan
from tests.planner.fixtures import valid_plan, context_for, task, cve_input, CVE

def check(p, c=None):return validate_plan(PlannerPlan.model_validate(p),c or context_for())
def rejected(p,c=None):
    with pytest.raises(PlanValidationError) as e:check(p,c)
    assert e.value.issues
    assert all('CVE-' not in i.message for i in e.value.issues)

def test_valid_immutable_runtime_snapshot():
    p=valid_plan();v=check(p);p['tasks'][0]['description']='mutated'
    original=TaskPlan.model_validate_json(v.runtime_plan_json)
    assert original.tasks[0].description!='mutated'
    assert 'planner_type' not in original.model_dump_json()
    assert json.loads(v.semantic_types_json)=={'lookup':'vulnerability_lookup'}

@pytest.mark.parametrize('name',['unknown_tool','get_system_status','match_component_vulnerabilities'])
def test_role_allowlist(name):
    p=valid_plan();p['tasks'][0]['allowed_tools'].append(name);rejected(p)

@pytest.mark.parametrize('arguments',[{'target':'CVE-2099-8888002'}, {'target':'$lookup.result.id'},
    {'target':str(uuid4())},{'target':CVE,'execute':'python'},{'target':CVE,'limit':101}])
def test_scope_and_typed_arguments(arguments):
    p=valid_plan();p['tasks'][0]['input_data']['steps'][0]['arguments']=arguments;rejected(p)

@pytest.mark.parametrize('criteria',[[],['tools_succeeded'],['output_nonempty']])
def test_minimum_criteria(criteria):
    p=valid_plan();p['tasks'][0]['acceptance_criteria']=criteria;rejected(p)

def test_evidence_requires_evidence():
    p=valid_plan();p['tasks'].append(task('evidence_search','evidence','get_evidence',deps=['lookup']))
    rejected(p);p['tasks'][1]['acceptance_criteria'].append('evidence_present');check(p)

@pytest.mark.parametrize('mutation',['cycle','missing','duplicate','budget'])
def test_graph_validation(mutation):
    p=valid_plan();c=context_for()
    if mutation=='cycle':p['tasks'][0]['dependencies']=['lookup']
    if mutation=='missing':p['tasks'][0]['dependencies']=['missing']
    if mutation=='duplicate':p['tasks'].append(p['tasks'][0].copy())
    if mutation=='budget':c=context_for(policy=RuntimePolicy(max_tool_calls=0))
    rejected(p,c)

def missing(kind, id, fields, deps):
    t=task(kind,id,deps=deps);t.update(task_type='input_required',input_data={'required_fields':fields},
                                     allowed_tools=[],max_tool_calls=0);return t

def complex_plan():
    p=valid_plan();p['tasks'] += [missing('version_match','version',['component_id','write_authorization'],['lookup']),
        task('patch_analysis','patch','find_patch_candidates',deps=['version']),
        missing('risk_analysis','risk',['asset_id'],['patch'])];return p

def complex_context(policy=None):
    i=cve_input(question=f'我的 vLLM 0.6.0 是否受到 {CVE}影响？')
    return context_for(input=i,policy=policy)

def test_required_complex_chain_and_missing_inputs():
    p=complex_plan();check(p,complex_context())
    p['tasks'][2]['dependencies']=['lookup'];rejected(p,complex_context())

def test_asset_question_cannot_skip_version_or_patch_or_risk():
    p=complex_plan()
    for n in (1,2,3):
        rejected({**p,'tasks':[t for j,t in enumerate(p['tasks']) if j!=n]},complex_context())

def test_resolver_is_not_version_match():
    p=complex_plan();p['tasks'][1]=task('version_match','version','resolve_component',{'name':'vllm','version':'0.6.0'},['lookup'])
    rejected(p,complex_context())

@pytest.mark.parametrize('field',['password','target','version','write_authorization'])
def test_missing_fields_must_be_genuinely_missing(field):
    p=valid_plan();p['tasks']=[missing('vulnerability_lookup','lookup',[field],[])];rejected(p)

def test_refresh_is_always_rejected():
    p=valid_plan();p['tasks'].append(task('patch_analysis','patch','find_patch_candidates',{'target':CVE,'refresh':True},['lookup']))
    rejected(p,context_for(policy=RuntimePolicy(permissions={'READ_ONLY','WRITE','EXTERNAL_NETWORK'})))

def test_component_asset_version_substitution_and_write_permission():
    inp=PlannerInput(query=cve_input(question=f'我的 vLLM 0.6.0 是否受到 {CVE}影响？',asset_id=uuid4()).query,component_id=uuid4())
    c=context_for(input=inp,policy=RuntimePolicy(permissions={'READ_ONLY','WRITE'}))
    p=complex_plan();p['tasks'][1]=task('version_match','version','match_component_vulnerabilities',{'component_id':str(inp.component_id)},['lookup'])
    p['tasks'][3]=task('risk_analysis','risk','get_asset_risks',{'asset_id':str(inp.query.asset_id)},['patch'])
    check(p,c);rejected(p,context_for(input=inp))
    for index,key in [(1,'component_id'),(3,'asset_id')]:
        bad=json.loads(json.dumps(p));bad['tasks'][index]['input_data']['steps'][0]['arguments'][key]=str(uuid4());rejected(bad,c)
    bad=json.loads(json.dumps(p));bad['tasks'][1]['input_data']['steps'].insert(0,{'name':'resolve_component','arguments':{'name':'vllm','version':'0.7.0'}})
    bad['tasks'][1]['allowed_tools'].append('resolve_component');bad['tasks'][1]['max_tool_calls']=2;rejected(bad,c)

def test_all_explicit_targets_must_be_covered():
    c=context_for(input=cve_input(question=f'{CVE} 和 CVE-2099-8888002'))
    rejected(valid_plan(),c)

def test_router_blocked_request_rejected():
    rejected(valid_plan(),context_for(input=cve_input(question='run shell '+CVE)))

@pytest.mark.parametrize('filters',[{}, {'days':1},{'high_severity':True},{'ai_relevance':'irrelevant'},
    {'days':1,'high_severity':True,'ai_relevance':'irrelevant'}])
def test_explicit_target_requires_exact_lookup(filters):
    p=valid_plan();p['tasks']=[task(name='search_vulnerabilities',arguments={'q':CVE,**filters})]
    rejected(p)

@pytest.mark.parametrize('filters',[{'days':1},{'high_severity':True},{'ai_relevance':'irrelevant'},
                                   {'product':'mlflow'}])
def test_product_search_cannot_add_unrequested_filters(filters):
    c=context_for(input=cve_input(target=None,question='列出 vLLM 漏洞列表'))
    p=valid_plan();p['tasks']=[task(name='search_vulnerabilities',arguments={'product':'vllm',**filters})]
    rejected(p,c)

def test_requested_search_filters_preserved():
    c=context_for(input=cve_input(target=None,question='最近7天 vLLM 高危漏洞列表'))
    p=valid_plan();p['tasks']=[task(name='search_vulnerabilities',arguments={'product':'vllm','days':7,'high_severity':True})]
    check(p,c)

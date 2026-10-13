"""SYNTHETIC scope controls, not examples fitted to benchmark answers."""
from copy import deepcopy
from uuid import uuid4
import pytest
from jsonschema import Draft202012Validator, ValidationError
from app.agents.investigation import planning
from tests.planner.fixtures import valid_plan, task, cve_input, context_for, CVE


def validator(context):
    factory=getattr(planning,'scoped_plan_model',lambda context:planning.InvestigationPlan)
    return Draft202012Validator(factory(context).model_json_schema())


@pytest.mark.parametrize('name,args',[
    ('get_vulnerability',{'target':'CVE-2099-0000002'}),
    ('semantic_search',{'query':'shortened question'}),
    ('inspect_component_version',{'target':CVE,'name':'torch','version':'9.9.9'}),
    ('get_asset',{'asset_id':str(uuid4())}),
])
def test_model_schema_rejects_out_of_scope_arguments_before_generation(name,args):
    c=context_for();p=valid_plan()
    role='asset_lookup' if name=='get_asset' else 'evidence_search' if name=='semantic_search' else 'vulnerability_lookup'
    p['tasks']=[task(role,name=name,arguments=args)]
    with pytest.raises(ValidationError):validator(c).validate(p)


def test_missing_version_has_no_version_tool_but_keeps_input_required():
    from app.planner.schemas import PlannerInput
    inp=PlannerInput(query=cve_input().query,component={'name':'torch','version':None})
    c=context_for(input=inp);p=valid_plan()
    p['tasks'].append({'type':'vulnerability_lookup','task_id':'ask-version','task_type':'input_required',
        'description':'Ask for absent version','input_data':{'required_fields':['version']},
        'allowed_tools':[],'max_tool_calls':0})
    validator(c).validate(p)
    p['tasks'][1]=task(name='inspect_component_version',arguments={'target':CVE,'name':'torch','version':'1.0'})
    with pytest.raises(ValidationError):validator(c).validate(p)


def test_supplied_version_exact_asset_and_original_query_remain_executable():
    from app.planner.schemas import PlannerInput
    aid=uuid4();inp=PlannerInput(query=cve_input(asset_id=aid).query,
        component={'name':'torch','package_name':'torch','ecosystem':'PyPI','version':'2.0'})
    c=context_for(input=inp);p=valid_plan()
    p['tasks'][0]['input_data']['steps'].append({'name':'inspect_component_version','arguments':
        {'target':CVE,'name':'torch','package_name':'torch','ecosystem':'PyPI','version':'2.0'}})
    p['tasks'][0].update(allowed_tools=['get_vulnerability','inspect_component_version'],max_tool_calls=2)
    p['tasks'].append(task('asset_lookup',task_id='asset',name='get_asset',arguments={'asset_id':str(aid)}))
    p['tasks'].append(task('evidence_search',task_id='evidence',name='semantic_search',arguments={'query':c.scope['question']}))
    validator(c).validate(p)
    changed=deepcopy(p);changed['tasks'][0]['input_data']['steps'][1]['arguments']['version']='2.1'
    with pytest.raises(ValidationError):validator(c).validate(changed)


def test_eight_target_scope_fits_existing_gateway_schema_budget():
    from app.llm.gateway import prepare_schema
    from app.llm.schemas import StructuredRequest
    import json
    c=context_for();scope=c.scope
    scope['targets']=[f'CVE-2099-999900{i}' for i in range(1,9)]
    scope['component']={'name':'torch','package_name':'torch','ecosystem':'PyPI','namespace':'test',
        'purl':'pkg:pypi/torch','package_identifier_id':str(uuid4()),'version':'2.0'}
    scope['asset_id']=str(uuid4())
    scope['question']='SYNTHETIC supported long query '+('q'*9000)
    c=c.model_copy(update={'scope_json':json.dumps(scope)})
    request=StructuredRequest(messages=[{'role':'user','content':'SYNTHETIC multi-target scope'}])
    schema=prepare_schema(request,planning.scoped_plan_model(c))
    assert schema

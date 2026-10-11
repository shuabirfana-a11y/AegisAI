import json
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.planner.schemas import PlannerPlan
from app.planner.registry import TASK_REGISTRY
from app.tooling.contracts import REGISTRY
from tests.planner.fixtures import valid_plan, context_for

@pytest.mark.parametrize('field,value',[('confidence',float('nan')),('confidence',float('inf')),
    ('confidence',-0.1),('confidence',1.1),('plan_id','not-uuid'),('extra_permission','WRITE')])
def test_bad_plan_fields(field,value):
    with pytest.raises(ValidationError):PlannerPlan.model_validate({**valid_plan(),field:value})

def test_unknown_type():
    p=valid_plan();p['tasks'][0]['type']='unknown_task'
    with pytest.raises(ValidationError):PlannerPlan.model_validate(p)

@pytest.mark.parametrize('field,value',[('max_tool_calls',9),('max_tool_calls',True),
    ('timeout_seconds',61),('permission','WRITE')])
def test_original_contract_bounds(field,value):
    p=valid_plan();p['tasks'][0][field]=value
    with pytest.raises(ValidationError):PlannerPlan.model_validate(p)

def test_full_candidate_bounded():
    p=valid_plan();p['tasks'][0]['input_data']['steps'][0]['arguments']['extra']='x'*65536
    with pytest.raises(ValidationError):PlannerPlan.model_validate(p)

def test_registry_and_schema_are_fixed():
    assert set(TASK_REGISTRY)=={'vulnerability_lookup','version_match','evidence_search','patch_analysis','risk_analysis'}
    assert all(set(s.tools)<=set(REGISTRY) for s in TASK_REGISTRY.values())
    for kind in TASK_REGISTRY:
        p=valid_plan();p['tasks'][0]['type']=kind
        assert PlannerPlan.model_validate(p).tasks[0].planner_type==kind
    assert 'type' in PlannerPlan.model_json_schema()['$defs']['PlannerTaskContract']['properties']

def test_context_is_server_owned_and_snapshot():
    c=context_for(); assert c.scope['targets']==['CVE-2099-9999001']
    assert not any(k in c.model_dump_json().lower() for k in ['api_key','database_url','password'])
    route=c.route;route['injected']=True
    assert 'injected' not in c.route

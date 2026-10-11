import pytest
from app.runtime.contracts import TaskPlan, RuntimePolicy, TaskContract
from tests.agents.fixtures import task


@pytest.mark.parametrize('semantic,name,args,expected', [
    ('vulnerability_lookup','get_vulnerability',{},'investigation_agent'),
    ('version_match','match_component_vulnerabilities',{'component_id':'00000000-0000-0000-0000-000000000001'},'investigation_agent'),
    ('patch_analysis','find_patch_candidates',{},'investigation_agent'),
    ('evidence_search','get_evidence',{},'verification_agent'),
    ('risk_analysis','get_epss',{},'security_analysis_agent')])
def test_router_selects_registered_capability(semantic,name,args,expected):
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    item=task(name=name,arguments=args,acceptance_criteria=['tools_succeeded','output_nonempty','evidence_present'])
    got=AgentRouter(create_default_registry().freeze()).route(item,semantic)
    assert got.agent_id==expected and got.semantic_type==semantic
    assert got.task_id==item.task_id and len(got.task_fingerprint)==64


def test_unknown_type_returns_agent_not_found():
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    from app.agents.contracts import AgentFrameworkError
    with pytest.raises(AgentFrameworkError,match='AGENT_NOT_FOUND'):
        AgentRouter(create_default_registry().freeze()).route(task(),'unknown_task')


def test_agent_tools_do_not_expand_task_permission():
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    from app.agents.contracts import AgentFrameworkError
    # Investigation supports patches, but lookup does not permit patch tools.
    with pytest.raises(AgentFrameworkError,match='AGENT_TOOL_FORBIDDEN'):
        AgentRouter(create_default_registry().freeze()).route(task(name='find_patch_candidates'),'vulnerability_lookup')


@pytest.mark.parametrize('mapping',[{}, {'lookup':'vulnerability_lookup','extra':'risk_analysis'}])
def test_binding_requires_exact_semantic_task_set(mapping):
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    from app.agents.contracts import AgentFrameworkError
    with pytest.raises(AgentFrameworkError,match='AGENT_PLAN_INVALID'):
        AgentRouter(create_default_registry().freeze()).bind_plan(TaskPlan(tasks=[task()]),mapping,RuntimePolicy())


def test_input_required_stays_unassigned():
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    item=TaskContract(task_id='missing',task_type='input_required',description='Missing target',
        input_data={'required_fields':['target']},max_tool_calls=0)
    bound=AgentRouter(create_default_registry().freeze()).bind_plan(TaskPlan(tasks=[item]),
        {'missing':'vulnerability_lookup'},RuntimePolicy())
    assert bound.binding('missing') is None
    assert bound.captured_plan.tasks==(item,)


def test_binding_preserves_tasks_and_rejects_supplied_metadata():
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    from app.agents.contracts import AgentFrameworkError
    router=AgentRouter(create_default_registry().freeze()); item=task()
    bound=router.bind_plan(TaskPlan(tasks=[item]),{'lookup':'vulnerability_lookup'},RuntimePolicy())
    captured=bound.captured_plan
    assert captured.tasks==(item,)
    captured.route['professional_agents_v1']['bindings'].clear()
    assert len(bound.captured_plan.route['professional_agents_v1']['bindings'])==1
    with pytest.raises(AgentFrameworkError,match='AGENT_PLAN_INVALID'):
        router.bind_plan(bound.captured_plan,{'lookup':'vulnerability_lookup'},RuntimePolicy())


def test_binding_uses_original_permission_validation():
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    item=task(name='match_component_vulnerabilities',arguments={'component_id':'00000000-0000-0000-0000-000000000001'})
    with pytest.raises(PermissionError):
        AgentRouter(create_default_registry().freeze()).bind_plan(TaskPlan(tasks=[item]),{'lookup':'version_match'},RuntimePolicy())

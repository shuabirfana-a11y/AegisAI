"""Invalid plans never reach workers; compiled plans resist caller mutations."""
import pytest
from .test_contracts_plan import task


def graph(tasks, **policy):
    from app.runtime.contracts import TaskPlan, RuntimePolicy
    from app.runtime.graph import compile_graph
    return compile_graph(TaskPlan(tasks=tasks), RuntimePolicy(**policy))


def test_graph_builder_supports_tasks_then_compiles_dependency_layers():
    from app.runtime.graph import TaskGraphBuilder, compile_graph
    from app.runtime.contracts import RuntimePolicy
    builder = TaskGraphBuilder()
    builder.add_task(task(task_id='a'))
    builder.add_task(task(task_id='b', dependencies=['a']))
    builder.add_task(task(task_id='c', dependencies=['a']))
    got = compile_graph(builder.compile(), RuntimePolicy())
    assert got.layers == (('a',), ('b', 'c'))
    with pytest.raises(ValueError):
        builder.add_task(task(task_id='a'))


@pytest.mark.parametrize('kind', ['cycle', 'missing', 'duplicate', 'self', 'depth', 'budget', 'unknown'])
def test_invalid_graphs_are_rejected(kind):
    tasks = {
        'cycle': lambda: [task(task_id='a', dependencies=['b']), task(task_id='b', dependencies=['a'])],
        'missing': lambda: [task(dependencies=['absent'])],
        'duplicate': lambda: [task(), task()],
        'self': lambda: [task(dependencies=['T1'])],
        'depth': lambda: [task(task_id=f't{i}', dependencies=[f't{i-1}'] if i else []) for i in range(9)],
        'budget': lambda: [task(task_id=f't{i}', max_tool_calls=8) for i in range(5)],
        'unknown': lambda: [task(allowed_tools=['get_vulnerability', 'delete_database'])],
    }[kind]()
    with pytest.raises(ValueError):
        graph(tasks)


def test_graph_rejects_seventeenth_task_and_lower_policy_limits():
    with pytest.raises(ValueError):
        graph([task(task_id=f't{i}') for i in range(17)])
    with pytest.raises(ValueError):
        graph([task(), task(task_id='T2')], max_tasks=1)


@pytest.mark.parametrize('name,args', [
    ('match_component_vulnerabilities', {'component_id': '00000000-0000-0000-0000-000000000001'}),
    ('find_poc_candidates', {'target': 'CVE-2099-9999001', 'refresh': True}),
])
def test_server_permissions_cannot_be_granted_by_task_allowlist(name, args):
    with pytest.raises(PermissionError):
        graph([task(allowed_tools=[name], input_data={'steps': [{'name': name, 'arguments': args}]})])


def test_graph_rejects_wrong_tool_input_before_execution():
    with pytest.raises(ValueError):
        graph([task(input_data={'steps': [{'name': 'get_vulnerability', 'arguments': {'target': 'invalid'}}]})])


def test_graph_snapshot_is_not_mutable_through_original_or_returned_task():
    original = task()
    got = graph([original])
    original.input_data['steps'][0]['arguments']['target'] = 'CVE-2099-1111'
    returned = got.task('T1')
    returned.input_data['steps'][0]['arguments']['target'] = 'CVE-2099-2222'
    assert got.task('T1').input_data['steps'][0]['arguments']['target'] == 'CVE-2099-9999001'


def test_state_machine_branches_and_rejects_late_success():
    from app.runtime.states import transition
    from app.runtime.contracts import TaskState as S
    assert transition(S.CREATED, S.PENDING) == S.PENDING
    assert transition(S.PENDING, S.READY) == S.READY
    assert transition(S.READY, S.RUNNING) == S.RUNNING
    for end in (S.SUCCESS, S.FAILED, S.WAITING_REVIEW):
        assert transition(S.RUNNING, end) == end
        with pytest.raises(ValueError):
            transition(end, S.SUCCESS)
    assert transition(S.PENDING, S.BLOCKED) == S.BLOCKED
    assert transition(S.READY, S.BLOCKED) == S.BLOCKED
    with pytest.raises(ValueError):
        transition(S.CREATED, S.SUCCESS)

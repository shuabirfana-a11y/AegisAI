"""Bounded rule templates. LLM planning is a separately approved future phase."""
from app.assistant.contracts import QueryRequest
from app.assistant.router import route
from app.runtime.contracts import RuntimePolicy, TaskContract, TaskPlan


def build_plan(request: QueryRequest, policy: RuntimePolicy) -> TaskPlan:
    routed = route(request.question, target=request.target,
                   asset_id=request.asset_id, mode=request.mode)
    if routed['blocked']:
        raise PermissionError('Request rejected by existing router policy')
    if request.realtime:
        raise PermissionError('Phase 10-A templates use locally stored intelligence')
    routed = {**routed, 'generation_calls': 0,
              'model_capability': 'Gateway available; generation not used by runtime-v1'}
    tasks = []

    def add(name, arguments, dependencies=(), description=None):
        item = TaskContract(task_id=f'T{len(tasks) + 1}',
                            description=description or name,
                            input_data={'steps': [{'name': name, 'arguments': arguments}]},
                            allowed_tools=[name], dependencies=dependencies, max_tool_calls=1)
        tasks.append(item)
        return item.task_id

    def missing(fields):
        tasks.append(TaskContract(task_id=f'T{len(tasks) + 1}', task_type='input_required',
                                  description='Specify the investigation target',
                                  input_data={'required_fields': fields},
                                  max_tool_calls=0, acceptance_criteria=[]))

    targets = routed['targets']
    if routed['asset'] and (not request.asset_id or not targets):
        missing((['asset_id'] if not request.asset_id else []) + (['target'] if not targets else []))
    elif routed['asset']:
        for target in targets:
            root = add('get_vulnerability', {'target': target}, description='查询漏洞')
            versions = add('relation_query', {'target': target}, [root], '读取影响版本和关系')
            asset = add('get_asset', {'asset_id': str(request.asset_id)}, [versions], '读取所属资产')
            add('get_asset_risks', {'asset_id': str(request.asset_id)}, [asset], '读取已有风险快照')
    elif targets:
        for target in targets:
            root = add('get_vulnerability', {'target': target}, description='查询漏洞')
            if routed['path'] == 'deep' or any(s in request.question.casefold() for s in ('poc', 'patch', '补丁')):
                add('find_poc_candidates', {'target': target, 'refresh': False}, [root], '查询 PoC 候选')
                add('find_patch_candidates', {'target': target, 'refresh': False}, [root], '查询补丁候选')
    elif any(s in request.question.casefold() for s in ('系统状态', 'system status')):
        add('get_system_status', {})
    elif routed['retrieval'] == 'semantic':
        add('semantic_search', {'query': request.question})
    else:
        add('search_vulnerabilities', {k: v for k, v in {
            'product': routed['product'], 'high_severity': routed['high_severity'],
            'days': routed['days']}.items() if v is not None})
    return TaskPlan(tasks=tasks, route=routed)

"""Scoped adapter validation. The original five-role Planner is unchanged."""
import hashlib,json
from app.runtime.contracts import TaskInput,TaskContract,TaskPlan,json_bytes
from app.runtime.graph import compile_graph
from app.planner.schemas import ValidatedPlan
from app.planner.validator import reject,missing_fields
from app.tooling.contracts import REGISTRY
from app.agents.investigation.planning import InvestigationPlan
from app.agents.investigation.roles import ROLES,PROMPT_VERSION,REGISTRY_VERSION

def validate_investigation_plan(plan,context):
    encoded=json_bytes(plan.model_dump(mode='json',by_alias=True),65536)
    plan=InvestigationPlan.model_validate_json(encoded)
    scope=context.scope; route=context.route
    if route.get('blocked'):reject('REQUEST_BLOCKED')
    covered=set(); observed_versions=set(); asset_covered=False; version_input=False
    candidate_covered=False
    ids={t.task_id for t in plan.tasks}
    if len(ids)!=len(plan.tasks):reject('DUPLICATE_TASK')
    missing=missing_fields(scope,context.policy)
    for idx,t in enumerate(plan.tasks):
        path=f'$.tasks[{idx}]'; role=ROLES[t.planner_type]
        if not set(t.allowed_tools)<=role.tools:reject('TASK_TOOL_FORBIDDEN',path)
        steps=TaskInput.model_validate(t.input_data)
        if t.task_type=='input_required':
            permitted={'vulnerability_lookup':{'target','version'},'evidence_search':{'target'},'asset_lookup':{'asset_id'}}[t.planner_type]
            if not set(steps.required_fields)<=permitted & missing:reject('FALSE_MISSING_INPUT',path)
            if t.planner_type=='asset_lookup':asset_covered=True
            if t.planner_type=='vulnerability_lookup' and 'version' in steps.required_fields:version_input=True
            continue
        if not role.criteria<=set(t.acceptance_criteria):reject('MINIMUM_CRITERIA_MISSING',path)
        for step in steps.steps:
            spec=REGISTRY.get(step.name)
            if spec is None or spec.permission!='READ_ONLY' or spec.permission not in context.policy.permissions:reject('TOOL_PERMISSION_DENIED',path)
            try:args=spec.input.model_validate(step.arguments).model_dump(mode='json',exclude_none=True)
            except (ValueError,TypeError):reject('TOOL_INPUT_INVALID',path)
            if args.get('refresh'):reject('REFRESH_FORBIDDEN',path)
            if scope.get('candidate_reference') and step.name=='get_vulnerability' and not args.get('candidate_reference'):
                reject('CANDIDATE_LOOKUP_REQUIRED',path)
            if args.get('candidate_reference'):
                if args['candidate_reference']!=scope.get('candidate_reference'):reject('CANDIDATE_SCOPE_MISMATCH',path)
                if step.name=='get_evidence':candidate_covered=True
            if 'target' in args:
                if args['target'] not in scope['targets']:reject('TARGET_SCOPE_MISMATCH',path)
                if step.name=='get_vulnerability':covered.add(args['target'])
            if 'asset_id' in args:
                if args['asset_id']!=scope.get('asset_id'):reject('ID_SCOPE_MISMATCH',path)
                asset_covered=True
            if step.name=='semantic_search' and args['query']!=scope['question']:reject('QUERY_SCOPE_MISMATCH',path)
            if step.name=='inspect_component_version':
                component=scope.get('component') or {}
                for key,value in args.items():
                    if key!='target' and str(value).casefold()!=str(component.get(key,'')).casefold():reject('COMPONENT_SCOPE_MISMATCH',path)
                observed_versions.add(args['target'])
            if step.name=='search_vulnerabilities':
                if scope['targets']:reject('EXACT_LOOKUP_REQUIRED',path)
                if args.get('q') is not None and args['q']!=scope['question']:reject('QUERY_SCOPE_MISMATCH',path)
                product=route.get('product') or (scope.get('component') or {}).get('name')
                if str(args.get('product') or '').casefold()!=str(product or '').casefold():reject('PRODUCT_SCOPE_MISMATCH',path)
                if args.get('days')!=route.get('days') or args.get('high_severity',False)!=bool(route.get('high_severity')) or args.get('ai_relevance') is not None:reject('FILTER_SCOPE_MISMATCH',path)
    if not set(scope['targets'])<=covered:reject('TARGET_COVERAGE_MISSING')
    if scope.get('candidate_reference') and not candidate_covered:reject('CANDIDATE_REFERENCE_REQUIRED')
    if (scope.get('component') or {}).get('version') and scope['targets'] and not set(scope['targets'])<=observed_versions:reject('VERSION_OBSERVATION_REQUIRED')
    if scope.get('component') and scope['asset_analysis'] and scope['targets'] and not scope['component'].get('version') and not version_input:reject('VERSION_INPUT_REQUIRED')
    if scope.get('asset_id') and not asset_covered:reject('ASSET_LOOKUP_REQUIRED')
    runtime=TaskPlan(tasks=tuple(TaskContract.model_validate({k:v for k,v in t.model_dump().items() if k!='planner_type'}) for t in plan.tasks),
        route={**route,'planner_run_id':str(context.planner_run_id),'planning_model_calls':context.model_calls,
               'model_capability':'Constrained investigation planner; source discovery only',
               'investigation_v1':{'prompt_version':PROMPT_VERSION,'registry_version':REGISTRY_VERSION}})
    try:graph=compile_graph(runtime,context.policy)
    except (ValueError,PermissionError,TypeError):reject('DAG_OR_BUDGET_INVALID')
    return ValidatedPlan(runtime_plan_json=graph.plan_json,semantic_types_json=json.dumps({t.task_id:t.planner_type for t in plan.tasks},sort_keys=True),
        candidate_json=encoded.decode(),plan_hash=hashlib.sha256(graph.plan_json.encode()).hexdigest(),validator_version='investigation-validator-v1')

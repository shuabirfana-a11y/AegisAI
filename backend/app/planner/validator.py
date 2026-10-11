"""No execution here: constrain intent and compile with the existing DAG checks."""
import hashlib
import json
from pydantic import ValidationError
from app.tooling.contracts import REGISTRY
from app.runtime.contracts import TaskContract, TaskInput, TaskPlan, json_bytes
from app.runtime.graph import compile_graph
from app.planner.registry import TASK_REGISTRY, MISSING_FIELDS
from app.planner.schemas import PlannerPlan, ValidatedPlan, ValidationIssue

class PlanValidationError(ValueError):
    def __init__(self, code, path='$'):
        self.issues=(ValidationIssue(code=code,path=path,message='Candidate plan rejected by server validation.'),)
        super().__init__(code)

def reject(code, path='$'):raise PlanValidationError(code,path)

def missing_fields(scope, policy):
    missing={k for k in ('asset_id','component_id','snapshot_id') if not scope.get(k)}
    if not scope['targets']:missing.add('target')
    if not (scope.get('component') or {}).get('version'):missing.add('version')
    if 'WRITE' not in policy.permissions:missing.add('write_authorization')
    return missing

def validate_plan(plan: PlannerPlan, context) -> ValidatedPlan:
    try:
        encoded=json_bytes(plan.model_dump(mode='json',by_alias=True),65536)
        plan=PlannerPlan.model_validate_json(encoded)
    except (ValueError,TypeError,RecursionError):reject('SCHEMA_INVALID')
    scope=context.scope;route=context.route
    if route.get('blocked'):reject('REQUEST_BLOCKED')
    tasks=plan.tasks;types={t.task_id:t.planner_type for t in tasks}
    if len(types)!=len(tasks):reject('DUPLICATE_TASK')
    available_missing=missing_fields(scope,context.policy)
    covered_targets=set()
    for idx,t in enumerate(tasks):
        path=f'$.tasks[{idx}]'
        role=TASK_REGISTRY[t.planner_type]
        if not set(t.allowed_tools)<=role.tools:reject('TASK_TOOL_FORBIDDEN',path+'.allowed_tools')
        for name in t.allowed_tools:
            if REGISTRY[name].permission not in context.policy.permissions:
                reject('TOOL_PERMISSION_DENIED',path+'.allowed_tools')
        inputs=TaskInput.model_validate(t.input_data)
        if t.task_type=='input_required':
            fields=set(inputs.required_fields)
            role_fields={'vulnerability_lookup':{'target'},'version_match':{'component_id','version','write_authorization'},
                         'evidence_search':{'target'},'patch_analysis':{'target'},
                         'risk_analysis':{'target','asset_id','snapshot_id'}}[t.planner_type]
            if not fields <= MISSING_FIELDS & available_missing & role_fields:reject('FALSE_MISSING_INPUT',path)
            continue
        if not role.criteria<=set(t.acceptance_criteria):reject('MINIMUM_CRITERIA_MISSING',path)
        if t.planner_type=='version_match':
            if 'match_component_vulnerabilities' not in {s.name for s in inputs.steps}:
                reject('VERSION_MATCH_REQUIRED',path)
            if not scope.get('component_id') or 'WRITE' not in context.policy.permissions:
                reject('VERSION_INPUT_OR_PERMISSION_MISSING',path)
        if t.planner_type=='risk_analysis' and scope['asset_analysis'] and not scope.get('asset_id'):
            reject('ASSET_INPUT_MISSING',path)
        if t.planner_type=='risk_analysis' and scope['asset_analysis'] and not (
                {'get_asset_risks','explain_asset_risk'} & {s.name for s in inputs.steps}):
            reject('ASSET_RISK_QUERY_REQUIRED',path)
        for j,s in enumerate(inputs.steps):
            sp=path+f'.input_data.steps[{j}]'
            try:args=REGISTRY[s.name].input.model_validate(s.arguments).model_dump(mode='json')
            except (ValueError,TypeError):reject('TOOL_INPUT_INVALID',sp)
            if args.get('refresh'):reject('REFRESH_FORBIDDEN',sp)
            for field in ('target','asset_id','component_id','snapshot_id'):
                if field in args:
                    val=args[field]
                    if field=='target':
                        if val not in scope['targets']:reject('TARGET_SCOPE_MISMATCH',sp)
                        if t.planner_type=='vulnerability_lookup':covered_targets.add(val)
                    elif not val or val!=scope.get(field):reject('ID_SCOPE_MISMATCH',sp)
            if s.name=='resolve_component':
                component=scope.get('component') or {}
                for key,val in args.items():
                    if val is not None and str(val).casefold()!=str(component.get(key,'')).casefold():
                        reject('COMPONENT_SCOPE_MISMATCH',sp)
            if s.name=='semantic_search' and args['query']!=scope['question']:
                reject('QUERY_SCOPE_MISMATCH',sp)
            if s.name=='search_vulnerabilities':
                if scope['targets']:
                    # Search can filter or return title matches before the actual
                    # target. Explicit targets require get_vulnerability instead.
                    reject('EXACT_LOOKUP_REQUIRED',sp)
                if args.get('q') is not None and args['q']!=scope['question']:
                    reject('QUERY_SCOPE_MISMATCH',sp)
                product=route.get('product') or (scope.get('component') or {}).get('name')
                if str(args.get('product') or '').casefold()!=str(product or '').casefold():
                    reject('PRODUCT_SCOPE_MISMATCH',sp)
                if args.get('days')!=route.get('days'):reject('FILTER_SCOPE_MISMATCH',sp)
                if args['high_severity']!=bool(route.get('high_severity')):reject('FILTER_SCOPE_MISMATCH',sp)
                if args.get('ai_relevance') is not None:reject('FILTER_SCOPE_MISMATCH',sp)
    if scope['targets'] and not set(scope['targets'])<=covered_targets:reject('TARGET_COVERAGE_MISSING')
    if scope['asset_analysis']:
        for kind in ('vulnerability_lookup','version_match','patch_analysis','risk_analysis'):
            if kind not in types.values():reject('TASK_COVERAGE_MISSING')
    by_id={t.task_id:t for t in tasks}
    def ancestors(t,seen=None):
        seen=set() if seen is None else seen
        for dep in t.dependencies:
            if dep not in by_id:reject('DEPENDENCY_MISSING')
            if dep not in seen:
                seen.add(dep);ancestors(by_id[dep],seen)
        return seen
    for t in tasks:
        previous={'version_match':'vulnerability_lookup','patch_analysis':
                  'version_match' if scope['asset_analysis'] else 'vulnerability_lookup',
                  'risk_analysis':'patch_analysis' if scope['asset_analysis'] else 'vulnerability_lookup'}.get(t.planner_type)
        if previous and previous not in {types[id] for id in ancestors(t)}:
            reject('REQUIRED_DEPENDENCY_MISSING')
    try:
        runtime=TaskPlan(tasks=tuple(TaskContract.model_validate({k:v for k,v in t.model_dump().items()
                              if k!='planner_type'}) for t in tasks),route={**route,
            'planner_run_id':str(context.planner_run_id),'planning_model_calls':context.model_calls,
            'model_capability':'Constrained structured planner; server validated'})
        graph=compile_graph(runtime,context.policy)
    except (ValueError,PermissionError,TypeError):reject('DAG_OR_BUDGET_INVALID')
    return ValidatedPlan(runtime_plan_json=graph.plan_json,semantic_types_json=json.dumps(types,sort_keys=True),
        candidate_json=encoded.decode(),plan_hash=hashlib.sha256(graph.plan_json.encode()).hexdigest())

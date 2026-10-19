"""Request-owned obligations and append-only completion from the readonly catalog.

This is plan construction, never fact repair. Unchanged generation schema, server
scope checks and graph budgets must all accept the effective plan before use.
"""
from dataclasses import dataclass
from copy import deepcopy
import hashlib
import json
from jsonschema.exceptions import ValidationError as SchemaError
from app.llm.gateway import prepare_schema
from app.llm.schemas import strict_json
from app.runtime.contracts import TaskInput, json_bytes
from app.tooling.contracts import REGISTRY
from app.planner.validator import PlanValidationError
from app.agents.investigation.roles import ROLES
from app.agents.investigation.planning import InvestigationPlan
from app.agents.investigation.validation import validate_investigation_plan


@dataclass(frozen=True)
class RequiredTask:
    role: str
    tool: str
    arguments_json: str

    def as_dict(self):
        return {'role':self.role,'tool':self.tool,'arguments':json.loads(self.arguments_json)}


def task_requirements(context):
    """Same pre-existing scope obligations as scoped schema/server validation.

    No product keywords, generated plan, benchmark ID, answer or missing input
    participates. Snapshot arguments as immutable JSON before model generation.
    """
    scope=context.scope;required=[]
    if scope.get('asset_id'):
        required.append(RequiredTask('asset_lookup','get_asset',json.dumps({'asset_id':scope['asset_id']},sort_keys=True)))
    component={k:v for k,v in (scope.get('component') or {}).items() if v is not None}
    if component.get('version'):
        for target in scope['targets']:
            required.append(RequiredTask('vulnerability_lookup','inspect_component_version',
                json.dumps({'target':target,**component},sort_keys=True)))
    if scope.get('candidate_reference'):
        for target in scope['targets']:
            required.append(RequiredTask('evidence_search','get_evidence',
                json.dumps({'target':target,'candidate_reference':scope['candidate_reference']},sort_keys=True)))
    return tuple(required)


def complete_required_tasks(raw,context,request,output_model,requirements):
    """Return a revalidated effective snapshot plus a private provenance receipt.

    Only append request-required asset, version or candidate-evidence tasks.
    Do not edit generated nodes/edges/criteria, replace bad arguments, fabricate
    facts, remove a missing dependency, or increase any budget. Unknown/malformed
    candidates and any unrelated contract failure stay rejected.
    """
    receipt={'contract':'investigation-task-invariants-v1','planner_run_id':str(context.planner_run_id),
        'trace_id':str(context.trace_id),'requirements':[r.as_dict() for r in requirements],
        'original_candidate_status':'REJECTED','status':'NOT_REPAIRABLE','added_tasks':[]}
    try:
        original=strict_json(raw);json_bytes(original,65536)
        # Parse solely to inspect legitimate nodes, not to inject model defaults.
        parsed=InvestigationPlan.model_validate(original)
        value=deepcopy(original)
        # Never accidentally satisfy an unresolved model dependency by assigning
        # its name to a new node; missing original producers must remain missing.
        ids={t.task_id for t in parsed.tasks}|{d for t in parsed.tasks for d in t.dependencies}
        for requirement in requirements:
            args=json.loads(requirement.arguments_json)
            present=any(step.name==requirement.tool and
                (requirement.tool=='get_asset' or step.arguments.get('target')==args['target'])
                for t in parsed.tasks if t.task_type=='tool_sequence'
                for step in TaskInput.model_validate(t.input_data).steps)
            if present:continue  # Wrong scoped values must fail, never get replaced.
            spec=REGISTRY[requirement.tool];role=ROLES[requirement.role]
            if spec.permission!='READ_ONLY' or spec.permission not in context.policy.permissions or requirement.tool not in role.tools:
                raise ValueError('Catalog permission mismatch')
            spec.input.model_validate(args)
            dependencies=[]
            if requirement.tool in {'inspect_component_version','get_evidence'}:
                producers=[t.task_id for t in parsed.tasks if t.task_type=='tool_sequence'
                    and t.planner_type=='vulnerability_lookup'
                    and any(s.name=='get_vulnerability' and s.arguments.get('target')==args['target']
                        for s in TaskInput.model_validate(t.input_data).steps)]
                if len(producers)!=1:raise ValueError('Unresolved lookup dependency')
                dependencies=producers
            base={'get_asset':'required-asset','inspect_component_version':'required-version',
                'get_evidence':'required-evidence'}[requirement.tool]
            task_id=base;index=1
            while task_id in ids:
                task_id=f'{base}-{index}';index+=1
            ids.add(task_id)
            node={'type':requirement.role,'task_id':task_id,'task_type':'tool_sequence',
                'description':'Execute supplied request observation required by the task contract',
                'input_data':{'steps':[{'name':requirement.tool,'arguments':args}]},
                'dependencies':dependencies,'allowed_tools':[requirement.tool],
                'acceptance_criteria':sorted(role.criteria),'max_tool_calls':1}
            value['tasks'].append(node);receipt['added_tasks'].append(deepcopy(node))
        if not receipt['added_tasks']:return None,receipt
        # Exactly the Gateway validator and strict output model, then the existing
        # scope/permissions/dependency/cycle/depth/call-budget validator. No bypass.
        _,_,schema_hash,validator=prepare_schema(request,output_model)
        validator.validate(value)
        encoded=json_bytes(value,65536).decode()
        output_model.model_validate_json(encoded,strict=True)
        validated=validate_investigation_plan(InvestigationPlan.model_validate_json(encoded),context)
        receipt.update(status='REPAIRED',effective_candidate_status='VALIDATED',schema_hash=schema_hash,
            original_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            effective_candidate_sha256=hashlib.sha256(validated.candidate_json.encode()).hexdigest(),
            effective_candidate=json.loads(validated.candidate_json),runtime_plan_sha256=validated.plan_hash)
        return validated,receipt
    except (ValueError,TypeError,KeyError,SchemaError,PlanValidationError) as exc:
        # Retain the original rejection; attempted appends are never executable.
        receipt.update(status='REJECTED',effective_candidate_status='REJECTED',error_type=type(exc).__name__)
        return None,receipt

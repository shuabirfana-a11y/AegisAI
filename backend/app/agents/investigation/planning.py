from typing import Literal
from pydantic import ConfigDict, Field
from app.planner.schemas import PlannerPlan, PlannerTaskContract

InvestigationTaskType=Literal['vulnerability_lookup','evidence_search','asset_lookup']
class InvestigationTaskCandidate(PlannerTaskContract):
    model_config=ConfigDict(extra='forbid',frozen=True,allow_inf_nan=False,populate_by_name=True)
    planner_type:InvestigationTaskType=Field(alias='type')

class InvestigationPlan(PlannerPlan):
    tasks:tuple[InvestigationTaskCandidate,...]=Field(min_length=1,max_length=16)


def scoped_plan_model(context):
    """Model-facing scope constraints only; original server validation still applies."""
    from copy import deepcopy
    from app.tooling.contracts import REGISTRY
    from app.agents.investigation.roles import ROLES
    scope=context.scope
    component={k:v for k,v in (scope.get('component') or {}).items() if v is not None}
    targets=scope['targets']
    tools=[]
    for name in sorted(set().union(*(role.tools for role in ROLES.values()))):
        variants=[]
        if name in ('get_vulnerability','get_evidence','get_claims','relation_query'):
            variants=[{'target':t} for t in targets]
        elif name=='inspect_component_version' and component.get('version'):
            variants=[{'target':t,**component} for t in targets]
        elif name=='get_asset' and scope.get('asset_id'):
            variants=[{'asset_id':scope['asset_id']}]
        elif name=='semantic_search':variants=[{'query':scope['question']}]
        elif name=='search_vulnerabilities' and not targets:
            route=context.route
            variants=[{'q':scope['question'],'product':route.get('product') or component.get('name'),
                'days':route.get('days'),'high_severity':bool(route.get('high_severity')),'ai_relevance':None}]
        for exact in variants:
            args=deepcopy(REGISTRY[name].input.model_json_schema())
            for key,prop in args.get('properties',{}).items():
                # Unbound optional fields cannot be guessed; bounded pagination
                # retains the original registered limits and defaults.
                if key in exact:prop['const']=exact[key]
                elif key not in ('limit','offset'):prop['const']=None
            tools.append({'type':'object','additionalProperties':False,'required':['name','arguments'],
                          'properties':{'name':{'type':'string','const':name},'arguments':args}})
    def constrain(schema):
        def visit(node):
            if isinstance(node,dict):
                props=node.get('properties',{})
                if 'steps' in props and isinstance(props['steps'],dict):
                    props['steps']['items']={'$ref':'#/$defs/ScopedToolStep'}
                for value in tuple(node.values()):visit(value)
            elif isinstance(node,list):
                for value in node:visit(value)
        visit(schema)
        # Store scope-bound alternatives once. Repeating these inside each
        # TaskContract branch exceeds gateway limits for supported target sets.
        schema.setdefault('$defs',{})['ScopedToolStep']={'anyOf':tools}
    # Field-level TaskContract schemas are resolved into $defs after Pydantic's
    # root json_schema_extra hook. Constrain the complete resolved schema.
    def model_schema(cls,*args,**kwargs):
        schema=InvestigationPlan.model_json_schema(*args,**kwargs)
        constrain(schema)
        return schema
    return type('ScopedInvestigationPlan',(InvestigationPlan,),{'model_json_schema':classmethod(model_schema)})


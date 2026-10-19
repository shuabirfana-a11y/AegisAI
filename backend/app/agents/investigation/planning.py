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
            if name in ('get_evidence','get_vulnerability') and scope.get('candidate_reference'):
                variants=[{**args,'candidate_reference':scope['candidate_reference']} for args in variants]
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
            if exact.get('candidate_reference'):
                args['required']=list(dict.fromkeys(args.get('required',[])+['candidate_reference']))
            for key,prop in args.get('properties',{}).items():
                # Unbound optional fields cannot be guessed; bounded pagination
                # retains the original registered limits and defaults.
                if key in exact:prop['const']=exact[key]
                elif key not in ('limit','offset'):prop['const']=None
            tools.append({'type':'object','additionalProperties':False,'required':['name','arguments'],
                          'properties':{'name':{'type':'string','const':name},'arguments':args}})
    def constrain(schema):
        definitions=schema.setdefault('$defs',{})
        candidate=definitions['InvestigationTaskCandidate']
        props=deepcopy(candidate['properties'])
        from app.planner.schemas import _task_input_schema
        props['input_data']=_task_input_schema()
        props['input_data']['properties']['steps']['items']={'$ref':'#/$defs/ScopedToolStep'}
        # Executable candidates must declare their existing role criteria;
        # Runtime's legacy two-condition default is insufficient for evidence.
        props['acceptance_criteria'].pop('default',None)
        props['acceptance_criteria']['description']='Explicit registered acceptance conditions for this executable task role.'
        refs=[]
        for index,tool in enumerate(tools):
            key='ScopeTool'+str(index);definitions[key]=tool
            refs.append({'$ref':'#/$defs/'+key})
        definitions['ScopedToolStep']={'anyOf':refs}
        executable={'required':['allowed_tools','acceptance_criteria'],'properties':{
            'allowed_tools':{'minItems':1},'max_tool_calls':{'minimum':1},
            'input_data':{'required':['steps'],'properties':{'steps':{'minItems':1},'required_fields':{'maxItems':0}}}}}
        missing={'properties':{'allowed_tools':{'maxItems':0},'max_tool_calls':{'const':0},
            'input_data':{'required':['required_fields'],'properties':{'steps':{'maxItems':0},'required_fields':{'minItems':1}}}}}
        rules=[{'if':{'properties':{'task_type':{'const':'tool_sequence'}}},'then':executable},
               {'if':{'properties':{'task_type':{'const':'input_required'}}},'then':missing}]
        for role,spec in ROLES.items():
            role_refs=[ref for ref,tool in zip(refs,tools) if tool['properties']['name']['const'] in spec.tools]
            key='RoleStep_'+role
            definitions[key]={'anyOf':role_refs} if role_refs else False
            rules.append({'if':{'properties':{'type':{'const':role}}},'then':{'properties':{
                'allowed_tools':{'items':{'enum':sorted(spec.tools)}},
                'input_data':{'properties':{'steps':{'items':{'$ref':'#/$defs/'+key}}}}}}})
            rules.append({'if':{'properties':{'type':{'const':role},'task_type':{'const':'tool_sequence'}}},
                'then':{'properties':{'acceptance_criteria':{'allOf':[
                    {'contains':{'const':criterion},'minContains':1} for criterion in sorted(spec.criteria)]}}}})
            # Optional absent deployment metadata is not a required input for
            # fact discovery. Request only inputs needed by the frozen scope.
            required=[]
            if role in ('vulnerability_lookup','evidence_search') and not targets:
                required.append('target')
            if (role=='vulnerability_lookup' and component and targets
                    and scope['asset_analysis'] and not component.get('version')):
                required.append('version')
            if role=='asset_lookup' and scope['asset_analysis'] and not scope.get('asset_id'):
                required.append('asset_id')
            rules.append({'if':{'properties':{'type':{'const':role},'task_type':{'const':'input_required'}}},
                'then':{'properties':{'input_data':{'properties':{'required_fields':{
                    'items':{'enum':required} if required else False}}}}}})
        # Present each wire field once, rather than duplicating complete tasks
        # across anyOf branches. Actual Pydantic/Runtime validation is unchanged.
        definitions['InvestigationTaskCandidate']={'type':'object','additionalProperties':False,
            'required':list(dict.fromkeys(candidate['required']+['task_type','allowed_tools','max_tool_calls'])),
            'properties':props,'allOf':rules}
        conditions=[]
        for target in targets:
            lookup={'type':'object','required':['name','arguments'],'properties':{
                'name':{'const':'get_vulnerability'},'arguments':{'required':['target'],'properties':{'target':{'const':target}}}}}
            matches={'required':['input_data'],'properties':{'input_data':{'required':['steps'],
                'properties':{'steps':{'contains':lookup,'minContains':1}}}}}
            conditions.append({'contains':matches,'minContains':1,'maxContains':1})
            if component.get('version'):
                observed={'type':'object','required':['name','arguments'],'properties':{
                    'name':{'const':'inspect_component_version'},
                    'arguments':{'required':['target'],'properties':{'target':{'const':target}}}}}
                conditions.append({'contains':{'required':['input_data'],'properties':{'input_data':{
                    'required':['steps'],'properties':{'steps':{'contains':observed,'minContains':1}}}}},
                    'minContains':1})
            # Even differing pagination cannot duplicate the same target inside one task.
            props['input_data']['properties']['steps'].setdefault('allOf',[]).append(
                {'contains':lookup,'minContains':0,'maxContains':1})
        # Mirror the existing server obligation in the generation contract.
        # A field-only repair must not silently discard the supplied asset read.
        if scope.get('asset_id'):
            asset_step={'type':'object','required':['name','arguments'],'properties':{
                'name':{'const':'get_asset'},'arguments':{'required':['asset_id'],
                'properties':{'asset_id':{'const':scope['asset_id']}}}}}
            conditions.append({'contains':{'required':['input_data'],'properties':{'input_data':{
                'required':['steps'],'properties':{'steps':{'contains':asset_step,'minContains':1}}}}},
                'minContains':1})
        if conditions:schema['properties']['tasks']['allOf']=conditions
        if scope.get('candidate_reference'):
            step={'type':'object','required':['name','arguments'],'properties':{
                'name':{'const':'get_evidence'},'arguments':{'required':['candidate_reference'],
                'properties':{'candidate_reference':{'const':scope['candidate_reference']}}}}}
            schema['properties']['tasks'].setdefault('allOf',[]).append({'contains':{
                'required':['input_data'],'properties':{'input_data':{'required':['steps'],
                'properties':{'steps':{'contains':step,'minContains':1}}}}},'minContains':1})
    # Field-level TaskContract schemas are resolved into $defs after Pydantic's
    # root json_schema_extra hook. Constrain the complete resolved schema.
    def model_schema(cls,*args,**kwargs):
        schema=InvestigationPlan.model_json_schema(*args,**kwargs)
        constrain(schema)
        return schema
    return type('ScopedInvestigationPlan',(InvestigationPlan,),{'model_json_schema':classmethod(model_schema)})


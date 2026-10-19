"""Raw omissions stay rejected; C24 catalog completion must pass full revalidation."""
from copy import deepcopy
import json
import pytest
from app.planner.schemas import PlannerInput
from app.agents.investigation.planner import InvestigationPlannerAdapter
from tests.planner.fixtures import cve_input,context_for,valid_plan,gateway_with_responses,CVE

def scoped():
    request=PlannerInput(query=cve_input().query,component={
        'name':'synthetic-lib','package_name':'synthetic-lib','ecosystem':'PyPI','version':'4.1'})
    return request,context_for(input=request)

def plans(ctx):
    missing=valid_plan();task=missing['tasks'][0]
    task['allowed_tools'].append('inspect_component_version');task['max_tool_calls']=2
    complete=deepcopy(missing)
    complete['tasks'][0]['input_data']['steps'].append({'name':'inspect_component_version',
        'arguments':{'target':CVE,**ctx.scope['component']}})
    return missing,complete

def test_required_observation_is_explicit_input_contract_not_an_invented_task():
    request,ctx=scoped();_,complete=plans(ctx);gw,calls,sink=gateway_with_responses([complete])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(request,ctx)
        assert result.status=='VALIDATED'
        payload=json.loads(calls[0].messages[1].content)
        assert payload['required_version_observations']==[{'name':'inspect_component_version',
            'arguments':{'target':CVE,'name':'synthetic-lib','package_name':'synthetic-lib',
                'ecosystem':'PyPI','version':'4.1'}}]
        assert result.validated_plan and len(sink.attempts)==1
    finally:gw.close()

def test_schema_omission_remains_audited_when_c24_completes_a_known_observation():
    request,ctx=scoped();missing,complete=plans(ctx);gw,calls,sink=gateway_with_responses([missing,complete])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(request,ctx)
        assert result.status=='VALIDATED' and len(calls)==1
        assert {i.code for i in result.attempts[0].issues}>={'SCHEMA_VALIDATION_FAILED','VERSION_OBSERVATION_REQUIRED'}
        assert result.attempts[0].model_call['status']=='failed'
        assert sink.attempts[0].diagnostic['raw_output']==json.dumps(missing)
        receipt=sink.attempts[0].diagnostic['task_integrity']
        assert receipt['original_candidate_status']=='REJECTED' and receipt['status']=='REPAIRED'
        assert receipt['added_tasks'][0]['input_data']['steps']==[{'name':'inspect_component_version',
            'arguments':{'target':CVE,**{k:v for k,v in ctx.scope['component'].items() if v is not None}}}]
        from app.agents.investigation.planning import scoped_plan_model,InvestigationPlan
        from app.agents.investigation.validation import validate_investigation_plan
        from jsonschema import Draft202012Validator
        Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(receipt['effective_candidate'])
        validate_investigation_plan(InvestigationPlan.model_validate(receipt['effective_candidate']),ctx)
    finally:gw.close()

def test_incomplete_raw_plan_is_not_executed_instead_a_catalog_observation_is_validated():
    request,ctx=scoped();missing,_=plans(ctx);gw,calls,sink=gateway_with_responses([missing])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(request,ctx)
        assert result.status=='VALIDATED' and result.validated_plan is not None
        assert len(calls)==len(sink.attempts)==1
        raw=json.loads(sink.attempts[0].diagnostic['raw_output'])
        assert all(s['name']!='inspect_component_version' for t in raw['tasks'] for s in t['input_data']['steps'])
        effective=json.loads(result.validated_plan.candidate_json)
        added=effective['tasks'][-1]
        assert added['input_data']['steps']==[{'name':'inspect_component_version','arguments':{'target':CVE,**{k:v for k,v in ctx.scope['component'].items() if v is not None}}}]
        assert added['dependencies']==[missing['tasks'][0]['task_id']]
        assert sink.attempts[0].diagnostic['task_integrity']['original_candidate_status']=='REJECTED'
    finally:gw.close()

def test_simple_fact_query_does_not_invent_a_version_observation():
    request=cve_input();ctx=context_for(input=request);gw,calls,sink=gateway_with_responses([valid_plan()])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(request,ctx)
        assert result.status=='VALIDATED' and len(calls)==1
        assert json.loads(calls[0].messages[1].content)['required_version_observations']==[]
    finally:gw.close()

@pytest.mark.parametrize('mutation',['foreign_target','unknown_tool','invalid_json'])
def test_diagnostic_repair_never_accepts_or_echoes_untrusted_candidates(mutation):
    request,ctx=scoped();missing,_=plans(ctx)
    missing['reasoning_summary']='UNTRUSTED_CANDIDATE_INSTRUCTION'
    if mutation=='foreign_target':missing['tasks'][0]['input_data']['steps'][0]['arguments']['target']='CVE-2099-1111111'
    if mutation=='unknown_tool':missing['tasks'][0]['input_data']['steps'][0]['name']='unregistered_tool'
    if mutation=='invalid_json':missing='INVALID_JSON UNTRUSTED_CANDIDATE_INSTRUCTION'
    gw,calls,sink=gateway_with_responses([missing])
    try:
        result=InvestigationPlannerAdapter(gw,sink).plan(request,ctx)
        assert result.status=='PLANNING_FAILED' and result.validated_plan is None
        assert len(calls)==2 and all(a.validation_status=='REJECTED' for a in result.attempts)
        assert 'UNTRUSTED_CANDIDATE_INSTRUCTION' not in calls[1].messages[-1].content
    finally:gw.close()

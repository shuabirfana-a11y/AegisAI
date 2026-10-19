"""The existing candidate-evidence obligation belongs to the request, not the LLM."""
from copy import deepcopy
from pathlib import Path
import json
from uuid import uuid4
import pytest
from jsonschema import Draft202012Validator,ValidationError
from app.agents.investigation.planner import InvestigationPlannerAdapter
from app.agents.investigation.planning import InvestigationPlan,scoped_plan_model
from app.agents.investigation.validation import validate_investigation_plan
from app.planner.schemas import PlannerInput
from app.planner.validator import PlanValidationError
from app.runtime.contracts import RuntimePolicy
from tests.planner.fixtures import valid_plan,task,cve_input,context_for,gateway_with_responses

URL='https://github.com/example/project/commit/'+'1'*40


def scoped(inp=None,policy=None):
    inp=inp or PlannerInput(query=cve_input().query,candidate_reference=URL)
    ctx=context_for(input=inp,policy=policy)
    ctx=ctx.model_copy(update={'scope_json':json.dumps({**ctx.scope,'candidate_reference':inp.candidate_reference})})
    plan=valid_plan();plan['tasks'][0]['input_data']['steps'][0]['arguments']={'target':inp.query.target,'candidate_reference':inp.candidate_reference}
    return inp,ctx,plan


def run(inp,ctx,*plans):
    gw,calls,sink=gateway_with_responses(plans)
    try:got=InvestigationPlannerAdapter(gw,sink).plan(inp,ctx)
    finally:gw.close()
    return got,calls


def effective(out):return json.loads(out.validated_plan.candidate_json)


@pytest.mark.parametrize('index',range(5))
def test_all_five_candidate_contexts_have_the_same_existing_obligation(index):
    row=json.loads((Path(__file__).with_name('fixtures')/'c25_candidate_inputs.json').read_text(encoding='utf8'))['cases'][index]
    inp,ctx,plan=scoped(PlannerInput.model_validate(row['input']))
    with pytest.raises(ValidationError):Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(plan)
    with pytest.raises(PlanValidationError,match='CANDIDATE_REFERENCE_REQUIRED'):validate_investigation_plan(InvestigationPlan.model_validate(plan),ctx)
    out,calls=run(inp,ctx,plan)
    assert out.status=='VALIDATED' and len(calls)==1
    node=effective(out)['tasks'][-1]
    assert node['type']=='evidence_search' and node['dependencies']==['lookup']
    assert node['input_data']['steps']==[{'name':'get_evidence','arguments':{'target':inp.query.target,'candidate_reference':inp.candidate_reference}}]
    assert set(node['acceptance_criteria'])=={'tools_succeeded','output_nonempty','evidence_present'}
    audit=out.attempts[0].diagnostic['task_integrity']
    assert audit['status']=='REPAIRED' and audit['original_candidate_status']=='REJECTED'
    Draft202012Validator(scoped_plan_model(ctx).model_json_schema()).validate(audit['effective_candidate'])


def test_recorded_twice_rejected_candidate_becomes_a_validated_plan_without_more_attempts():
    rows=json.loads((Path(__file__).with_name('fixtures')/'c25_candidate_inputs.json').read_text(encoding='utf8'))['cases']
    row=next(r for r in rows if len(r['plans'])==2 and all(len(p['tasks'])==1 for p in r['plans']))
    inp,ctx,_=scoped(PlannerInput.model_validate(row['input']))
    out,calls=run(inp,ctx,*row['plans'])
    assert out.status=='VALIDATED' and len(calls)==1
    assert json.loads(out.attempts[0].diagnostic['raw_output'])==row['plans'][0]
    assert out.attempts[0].diagnostic['task_integrity']['status']=='REPAIRED'


def test_already_complete_candidate_plan_is_unchanged():
    inp,ctx,p=scoped();p['tasks'].append(task('evidence_search','evidence','get_evidence',{'target':inp.query.target,'candidate_reference':URL},['lookup']))
    p['tasks'][-1]['acceptance_criteria'].append('evidence_present')
    out,calls=run(inp,ctx,p)
    assert out.status=='VALIDATED' and len(calls)==1 and len(effective(out)['tasks'])==2
    assert 'task_integrity' not in out.attempts[0].diagnostic


def test_ordinary_fact_query_does_not_get_a_candidate_evidence_task():
    inp=cve_input();out,_=run(inp,context_for(input=inp),valid_plan())
    assert out.status=='VALIDATED' and len(effective(out)['tasks'])==1


@pytest.mark.parametrize('mutation',['criteria_missing','wrong_url','missing_dependency','reserved_dependency','no_lookup','bad_budget'])
def test_completion_cannot_hide_other_schema_scope_dependency_or_budget_errors(mutation):
    inp,ctx,p=scoped()
    if mutation=='criteria_missing':p['tasks'][0].pop('acceptance_criteria')
    if mutation=='wrong_url':p['tasks'][0]['input_data']['steps'][0]['arguments']['candidate_reference']=URL.replace('1'*40,'2'*40)
    if mutation=='missing_dependency':p['tasks'][0]['dependencies']=['missing']
    if mutation=='reserved_dependency':p['tasks'][0]['dependencies']=['required-evidence']
    if mutation=='no_lookup':p['tasks'][0]=task('evidence_search','claims','get_claims',{'target':inp.query.target});p['tasks'][0]['acceptance_criteria'].append('evidence_present')
    if mutation=='bad_budget':inp,ctx,p=scoped(policy=RuntimePolicy(max_tool_calls=1))
    out,calls=run(inp,ctx,p,p)
    assert out.status=='PLANNING_FAILED' and out.validated_plan is None and len(calls)==2


def test_two_invalid_attempts_still_stop_without_trusted_output():
    inp,ctx,p=scoped();p['tasks'][0].pop('acceptance_criteria')
    out,calls=run(inp,ctx,p,p,p)
    assert out.status=='PLANNING_FAILED' and len(calls)==2


@pytest.mark.parametrize('url',['http://127.0.0.1/secret','https://169.254.169.254/latest/meta-data','file:///c:/secret'])
def test_candidate_input_never_bypasses_existing_url_security(url):
    with pytest.raises(ValueError):PlannerInput(query=cve_input().query,candidate_reference=url)


def test_asset_version_and_candidate_requirements_remain_separate_and_request_bound():
    base=cve_input(asset_id=uuid4())
    inp=PlannerInput(query=base.query,component={'name':'synthetic-lib','version':'1.0.0'},candidate_reference=URL)
    inp,ctx,p=scoped(inp);out,_=run(inp,ctx,p)
    assert out.status=='VALIDATED'
    nodes=effective(out)['tasks'];assert len(nodes)==4
    assert {s['name'] for t in nodes for s in t['input_data']['steps']}=={'get_vulnerability','get_asset','inspect_component_version','get_evidence'}
    assert next(t for t in nodes if t['type']=='asset_lookup')['input_data']['steps'][0]['arguments']=={'asset_id':str(base.query.asset_id)}
    assert next(t for t in nodes if t['type']=='evidence_search')['input_data']['steps'][0]['arguments']['candidate_reference']==URL

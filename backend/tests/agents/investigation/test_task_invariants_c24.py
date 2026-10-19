"""Contract-bound plan completion; synthetic inputs are never security facts."""
from copy import deepcopy
import json
from uuid import uuid4
import pytest
from app.agents.investigation.planner import InvestigationPlannerAdapter
from app.planner.schemas import PlannerInput
from app.runtime.contracts import RuntimePolicy
from tests.planner.fixtures import cve_input,context_for,valid_plan,task,gateway_with_responses,CVE


def case(*, version=None, asset=True):
    inp=cve_input(**({'asset_id':uuid4()} if asset else {}))
    if version is not None:inp=PlannerInput(query=inp.query,component={'name':'synthetic-lib','version':version})
    return inp,context_for(input=inp),valid_plan()


def run(inp,ctx,*plans):
    gateway,calls,sink=gateway_with_responses(plans)
    try:out=InvestigationPlannerAdapter(gateway,sink).plan(inp,ctx)
    finally:gateway.close()
    return out,calls,sink


def effective(out):return json.loads(out.validated_plan.candidate_json)
def steps(plan):return [s for t in plan['tasks'] for s in t['input_data'].get('steps',[])]
def receipt(out):return out.attempts[-1].diagnostic['task_integrity']


def test_missing_asset_is_completed_from_original_contract_and_fully_revalidated():
    inp,ctx,p=case();original=deepcopy(p)
    out,calls,sink=run(inp,ctx,p)
    assert out.status=='VALIDATED' and len(calls)==1
    from app.agents.investigation.planning import InvestigationPlan
    assert p==original
    assert effective(out)['tasks'][0]==InvestigationPlan.model_validate(p).model_dump(mode='json',by_alias=True)['tasks'][0]
    added=effective(out)['tasks'][1]
    assert added['type']=='asset_lookup' and added['dependencies']==[]
    assert added['input_data']['steps']==[{'name':'get_asset','arguments':{'asset_id':str(inp.query.asset_id)}}]
    assert receipt(out)['status']=='REPAIRED' and receipt(out)['original_candidate_status']=='REJECTED'
    assert sink.attempts==list(out.attempts)
    assert any(i.code=='ASSET_LOOKUP_REQUIRED' for i in out.attempts[0].issues)


def test_second_attempt_may_not_delete_an_independent_request_requirement():
    inp,ctx,p=case();bad=deepcopy(p);bad['tasks'][0].pop('acceptance_criteria')
    out,calls,_=run(inp,ctx,bad,p)
    assert out.status=='VALIDATED' and len(calls)==2 and len(out.attempts)==2
    assert out.attempts[0].validation_status=='REJECTED'
    assert receipt(out)['status']=='REPAIRED'
    assert any(s['name']=='get_asset' for s in steps(effective(out)))


def test_already_complete_plan_preserves_model_task_graph():
    inp,ctx,p=case();p['tasks'].append(task('asset_lookup','asset','get_asset',{'asset_id':str(inp.query.asset_id)}))
    out,calls,_=run(inp,ctx,p)
    assert out.status=='VALIDATED' and len(calls)==1
    assert effective(out)['tasks'][0]['task_id']=='lookup' and len(effective(out)['tasks'])==2
    assert 'task_integrity' not in out.attempts[0].diagnostic


def test_simple_query_never_gets_unrelated_asset_tasks():
    inp,ctx,p=case(asset=False);out,calls,_=run(inp,ctx,p)
    assert out.status=='VALIDATED' and len(effective(out)['tasks'])==1


def test_missing_asset_identity_is_never_manufactured():
    inp,ctx,p=case(asset=False,version='1.0.0');out,_,_=run(inp,ctx,p)
    assert out.status=='VALIDATED'
    assert not any(s['name']=='get_asset' for s in steps(effective(out)))


def test_version_observation_uses_only_supplied_version_and_existing_lookup_dependency():
    inp,ctx,p=case(version='1.0.0');out,_,_=run(inp,ctx,p)
    assert out.status=='VALIDATED'
    version=next(t for t in effective(out)['tasks'] if t['input_data']['steps'][0]['name']=='inspect_component_version')
    assert version['dependencies']==['lookup']
    assert version['input_data']['steps'][0]['arguments']=={'target':CVE,'name':'synthetic-lib','version':'1.0.0'}


def test_missing_version_is_not_guessed_or_filled_as_success():
    inp,ctx,p=case();inp=PlannerInput(query=inp.query,component={'name':'synthetic-lib'});ctx=context_for(input=inp)
    out,calls,_=run(inp,ctx,p,p)
    assert out.status=='PLANNING_FAILED' and len(calls)==2
    assert not any(s['name']=='inspect_component_version' for s in steps(p))
    assert any(i.code=='VERSION_INPUT_REQUIRED' for i in out.issues)


@pytest.mark.parametrize('mutation', ['missing_criteria','unknown_dependency','completion_id_dependency','cycle','wrong_asset','unknown_tool','missing_target'])
def test_completion_does_not_mask_other_contract_or_graph_errors(mutation):
    inp,ctx,p=case()
    if mutation=='missing_criteria':p['tasks'][0].pop('acceptance_criteria')
    if mutation=='unknown_dependency':p['tasks'][0]['dependencies']=['no-producer']
    if mutation=='completion_id_dependency':p['tasks'][0]['dependencies']=['required-asset']
    if mutation=='cycle':p['tasks'][0]['dependencies']=['lookup']
    if mutation=='wrong_asset':p['tasks'].append(task('asset_lookup','wrong','get_asset',{'asset_id':str(uuid4())}))
    if mutation=='unknown_tool':p['tasks'][0]['input_data']['steps'][0]['name']='not-a-tool'
    if mutation=='missing_target':p['tasks'][0]=task('evidence_search','evidence','get_claims',{'target':CVE});p['tasks'][0]['acceptance_criteria'].append('evidence_present')
    out,calls,_=run(inp,ctx,p,p)
    assert out.status=='PLANNING_FAILED' and out.validated_plan is None and len(calls)==2


@pytest.mark.parametrize('policy',[RuntimePolicy(max_tasks=1),RuntimePolicy(max_tool_calls=1),RuntimePolicy(permissions=frozenset())])
def test_completion_never_increases_permissions_or_budgets(policy):
    inp,_,p=case();ctx=context_for(input=inp,policy=policy)
    out,calls,_=run(inp,ctx,p,p)
    assert out.status=='PLANNING_FAILED' and len(calls)==2


def test_model_task_id_collision_is_not_reused_as_a_fake_producer():
    inp,ctx,p=case();p['tasks'][0]['task_id']='required-asset'
    out,_,_=run(inp,ctx,p)
    assert out.status=='VALIDATED'
    assert len({t['task_id'] for t in effective(out)['tasks']})==2


def test_version_producer_dependency_must_fit_the_unchanged_depth_budget():
    inp,_,p=case(version='1.0.0');ctx=context_for(input=inp,policy=RuntimePolicy(max_depth=1))
    out,calls,_=run(inp,ctx,p,p)
    assert out.status=='PLANNING_FAILED' and len(calls)==2
    assert receipt(out)['status']=='REJECTED'


def test_requirements_are_immutable_before_any_candidate_is_generated():
    from dataclasses import FrozenInstanceError
    from app.agents.investigation.task_invariants import task_requirements
    inp,ctx,_=case(version='1.0.0');required=task_requirements(ctx)
    assert isinstance(required,tuple) and len(required)==2
    with pytest.raises(FrozenInstanceError):required[0].arguments_json='{}'
    exported=required[0].as_dict();exported['arguments']['asset_id']=str(uuid4())
    assert required[0].as_dict()['arguments']['asset_id']==str(inp.query.asset_id)


def test_requirements_do_not_leak_between_two_assets_or_investigations():
    a,ca,pa=case(version='1.0.0');b,cb,pb=case(version='2.0.0')
    gateway,calls,sink=gateway_with_responses([pa,pb]);adapter=InvestigationPlannerAdapter(gateway,sink)
    try:ra=adapter.plan(a,ca);rb=adapter.plan(b,cb)
    finally:gateway.close()
    for result,inp,other in [(ra,a,b),(rb,b,a)]:
        assert result.status=='VALIDATED'
        wire=json.dumps(effective(result))
        assert str(inp.query.asset_id) in wire and str(other.query.asset_id) not in wire
        assert receipt(result)['planner_run_id'] in (str(ca.planner_run_id),str(cb.planner_run_id))
    assert calls[0].trace_id!=calls[1].trace_id


def test_two_invalid_candidates_exhaust_budget_without_any_trusted_plan():
    inp,ctx,p=case();p['tasks'][0].pop('acceptance_criteria')
    out,calls,_=run(inp,ctx,p,p,p)
    assert len(calls)==2 and out.status=='PLANNING_FAILED' and out.validated_plan is None


def test_historical_c23_retry_candidate_no_longer_depends_on_a_third_model_attempt():
    from pathlib import Path
    row=json.loads((Path(__file__).with_name('fixtures')/'c23_missing_asset_plan.json').read_text(encoding='utf8'))
    inp=PlannerInput.model_validate(row['input']);ctx=context_for(input=inp)
    plans=row['plans']
    out,calls,_=run(inp,ctx,*plans)
    assert out.status=='VALIDATED' and len(calls)==2
    assert receipt(out)['status']=='REPAIRED'
    assert [s['name'] for s in steps(effective(out))].count('get_asset')==1
    assert [s['name'] for s in steps(effective(out))].count('inspect_component_version')==1

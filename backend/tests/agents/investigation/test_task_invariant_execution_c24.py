"""Deterministic completion reaches real PostgreSQL/tools, never fake tool success."""
import json
from app.agents.investigation.service import IntelligenceInvestigationService
from app.planner.schemas import PlannerInput
from tests.planner.fixtures import cve_input,valid_plan,gateway_with_responses


def test_completed_asset_and_version_nodes_are_persisted_executed_and_bound(engine,investigation_seed):
    seed=investigation_seed
    query=cve_input(target=seed.cve,asset_id=seed.asset_id).query
    inp=PlannerInput(query=query,component=seed.component)
    candidate=valid_plan();candidate['tasks'][0]['input_data']['steps'][0]['arguments']['target']=seed.cve
    gateway,calls,_=gateway_with_responses([candidate]);service=IntelligenceInvestigationService(engine,gateway)
    try:snapshot=service.plan_and_run(inp,seed.actor)
    finally:gateway.close()
    assert snapshot.planning_status=='VALIDATED' and snapshot.runtime_status=='COMPLETED' and len(calls)==1
    audit=service.read_planner_trace(snapshot.planner_run_id,seed.actor)
    repaired=audit.attempts[0].diagnostic['task_integrity']
    assert repaired['status']=='REPAIRED' and len(repaired['added_tasks'])==2
    effective=json.loads(audit.validated_plan.candidate_json)
    assert len(effective['tasks'])==3 and len(candidate['tasks'])==1
    observed=service.read_results(snapshot.runtime_run_id,seed.actor)
    assert len(observed.artifacts)==3
    asset=next(a for a in observed.artifacts if a.task_id=='required-asset')
    version=next(a for a in observed.artifacts if a.task_id=='required-version')
    lookup=next(a for a in observed.artifacts if a.task_id=='lookup')
    assert asset.asset['id']==str(seed.asset_id)
    assert version.version_match and version.component['version']==seed.component['version']
    assert version.dependency_artifact_ids==(str(lookup.artifact_id),)
    assert all(a.run_id==snapshot.runtime_run_id for a in observed.artifacts)
    for trace in observed.traces:
        assert trace.artifact_id and trace.tools_called
        assert all(t['record_id'] for t in trace.tools_called)
    assert all(a.information_status=='CANDIDATE' for a in observed.artifacts)


def test_failed_revalidation_never_starts_runtime_or_publishes_a_risk(engine,investigation_seed):
    seed=investigation_seed;inp=PlannerInput(query=cve_input(target=seed.cve,asset_id=seed.asset_id).query)
    candidate=valid_plan();candidate['tasks'][0]['input_data']['steps'][0]['arguments']['target']=seed.cve
    candidate['tasks'][0]['acceptance_criteria']=[]
    gateway,calls,_=gateway_with_responses([candidate,candidate]);service=IntelligenceInvestigationService(engine,gateway)
    try:snapshot=service.plan_and_run(inp,seed.actor)
    finally:gateway.close()
    assert snapshot.planning_status=='PLANNING_FAILED' and snapshot.runtime_run_id is None and len(calls)==2
    trace=service.read_planner_trace(snapshot.planner_run_id,seed.actor)
    assert trace.validated_plan is None and trace.generated_plan is None
    assert all(a.validation_status=='REJECTED' and a.diagnostic['task_integrity']['status']=='REJECTED' for a in trace.attempts)

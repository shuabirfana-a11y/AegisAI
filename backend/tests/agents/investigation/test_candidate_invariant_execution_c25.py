"""Replay the omitted task through real storage/tools; only generation is stubbed."""
import json
from sqlalchemy import select
from app.agents.investigation.service import IntelligenceInvestigationService
from app.db import models as m
from app.db.session import transaction
from app.planner.schemas import PlannerInput
from tests.investigation_api.test_c5_boundaries import URL, seed_reference
from tests.orchestration.fixtures import scenario
from tests.planner.fixtures import cve_input, valid_plan, gateway_with_responses


def test_candidate_completion_executes_and_persists_only_scoped_candidate_evidence(engine):
    seed, _, old_gateway, _, _ = scenario(engine)
    old_gateway.close()
    evidence_id, raw_id = seed_reference(engine, seed, URL)
    inp = PlannerInput(query=cve_input(target=seed.cve).query, candidate_reference=URL)
    original = valid_plan()
    original['tasks'][0]['input_data']['steps'][0]['arguments'] = {
        'target': seed.cve, 'candidate_reference': URL}
    gateway, calls, _ = gateway_with_responses([original])
    service = IntelligenceInvestigationService(engine, gateway)
    try:
        snapshot = service.plan_and_run(inp, seed.actor)
    finally:
        gateway.close()
    assert snapshot.planning_status == 'VALIDATED' and snapshot.runtime_status == 'COMPLETED'
    assert len(calls) == 1 and len(original['tasks']) == 1
    audit = service.read_planner_trace(snapshot.planner_run_id, seed.actor)
    completion = audit.attempts[0].diagnostic['task_integrity']
    assert completion['original_candidate_status'] == 'REJECTED'
    assert completion['status'] == 'REPAIRED'
    result = service.read_results(snapshot.runtime_run_id, seed.actor)
    evidence = next(a for a in result.artifacts if a.task_id == 'required-evidence')
    lookup = next(a for a in result.artifacts if a.task_id == 'lookup')
    assert evidence.dependency_artifact_ids == (str(lookup.artifact_id),)
    assert evidence.run_id == snapshot.runtime_run_id
    candidate = next(p for p in evidence.patch_information if p.get('reference') == URL)
    assert candidate['status'] == 'CANDIDATE' and candidate['patch_applied'] is None
    assert candidate['applicability'] == 'UNKNOWN' and evidence_id in candidate['evidence_ids']
    assert candidate['reference_evidence'][0]['raw_document_id'] == raw_id
    with transaction(engine) as db:
        records = list(db.scalars(select(m.ToolCallRecord).where(
            m.ToolCallRecord.agent_run_id == snapshot.runtime_run_id,
            m.ToolCallRecord.tool_name == 'get_evidence')))
        assert len(records) == 1
        args = records[0].input_summary.get('arguments', records[0].input_summary)
        assert args['target'] == seed.cve and args['candidate_reference'] == URL
    assert json.loads(audit.attempts[0].diagnostic['raw_output']) == original

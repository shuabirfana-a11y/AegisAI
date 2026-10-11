from uuid import uuid4
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from app.integration.service import IntegrationService
from tests.orchestration.fixtures import scenario


def test_one_request_drives_three_actual_agent_runs_to_gate(engine):
    from app.orchestration.service import InvestigationOrchestrator
    seed,request,gw,calls,_=scenario(engine)
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        ids=(result.context.investigation_run_id,result.context.verification_run_id,result.context.analysis_run_id)
        assert all(ids) and len(set(ids))==3
        gate=IntegrationService(engine).read(result.context.integration_result_id,actor=seed.actor)
        assert gate.status=='PASS',gate.blocking_issues
        assert gate.source_run_ids==ids and len(calls)==1
        assert result.context.logical_investigation_id!=gate.logical_investigation_id
        assert result.context.gate_logical_investigation_id==gate.logical_investigation_id
        with transaction(engine) as db:
            for id in ids:
                row=db.get(m.AgentRun,id)
                assert row.actor_principal==seed.actor and row.agent_type=='runtime-v1'
                assert db.scalar(select(func.count()).select_from(m.ToolCallRecord).where(m.ToolCallRecord.agent_run_id==id))>0
    finally:gw.close()

"""Reproduce accepted-artifact expansion across the actual original Store."""
import pytest
from tests.agents.test_service_trace import service_for
from tests.agents.test_executor import delegate_registry
from tests.agents.fixtures import outcome
from tests.planner.test_end_to_end import seeded_plan,seeded_input


@pytest.mark.parametrize('calls',[1,2,8])
@pytest.mark.parametrize('padding',['warnings','evidence'])
def test_near_limit_outcome_remains_readable_after_canonical_storage(engine,runtime_seed,calls,padding):
    from app.agents.artifacts import AgentArtifact
    from app.agents.router import AgentRouter
    from app.agents.registry import create_default_registry
    from app.agents.trace import ProfessionalTraceStore
    from app.runtime.contracts import ARTIFACT_LIMIT
    from app.runtime.store import PostgresRuntimeStore
    from app.runtime.executor import evidence_reference
    p=seeded_plan(runtime_seed)
    step=p['tasks'][0]['input_data']['steps'][0]
    p['tasks'][0]['input_data']['steps']=[dict(step) for _ in range(calls)]
    p['tasks'][0]['max_tool_calls']=calls
    captured=[]
    def action(request):
        binding=AgentRouter(create_default_registry().freeze()).route(request.task,'vulnerability_lookup')
        if padding=='warnings':
            got=outcome(request.task,request.context)
            initial=AgentArtifact.from_task_artifact(got.artifact,binding)
            room=ARTIFACT_LIMIT-len(initial.model_dump_json().encode('utf-8'))-3
            got.artifact.warnings.append('x'*room)
        else:
            response={'status':'success','data':{'SYNTHETIC':True},
                'evidence_refs':[{'source_url':'https://example.invalid/SYNTHETIC','locator':{'excerpt':''},'verified':False}]}
            initial=outcome(request.task,request.context,response=response)
            size=len(AgentArtifact.from_task_artifact(initial.artifact,binding).model_dump_json().encode('utf-8'))
            response['evidence_refs'][0]['locator']['excerpt']='x'*(ARTIFACT_LIMIT-size-3)
            got=outcome(request.task,request.context,response=response)
        assert got.artifact.status=='SUCCESS'
        assert len(AgentArtifact.from_task_artifact(got.artifact,binding).model_dump_json().encode('utf-8'))<=ARTIFACT_LIMIT
        captured.append(got)
        return got
    svc,gw,_=service_for(engine,[p],delegate_registry(action=action))
    try:
        saved=svc.plan_and_run(seeded_input(runtime_seed),runtime_seed.actor)
        trace=ProfessionalTraceStore(engine).read(saved.runtime_run_id,runtime_seed.actor)
        original=PostgresRuntimeStore(engine).read_trace(saved.runtime_run_id,runtime_seed.actor)
        artifact=trace.artifacts[0]
        assert trace.agents[0].status=='FAILED'
        assert any(e['code']=='ARTIFACT_SIZE_LIMIT' for e in artifact.errors)
        assert len(artifact.tool_calls)==calls
        assert all(c['record_id'] for c in artifact.tool_calls)
        assert original.artifacts[0].status=='FAILED'
        if padding=='evidence':
            assert artifact.evidence==[]
            assert artifact.result==evidence_reference(captured[0].receipts)
            from sqlalchemy import select
            from app.db import models as m
            from app.db.session import transaction
            with transaction(engine) as db:
                records=list(db.scalars(select(m.ToolCallRecord).where(m.ToolCallRecord.agent_run_id==saved.runtime_run_id)))
                assert len(records)==calls
                assert all(len(r.output_summary['evidence_refs'][0]['locator']['excerpt'])>500000 for r in records)
    finally:gw.close()

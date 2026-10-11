"""Breaks caught: fabricated opt-in plans and duplicate execution side effects."""
import pytest
from app.db import models as m
from app.db.session import transaction
from sqlalchemy import select,func
from app.runtime.contracts import TaskPlan
from tests.agents.analysis.helpers import module,request
from tests.agents.analysis.test_agent import task


def test_runtime_runs_fixed_plan_and_preserves_input_artifacts(engine,analysis_source):
    src=analysis_source;svc=module('service').SecurityAnalysisService(engine);req=request(src)
    original=src.verification.model_dump_json()
    saved=svc.run(req,actor=src.seed.actor)
    assert saved.status=='WAITING_REVIEW'  # Original Runtime UI status, not tool partiality.
    with transaction(engine) as db:
        records=list(db.scalars(select(m.ToolCallRecord).where(m.ToolCallRecord.agent_run_id==saved.run_id)))
        assert len(records)==1 and records[0].tool_name=='analyze_risk_snapshot'
        assert records[0].output_summary['data']['assessment']['version_match_status']=='AFFECTED'
    assert src.verifier.read_results(src.verification.run_id,actor=src.seed.actor).artifacts[0].model_dump_json()==original


def test_runtime_rejects_forged_context_and_arbitrary_plan(engine,analysis_source):
    src=analysis_source;svc=module('service').SecurityAnalysisService(engine)
    ctx=svc.contexts.capture(request(src),actor=src.seed.actor)
    with pytest.raises(ValueError,match='AGENT_PLAN_INVALID'):
        svc.runtime.run_context(ctx.model_copy(update={'input_snapshot_hash':'f'*64}),actor=src.seed.actor)
    with pytest.raises(ValueError,match='AGENT_PLAN_INVALID'):svc.runtime.run_plan(TaskPlan(tasks=(task(),)),src.seed.actor,'forged')
    with pytest.raises(LookupError):svc.runtime.run_context(ctx,actor='foreign')


def test_idempotent_execution_does_not_repeat_tools(engine,analysis_source):
    src=analysis_source;svc=module('service').SecurityAnalysisService(engine);req=request(src)
    first=svc.run(req,actor=src.seed.actor)
    with transaction(engine) as db:count=db.scalar(select(func.count()).select_from(m.ToolCallRecord))
    assert svc.run(req,actor=src.seed.actor)==first
    with transaction(engine) as db:assert db.scalar(select(func.count()).select_from(m.ToolCallRecord))==count

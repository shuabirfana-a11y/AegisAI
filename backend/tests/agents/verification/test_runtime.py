"""Breaks caught: context forgery, rerun side effects and changed original gates."""
import copy
import importlib
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import fingerprint
import pytest
from tests.agents.verification.test_snapshot import request


def service(engine):
    try:return importlib.import_module('app.agents.verification.service').EvidenceVerificationService(engine)
    except ModuleNotFoundError:pytest.fail('Owned verification runtime service is missing')


def test_investigation_to_verification_uses_original_runtime_and_formal_receipts(engine,investigation_source):
    src=investigation_source;svc=service(engine)
    before=src.artifact.model_dump(mode='json')
    saved=svc.run(request(src),actor=src.seed.actor)
    got=svc.read_results(saved.run_id,actor=src.seed.actor)
    assert saved.run_id!=src.artifact.run_id and saved.status=='COMPLETED'
    artifact=got.artifacts[0]
    assert artifact.agent_id=='verification_agent' and artifact.verification_status=='CONFIRMED'
    assert artifact.source_artifact_id==src.artifact.artifact_id and artifact.source_run_id==src.artifact.run_id
    assert artifact.execution_status=='SUCCESS' and artifact.tool_calls[0]['record_id']
    trace=got.traces[0]
    assert trace.claims_checked==(str(src.seed.claim_id),)
    assert trace.evidence_used==(str(src.seed.evidence_id),)
    assert trace.verification_result=='CONFIRMED' and trace.execution_time>=0
    assert before==src.service.read_results(src.artifact.run_id,src.seed.actor).artifacts[0].model_dump(mode='json')


def test_repeat_request_does_not_repeat_tool_calls(engine,investigation_source):
    svc=service(engine);src=investigation_source;req=request(src)
    first=svc.run(req,actor=src.seed.actor)
    with transaction(engine) as db:before=db.scalar(select(func.count()).select_from(m.ToolCallRecord))
    second=svc.run(req,actor=src.seed.actor)
    with transaction(engine) as db:after=db.scalar(select(func.count()).select_from(m.ToolCallRecord))
    assert first==second and before==after
    assert svc.read_results(first.run_id,actor=src.seed.actor)==svc.read_results(second.run_id,actor=src.seed.actor)


def test_runtime_rejects_forged_context_and_foreign_owner(engine,investigation_source):
    from app.agents.verification.context_store import VerificationContextStore
    svc=service(engine);src=investigation_source
    ctx=VerificationContextStore(engine).capture(request(src),actor=src.seed.actor)
    with pytest.raises(ValueError,match='AGENT_PLAN_INVALID'):
        svc.runtime.run_context(ctx.model_copy(update={'source_snapshot_hash':'f'*64}),actor=src.seed.actor)
    with pytest.raises(LookupError):svc.runtime.run_context(ctx,actor='foreign-owner')


def test_verification_profile_does_not_enable_arbitrary_runtime_plans(engine,investigation_source):
    from app.runtime.contracts import TaskPlan
    from tests.agents.verification.test_agent import task
    svc=service(engine)
    with pytest.raises(ValueError,match='AGENT_PLAN_INVALID'):
        svc.runtime.run_plan(TaskPlan(tasks=[task()]),investigation_source.seed.actor,'forged')

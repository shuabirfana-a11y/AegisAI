"""Breaks caught: rebinding a key, foreign context access and mutable evaluation time."""
import importlib
import pytest
import copy
from datetime import timedelta
from app.db import models as m
from app.db.session import transaction
from app.assistant.storage import IdempotencyConflict
from tests.agents.verification.test_snapshot import request


def store(engine):
    try:return importlib.import_module('app.agents.verification.context_store').VerificationContextStore(engine)
    except ModuleNotFoundError:pytest.fail('Sealed verification context store is missing')


def test_repeat_key_returns_same_sealed_context(engine,investigation_source):
    instance=store(engine);src=investigation_source;req=request(src)
    first=instance.capture(req,actor=src.seed.actor)
    second=instance.capture(req,actor=src.seed.actor)
    assert first.context_id==second.context_id
    assert first.evaluation_time==second.evaluation_time
    assert first.source_snapshot_hash==second.source_snapshot_hash
    assert first==instance.read(first.context_id,actor=src.seed.actor)


def test_same_key_different_content_and_foreign_owner_are_rejected(engine,investigation_source):
    instance=store(engine);src=investigation_source;req=request(src)
    first=instance.capture(req,actor=src.seed.actor)
    with pytest.raises(IdempotencyConflict):
        instance.capture(req.model_copy(update={'task_type':'conflict_detection'}),actor=src.seed.actor)
    with pytest.raises(LookupError):instance.read(first.context_id,actor='different-owner')


def test_evaluation_time_cannot_drift_from_sealed_snapshot(engine,investigation_source):
    src=investigation_source;instance=store(engine)
    ctx=instance.capture(request(src),actor=src.seed.actor)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,ctx.context_id);original=copy.deepcopy(row.details);changed=copy.deepcopy(original)
        changed['verification_v1']['context']['evaluation_time']=(ctx.evaluation_time+timedelta(days=60)).isoformat()
        row.details=changed
    try:
        with pytest.raises(ValueError):instance.read(ctx.context_id,actor=src.seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,ctx.context_id).details=original

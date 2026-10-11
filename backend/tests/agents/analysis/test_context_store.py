"""Breaks caught: idempotent calls silently consuming changed live inputs."""
import pytest
from app.db import models as m
from app.db.session import transaction
from app.assistant.storage import IdempotencyConflict
from tests.agents.analysis.helpers import module,request


def test_idempotent_snapshot_does_not_refresh_inventory_or_time(engine,analysis_source):
    src=analysis_source;store=module('context_store').AnalysisContextStore(engine);req=request(src)
    original=store.capture(req,actor=src.seed.actor)
    with transaction(engine) as db:
        c=db.get(m.AssetComponent,src.component_id);version=c.version;revision=c.inventory_revision
        c.version='0.7.0';c.inventory_revision+=1
    try:
        same=store.capture(req,actor=src.seed.actor)
        assert same==original and same.inputs.asset.deployed_version=='0.6.0'
        fresh=store.capture(request(src),actor=src.seed.actor)
        assert fresh.inputs.asset.deployed_version=='0.7.0'
        assert fresh.context_id!=original.context_id
    finally:
        with transaction(engine) as db:
            c=db.get(m.AssetComponent,src.component_id);c.version=version;c.inventory_revision=revision


def test_changed_request_same_key_rejected(engine,analysis_source):
    src=analysis_source;store=module('context_store').AnalysisContextStore(engine);req=request(src)
    store.capture(req,actor=src.seed.actor)
    with pytest.raises(IdempotencyConflict):store.capture(req.model_copy(update={'model_assistance':True}),actor=src.seed.actor)


def test_foreign_context_read_is_denied(engine,analysis_source):
    src=analysis_source;store=module('context_store').AnalysisContextStore(engine)
    saved=store.capture(request(src),actor=src.seed.actor)
    with pytest.raises(LookupError):store.read(saved.context_id,actor='foreign')

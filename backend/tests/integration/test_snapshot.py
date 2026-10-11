from copy import deepcopy
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from tests.integration.helpers import request

def test_real_cross_run_receipts_and_original_objective(engine,gate_chain):
    from app.integration.snapshot import IntegrationSnapshotReader
    c=gate_chain;ctx=IntegrationSnapshotReader(engine).capture(request(c),actor=c.seed.actor)
    assert len(set(ctx.source_run_ids))==3
    assert ctx.objective.asset_id==c.asset_id and ctx.objective.version=='0.6.0'
    assert ctx.verification_source.source_task_id==c.investigation.task_id
    assert ctx.analysis.input_artifact_ids==(c.investigation.artifact_id,c.verification.artifact_id)
    assert ctx.source_fingerprints and ctx.trace_references
    assert {str(c.investigation.run_id),str(c.verification.run_id),str(c.analysis.run_id)}<=set(ctx.source_fingerprints)
    assert c.analysis.risk_level=='HIGH' and c.analysis.execution_status=='SUCCESS'

@pytest.mark.parametrize('change',['foreign_owner','task','artifact','anchor','planner','schema'])
def test_unowned_or_wrong_associations_rejected(engine,gate_chain,change):
    from app.integration.snapshot import IntegrationSnapshotReader
    c=gate_chain;r=request(c);actor=c.seed.actor
    if change=='foreign_owner':actor='somebody-else'
    elif change in ('task','artifact'):
        r=r.model_copy(update={'verification':r.verification.model_copy(update={('task_id' if change=='task' else 'artifact_id'):('bad' if change=='task' else uuid4())})})
    elif change=='anchor':r=r.model_copy(update={'run_id':uuid4()})
    elif change=='planner':r=r.model_copy(update={'planner_run_id':uuid4()})
    else:r=r.model_copy(update={'analysis':r.analysis.model_copy(update={'schema_version':'old'})})
    with pytest.raises((ValueError,LookupError)):IntegrationSnapshotReader(engine).capture(r,actor=actor)

def test_missing_historical_original_request_is_not_invented(engine,gate_chain):
    from app.integration.snapshot import IntegrationSnapshotReader
    c=gate_chain
    with transaction(engine) as db:
        row=db.get(m.AgentRun,c.planner.planner_run_id);old=deepcopy(row.context);row.context={'planner_version':'planner-v1'}
    try:
        ctx=IntegrationSnapshotReader(engine).capture(request(c),actor=c.seed.actor)
        assert ctx.objective is None and any(ch.code=='OBJECTIVE_CONTEXT_MISSING' for ch in ctx.capture_checks)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,c.planner.planner_run_id).context=old

def test_reader_detects_formal_receipt_damage(engine,gate_chain):
    from app.integration.snapshot import IntegrationSnapshotReader
    c=gate_chain
    with transaction(engine) as db:
        row=db.get(m.AgentRun,c.investigation.run_id);old=deepcopy(row.details);data=deepcopy(old)
        data['runtime_v1']['artifacts']['lookup']['tool_calls'][0]['sequence_no']+=10;row.details=data
    try:
        with pytest.raises(ValueError):IntegrationSnapshotReader(engine).capture(request(c),actor=c.seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,c.investigation.run_id).details=old

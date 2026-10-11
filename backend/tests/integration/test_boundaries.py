from copy import deepcopy
from datetime import timedelta
from itertools import product,permutations
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import fingerprint
from tests.integration.helpers import request

def test_original_asset_objective_cannot_be_downgraded_to_overview(engine,gate_chain):
    from app.integration.snapshot import IntegrationSnapshotReader
    c=gate_chain
    ctx=IntegrationSnapshotReader(engine).capture(request(c,objective_profile='overview_v1'),actor=c.seed.actor)
    assert 'version_impact' in ctx.objective.required_outcomes

def test_as_of_validity_changes_make_new_revision_without_destroying_history(engine,gate_chain,monkeypatch):
    from app.integration.service import IntegrationService
    import app.integration.snapshot as snapshot
    c=gate_chain;svc=IntegrationService(engine);r=request(c)
    first=svc.evaluate(r,actor=c.seed.actor);assert first.status=='PASS'
    monkeypatch.setattr(snapshot,'utcnow',lambda:first.evaluation_time+timedelta(days=8))
    second=svc.evaluate(r,actor=c.seed.actor)
    assert second.status=='REPLAN_REQUIRED' and second.integration_id!=first.integration_id
    assert svc.read(first.integration_id,actor=c.seed.actor)==first

def test_pre_fingerprint_source_change_is_detected(engine,gate_chain,monkeypatch):
    import app.integration.snapshot as snapshot
    c=gate_chain;original=snapshot.source_fingerprints;called=False
    with transaction(engine) as db:old=deepcopy(db.get(m.AgentRun,c.investigation.run_id).context)
    def changed(*args,**kwargs):
        nonlocal called
        if not called:
            called=True
            with transaction(engine) as db:db.get(m.AgentRun,c.investigation.run_id).context={'changed_during_capture':True}
        return original(*args,**kwargs)
    monkeypatch.setattr(snapshot,'source_fingerprints',changed)
    try:
        with pytest.raises(ValueError,match='SOURCE_CHANGED'):snapshot.IntegrationSnapshotReader(engine).capture(request(c),actor=c.seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,c.investigation.run_id).context=old

@pytest.mark.parametrize('data',[float('nan'),float('inf'),float('-inf')])
def test_corrupted_nested_nonfinite_input_is_failed(engine,gate_chain,data):
    from app.integration.snapshot import IntegrationSnapshotReader
    from app.integration.evaluator import IntegrationGateEvaluator
    c=gate_chain;ctx=IntegrationSnapshotReader(engine).capture(request(c),actor=c.seed.actor)
    inv=ctx.investigation.model_copy(update={'component':{'unexpected':data}})
    result=IntegrationGateEvaluator().evaluate(ctx.model_copy(update={'investigation':inv}))
    assert result.status=='FAILED' and not result.final_result_references

def test_policy_not_client_replaceable_and_historical_unknown_rejected(engine,gate_chain):
    from app.integration.contracts import IntegrationRequest
    from app.integration.service import IntegrationService
    with pytest.raises(ValidationError):IntegrationRequest(request_key='x',policy_version='weaker-policy')
    c=gate_chain;svc=IntegrationService(engine);got=svc.evaluate(request(c),actor=c.seed.actor)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,got.integration_id);old=deepcopy(row.details);data=deepcopy(old)
        data['integration_v1']['context']['policy_version']='unsupported-v2';row.details=data
    try:
        with pytest.raises(ValueError):svc.read(got.integration_id,actor=c.seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,got.integration_id).details=old

def test_exact_patch_request_without_fixed_release_does_not_pass(engine,gate_chain):
    from app.integration.snapshot import IntegrationSnapshotReader
    from app.integration.evaluator import IntegrationGateEvaluator
    c=gate_chain;ctx=IntegrationSnapshotReader(engine).capture(request(c),actor=c.seed.actor)
    obj=ctx.objective.model_copy(update={'required_outcomes':(*ctx.objective.required_outcomes,'precise_remediation')})
    r=ctx.analysis.model_copy(update={'recommended_actions':tuple(a for a in ctx.analysis.recommended_actions if not a.fixed_version and not a.patch_reference)})
    assert IntegrationGateEvaluator().evaluate(ctx.model_copy(update={'objective':obj,'analysis':r})).status=='REPLAN_REQUIRED'

def test_required_dependency_cannot_be_declared_optional(engine,gate_chain):
    from app.integration.contracts import OptionalTask
    from app.integration.snapshot import IntegrationSnapshotReader
    c=gate_chain
    r=request(c,optional_tasks=(OptionalTask(run_id=c.investigation.run_id,task_id='lookup'),))
    with pytest.raises(ValueError,match='ESSENTIAL_TASK'):IntegrationSnapshotReader(engine).capture(r,actor=c.seed.actor)

def test_original_time_window_and_freshness_threshold_edges(engine,gate_chain):
    from app.integration.snapshot import IntegrationSnapshotReader
    from app.integration.freshness import check_freshness
    c=gate_chain;ctx=IntegrationSnapshotReader(engine).capture(request(c),actor=c.seed.actor)
    e=ctx.verification.supporting_evidence[0]
    for age,stale in ((30,False),(30+1/86400,True)):
        item=e.model_copy(update={'retrieved_at':ctx.evaluation_time-timedelta(days=age),'published_at':None})
        v=ctx.verification.model_copy(update={'supporting_evidence':(item,)})
        assert ('REQUIRED_EVIDENCE_STALE' in {x.code for x in check_freshness(ctx.model_copy(update={'verification':v}))})==stale

def test_exhaustive_decision_order_and_adding_blockers_never_improves_verdict():
    from app.integration.rules_common import decision
    rank={'PASS':0,'PASS_WITH_WARNINGS':1,'REPLAN_REQUIRED':2,'HUMAN_REVIEW_REQUIRED':3,'FAILED':4}
    for values in product(('NONE','REPLAN','HUMAN','FATAL'),repeat=4):
        base=decision(values,warning=True)
        for order in set(permutations(values)):assert decision(order,warning=True)==base
        for added in ('REPLAN','HUMAN','FATAL'):assert rank[decision((*values,added),warning=True)]>=rank[base]

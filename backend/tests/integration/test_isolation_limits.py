from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.db import models as m
from app.db.session import transaction
from tests.integration.helpers import request

def test_other_investigation_same_actor_not_accepted(engine,gate_chain):
    from app.integration.service import IntegrationService
    from app.agents.investigation.service import IntelligenceInvestigationService
    from tests.agents.investigation.test_end_to_end import plan_for
    from tests.planner.fixtures import gateway_with_responses,task
    from app.integration.contracts import ArtifactRef
    c=gate_chain;plan=plan_for(c.seed,'version');plan['tasks'].append(task('asset_lookup','asset','get_asset',{'asset_id':str(c.asset_id)}))
    gw,_,_=gateway_with_responses([plan]);svc=IntelligenceInvestigationService(engine,gw)
    try:run=svc.plan_and_run(c.input.model_copy(update={'query':c.input.query.model_copy(update={'request_key':uuid4().hex})}),c.seed.actor)
    finally:gw.close()
    art=svc.read_results(run.runtime_run_id,c.seed.actor).artifacts[0]
    ref=ArtifactRef(run_id=art.run_id,task_id=art.task_id,artifact_id=art.artifact_id,schema_version=art.schema_version)
    got=IntegrationService(engine).evaluate(request(c,run_id=art.run_id,planner_run_id=run.planner_run_id,investigation=ref),actor=c.seed.actor)
    assert got.status=='FAILED' and not got.evidence_references

def test_concurrent_distinct_investigations_do_not_cross_read(engine,gate_chain):
    from tests.integration.conftest import build_chain
    from app.integration.service import IntegrationService
    c=gate_chain;other=build_chain(engine);svc=IntegrationService(engine)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(svc.evaluate,request(chain),actor=chain.seed.actor) for chain in (c,other)]
        first,second=[f.result() for f in fs]
    assert first.status==second.status=='PASS'
    assert first.logical_investigation_id!=second.logical_investigation_id
    assert first.source_run_ids!=second.source_run_ids
    assert first.evidence_references!=second.evidence_references
    assert svc.read(first.integration_id,actor=c.seed.actor)==first
    with pytest.raises(LookupError):svc.read(first.integration_id,actor=other.seed.actor)

def test_cancelled_source_run_even_with_success_tasks_never_passes(engine,gate_chain):
    from app.integration.service import IntegrationService
    c=gate_chain
    with transaction(engine) as db:
        row=db.get(m.AgentRun,c.investigation.run_id);old=row.status;row.status='cancelled'
    try:
        got=IntegrationService(engine).evaluate(request(c),actor=c.seed.actor)
        assert got.status=='FAILED' and 'EXECUTION_CANCELLED' in got.blocking_issues
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,c.investigation.run_id).status=old

def test_context_size_limit_rejects_without_silent_truncation(engine,gate_chain):
    from app.integration.snapshot import IntegrationSnapshotReader
    from app.integration.contracts import IntegrationContext
    c=gate_chain;ctx=IntegrationSnapshotReader(engine).capture(request(c),actor=c.seed.actor)
    data=ctx.model_dump(mode='python');data['trace_references']=('x'*(4*1024*1024),)
    with pytest.raises(ValidationError,match='size limit'):IntegrationContext.model_validate(data)

def test_unexpected_rule_failure_does_not_mutate_original_agent(engine,gate_chain,monkeypatch):
    from app.integration.service import IntegrationService
    c=gate_chain;svc=IntegrationService(engine)
    with transaction(engine) as db:original=deepcopy(db.get(m.AgentRun,c.analysis.run_id).details)
    old=svc.evaluator.evaluate;count=0
    def once(*args,**kwargs):
        nonlocal count
        count+=1
        if count==1:raise RuntimeError('not business evidence')
        return old(*args,**kwargs)
    monkeypatch.setattr(svc.evaluator,'evaluate',once)
    got=svc.evaluate(request(c),actor=c.seed.actor)
    assert got.status=='FAILED' and 'GATE_EXECUTION_FAILED' in got.blocking_issues
    with transaction(engine) as db:assert db.get(m.AgentRun,c.analysis.run_id).details==original

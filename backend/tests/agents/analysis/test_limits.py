"""Oversize and truncated scope never unlock a definite conclusion."""
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import fingerprint
from app.runtime.contracts import json_bytes
from tests.agents.analysis.helpers import module,context,verified,request
from tests.agents.analysis.test_rules import kev


def store(engine,ctx):
    with transaction(engine) as db:
        db.add(m.AgentRun(id=ctx.context_id,actor_principal=ctx.owner,agent_type='analysis-context-v1',
            user_request='SYNTHETIC bounded-context test only',status='succeeded',started_at=ctx.evaluation_time,
            details={'analysis_v1':{'request_key':ctx.request.request_key,'context':ctx.model_dump(mode='json')}}))


def test_large_output_returns_partial_and_retains_full_context(engine):
    ctx=context([verified(),kev()]);v=ctx.inputs.verification
    e=v.supporting_evidence[0].model_copy(update={'reference':{'padding':'x'*430000}})
    v=module('schemas').VerificationArtifact.model_validate({**v.model_dump(),
        'supporting_evidence':(e,*v.supporting_evidence[1:])})
    inputs=ctx.inputs.model_copy(update={'verification':v});ctx=ctx.model_copy(update={
        'inputs':inputs,'input_snapshot_hash':fingerprint(inputs.model_dump(mode='json'))})
    store(engine,ctx)
    svc=module('service').SecurityAnalysisService(engine)
    saved=svc.runtime.run_context(ctx,actor=ctx.owner)
    art=svc.read_results(saved.run_id,actor=ctx.owner).artifacts[0]
    assert art.partial_result and art.risk_level=='UNKNOWN' and art.affected is None
    assert art.priority=='REVIEW_REQUIRED' and art.verification_status=='CONFIRMED'
    assert art.input_snapshot_hash==ctx.input_snapshot_hash and len(json_bytes(art.model_dump(mode='json'),512*1024))<512*1024
    assert svc.contexts.read(ctx.context_id,actor=ctx.owner).inputs.verification.supporting_evidence[0].reference['padding']=='x'*430000


def test_inventory_over_limit_cannot_say_target_not_deployed(engine,analysis_source):
    src=analysis_source
    with transaction(engine) as db:
        package=db.get(m.PackageIdentifier,src.seed.package_id)
        asset=m.Asset(name='SYNTHETIC over-limit inventory',asset_type='service',owner_principal=src.seed.actor,is_demo=True)
        db.add(asset);db.flush();asset_id=asset.id
        for index in range(101):
            db.add(m.AssetComponent(asset_id=asset.id,product_id=package.product_id,package_identifier_id=package.id,
                raw_package_name=package.package_name,version='0.6.0',ecosystem='PyPI',purl=package.purl,identity_status='resolved'))
    svc=module('service').SecurityAnalysisService(engine)
    req=request(src,asset_id=asset_id,component_id=None);saved=svc.run(req,actor=src.seed.actor)
    art=svc.read_results(saved.run_id,actor=src.seed.actor).artifacts[0]
    assert art.asset_match_status=='UNKNOWN' and art.affected is None and art.priority=='REVIEW_REQUIRED'
    assert svc.contexts.capture(req,actor=src.seed.actor).inputs.asset.context_status=='LIMITED'


def test_context_size_cap_rejects_unbounded_input():
    ctx=context();value=ctx.model_dump(mode='json');value['inputs']['receipt_references']=[{'padding':'x'*(2*1024*1024)}]
    with pytest.raises(ValueError,match='size limit'):module('schemas').AnalysisContext.model_validate(value)


def test_omitted_evidence_count_abstains_even_if_other_facts_confirm():
    ctx=context([verified(),kev()]);inputs=ctx.inputs.model_copy(update={'omitted_evidence_count':1})
    got=module('rules').assess_risk(ctx.model_copy(update={'inputs':inputs}))
    assert got.affected is None and got.risk_level=='UNKNOWN' and got.priority=='REVIEW_REQUIRED'


def test_worker_failure_reader_preserves_unknown_and_formal_error(engine,analysis_source):
    from app.agents.artifacts import AgentExecutionRequest
    from app.runtime.executor import failure
    from app.runtime.contracts import ExecutionOutcome
    src=analysis_source;svc=module('service').SecurityAnalysisService(engine)
    class Supervisor:
        def cancel_all(self):pass
        def execute(self,task,ctx,*args,**kwargs):
            return ExecutionOutcome(artifact=failure(task,ctx,'WORKER_FAILED'))
    agent=module('agent').SecurityAnalysisAgent(supervisor_factory=Supervisor)
    svc.runtime.registry=module('registry').create_analysis_registry(agent).freeze()
    saved=svc.run(request(src),actor=src.seed.actor)
    art=svc.read_results(saved.run_id,actor=src.seed.actor).artifacts[0]
    assert art.execution_status=='FAILED' and art.affected is None and art.risk_level=='UNKNOWN'
    assert art.partial_result and art.verification_status=='CONFIRMED' and not art.tool_calls


def test_cancelled_prototype_does_not_poison_fresh_runtime(engine,analysis_source):
    src=analysis_source;svc=module('service').SecurityAnalysisService(engine)
    prototype=module('agent').SecurityAnalysisAgent();prototype.cancel_all()
    svc.runtime.registry=module('registry').create_analysis_registry(prototype).freeze()
    saved=svc.run(request(src),actor=src.seed.actor)
    art=svc.read_results(saved.run_id,actor=src.seed.actor).artifacts[0]
    assert art.affected is True and art.execution_status=='WAITING_REVIEW'

"""Breaks caught: silent coverage loss and full confirmation on truncated inputs."""
from types import SimpleNamespace
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import fingerprint
from app.agents.verification.context_store import VerificationContextStore
from app.agents.verification.rules import evaluate_snapshot
from tests.agents.verification.conftest import verification_seed
from tests.agents.verification.test_snapshot import request
from tests.agents.verification.test_end_to_end import source_for
from tests.agents.verification.helpers import context,claim,evidence
from app.agents.verification.context_store import CONTEXT_TYPE
from app.runtime.contracts import json_bytes


def test_input_limit_blocks_full_confirmation_even_when_kept_claim_confirms():
    ctx=context()
    snapshot=ctx.snapshot.model_copy(update={'omitted_claim_ids':('unprocessed',),'omitted_claim_count':1})
    got=evaluate_snapshot(ctx.model_copy(update={'snapshot':snapshot,'source_snapshot_hash':fingerprint(snapshot.model_dump(mode='json'))}))
    assert got.partial_result and got.verification_status!='CONFIRMED'
    assert got.confidence<=0.49 and any('PARTIAL_INPUT' in x for x in got.unresolved_items)


def test_database_claim_limit_preserves_omitted_coverage(engine):
    seed=verification_seed.__wrapped__(engine)
    with transaction(engine) as db:
        for i in range(32):
            db.add(m.Claim(claim_key='SYNTHETIC-overflow:'+str(seed.vulnerability_id)+':'+str(i),
                vulnerability_id=seed.vulnerability_id,claim_type='AFFECTS_VERSION',predicate='AFFECTS_VERSION',
                scope_key='SYNTHETIC:'+str(i),value_json={'raw_expression':'<=0.6'},details={'is_test':True}))
    src=source_for(engine,seed)
    captured=VerificationContextStore(engine).capture(request(src),actor=seed.actor)
    assert len(captured.snapshot.claims)==32 and captured.snapshot.omitted_claim_count==1
    assert len(captured.snapshot.omitted_claim_ids)==1
    assert evaluate_snapshot(captured).partial_result


def test_large_assessment_returns_bounded_partial_and_preserves_sealed_input(engine):
    from app.tooling.verification import execute_verification
    ctx=context()
    big=ctx.snapshot.claims[0].model_copy(update={'related_entities':{'padding':'x'*440000}})
    snap=ctx.snapshot.model_copy(update={'claims':(big,)})
    ctx=ctx.model_copy(update={'snapshot':snap,'source_snapshot_hash':fingerprint(snap.model_dump(mode='json'))})
    with transaction(engine) as db:
        db.add(m.AgentRun(id=ctx.context_id,actor_principal=ctx.owner,agent_type=CONTEXT_TYPE,
            user_request='SYNTHETIC size budget fixture only',status='succeeded',started_at=ctx.evaluation_time,
            details={'verification_v1':{'request_key':ctx.request.request_key,'context':ctx.model_dump(mode='json')}}))
    with transaction(engine) as db:
        out=execute_verification(db,'evaluate_evidence_snapshot',{'context_id':str(ctx.context_id)},ctx.owner)
    assert out['status']=='partial'
    assert out['data']['assessment']['verification_status']!='CONFIRMED'
    assert len(json_bytes(out,400*1024))<400*1024
    assert VerificationContextStore(engine).read(ctx.context_id,actor=ctx.owner).snapshot.claims[0].related_entities['padding']=='x'*440000
    from app.agents.verification.service import EvidenceVerificationService
    svc=EvidenceVerificationService(engine)
    saved=svc.runtime.run_context(ctx,actor=ctx.owner)
    projected=svc.read_results(saved.run_id,actor=ctx.owner)
    assert projected.artifacts[0].partial_result
    assert projected.traces[0].claims_checked==('C1',)


def test_many_source_conflicts_are_bounded_and_never_complete_confirmation():
    claims=[];items=[]
    for index in range(16):
        claims.append(claim('C'+str(index),'<='+str(index+1),evidence_ids=tuple('E'+str(index*8+j) for j in range(8))))
        for j in range(8):
            items.append(evidence('E'+str(index*8+j),'C'+str(index),'<='+str(index*8+j+1),lineage_key='source-'+str(index*8+j)))
    got=evaluate_snapshot(context(claims,items))
    assert got.verification_status=='CONFLICT' and got.partial_result
    assert len(got.conflicts)<=128
    assert any('CONFLICT_LIMIT' in warning for warning in got.warnings)

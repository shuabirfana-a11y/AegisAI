"""Breaks caught: accepting forged traces and rereading live sources as old results."""
import copy
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from tests.agents.verification.test_snapshot import request
from tests.agents.verification.test_runtime import service


def test_reader_replays_sealed_result_after_live_claim_and_source_changes(engine,investigation_source):
    src=investigation_source;svc=service(engine)
    saved=svc.run(request(src),actor=src.seed.actor)
    before=svc.read_results(saved.run_id,actor=src.seed.actor)
    with transaction(engine) as db:
        source=db.get(m.Source,src.seed.source_id);old=source.authority_level;source.authority_level='secondary'
        c=db.get(m.Claim,src.seed.claim_id);revision=c.revision;c.revision+=1
    try:
        assert svc.read_results(saved.run_id,actor=src.seed.actor)==before
        with pytest.raises(LookupError):svc.read_results(saved.run_id,actor='foreign-owner')
    finally:
        with transaction(engine) as db:
            db.get(m.Source,src.seed.source_id).authority_level=old
            db.get(m.Claim,src.seed.claim_id).revision=revision


@pytest.mark.parametrize('part',['receipt','status','binding','context'])
def test_reader_rejects_inconsistent_canonical_execution(engine,investigation_source,part):
    src=investigation_source;svc=service(engine)
    saved=svc.run(request(src),actor=src.seed.actor)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,saved.run_id);original=copy.deepcopy(row.details);changed=copy.deepcopy(original)
        ns=changed['runtime_v1']
        if part=='receipt':ns['artifacts']['verify']['tool_calls'][0]['sequence_no']+=100
        if part=='status':ns['traces']['verify']['status']='FAILED'
        if part=='binding':ns['plan']['route']['professional_agents_v1']['bindings']['verify']['implementation_key']='unknown-v1'
        if part=='context':ns['plan']['route']['verification_v1']['context_id']=str(uuid4())
        row.details=changed
    try:
        with pytest.raises((ValueError,LookupError)):svc.read_results(saved.run_id,actor=src.seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,saved.run_id).details=original

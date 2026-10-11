"""Immutable replay and rejection of altered canonical execution records."""
import copy
import pytest
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from tests.agents.analysis.helpers import module,request


@pytest.fixture
def analyzed(engine,analysis_source):
    src=analysis_source;svc=module('service').SecurityAnalysisService(engine)
    saved=svc.run(request(src),actor=src.seed.actor)
    return svc,saved,src


def test_trace_rebuilds_factors_evidence_time_and_source_links(analyzed):
    svc,saved,src=analyzed;result=svc.read_results(saved.run_id,actor=src.seed.actor)
    art=result.artifacts[0];trace=result.traces[0]
    assert art.affected is True and art.risk_level=='UNKNOWN' and art.priority=='REVIEW_REQUIRED'
    assert art.execution_status=='WAITING_REVIEW' and art.verification_status=='CONFIRMED'
    assert art.input_artifact_ids==(src.investigation.artifact_id,src.verification.artifact_id)
    assert trace.output_artifact_id==art.artifact_id and trace.input_snapshot_hash==art.input_snapshot_hash
    assert trace.rule_ids==('R6_MISSING_SEVERITY',) and trace.tools_called==art.tool_calls
    assert art.version_match_result.comparisons and art.evidence_refs
    assert art.evaluation_time>=art.source_verification_time and trace.execution_time>=0
    assert art.historical_snapshot and art.inventory_revision==1 and not art.model_calls


def test_live_changes_leave_historical_result_unchanged(engine,analyzed):
    svc,saved,src=analyzed;before=svc.read_results(saved.run_id,actor=src.seed.actor)
    with transaction(engine) as db:
        component=db.get(m.AssetComponent,src.component_id);version=component.version;revision=component.inventory_revision
        component.version='0.7.0';component.inventory_revision+=1
        source=db.get(m.Source,src.seed.source_id);authority=source.authority_level;source.authority_level='community'
    try:
        assert svc.read_results(saved.run_id,actor=src.seed.actor)==before
        with pytest.raises(LookupError):svc.read_results(saved.run_id,actor='foreign')
    finally:
        with transaction(engine) as db:
            component=db.get(m.AssetComponent,src.component_id);component.version=version;component.inventory_revision=revision
            db.get(m.Source,src.seed.source_id).authority_level=authority


@pytest.mark.parametrize('part',['record','status','binding','context','source'])
def test_reader_rejects_tampered_context_and_binding(engine,analyzed,part):
    svc,saved,src=analyzed
    with transaction(engine) as db:
        row=db.get(m.AgentRun,saved.run_id);original=copy.deepcopy(row.details);changed=copy.deepcopy(original)
        ns=changed['runtime_v1']
        if part=='record':ns['artifacts']['analyze']['tool_calls'][0]['sequence_no']+=5
        if part=='status':ns['traces']['analyze']['status']='SUCCESS'
        if part=='binding':ns['plan']['route']['professional_agents_v1']['bindings']['analyze']['implementation_key']='fake'
        if part=='context':ns['plan']['route']['analysis_v1']['input_snapshot_hash']='f'*64
        if part=='source':ns['plan']['route']['analysis_v1']['verification_artifact_id']=str(src.investigation.artifact_id)
        row.details=changed
    try:
        with pytest.raises(ValueError):svc.read_results(saved.run_id,actor=src.seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,saved.run_id).details=original


def test_reader_rejects_schema_valid_but_unbacked_verdict(engine,analyzed):
    svc,saved,src=analyzed
    with transaction(engine) as db:
        row=db.get(m.AgentRun,saved.run_id)
        original=copy.deepcopy(row.details);changed=copy.deepcopy(original)
        # Even a valid severity-based shape must match the sealed deterministic facts.
        changed['runtime_v1']['artifacts']['analyze']['result']['outputs'][0]['data']['assessment'].update(risk_level='HIGH',priority='P1')
        row.details=changed
    try:
        with pytest.raises(ValueError,match='AGENT_TRACE_INVALID'):svc.read_results(saved.run_id,actor=src.seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,saved.run_id).details=original

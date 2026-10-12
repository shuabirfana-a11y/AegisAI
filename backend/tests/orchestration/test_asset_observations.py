"""Snapshot origin and handoff are real services over explicitly synthetic fixtures."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.orchestration.service import InvestigationOrchestrator
from app.agents.verification.context_store import VerificationContextStore
from app.agents.contracts import fingerprint
from tests.orchestration.fixtures import scenario
from app.orchestration.answer_sources import AnswerSourcesLoader


def test_asset_version_is_sealed_and_verification_can_consume_it(engine):
    seed,request,gw,_,_=scenario(engine)
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        assert result.status.error_code is None
        with transaction(engine) as db:
            row=db.get(m.AgentRun,result.context.verification_run_id)
            cid=row.details['runtime_v1']['plan']['route']['verification_v1']['context_id']
        sealed=VerificationContextStore(engine).read(cid,actor=seed.actor)
        observations=getattr(sealed.snapshot,'version_observations',())
        assert len(observations)==1
        obs=observations[0]
        assert (obs.asset_id,obs.component_id,obs.version)==(seed.asset_id,seed.component_id,'0.6.0')
        assert obs.type=='VERSION_OBSERVATION' and obs.source=='OWNER_INVENTORY_NOT_SCANNED'
        assert obs.asset_name and obs.environment=='production' and obs.exposure=='internet'
        assert obs.is_demo and obs.receipt_id and obs.receipt_hash
        assert sealed.snapshot.impact_version_evidence
        sources,gate,_=AnswerSourcesLoader(engine).load(result.context,actor=seed.actor)
        assert sources.verification.version_observations==observations
        assert sources.analysis.affected is True and sources.analysis.risk_level=='HIGH'
        with pytest.raises(ValueError):obs.version='99.0.0'
        assert sealed.source_snapshot_hash==fingerprint(sealed.snapshot.model_dump(mode='json'))
    finally:gw.close()


def test_insufficient_source_remains_blocked_with_asset_observation(engine):
    seed,request,gw,_,_=scenario(engine,'insufficient')
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        sources,gate,_=AnswerSourcesLoader(engine).load(result.context,actor=seed.actor)
        assert sources.analysis is None or sources.analysis.affected is None and sources.analysis.risk_level=='UNKNOWN'
        assert gate.status=='REPLAN_REQUIRED'
    finally:gw.close()


@pytest.mark.parametrize('mode',['unknown_version','conflict'])
def test_unknown_and_conflict_never_become_safe(engine,mode):
    seed,request,gw,_,_=scenario(engine,mode)
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        sources,gate,_=AnswerSourcesLoader(engine).load(result.context,actor=seed.actor)
        assert sources.analysis is None or sources.analysis.affected is None and sources.analysis.risk_level=='UNKNOWN'
        assert gate.status in ('REPLAN_REQUIRED','HUMAN_REVIEW_REQUIRED')
        if sources.verification and mode=='conflict':assert sources.verification.verification_status=='CONFLICT'
    finally:gw.close()


def test_analysis_uses_original_observation_after_inventory_version_changes(engine):
    from app.agents.analysis.context_store import AnalysisContextStore
    from app.agents.analysis.snapshot import AnalysisSnapshotReader
    seed,request,gw,_,_=scenario(engine)
    try:
        result=InvestigationOrchestrator(engine,gw).investigate(request,actor=seed.actor)
        with transaction(engine) as db:
            row=db.get(m.AgentRun,result.context.analysis_run_id)
            cid=row.details['runtime_v1']['plan']['route']['analysis_v1']['context_id']
        original=AnalysisContextStore(engine).read(cid,actor=seed.actor)
        with transaction(engine) as db:
            component=db.get(m.AssetComponent,seed.component_id)
            component.version='0.7.0';component.inventory_revision+=1
        replay=AnalysisSnapshotReader(engine).read(original.request,actor=seed.actor,evaluation_time=original.evaluation_time)
        assert replay.asset.deployed_version=='0.6.0' and replay.asset.inventory_revision==1
        assert replay.asset.version_observation_id==original.inputs.asset.version_observation_id
        from app.agents.contracts import AgentFrameworkError
        with pytest.raises(AgentFrameworkError,match='INVALID_INPUT_ARTIFACT'):
            AnalysisSnapshotReader(engine).read(original.request,actor='someone-else',evaluation_time=original.evaluation_time)
    finally:gw.close()

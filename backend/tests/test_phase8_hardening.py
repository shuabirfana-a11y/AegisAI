"""Failures of real domain rules; synthetic labelled fixtures only."""
from datetime import timedelta
from sqlalchemy import select,func
from app.db import models as m
from app.utils.time import utcnow
from test_phase8_matching import confirmed_range,synthetic_verification

def test_snapshot_records_intelligence_a_b_a_transition(db,seed):
    from app.assets.risk import RiskService
    c=confirmed_range(db,seed)
    RiskService.recompute(db,seed.asset.id)
    c.verification_status='conflict';c.adopted=False;db.flush();RiskService.recompute(db,seed.asset.id)
    c.verification_status='confirmed';c.adopted=True;db.flush();RiskService.recompute(db,seed.asset.id)
    assert [s.match_status for s in db.scalars(select(m.AssetRiskSnapshot).order_by(m.AssetRiskSnapshot.created_at))]==['AFFECTED','UNCERTAIN','AFFECTED']

def test_old_verified_evidence_cannot_justify_current_safe_match(db,seed,monkeypatch):
    from app.assets import matching
    from conftest import NOW
    confirmed_range(db,seed);seed.component.version='0.8.4';db.flush()
    monkeypatch.setattr(matching,'utcnow',lambda:NOW+timedelta(days=31),raising=False)
    assert matching.AssetVulnerabilityMatcher.match(db,seed.component)[0]['match_status']=='UNCERTAIN'

def test_changed_public_poc_confirmation_emits_change_and_priority(db,seed):
    from app.assets.risk import RiskService
    from app.enrichment.repository import ClaimStore
    from app.enrichment.evidence import EvidenceService
    confirmed_range(db,seed);seed.vuln.primary_severity='high';db.flush();RiskService.recompute(db,seed.asset.id)
    p=seed.poc;p.status='confirmed'
    c=ClaimStore.add(db,seed.vuln.id,'POC_ASSOCIATION','poc:test',{'url':p.url,'association':'candidate'},subject={'poc_candidate_id':p.id})
    evidence=EvidenceService.add(db,c,seed.observations[0],c.value_json,{'json_pointer':''});synthetic_verification(db,c,evidence);c.verification_status='confirmed';c.adopted=True;db.flush()
    RiskService.recompute(db,seed.asset.id)
    rows=list(db.scalars(select(m.AssetRiskSnapshot).order_by(m.AssetRiskSnapshot.created_at)))
    assert rows[-1].priority=='P1' and rows[-1].payload['poc']['confirmed']
    assert 'POC_CONFIRMED' in set(db.scalars(select(m.AssetRiskChange.event_type)))

def test_private_review_evidence_is_readable_by_asset_owner_only(db,seed,monkeypatch):
    from test_phase8_api_events import HEAD
    from app.main import create_app
    from app.api.dependencies import get_session
    from fastapi.testclient import TestClient
    from app.assets.risk import RiskService
    monkeypatch.setenv('AEGIS_ASSET_TOKEN','TEST-LOCAL-SECRET');monkeypatch.setenv('AEGIS_ASSET_OWNER','test-analyst')
    confirmed_range(db,seed);seed.asset.environment='production';seed.component.version='custom';db.flush();RiskService.recompute(db,seed.asset.id)
    application=create_app(db.get_bind());application.dependency_overrides[get_session]=lambda:db
    with TestClient(application) as client:
        r=client.get('/api/v1/assets/'+str(seed.asset.id)+'/reviews',headers=HEAD)
        assert r.status_code==200 and r.json()['total']==1
        assert r.json()['items'][0]['claim']['id'] and r.json()['items'][0]['evidence']

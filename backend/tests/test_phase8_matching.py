import json
import pytest
from sqlalchemy import select,func
from app.db import models as m
from conftest import NOW
from test_phase8_units import cdx

def synthetic_verification(db,c,evidence):
    # Explicit independent test decision; never inserted in the real demo DB.
    r=m.VerificationResult(claim_id=c.id,claim_revision=c.revision,status='confirmed',verification_method='TEST',reason_summary='SYNTHETIC labelled fixture',verified_at=NOW,verified_by_type='system',verified_by_id='TEST',decision_key='TEST:'+str(c.id),adopted_value=c.value_json,details={'observed_evidence_ids':[str(evidence.id)]})
    db.add(r);db.flush();return r

def confirmed_range(db,seed):
    from app.enrichment.repository import ClaimStore
    from app.enrichment.evidence import EvidenceService
    c=ClaimStore.add(db,seed.vuln.id,'AFFECTS_VERSION','PyPI:vllm',{'ecosystem':'PyPI','package':'vllm','raw_expression':'>=0.8.0,<0.8.4'},subject={'package_identifier_id':seed.packages[0].id})
    evidence=EvidenceService.add(db,c,seed.observations[0],c.value_json,{'json_pointer':''})
    synthetic_verification(db,c,evidence)
    c.verification_status='confirmed';c.adopted=True;db.flush();return c

def test_asset_matching_affected_has_range_claim_evidence_comparison(db,seed):
    from app.assets.matching import AssetVulnerabilityMatcher
    c=confirmed_range(db,seed)
    r=AssetVulnerabilityMatcher.match(db,seed.component)
    assert len(r)==1 and r[0]['match_status']=='AFFECTED'
    assert r[0]['claim_ids']==[str(c.id)] and r[0]['evidence_refs']
    assert r[0]['affected_ranges'] and r[0]['comparisons'][0]['in_range'] is True

def test_product_related_at_fixed_boundary_not_affected(db,seed):
    from app.assets.matching import AssetVulnerabilityMatcher
    confirmed_range(db,seed);seed.component.version='0.8.4';db.flush()
    r=AssetVulnerabilityMatcher.match(db,seed.component)[0]
    assert r['match_status']=='NOT_AFFECTED' and r['version_result']=='NOT_AFFECTED'

@pytest.mark.parametrize('status',['pending','insufficient','conflict'])
def test_untrusted_version_assertion_never_safe_or_definite(db,seed,status):
    from app.assets.matching import AssetVulnerabilityMatcher
    c=confirmed_range(db,seed);c.verification_status=status;c.adopted=False;seed.component.version='0.8.4';db.flush()
    r=AssetVulnerabilityMatcher.match(db,seed.component)[0]
    assert r['match_status']=='UNCERTAIN' and r['version_result']=='NOT_AFFECTED'

def test_unknown_custom_version_retains_uncertain(db,seed):
    from app.assets.matching import AssetVulnerabilityMatcher
    confirmed_range(db,seed);seed.component.version='0.8.2-custom';db.flush()
    assert AssetVulnerabilityMatcher.match(db,seed.component)[0]['match_status']=='UNCERTAIN'

def test_other_package_range_never_crosses_scope(db,seed):
    from app.assets.matching import AssetVulnerabilityMatcher
    c=confirmed_range(db,seed);seed.component.product_id=seed.products[1].id;seed.component.package_identifier_id=seed.packages[1].id;seed.component.version='2.6.0';db.flush()
    r=AssetVulnerabilityMatcher.match(db,seed.component)[0]
    assert str(c.id) not in r['claim_ids'] and r['match_status']=='UNCERTAIN'

def test_withdrawn_vulnerability_is_not_evaluated(db,seed):
    from app.assets.matching import AssetVulnerabilityMatcher
    confirmed_range(db,seed);seed.vuln.status='withdrawn';db.flush()
    assert AssetVulnerabilityMatcher.match(db,seed.component)[0]['match_status']=='NOT_EVALUATED'

def test_inventory_manual_create_idempotency_and_revision_history(db,seed):
    from app.assets.inventory import AssetService
    a=AssetService.create(db,{'name':'Demo','environment':'production','is_demo':True},'analyst','create-1')
    assert AssetService.create(db,{'name':'Demo','environment':'production','is_demo':True},'analyst','create-1').id==a.id
    c=AssetService.add_component(db,a.id,{'name':'vllm','ecosystem':'PyPI','version':'0.8.2'},'analyst','comp-1')
    assert AssetService.add_component(db,a.id,{'name':'vllm','ecosystem':'PyPI','version':'0.8.2'},'analyst','comp-1').id==c.id
    AssetService.update_component(db,a.id,c.id,'0.8.4',1,'analyst','upgrade-1')
    assert c.version=='0.8.4' and c.inventory_revision==2
    assert db.scalar(select(func.count()).select_from(m.AssetInventoryEvent).where(m.AssetInventoryEvent.asset_id==a.id))==2

def test_sbom_repeat_update_diff_preserves_manual_inventory(db,seed):
    from app.assets.inventory import AssetService
    a=AssetService.create(db,{'name':'SBOM demo','is_demo':True},'analyst','sbom-a')
    manual=AssetService.add_component(db,a.id,{'name':'PyTorch','version':'2.6.0'},'analyst','manual-a')
    raw=json.dumps(cdx()).encode()
    first=AssetService.import_sbom(db,a.id,raw,'analyst','import-1')
    repeat=AssetService.import_sbom(db,a.id,raw,'analyst','import-2')
    assert first['added']==1 and repeat['added']==0 and repeat['updated']==0
    newer=cdx();newer['components'][0]['version']='0.8.4';newer['components'][0]['purl']='pkg:pypi/vllm@0.8.4'
    assert AssetService.import_sbom(db,a.id,json.dumps(newer).encode(),'analyst','import-3')['updated']==1
    empty=cdx();empty['components']=[]
    assert AssetService.import_sbom(db,a.id,json.dumps(empty).encode(),'analyst','import-4')['removed']==1
    assert manual.deleted_at is None

def test_duplicate_request_changed_body_rejected(db,seed):
    from app.assets.inventory import AssetService
    from app.db.persistence import IdempotencyConflict
    AssetService.create(db,{'name':'first'},'analyst','idempotency')
    with pytest.raises(IdempotencyConflict):AssetService.create(db,{'name':'second'},'analyst','idempotency')

def test_risk_priority_kev_poc_remediation_factors_are_transparent():
    from app.assets.priority import assess_priority
    ctx={'match_status':'AFFECTED','severity':'high','kev':{'confirmed':True},'poc':{'confirmed':True},'epss':{'score':0.8},'remediation':{'statuses':['PATCH_AVAILABLE']},'environment':'production','exposure':'internet','verification_status':'CONFIRMED'}
    r=assess_priority(ctx)
    assert r['priority']=='P0'
    assert {'ASSET_MATCH','KEV','CONFIRMED_POC','PATCH_AVAILABLE','PRODUCTION','INTERNET_EXPOSED'}<=set(r['factor_codes'])
    assert 'KEV' in r['why_now']
    ctx['match_status']='NOT_AFFECTED';assert assess_priority(ctx)['priority']=='INFO'
    ctx['match_status']='UNCERTAIN';assert assess_priority(ctx)['priority']=='REVIEW'

def test_upgrade_creates_match_changed_event_and_history(db,seed):
    from app.assets.inventory import AssetService
    from app.assets.risk import RiskService
    confirmed_range(db,seed)
    RiskService.recompute(db,seed.asset.id)
    AssetService.update_component(db,seed.asset.id,seed.component.id,'0.8.4',1,'test-analyst','upgrade-risk')
    snapshots=list(db.scalars(select(m.AssetRiskSnapshot).order_by(m.AssetRiskSnapshot.created_at)))
    assert [s.match_status for s in snapshots]==['AFFECTED','NOT_AFFECTED']
    assert 'MATCH_CHANGED' in set(db.scalars(select(m.AssetRiskChange.event_type)))

def test_repeated_recompute_does_not_duplicate_snapshots(db,seed):
    from app.assets.risk import RiskService
    confirmed_range(db,seed)
    RiskService.recompute(db,seed.asset.id);RiskService.recompute(db,seed.asset.id)
    assert db.scalar(select(func.count()).select_from(m.AssetRiskSnapshot))==1

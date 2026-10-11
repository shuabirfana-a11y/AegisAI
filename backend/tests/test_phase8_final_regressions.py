import json
from datetime import timedelta
from hashlib import sha256
from sqlalchemy import select,func
from app.db import models as m
from conftest import NOW
from test_phase8_matching import confirmed_range,synthetic_verification
from test_phase8_api_events import asset_client,HEAD
from app.utils.time import utcnow

def test_confirmed_flag_without_verification_record_is_not_trusted(db,seed):
    from app.enrichment.repository import ClaimStore
    from app.enrichment.evidence import EvidenceService
    from app.assets.remediation import trusted_claim
    c=ClaimStore.add(db,seed.vuln.id,'FIXED_VERSION','PyPI:vllm:unverified',{'ecosystem':'PyPI','package':'vllm','version':'0.8.4'},subject={'package_identifier_id':seed.packages[0].id})
    EvidenceService.add(db,c,seed.observations[0],c.value_json,{'json_pointer':''})
    c.verification_status='confirmed';c.adopted=True;db.flush()
    assert not trusted_claim(db,c)

def test_public_vulnerability_aggregate_never_exposes_private_asset_review(db,seed,asset_client):
    from app.assets.risk import RiskService
    confirmed_range(db,seed);seed.asset.environment='production';seed.component.version='custom';db.flush();RiskService.recompute(db,seed.asset.id)
    result=asset_client.get('/api/v1/vulnerabilities/'+seed.vuln.canonical_id).json()
    assert all(r['review_type']!='ASSET_MATCH_REVIEW' for r in result['reviews'])
    assert str(seed.asset.id) not in json.dumps(result)

def test_read_projection_expires_without_domain_event(db,seed,monkeypatch):
    from app.assets.risk import RiskService
    from app.assets import queries
    confirmed_range(db,seed);seed.component.version='0.8.4';db.flush();RiskService.recompute(db,seed.asset.id)
    monkeypatch.setattr(queries,'utcnow',lambda:utcnow()+timedelta(days=31),raising=False)
    r=queries.get_asset_risks(db,seed.asset.id,'test-analyst')['items'][0]
    assert r['is_stale'] and r['match_status']=='UNCERTAIN'

def new_observation(db,seed):
    payload=b'SYNTHETIC broader current range'
    raw=m.RawDocument(source_id=seed.sources[0].id,external_id=seed.raws[0].external_id,source_url=seed.raws[0].source_url,retrieved_at=utcnow(),raw_payload=payload,content_hash=sha256(payload).hexdigest(),content_type='text/plain',publisher='TEST',completeness='complete')
    db.add(raw);db.flush()
    obs=m.SourceObservation(source_id=raw.source_id,raw_document_id=raw.id,external_id=raw.external_id,record_type='vulnerability',retrieved_at=raw.retrieved_at,publisher='TEST',lineage_key='TEST',parse_status='parsed',normalizer_version='TEST-NEW')
    db.add(obs);db.flush();return obs

def test_new_phase6_range_without_event_invalidates_and_targets_asset(db,seed):
    from app.assets.risk import RiskService
    from app.assets.queries import get_asset_risks
    from app.assets.events import dispatch_events
    confirmed_range(db,seed);seed.component.version='0.8.4';db.flush();RiskService.recompute(db,seed.asset.id)
    obs=new_observation(db,seed)
    r=m.AffectedVersionRange(vulnerability_id=seed.vuln.id,product_id=seed.products[0].id,package_identifier_id=seed.packages[0].id,source_id=obs.source_id,observation_id=obs.id,range_type='ECOSYSTEM',raw_expression='<0.8.5',fixed='0.8.5',scope_key='PyPI:vllm',parse_status='parsed',parser_version='TEST')
    db.add(r);db.flush()
    current=get_asset_risks(db,seed.asset.id,'test-analyst')['items'][0]
    assert current['is_stale'] and current['match_status']=='UNCERTAIN'
    assert any(j.asset_id==seed.asset.id for j in dispatch_events(db,50))

def test_package_claim_event_with_no_range_still_targets_asset(db,seed):
    from app.assets.events import dispatch_events
    vuln=m.Vulnerability(canonical_id='CVE-2099-9999002',title='SYNTHETIC vendor only',status='published');db.add(vuln);db.flush()
    c=m.Claim(claim_key='vendor-no-range',vulnerability_id=vuln.id,package_identifier_id=seed.packages[0].id,claim_type='AFFECTS_VERSION',predicate='AFFECTS_VERSION',value_json={'ecosystem':'PyPI','range':'<0.8.4'},scope_key='PyPI:vllm');db.add(c);db.flush()
    e=m.IntelligenceEvent(event_key='vendor-no-range-event',vulnerability_id=vuln.id,claim_id=c.id,event_type='VERIFICATION_CHANGED',summary='SYNTHETIC',detected_at=utcnow());db.add(e);db.flush()
    assert any(j.asset_id==seed.asset.id for j in dispatch_events(db,50))

def test_current_contradiction_blocks_retained_human_claim_and_remediation(db,seed):
    from app.assets.matching import AssetVulnerabilityMatcher
    from app.assets.remediation import trusted_claim
    from app.enrichment.evidence import EvidenceService
    c=confirmed_range(db,seed)
    # System cannot silently reuse a retained human decision against new contrary evidence.
    c.revision=2;db.flush()
    result=m.VerificationResult(claim_id=c.id,claim_revision=2,status='confirmed',verification_method='human',reason_summary='SYNTHETIC analyst',verified_at=NOW,verified_by_type='human',verified_by_id='TEST',decision_key='TEST-HUMAN',adopted_value=c.value_json)
    db.add(result);db.flush()
    EvidenceService.add(db,c,seed.observations[1],{'ecosystem':'PyPI','range':'<0.8.5'}, {'json_pointer':'/new'},stance='contradict')
    assert not trusted_claim(db,c)
    assert AssetVulnerabilityMatcher.match(db,seed.component)[0]['match_status']=='UNCERTAIN'

def test_incomplete_claim_does_not_hide_another_interval(db,seed):
    from app.assets.matching import AssetVulnerabilityMatcher
    confirmed_range(db,seed)
    r=m.AffectedVersionRange(vulnerability_id=seed.vuln.id,product_id=seed.products[0].id,package_identifier_id=seed.packages[0].id,source_id=seed.sources[0].id,observation_id=seed.observations[0].id,range_type='ECOSYSTEM',raw_expression='>=0.9.0,<0.9.5',introduced='0.9.0',fixed='0.9.5',scope_key='PyPI:vllm',parse_status='parsed',parser_version='TEST')
    db.add(r);db.flush();seed.component.version='0.9.2'
    assert AssetVulnerabilityMatcher.match(db,seed.component)[0]['match_status']!='NOT_AFFECTED'

def test_simple_claim_does_not_hide_current_unsupported_source_range(db,seed):
    from app.assets.matching import AssetVulnerabilityMatcher
    from app.enrichment.repository import ClaimStore
    from app.enrichment.evidence import EvidenceService
    confirmed_range(db,seed);obs=new_observation(db,seed)
    r=m.AffectedVersionRange(vulnerability_id=seed.vuln.id,product_id=seed.products[0].id,package_identifier_id=seed.packages[0].id,source_id=obs.source_id,observation_id=obs.id,range_type='ECOSYSTEM',raw_expression='SYNTHETIC unsupported branch expression',scope_key='PyPI:vllm',parse_status='unsupported',parser_version='TEST')
    db.add(r);db.flush()
    c=ClaimStore.add(db,seed.vuln.id,'AFFECTS_VERSION','PyPI:vllm:partial',{'ecosystem':'PyPI','package':'vllm','raw_expression':'<0.8.4'},subject={'package_identifier_id':seed.packages[0].id})
    evidence=EvidenceService.add(db,c,obs,c.value_json,{'json_pointer':''});synthetic_verification(db,c,evidence);c.verification_status='confirmed';c.adopted=True
    seed.component.version='0.8.5';db.flush()
    assert AssetVulnerabilityMatcher.match(db,seed.component)[0]['match_status']=='UNCERTAIN'

def test_metadata_root_without_purl_still_imports_nested_package(db,seed):
    from app.assets.inventory import AssetService
    doc={'bomFormat':'CycloneDX','specVersion':'1.6','version':1,'metadata':{'component':{'type':'application','name':'root','components':[{'type':'library','bom-ref':'nested-vllm','name':'vllm','version':'0.8.2','purl':'pkg:pypi/vllm@0.8.2'}]}}}
    r=AssetService.import_sbom(db,seed.asset.id,json.dumps(doc).encode(),'test-analyst','nested-import')
    assert r['added']==1 and r['component_count']==1

def test_unresolved_identity_replacement_preserves_history(db,seed):
    from app.assets.inventory import AssetService
    def doc(name,purl):return json.dumps({'bomFormat':'CycloneDX','specVersion':'1.6','version':1,'components':[{'type':'library','bom-ref':'slot','name':name,'version':'1.0','purl':purl}]}).encode()
    first=AssetService.import_sbom(db,seed.asset.id,doc('unknown-a','pkg:pypi/unknown-a@1.0'),'test-analyst','unknown-a')
    second=AssetService.import_sbom(db,seed.asset.id,doc('unknown-b','pkg:npm/unknown-b@1.0'),'test-analyst','unknown-b')
    assert second['added']==1 and second['removed']==1
    old=db.get(m.AssetComponent,first['added_ids'][0]);new=db.get(m.AssetComponent,second['added_ids'][0])
    assert old.deleted_at is not None and new.raw_package_name=='unknown-b' and new.ecosystem=='npm'

def test_exhausted_job_does_not_poison_later_successful_recompute(db,seed):
    from app.assets.risk import RiskService
    from app.assets.queries import get_asset_risks
    confirmed_range(db,seed)
    job=m.AssetRecomputeJob(asset_id=seed.asset.id,job_key='TEST-exhausted',status='failed',attempt=3,started_at=NOW,finished_at=NOW,error_code='TEST');db.add(job);db.flush()
    RiskService.recompute(db,seed.asset.id)
    r=get_asset_risks(db,seed.asset.id,'test-analyst')['items'][0]
    assert not r['is_stale'] and r['match_status']=='AFFECTED'

def test_patch_product_association_is_not_other_package_applicability(db,seed):
    from app.enrichment.repository import ClaimStore
    from app.enrichment.evidence import EvidenceService
    from app.assets.remediation import get_remediation
    other=m.PackageIdentifier(product_id=seed.products[0].id,ecosystem='PyPI',package_name='vllm-other',purl='pkg:pypi/vllm-other');db.add(other);db.flush()
    p=m.PatchCandidate(vulnerability_id=seed.vuln.id,product_id=seed.products[0].id,source_id=seed.sources[0].id,observation_id=seed.observations[0].id,patch_type='pull_request',identity_key='patch-A',url='https://example.invalid/patch',status='confirmed',first_seen_at=NOW,details={'package_identifier_id':str(seed.packages[0].id),'branch':'other-branch'})
    db.add(p);db.flush();c=ClaimStore.add(db,seed.vuln.id,'PATCH_EXISTS','patch:A',{'url':p.url},subject={'patch_candidate_id':p.id});evidence=EvidenceService.add(db,c,seed.observations[0],c.value_json,{'json_pointer':''});synthetic_verification(db,c,evidence);c.verification_status='confirmed';c.adopted=True;db.flush()
    result=get_remediation(db,seed.vuln.id,other.id)
    assert 'PATCH_AVAILABLE' not in result['statuses']
    assert result.get('related_patches')

def test_expired_risk_snapshot_does_not_reference_old_definite_match(db,seed,monkeypatch):
    from app.assets import matching
    from app.assets.risk import RiskService
    confirmed_range(db,seed);RiskService.recompute(db,seed.asset.id)
    old=db.scalar(select(m.AssetRiskSnapshot))
    monkeypatch.setattr(matching,'utcnow',lambda:NOW+timedelta(days=31));RiskService.recompute(db,seed.asset.id)
    new=db.scalar(select(m.AssetRiskSnapshot).order_by(m.AssetRiskSnapshot.created_at.desc()))
    assert new.match_status=='UNCERTAIN' and new.match_id!=old.match_id
    assert db.get(m.AssetVulnerabilityMatch,new.match_id).match_status=='unknown'

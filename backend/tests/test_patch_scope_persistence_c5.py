"""Existing remediation contracts over synthetic, isolated PostgreSQL fixtures."""
from datetime import timedelta
from uuid import uuid4
import pytest
from app.db import models as m
from app.enrichment.repository import ClaimStore
from app.enrichment.evidence import EvidenceService
from app.assets.remediation import get_remediation
from conftest import NOW
from test_phase8_matching import synthetic_verification

@pytest.mark.parametrize('scope',['exact','other_product','other_package','other_branch','unspecified','conflict','historical'])
def test_patch_claim_evidence_scope_roundtrip(db,seed,monkeypatch,scope):
    package=seed.packages[0]
    if scope=='other_product':query_package=seed.packages[1]
    elif scope=='other_package':
        query_package=m.PackageIdentifier(product_id=package.product_id,ecosystem='PyPI',package_name='synthetic-other',purl='pkg:pypi/synthetic-other')
        db.add(query_package);db.flush()
    else:query_package=package
    details={'is_test':True}
    if scope!='unspecified':details['package_identifier_id']=str(package.id)
    p=m.PatchCandidate(vulnerability_id=seed.vuln.id,product_id=package.product_id,
        source_id=seed.sources[0].id,observation_id=seed.observations[0].id,patch_type='commit',
        identity_key='C5_SYNTHETIC_'+uuid4().hex,url='https://github.com/synthetic/project/commit/'+'b'*40,
        commit_sha='b'*40,branch='other-release' if scope=='other_branch' else '',status='confirmed',first_seen_at=NOW,details=details)
    db.add(p);db.flush()
    c=ClaimStore.add(db,seed.vuln.id,'FIX_COMMIT','patch:'+p.identity_key,{'url':p.url},subject={'patch_candidate_id':p.id})
    e=EvidenceService.add(db,c,seed.observations[0],c.value_json,{'json_pointer':''})
    synthetic_verification(db,c,e);c.verification_status='conflict' if scope=='conflict' else 'confirmed';c.adopted=scope!='conflict';db.flush()
    ids=(p.id,c.id,e.id);db.expire_all()
    assert db.get(m.Claim,ids[1]).patch_candidate_id==ids[0]
    assert db.get(m.Evidence,ids[2]).claim_id==ids[1]
    if scope=='historical':monkeypatch.setattr('app.assets.remediation.utcnow',lambda:NOW+timedelta(days=31))
    result=get_remediation(db,seed.vuln.id,query_package.id)
    if scope=='exact':
        assert result['statuses']==['PATCH_AVAILABLE']
        assert result['patches'][0]['claim_id']==str(c.id)
        assert str(e.id) in result['patches'][0]['evidence_ids']
        assert result['patches'][0]['applicability']=='PACKAGE_CONFIRMED'
    else:assert 'PATCH_AVAILABLE' not in result['statuses']
    if scope in ('other_package','other_branch','unspecified'):
        assert result['related_patches'] and result['related_patches'][0]['applicability']=='UNKNOWN'
    assert 'PATCH_APPLIED' not in result['statuses']
    assert not result['fixed_versions'], 'Commit association is not a release fixed-version claim'

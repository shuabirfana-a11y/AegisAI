from hashlib import sha256
from uuid import uuid4
import pytest
from sqlalchemy import select,func,update
from app.db import models as m
from app.db.persistence import RevisionConflict
from conftest import NOW

def claim_with_evidence(db,seed,value=None,kind='FIXED_VERSION',index=0):
    from app.enrichment.repository import ClaimStore
    from app.enrichment.evidence import EvidenceService
    value=value or {'package':'vllm','ecosystem':'PyPI','version':'0.8.4'}
    seed.sources[index].authority_level='official'
    claim=ClaimStore.add(db,seed.vuln.id,kind,'PyPI:vllm',value)
    observation=seed.observations[index]
    evidence=EvidenceService.add(db,claim,observation,value,{'json_pointer':'/test/fixed'},
        evidence_type='official_vendor_advisory',explicit=True)
    return claim,evidence

def test_equal_claims_and_same_raw_locator_are_idempotent(db,seed):
    c,e=claim_with_evidence(db,seed)
    c2,e2=claim_with_evidence(db,seed)
    assert c.id==c2.id and e.id==e2.id
    assert db.scalar(select(func.count()).select_from(m.Evidence).where(m.Evidence.claim_id==c.id))==1

def test_evidence_preserves_raw_source_locator_and_hash(db,seed):
    c,e=claim_with_evidence(db,seed)
    assert e.raw_document_id==seed.raws[0].id and e.source_id==seed.sources[0].id
    assert e.excerpt_hash==sha256(e.excerpt.encode()).hexdigest() and e.locator['json_pointer']=='/test/fixed'
    assert e.details['content_trust_level']=='UNTRUSTED_EXTERNAL_CONTENT'

def test_critical_claim_without_evidence_cannot_pass_gate(db,seed):
    from app.enrichment.repository import ClaimStore
    from app.enrichment.verification import VerificationService
    from app.enrichment.integration import IntelligenceIntegrationService
    c=ClaimStore.add(db,seed.vuln.id,'FIXED_VERSION','PyPI:vllm',{'version':'0.8.4'})
    result=VerificationService.verify(db,c,now=NOW)
    gate=IntelligenceIntegrationService.adopt(db,c,result,now=NOW)
    assert result.status=='insufficient' and not gate['adopted'] and not c.adopted

def test_confirmed_claim_has_verification_evidence_and_real_event(db,seed):
    from app.enrichment.verification import VerificationService
    c,e=claim_with_evidence(db,seed,index=2)
    result=VerificationService.verify(db,c,now=NOW)
    assert result.status=='confirmed'
    assert db.scalar(select(m.VerificationEvidence.evidence_id).where(m.VerificationEvidence.verification_result_id==result.id))==e.id
    assert db.scalar(select(m.IntelligenceEvent).where(m.IntelligenceEvent.claim_id==c.id))

def test_two_different_current_ranges_generate_conflict_and_review(db,seed):
    from app.enrichment.conflict import ConflictDetectionService
    a,e=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<0.8.4'},'AFFECTS_VERSION',0)
    b,e2=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<=0.8.5'},'AFFECTS_VERSION',2)
    conflicts=ConflictDetectionService.detect(db,seed.vuln.id,now=NOW)
    assert len(conflicts)==1 and conflicts[0].conflict_type=='VERSION_CONFLICT'
    assert {conflicts[0].claim_a_id,conflicts[0].claim_b_id}=={a.id,b.id}
    assert db.get(m.ReviewTask,conflicts[0].review_task_id).review_type=='VERSION_CONFLICT'
    assert {x.stance for x in db.scalars(select(m.Evidence).where(m.Evidence.claim_id==a.id))}=={'support','contradict'}
    assert len(ConflictDetectionService.detect(db,seed.vuln.id,now=NOW))==1

def test_same_content_sources_do_not_create_conflict(db,seed):
    from app.enrichment.conflict import ConflictDetectionService
    c,e=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<0.8.4'},'AFFECTS_VERSION',0)
    c2,e2=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'< 0.8.4.0'},'AFFECTS_VERSION',2)
    assert c.id==c2.id and ConflictDetectionService.detect(db,seed.vuln.id,now=NOW)==[]

def test_old_same_publisher_revision_retained_without_false_conflict(db,seed):
    from app.enrichment.conflict import ConflictDetectionService
    a,e=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<0.8.4'},'AFFECTS_VERSION',0)
    b,e2=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<=0.8.5'},'AFFECTS_VERSION',2)
    a.details={**a.details,'superseded':True};db.flush()
    assert ConflictDetectionService.detect(db,seed.vuln.id,now=NOW)==[]
    assert db.get(m.Evidence,e.id).excerpt_hash==e.excerpt_hash

def test_review_resolution_result_audit_timeline_and_retry_are_atomic(db,seed):
    from app.enrichment.review import ReviewWorkflow
    args=dict(task_id=seed.review.id,actor='test-analyst',expected_revision=1,expected_claim_revision=1,
        request_key='P7-review',status='confirmed',value={'raw_expression':'<0.8.4'},reason='TEST analyst compared original sources',evidence_ids=[seed.evidence[0].id])
    audit=ReviewWorkflow.resolve(db,**args)
    again=ReviewWorkflow.resolve(db,**args)
    assert audit.id==again.id and audit.verification_result_id is not None
    event=db.scalar(select(m.IntelligenceEvent).where(m.IntelligenceEvent.event_type=='REVIEW_RESOLVED'))
    assert event and event.claim_id==seed.claim.id
    assert db.scalar(select(func.count()).select_from(m.AuditLog))==1
    with pytest.raises(RevisionConflict):ReviewWorkflow.resolve(db,**{**args,'request_key':'P7-stale'})

def test_rejected_review_is_explicit_and_keeps_history(db,seed):
    from app.enrichment.review import ReviewWorkflow
    audit=ReviewWorkflow.resolve(db,task_id=seed.review.id,actor='test-analyst',expected_revision=1,
        expected_claim_revision=1,request_key='P7-reject',status='rejected',value=None,
        reason='TEST evidence demonstrates unrelated repository',evidence_ids=[seed.evidence[2].id])
    assert db.get(m.VerificationResult,audit.verification_result_id).status=='rejected'
    assert db.get(m.Evidence,seed.evidence[0].id) is not None

def test_automatic_reverification_does_not_overwrite_human_resolution(db,seed):
    from app.enrichment.review import ReviewWorkflow
    from app.enrichment.verification import VerificationService
    from app.enrichment.repository import ClaimStore
    c,e=claim_with_evidence(db,seed,index=2)
    task=m.ReviewTask(claim_id=c.id,review_type='INSUFFICIENT_EVIDENCE',reason='TEST review');db.add(task);db.flush()
    audit=ReviewWorkflow.resolve(db,task_id=task.id,actor='test-analyst',expected_revision=1,expected_claim_revision=1,
        request_key='P7-human',status='confirmed',value=c.value_json,reason='TEST checked',evidence_ids=[e.id])
    c2=ClaimStore.add(db,seed.vuln.id,'FIXED_VERSION','PyPI:vllm',c.value_json)
    result=VerificationService.verify(db,c2,now=NOW)
    assert result.id==audit.verification_result_id and result.verified_by_type=='human'
    assert c2.revision==2 and c2.adopted

def test_new_evidence_appends_verification_revision_but_same_evidence_does_not(db,seed):
    from app.enrichment.verification import VerificationService
    c,e=claim_with_evidence(db,seed,index=2)
    first=VerificationService.verify(db,c,now=NOW)
    assert VerificationService.verify(db,c,now=NOW).id==first.id
    c2,e2=claim_with_evidence(db,seed,index=0)
    second=VerificationService.verify(db,c2,now=NOW)
    assert second.claim_revision==first.claim_revision+1 and db.get(m.VerificationResult,first.id)

def test_resolved_conflict_is_not_reopened_by_identical_sources(db,seed):
    from app.enrichment.conflict import ConflictDetectionService
    from app.enrichment.review import ReviewWorkflow
    a,e=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<0.8.4'},'AFFECTS_VERSION',0)
    b,e2=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<0.8.5'},'AFFECTS_VERSION',2)
    conflict=ConflictDetectionService.detect(db,seed.vuln.id,now=NOW)[0]
    c=db.get(m.Claim,conflict.claim_a_id)
    support=db.scalar(select(m.Evidence).where(m.Evidence.claim_id==c.id,m.Evidence.stance=='support'))
    ReviewWorkflow.resolve(db,task_id=conflict.review_task_id,actor='TEST',expected_revision=1,expected_claim_revision=1,
        request_key='TEST-resolved-conflict',status='confirmed',value=c.value_json,reason='TEST compared sources',evidence_ids=[support.id])
    before=db.scalar(select(func.count()).select_from(m.ReviewTask))
    ConflictDetectionService.detect(db,seed.vuln.id,now=NOW)
    assert db.scalar(select(func.count()).select_from(m.ReviewTask))==before

def test_verification_retains_value_snapshot(db,seed):
    from app.enrichment.verification import VerificationService
    c,e=claim_with_evidence(db,seed,index=2)
    result=VerificationService.verify(db,c,now=NOW)
    assert result.adopted_value==c.value_json and result.details['evaluated_value']==c.value_json

def test_typed_human_confirmation_cannot_change_to_unsupported_value(db,seed):
    from app.enrichment.review import ReviewWorkflow
    c,e=claim_with_evidence(db,seed,index=2)
    task=m.ReviewTask(claim_id=c.id,review_type='TEST',reason='TEST');db.add(task);db.flush()
    with pytest.raises(ValueError):
        ReviewWorkflow.resolve(db,task_id=task.id,actor='TEST',expected_revision=1,expected_claim_revision=1,request_key='TEST-bad-value',
            status='confirmed',value={**c.value_json,'version':'99.0.0'},reason='TEST unsupported value',evidence_ids=[e.id])

def test_ghsa_reprint_uses_same_vendor_origin(db,seed):
    from app.enrichment.evidence import EvidenceService
    c,e=claim_with_evidence(db,seed,index=2)
    original=seed.observations[1]
    obs=m.SourceObservation(source_id=original.source_id,raw_document_id=original.raw_document_id,external_id=original.external_id,
        record_type='vulnerability',retrieved_at=NOW,lineage_key=original.lineage_key,publisher=original.publisher,parse_status='parsed',
        normalizer_version='TEST-ghsa-origin',normalized_payload={'external_id':'GHSA-test-test-test','packages':[{'name':'vllm','ecosystem':'PyPI'}]})
    db.add(obs);db.flush()
    e2=EvidenceService.add(db,c,obs,c.value_json,{'json_pointer':'/test/ghsa'},evidence_type='normalized_version')
    assert e2.lineage_key=='github:vllm-project/vllm'

def test_stale_current_source_assertions_do_not_manufacture_live_conflict(db,seed):
    from datetime import timedelta
    from app.enrichment.conflict import ConflictDetectionService
    claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<0.8.4'},'AFFECTS_VERSION',0)
    claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<0.8.5'},'AFFECTS_VERSION',2)
    assert ConflictDetectionService.detect(db,seed.vuln.id,now=NOW+timedelta(days=31))==[]

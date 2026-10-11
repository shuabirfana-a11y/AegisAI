from datetime import timedelta
from uuid import uuid4
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from app.db import models as m
from conftest import NOW


def test_enrichment_job_retains_no_result_as_terminal_outcome(db,seed):
    job=m.EnrichmentJob(vulnerability_id=seed.vuln.id,enrichment_type='poc',status='no_result',
        scheduled_at=NOW,started_at=NOW,finished_at=NOW+timedelta(seconds=1),attempt=1,
        trace_id=str(uuid4()),duration_ms=1000,result={'sources_checked':['TEST_GITHUB'],'as_of':NOW.isoformat()})
    db.add(job);db.flush()
    assert db.get(m.EnrichmentJob,job.id).status=='no_result'
    assert job.result['sources_checked']==['TEST_GITHUB'] and job.error_code is None


def test_conflict_retains_both_claims_and_review_relationship(db,seed):
    other=m.Claim(claim_key='TEST-P7-OTHER',vulnerability_id=seed.vuln.id,claim_type='affected_version',
        predicate='is_affected',value_json={'raw_expression':'<=0.8.5'},scope_key=seed.claim.scope_key)
    db.add(other);db.flush()
    conflict=m.ConflictRecord(conflict_key='TEST-P7-CONFLICT',vulnerability_id=seed.vuln.id,
        claim_a_id=seed.claim.id,claim_b_id=other.id,scope_key=seed.claim.scope_key,
        conflict_type='VERSION_CONFLICT',detected_at=NOW,review_task_id=seed.review.id)
    db.add(conflict);db.flush()
    row=db.scalar(select(m.ConflictRecord))
    assert row.claim_a_id==seed.claim.id and row.claim_b_id==other.id and row.status=='open'


def test_rejected_claim_and_immutable_verification_can_be_stored(db,seed):
    seed.claim.verification_status='rejected'
    result=m.VerificationResult(claim_id=seed.claim.id,claim_revision=1,status='rejected',
        verification_method='static_rule',reason_summary='TEST unrelated scanner',verified_at=NOW,
        verified_by_type='system',verified_by_id='TEST',decision_key='TEST-REJECTED')
    db.add(result);db.flush()
    assert result.status==seed.claim.verification_status=='rejected'


@pytest.mark.parametrize('override',[{'duration_ms':-1},{'finished_at':None},{'finished_at':NOW-timedelta(seconds=1)}])
def test_enrichment_contract_refuses_invalid_terminal_timing(override):
    from app.enrichment.contracts import EnrichmentResult
    data=dict(task_id=uuid4(),enrichment_type='poc',target_id=uuid4(),status='SUCCESS',
        started_at=NOW,finished_at=NOW,duration_ms=0,trace_id=uuid4())
    with pytest.raises(ValidationError):EnrichmentResult(**{**data,**override})

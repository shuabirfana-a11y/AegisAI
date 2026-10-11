"""Hand-checked SYNTHETIC semantic inputs, never used as production provenance."""
from uuid import uuid4
from app.utils.time import utcnow
from app.agents.contracts import fingerprint
from app.agents.verification.schemas import (
    VerificationClaim,VerificationEvidence,VerificationRequest,VerificationSourceSnapshot,VerificationContext,
)


def claim(identifier='C1',expression='<=0.6',**changes):
    data=dict(claim_id=identifier,statement='SYNTHETIC vLLM affected '+expression,claim_type='AFFECTS_VERSION',
        source_task_id='lookup',value={'ecosystem':'PyPI','package':'vllm','raw_expression':expression},
        scope_key='PyPI:vllm',vulnerability_id='CVE-2099-9999001',package_identifier_id='pkg-vllm',
        evidence_ids=('E1',),origin='stored',claim_revision=1)
    data.update(changes)
    return VerificationClaim(**data)


def evidence(identifier='E1',claim_id='C1',expression='<=0.6',**changes):
    now=utcnow()
    data=dict(evidence_id=identifier,claim_id=claim_id,source_id=uuid4(),source_key='SYNTHETIC_vendor',
        source_type='official_vendor_advisory',source_name='SYNTHETIC vendor',source_time=now,
        content='affected '+expression,reference={'url':'https://example.invalid/SYNTHETIC','locator':{'line':1}},
        hash='a'*64,excerpt_hash='b'*64,authority_level='official',authority_scope='vulnerability affected versions',
        lineage_key='vendor-one',raw_document_id=uuid4(),observation_id=uuid4(),published_at=now,retrieved_at=now,
        observed_value={'ecosystem':'PyPI','package':'vllm','raw_expression':expression},scope_key='PyPI:vllm',
        vulnerability_id='CVE-2099-9999001',stance='support',directness='direct',
        evidence_type='official_vendor_advisory',is_current=True,integrity_status='VALID',details={'explicit':True})
    data.update(changes)
    return VerificationEvidence(**data)


def context(claims=None,evidence_items=None,task_type='evidence_verification',**request_changes):
    now=utcnow();run_id=uuid4();artifact_id=uuid4()
    req=VerificationRequest(source_run_id=run_id,source_task_id='lookup',source_artifact_id=artifact_id,
        request_key='SYNTHETIC-'+uuid4().hex,task_type=task_type,**request_changes)
    snap=VerificationSourceSnapshot(source_run_id=run_id,source_task_id='lookup',source_artifact_id=artifact_id,
        source_snapshot_as_of=now,artifact={'is_test':True},claims=tuple(claims if claims is not None else [claim()]),
        evidence=tuple(evidence_items if evidence_items is not None else [evidence()]))
    return VerificationContext(context_id=uuid4(),owner='SYNTHETIC-owner',request=req,
        request_hash=fingerprint(req.model_dump(mode='json')),source_snapshot_hash=fingerprint(snap.model_dump(mode='json')),
        evaluation_time=now,snapshot=snap)

"""Breaks caught: permissive identities, nonfinite outputs and unbounded artifacts."""
import importlib
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError


def schemas():
    try:
        return importlib.import_module('app.agents.verification.schemas')
    except ModuleNotFoundError:
        pytest.fail('Verification DTOs are not implemented')


def artifact(**changes):
    return dict(artifact_id=uuid4(), task_id='verify', run_id=uuid4(),
                source_run_id=uuid4(), source_artifact_id=uuid4(), source_snapshot_hash='a'*64,
                evaluation_time=datetime.now(timezone.utc), verification_status='PENDING',
                confidence=0, **changes)


@pytest.mark.parametrize('state', ['CONFIRMED','PENDING','CONFLICT','INSUFFICIENT_EVIDENCE','REJECTED'])
def test_verification_status_round_trip_preserves_identity(state):
    cls = schemas().VerificationArtifact
    value = artifact()
    value['verification_status'] = state
    item = cls(**value)
    loaded = cls.model_validate_json(item.model_dump_json())
    assert loaded.verification_status == state
    assert loaded.agent_id == 'verification_agent'
    assert loaded.artifact_id == item.artifact_id


@pytest.mark.parametrize('change', [dict(agent_id='investigation_agent'), dict(confidence=float('nan')),
    dict(confidence=float('inf')), dict(confidence=1.01), dict(verification_status='probably'),
    dict(evaluation_time=datetime(2026,10,8)), dict(unknown='silently ignored')])
def test_invalid_verification_output_is_rejected(change):
    cls = schemas().VerificationArtifact
    value = artifact()
    value.update(change)
    with pytest.raises(ValidationError):
        cls(**value)


def test_claim_keeps_requested_fields_and_rejects_unknown_type():
    cls = schemas().VerificationClaim
    item = cls(claim_id='C1',statement='SYNTHETIC vLLM affected',claim_type='AFFECTS_VERSION',
        source_task_id='lookup',related_entities={'component':'vllm'},scope_key='pkg:pypi/vllm',
        vulnerability_id='CVE-2099-9999001',value={'raw_expression':'<=0.6'})
    value = item.model_dump(mode='json')
    assert value['status'] == 'PENDING'
    assert value['source_task_id'] == 'lookup'
    assert value['related_entities']['component'] == 'vllm'
    with pytest.raises(ValidationError):
        cls(**{**value,'claim_type':'invented_security_claim'})


def test_evidence_is_traceable_without_using_model_authority():
    cls = schemas().VerificationEvidence
    now=datetime.now(timezone.utc)
    item=cls(evidence_id='E1',claim_id='C1',source_id=uuid4(),source_key='vendor',
        source_type='vendor_advisory',source_name='SYNTHETIC vendor',source_time=now,
        content='affected <=0.6',reference={'url':'https://example.invalid/notice','line':1},
        hash='b'*64,authority_score=0.95,directness_score=1.0,retrieved_at=now,
        observed_value={'raw_expression':'<=0.6'},scope_key='pkg:pypi/vllm')
    value=item.model_dump(mode='json')
    assert value['content'] == 'affected <=0.6'
    assert value['reference']['line'] == 1
    assert value['hash'] == 'b'*64
    with pytest.raises(ValidationError):
        cls(**{**value,'authority_score':float('inf')})


def test_nested_nonfinite_value_and_artifact_overflow_are_rejected():
    cls=schemas().VerificationArtifact
    with pytest.raises((ValidationError, ValueError)):
        cls(**artifact(model_calls=({'bad':float('nan')},)))
    with pytest.raises((ValidationError, ValueError)):
        cls(**artifact(warnings=('x'*600000,)))


def test_request_cannot_override_actor_or_supply_unknown_task():
    cls=schemas().VerificationRequest
    base=dict(source_run_id=uuid4(),source_task_id='lookup',source_artifact_id=uuid4(),request_key='verify-1')
    assert cls(**base).model_assistance is False
    for field in ({'actor':'other'}, {'task_type':'unknown'}, {'claim_ids':('C1','C1')}):
        with pytest.raises(ValidationError):
            cls(**{**base,**field})

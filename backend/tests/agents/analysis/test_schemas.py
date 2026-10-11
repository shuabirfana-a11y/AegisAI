"""Breaks caught: UNKNOWN converted to safety, invalid scores and forged decisions."""
import importlib
import json
import random
from uuid import uuid4
import pytest
from pydantic import ValidationError


def api():
    try:
        return importlib.import_module('app.agents.analysis.schemas')
    except ModuleNotFoundError:
        pytest.fail('Analysis schemas are missing')


def request_data():
    return dict(investigation_run_id=uuid4(),investigation_task_id='lookup',investigation_artifact_id=uuid4(),
                verification_run_id=uuid4(),verification_task_id='verify',verification_artifact_id=uuid4(),
                request_key='SYNTHETIC-'+uuid4().hex)


def test_schemas_roundtrip_preserves_unknown():
    model=api().RiskAssessment
    value=model(verification_status='CONFLICT')
    restored=model.model_validate_json(value.model_dump_json())
    assert restored.affected is None and restored.risk_level=='UNKNOWN'
    assert restored.priority=='REVIEW_REQUIRED' and restored.verification_status=='CONFLICT'


@pytest.mark.parametrize('change',[{'owner':'forged'},{'model_assistance':'true'},{'request_key':'  '},
    {'task_type':'unknown'},{'component_id':uuid4()}])
def test_request_rejects_extra_or_unscoped_inputs(change):
    with pytest.raises(ValidationError):api().AnalysisRequest(**{**request_data(),**change})


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-0.1,1.1])
def test_nonfinite_or_out_of_bounds_confidence_rejected(value):
    with pytest.raises(ValidationError):api().RiskAssessment(verification_status='CONFIRMED',confidence=value)


@pytest.mark.parametrize('change',[{'risk_level':'CRITICAL','priority':'P0'}, {'affected':False},
    {'affected':'false'}, {'risk_level':'LOW','priority':'DEFER','affected':False}])
def test_unverified_result_cannot_claim_risk_or_safety(change):
    with pytest.raises(ValidationError):api().RiskAssessment(verification_status='CONFLICT',**change)


def test_generated_unknown_roundtrips_keep_tristate_and_warnings():
    rng=random.Random(113)
    for _ in range(100):
        warning='SYNTHETIC-'+str(rng.randrange(1000000))
        value=api().RiskAssessment(verification_status='PENDING',warnings=(warning,))
        copy=api().RiskAssessment.model_validate_json(value.model_dump_json())
        assert copy.affected is None and copy.warnings==(warning,)
        assert json.loads(copy.model_dump_json())['confidence_kind']=='uncalibrated_heuristic'


def test_original_artifacts_parse_unchanged():
    from app.agents.investigation.schemas import InvestigationArtifact
    original=InvestigationArtifact(artifact_id=uuid4(),run_id=uuid4(),task_id='lookup',
        status='INSUFFICIENT_EVIDENCE',runtime_status='WAITING_REVIEW')
    api()
    assert InvestigationArtifact.model_validate_json(original.model_dump_json())==original

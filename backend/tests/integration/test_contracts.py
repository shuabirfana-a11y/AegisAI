from uuid import uuid4
import pytest
from pydantic import ValidationError

def test_request_rejects_duplicate_artifact_refs_and_external_payload():
    from app.integration.contracts import IntegrationRequest, ArtifactRef
    ref=ArtifactRef(run_id=uuid4(),task_id='lookup',artifact_id=uuid4(),schema_version='investigation-artifact-v1')
    with pytest.raises(ValidationError):IntegrationRequest(request_key='k',investigation=ref,verification=ref)
    with pytest.raises(ValidationError):IntegrationRequest(request_key='k',artifacts={'forged':True})

@pytest.mark.parametrize('key',['',' ','x'*151])
def test_request_key_bounded(key):
    from app.integration.contracts import IntegrationRequest
    with pytest.raises(ValidationError):IntegrationRequest(request_key=key)

def test_objective_profiles_are_closed():
    from app.integration.contracts import IntegrationRequest,ObjectiveContract
    with pytest.raises(ValidationError):IntegrationRequest(request_key='x',objective_profile='anything')
    with pytest.raises(ValidationError):ObjectiveContract(question='test',required_outcomes=('fake',))

def test_objective_respects_original_scope_not_model_plan():
    from app.integration.objective import from_planner_input
    from app.planner.schemas import PlannerInput
    from tests.planner.fixtures import cve_input
    raw=cve_input(target='CVE-2099-12345',question='我的部署是否受 CVE-2099-12345 影响，如何修复？')
    asset=uuid4();raw=raw.model_copy(update={'query':raw.query.model_copy(update={'asset_id':asset})})
    objective=from_planner_input(raw,'asset_impact_v1')
    assert objective.asset_id==asset and objective.targets==('CVE-2099-12345',)
    assert {'identity','asset','version_impact','remediation_status'}<=set(objective.required_outcomes)
    assert objective.version is None

def test_overview_unknown_is_bounded_scope_and_time_is_explicit():
    from app.integration.objective import from_planner_input
    from tests.planner.fixtures import cve_input
    objective=from_planner_input(cve_input(target='CVE-2099-12345',question='近7天 CVE-2099-12345 情报概览'),'overview_v1')
    assert objective.required_outcomes==('identity','overview')
    assert objective.window_days==7 and objective.requires_current is False

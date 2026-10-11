import inspect
import pytest
from pydantic import ValidationError


def test_default_registration_is_interface_only():
    from app.agents.registry import create_default_registry
    snapshot = create_default_registry().freeze()
    expected = {'investigation_agent', 'verification_agent', 'security_analysis_agent'}
    assert {r.contract.agent_id for r in snapshot.entries} == expected
    assert {t for r in snapshot.entries for t in r.contract.supported_tasks} == {
        'vulnerability_lookup','version_match','evidence_search','patch_analysis','risk_analysis'}
    assert all(inspect.isabstract(r.interface) and r.implementation is None for r in snapshot.entries)
    assert all(e['implementation_key'] == 'interface_only' for e in snapshot.metadata['agents'])


@pytest.mark.parametrize('overlap', [False, True])
def test_registration_rejects_duplicate_or_overlap(overlap):
    from app.agents.registry import create_default_registry
    from app.agents.contracts import AgentContract, AgentFrameworkError
    registry = create_default_registry()
    entry = registry.freeze().get('investigation_agent')
    values = entry.contract.model_dump()
    if overlap: values['agent_id'] = 'other_investigator'
    with pytest.raises(AgentFrameworkError, match='AGENT_REGISTRATION_CONFLICT'):
        registry.register(AgentContract(**values), entry.interface)


@pytest.mark.parametrize('changes', [
    {'timeout_seconds':0}, {'timeout_seconds':61}, {'timeout_seconds':True},
    {'allowed_tools':['missing_tool']}, {'input_schema':'arbitrary.module'},
    {'output_schema':'UnknownSchema'}, {'supported_tasks':['unknown_task']},
    {'supported_tasks':['evidence_search','evidence_search']},
    {'allowed_tools':['get_claims','get_claims']}, {'agent_id':'../agent'},
    {'description':''}, {'surprise':True}])
def test_contract_schema_and_tool_limits(changes):
    from app.agents.contracts import AgentContract
    from app.agents.registry import create_default_registry
    values = create_default_registry().freeze().get('verification_agent').contract.model_dump()
    with pytest.raises(ValidationError): AgentContract(**{**values, **changes})


def test_snapshot_cannot_change_after_registration():
    from app.agents.registry import create_default_registry
    registry = create_default_registry()
    snapshot = registry.freeze()
    metadata = snapshot.metadata
    metadata['agents'][0]['contract']['allowed_tools'].append('missing_tool')
    assert 'missing_tool' not in snapshot.metadata['agents'][0]['contract']['allowed_tools']
    assert snapshot.for_task('patch_analysis').contract.agent_id == 'investigation_agent'
    assert snapshot.get('missing') is None and snapshot.for_task('missing') is None
    assert len(snapshot.fingerprint) == 64


def test_interfaces_expose_only_abstract_capabilities():
    from app.agents.interfaces import InvestigationAgent, VerificationAgent, SecurityAnalysisAgent
    for cls, method in [(InvestigationAgent,'investigate'),(VerificationAgent,'verify'),(SecurityAnalysisAgent,'analyze')]:
        assert method in cls.__abstractmethods__
        with pytest.raises(TypeError): cls()

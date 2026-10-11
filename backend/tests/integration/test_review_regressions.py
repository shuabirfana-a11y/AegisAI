"""Independent review counterexamples; preserve actual failing examples."""
import pytest

@pytest.mark.parametrize('key',['X-API-Key','client_secret','Client-Secret','apiKey','Bearer-Token','X-Auth-Token','proxy-authorization'])
def test_i1_header_and_client_credential_keys_redacted(key):
    from app.integration.redaction import public_reference
    value=public_reference({'locator':{key:'PRIVATE_VALUE','line':1}})
    assert 'PRIVATE_VALUE' not in repr(value)
    assert value['locator']['line']==1

@pytest.mark.parametrize('url',['HTTPS://user:PRIVATE_PASS@example.invalid/a?token=PRIVATE_TOKEN',
    'HtTpS://user:PRIVATE_PASS@example.invalid/a?api_key=PRIVATE_TOKEN',
    ' HTTP://user:PRIVATE_PASS@example.invalid/a?signature=PRIVATE_TOKEN '])
def test_i1_mixed_case_urls_and_whitespace_are_redacted(url):
    from app.integration.redaction import public_reference
    result=public_reference({'url':url})
    assert all(s not in repr(result) for s in ('PRIVATE_PASS','PRIVATE_TOKEN','user:'))
    assert 'example.invalid/a' in result['url']

@pytest.mark.parametrize('days',[0,366,99999999])
def test_i2_recognized_unsupported_time_scope_never_becomes_unbounded_pass(days):
    from app.integration.objective import from_planner_input
    from tests.planner.fixtures import cve_input
    o=from_planner_input(cve_input(question=f'CVE-2099-9999001 最近{days}天情报概览'),'overview_v1')
    assert o.scope_gaps==('UNSUPPORTED_TIME_SCOPE',)
    assert o.window_days is None

@pytest.mark.parametrize('days',[1,365])
def test_i2_supported_window_boundaries_preserved(days):
    from app.integration.objective import from_planner_input
    from tests.planner.fixtures import cve_input
    o=from_planner_input(cve_input(question=f'CVE-2099-9999001 最近{days}天情报概览'),'overview_v1')
    assert o.window_days==days and not o.scope_gaps

def test_i2_unsupported_time_scope_blocks_actual_captured_context(engine,gate_chain):
    from app.integration.objective import from_planner_input
    from app.integration.snapshot import IntegrationSnapshotReader
    from app.integration.evaluator import IntegrationGateEvaluator
    from tests.integration.helpers import request
    from tests.planner.fixtures import cve_input
    cve=gate_chain.seed.cve
    objective=from_planner_input(cve_input(target=cve,question=f'{cve} 最近366天情报概览'),'overview_v1')
    context=IntegrationSnapshotReader(engine).capture(request(gate_chain),actor=gate_chain.seed.actor)
    # Deliberate test-only scope mutation on an actually captured service chain.
    result=IntegrationGateEvaluator().evaluate(context.model_copy(update={'objective':objective}))
    assert result.status=='REPLAN_REQUIRED'
    assert result.blocking_issues==('UNSUPPORTED_TIME_SCOPE',)
    assert not result.final_result_references

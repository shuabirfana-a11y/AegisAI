"""Synthetic metadata tests; never security ground truth."""
from copy import deepcopy
import pytest


def analyze(*args, **kwargs):
    from scripts.probe_investigation_failures import analyze_case
    return analyze_case(*args, **kwargs)


def snapshot():
    return {'id':'SYNTHETIC-investigation','question':'SYNTHETIC question',
        'execution_mode':'REAL','model':'SYNTHETIC-compatible',
        'data_origin':'SYNTHETIC_CONTROL','current_stage':'FAILED','last_work_stage':'INTEGRATING',
        'objective':{'asset_id':None,'version':'2.5.1'},
        'selected_artifact_id':'base','plan_tasks':[{'task_id':'lookup','tools':['get_vulnerability']}],
        'artifacts':[{'artifact_id':'base','task_id':'lookup','version_match':None},
                     {'artifact_id':'version','task_id':'version','version_match':{'status':'UNKNOWN'}}],
        'asset_snapshot':{'context_status':'MISSING','deployed_version':None},
        'verification':{'verification_status':'INSUFFICIENT_EVIDENCE','claims':[],'conflicts':[]},
        'analysis':{'risk_level':'UNKNOWN','version_match_status':'UNKNOWN'},
        'gate':{'integration_id':'SYNTHETIC-gate','status':'FAILED','checks':[
            {'gate':'objective','code':'OBJECTIVE_VERSION_MISMATCH','blocking':'FATAL','message':'scope differs','refs':[]}]}}


def test_preserves_gate_failure_and_original_unknown_without_mutating_input():
    value=snapshot(); before=deepcopy(value)
    result=analyze(value)
    assert result['gate_status']=='FAILED'
    assert result['analysis']['risk_level']=='UNKNOWN'
    assert result['gate_rules'][0]['blocking']=='FATAL'
    assert value==before


def test_missing_gate_is_reported_as_not_executed_instead_of_invented_verdict():
    value=snapshot(); value.update(gate=None,last_work_stage='INVESTIGATING')
    result=analyze(value)
    assert result['gate_status'] is None and not result['gate_executed']
    assert result['failed_stage']=='INVESTIGATING'


def test_upstream_stop_keeps_native_reason_without_claiming_a_gate_decision():
    value=snapshot(); value.update(gate=None,planner_validation='VALIDATED',
        last_work_stage='INVESTIGATING',chain_error_code='SYNTHETIC_REQUIRED_TASK_STOP',
        upstream_unresolved_items=['SYNTHETIC_BLOCKED_DEPENDENCY'])
    result=analyze(value)
    assert result['chain_error_code']=='SYNTHETIC_REQUIRED_TASK_STOP'
    assert result['classification']=='UPSTREAM_NOT_INTEGRATED'
    assert result['upstream_unresolved_items']==['SYNTHETIC_BLOCKED_DEPENDENCY']
    assert result['gate_status'] is None


def test_separate_version_observation_is_linked_without_merging_or_promoting_it():
    result=analyze(snapshot())
    assert result['version_observation_handoff']['observed_artifact_ids']==['version']
    assert result['version_observation_handoff']['selected_has_version'] is False
    assert result['classification']=='C_AND_DATA'


def test_valid_inventory_does_not_erase_remaining_evidence_blockers():
    value=snapshot(); value['asset_snapshot']={'context_status':'RESOLVED','deployed_version':'2.5.1'}
    value['gate'].update(status='REPLAN_REQUIRED',checks=[
        {'gate':'freshness','code':'UNRESOLVED_ANALYSIS','blocking':'REPLAN','message':'unknown','refs':[]}])
    result=analyze(value)
    assert result['gate_status']=='REPLAN_REQUIRED'
    assert 'asset_id' not in result['missing_information']
    assert 'eligible claim-bound evidence' in result['missing_information']


def test_recorded_conflict_is_not_falsely_described_as_verified_conflict():
    value=snapshot(); value['artifacts'][0]['conflicts']=[{'status':'open'}]
    result=analyze(value)
    assert result['recorded_source_conflict_count']==1
    assert result['verified_conflict_count']==0


def test_inherited_conflict_observations_are_not_counted_as_independent_records():
    value=snapshot(); conflict={'id':'SYNTHETIC-conflict','status':'open'}
    for artifact in value['artifacts']:
        artifact['conflicts']=[dict(conflict)]
    assert analyze(value)['recorded_source_conflict_count']==1


def test_blocking_rules_link_verification_and_risk_artifacts_too():
    value=snapshot()
    value['verification']['artifact_id']='SYNTHETIC-verification'
    value['analysis']['artifact_id']='SYNTHETIC-risk'
    refs=analyze(value)['gate_rules'][0]['involved_artifacts']
    assert 'SYNTHETIC-verification' in refs and 'SYNTHETIC-risk' in refs


def test_redacts_untrusted_question_and_task_identifiers():
    value=snapshot(); secret='sk-'+'SYNTHETIC_PRIVATE_TEXT_1234567890'
    value['question']=secret; value['plan_tasks'][0]['task_id']=secret
    result=analyze(value)
    assert secret not in str(result)


def test_rejects_mock_measurement_in_real_scene_report():
    value=snapshot(); value['execution_mode']='MOCK'
    with pytest.raises(ValueError,match='REAL_EXECUTION_REQUIRED'):
        analyze(value)


def test_successful_overview_retains_pending_claims_and_is_not_security_accuracy():
    value=snapshot(); value['gate'].update(status='PASS_WITH_WARNINGS',checks=[])
    result=analyze(value)
    assert result['failed_stage'] is None
    assert result['verification']['verification_status']=='INSUFFICIENT_EVIDENCE'
    assert result['security_accuracy_evaluated'] is False

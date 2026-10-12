"""Synthetic metadata tests; never security ground truth."""
from copy import deepcopy
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4
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


@pytest.mark.parametrize('stage',['VERIFYING','ANALYZING'])
def test_started_run_without_artifact_is_still_collectable(monkeypatch,stage):
    from scripts.probe_investigation_failures import collect_snapshot
    from app.orchestration.store import PostgresInvestigationStore
    from app.agents.verification.reader import VerificationReader
    from app.agents.analysis.reader import AnalysisReader
    run_id=uuid4()
    ctx=SimpleNamespace(logical_investigation_id=uuid4(),planner_run_id=None,
        investigation_run_id=None,verification_run_id=run_id if stage=='VERIFYING' else None,
        analysis_run_id=run_id if stage=='ANALYZING' else None,integration_result_id=None,
        original_request=SimpleNamespace(user_query='SYNTHETIC incomplete run'),
        current_stage=stage,events=[SimpleNamespace(stage=stage)],error_code='SYNTHETIC_STOP',
        unresolved_items=('SYNTHETIC_MISSING_ARTIFACT',),
        resolved_scope=SimpleNamespace(objective=SimpleNamespace(model_dump=lambda **kw:{})))
    monkeypatch.setattr(PostgresInvestigationStore,'read_audit',lambda *a,**kw:(ctx,{}))
    monkeypatch.setattr(VerificationReader,'read',lambda *a,**kw:SimpleNamespace(artifacts=()))
    monkeypatch.setattr(AnalysisReader,'read',lambda *a,**kw:SimpleNamespace(artifacts=()))
    got=collect_snapshot(None,str(ctx.logical_investigation_id),'SYNTHETIC-owner',{'data_origin':'SYNTHETIC_CONTROL'})
    assert got['verification'] is None and got['analysis'] is None
    assert got['run_ids']['verification' if stage=='VERIFYING' else 'analysis']==str(run_id)
    assert got['last_work_stage']==stage and got['gate'] is None


def test_diagnostic_read_failure_does_not_prevent_following_independent_case(monkeypatch):
    import scripts.probe_investigation_failures as probe
    seen=[]
    def collect(*args):
        seen.append(args[1])
        if args[1]=='SYNTHETIC-missing':raise LookupError('SYNTHETIC reader failure')
        return snapshot()
    monkeypatch.setattr(probe,'collect_snapshot',collect)
    first={'receipt':{'investigation_id':'SYNTHETIC-missing'},'diagnostic':None}
    next_case={'receipt':{'investigation_id':'SYNTHETIC-next'},'diagnostic':None}
    for entry in (first,next_case):probe.add_diagnostic(entry,None,'SYNTHETIC-owner',{})
    assert first['diagnostic'] is None
    assert first['diagnostic_error']=='OWNED_DIAGNOSTIC_UNAVAILABLE'
    assert next_case['diagnostic']['gate_status']=='FAILED'
    assert seen==['SYNTHETIC-missing','SYNTHETIC-next']


def inventory_case():
    return {'data_origin':'REAL_SOURCE_WITH_DEMO_INVENTORY',
            'request':{'asset_scope':{'asset_id':str(uuid4())}}}


def mock_asset_read(monkeypatch,owner):
    asset=SimpleNamespace(owner_principal=owner,is_demo=True,deleted_at=None)
    @contextmanager
    def transaction(engine):
        yield SimpleNamespace(get=lambda *a:asset)
    monkeypatch.setattr('app.db.session.transaction',transaction)


def test_inventory_actor_cannot_be_adopted_from_another_owners_asset(monkeypatch):
    from scripts.probe_investigation_failures import resolve_case_actor
    mock_asset_read(monkeypatch,'SYNTHETIC-owner-B')
    with pytest.raises(ValueError,match='ASSET_OWNERSHIP_MISMATCH'):
        resolve_case_actor(None,inventory_case(),'SYNTHETIC-owner-A')


def test_inventory_requires_independently_configured_owner():
    from scripts.probe_investigation_failures import resolve_case_actor
    with pytest.raises(ValueError,match='AUTHORIZED_OWNER_REQUIRED'):
        resolve_case_actor(None,inventory_case(),None)


def test_matching_owner_is_preserved_without_adopting_new_identity(monkeypatch):
    from scripts.probe_investigation_failures import resolve_case_actor
    mock_asset_read(monkeypatch,'SYNTHETIC-owner-A')
    assert resolve_case_actor(None,inventory_case(),'SYNTHETIC-owner-A')=='SYNTHETIC-owner-A'


def test_source_only_case_uses_separate_temporary_actor():
    from scripts.probe_investigation_failures import resolve_case_actor
    assert resolve_case_actor(None,{'request':{}},None).startswith('phase12d2-')

"""Rule counterexamples use captured real context, then explicit test-only mutations."""
from datetime import timedelta
from uuid import uuid4
import pytest
from app.integration.contracts import GateCheck
from tests.integration.helpers import request

@pytest.fixture
def context(engine,gate_chain):
    from app.integration.snapshot import IntegrationSnapshotReader
    return IntegrationSnapshotReader(engine).capture(request(gate_chain,objective_profile='asset_risk_v1'),actor=gate_chain.seed.actor)

def evaluate(ctx):
    from app.integration.evaluator import IntegrationGateEvaluator
    return IntegrationGateEvaluator().evaluate(ctx)

def test_complete_real_context_pass_and_deterministic(context):
    result=evaluate(context)
    assert result.status=='PASS', result.blocking_issues
    assert {x.gate for x in result.checks}=={'completion','integrity','evidence','consistency','objective','freshness'}
    assert evaluate(context)==result and result.final_result_references
    assert all(c.status=='SATISFIED' for c in result.objective_coverage)

@pytest.mark.parametrize('stage',['investigation','verification','analysis'])
def test_missing_required_stage_replans(context,stage):
    got=evaluate(context.model_copy(update={stage:None}))
    assert got.status=='REPLAN_REQUIRED' and not got.final_result_references

@pytest.mark.parametrize('state',['BLOCKED','WAITING_REVIEW','READY','FAILED'])
def test_required_incomplete_never_passes(context,state):
    t=context.tasks[0].model_copy(update={'status':state,'error_codes':('NOT_FOUND',) if state=='FAILED' else ()})
    ctx=context.model_copy(update={'tasks':(t,*context.tasks[1:])})
    assert evaluate(ctx).status=='REPLAN_REQUIRED'

@pytest.mark.parametrize('code',['RUN_CANCELLED','TASK_CLEANUP_FAILED','WORKER_PROTOCOL_ERROR','UNEXPECTED_EXECUTOR_ERROR'])
def test_corrupt_execution_and_cancellation_fail(context,code):
    t=context.tasks[0].model_copy(update={'status':'FAILED','error_codes':(code,)})
    assert evaluate(context.model_copy(update={'tasks':(t,*context.tasks[1:])})).status=='FAILED'

def test_optional_recoverable_source_timeout_warns(context):
    from app.integration.contracts import TaskExecution
    t=TaskExecution(run_id=context.investigation.run_id,task_id='extra_source',semantic_type='evidence_search',
        status='FAILED',run_status='failed',required=False,error_codes=('TASK_TIMEOUT',))
    result=evaluate(context.model_copy(update={'tasks':(*context.tasks,t)}))
    assert result.status=='PASS_WITH_WARNINGS' and 'OPTIONAL_TASK_INCOMPLETE' in result.warnings

def test_dangling_evidence_reference_fails(context):
    r=context.analysis;factor=r.risk_factors[0].model_copy(update={'evidence_ids':('invented',)})
    r=r.model_copy(update={'risk_factors':(factor,*r.risk_factors[1:])})
    result=evaluate(context.model_copy(update={'analysis':r}))
    assert result.status=='FAILED' and 'EVIDENCE_REFERENCE_INVALID' in result.blocking_issues

def test_missing_claim_support_replans(context):
    v=context.verification
    checks=tuple(c.model_copy(update={'supporting_evidence_ids':()}) if c.claim.claim_type=='AFFECTS_VERSION' else c for c in v.claims)
    result=evaluate(context.model_copy(update={'verification':v.model_copy(update={'claims':checks})}))
    assert result.status=='REPLAN_REQUIRED' and 'CONFIRMED_CLAIM_WITHOUT_SUPPORT' in result.replan_reasons

def test_conflict_preserved_and_priority_combines_reasons(context):
    v=context.verification.model_copy(update={'verification_status':'CONFLICT'})
    r=context.analysis.model_copy(update={'verification_status':'CONFLICT','affected':None,'risk_level':'UNKNOWN',
        'priority':'REVIEW_REQUIRED','asset_match_status':'UNKNOWN','version_match_status':'UNKNOWN',
        'asset_match_result':context.analysis.asset_match_result.model_copy(update={'status':'UNKNOWN'}),
        'version_match_result':context.analysis.version_match_result.model_copy(update={'status':'UNKNOWN','affected':None})})
    ctx=context.model_copy(update={'verification':v,'analysis':r})
    got=evaluate(ctx)
    assert got.status=='HUMAN_REVIEW_REQUIRED' and got.human_review_reasons and got.replan_reasons

def test_conflict_cannot_turn_into_confirmed_risk(context):
    v=context.verification.model_copy(update={'verification_status':'CONFLICT'})
    assert evaluate(context.model_copy(update={'verification':v})).status=='FAILED'

@pytest.mark.parametrize('kind',['unknown_safe','candidate_exploit','unsupported_fix','rejected_impact','not_matched_affected','wrong_version','fake_action_evidence'])
def test_local_success_does_not_hide_cross_agent_contradictions(context,kind):
    r=context.analysis;v=context.verification
    if kind=='unknown_safe':r=r.model_copy(update={'affected':False,'version_match_status':'UNKNOWN','risk_level':'LOW','priority':'DEFER'})
    if kind=='candidate_exploit':r=r.model_copy(update={'exploitation_signal':r.exploitation_signal.model_copy(update={'status':'KNOWN_EXPLOITED','claim_ids':()})})
    if kind=='unsupported_fix':
        action=r.recommended_actions[0].model_copy(update={'fixed_version':'99.99','claim_ids':(),'evidence_ids':()})
        r=r.model_copy(update={'recommended_actions':(action,*r.recommended_actions[1:])})
    if kind=='rejected_impact':v=v.model_copy(update={'claims':tuple(c.model_copy(update={'status':'REJECTED'}) if c.claim.claim_type=='AFFECTS_VERSION' else c for c in v.claims)})
    if kind=='not_matched_affected':r=r.model_copy(update={'asset_match_status':'NOT_MATCHED'})
    if kind=='wrong_version':r=r.model_copy(update={'version':'99.99'})
    if kind=='fake_action_evidence':r=r.model_copy(update={'recommended_actions':(r.recommended_actions[0].model_copy(update={'evidence_ids':('missing',)}),)})
    assert evaluate(context.model_copy(update={'analysis':r,'verification':v})).status=='FAILED'

def test_unknown_risk_does_not_mean_safe(context):
    r=context.analysis.model_copy(update={'risk_level':'UNKNOWN','priority':'REVIEW_REQUIRED','unresolved_items':('VERIFIED_SEVERITY_MISSING',)})
    got=evaluate(context.model_copy(update={'analysis':r}))
    assert got.status=='REPLAN_REQUIRED' and context.analysis.affected is True

def test_overview_can_disclose_unknown_without_claiming_safety(context):
    r=context.analysis.model_copy(update={'risk_level':'UNKNOWN','priority':'REVIEW_REQUIRED','affected':None,
        'asset_match_status':'UNKNOWN','version_match_status':'UNKNOWN','unresolved_items':('VERSION_MATCH_UNKNOWN',),
        'asset_match_result':context.analysis.asset_match_result.model_copy(update={'status':'UNKNOWN'}),
        'version_match_result':context.analysis.version_match_result.model_copy(update={'status':'UNKNOWN','affected':None})})
    objective=context.objective.model_copy(update={'required_outcomes':('identity','overview')})
    ctx=context.model_copy(update={'objective':objective,'request':context.request.model_copy(update={'objective_profile':'overview_v1'}),'analysis':r})
    assert evaluate(ctx).status=='PASS_WITH_WARNINGS'

def test_description_only_does_not_answer_asset_question(context):
    assert evaluate(context.model_copy(update={'analysis':None,'asset_snapshot':None})).status=='REPLAN_REQUIRED'

@pytest.mark.parametrize('field',['asset_id','version','component_id'])
def test_objective_scope_mismatch_is_rejected(context,field):
    obj=context.objective.model_copy(update={field:'99.99' if field=='version' else uuid4()})
    assert evaluate(context.model_copy(update={'objective':obj})).status=='FAILED'

def test_missing_original_scope_replans(context):
    assert evaluate(context.model_copy(update={'objective':None})).status=='REPLAN_REQUIRED'

def test_recent_query_uses_publication_not_just_fresh_retrieval(context):
    old=context.evaluation_time-timedelta(days=10)
    v=context.verification.model_copy(update={'supporting_evidence':tuple(e.model_copy(update={'published_at':old}) for e in context.verification.supporting_evidence)})
    obj=context.objective.model_copy(update={'window_days':7})
    got=evaluate(context.model_copy(update={'objective':obj,'verification':v}))
    assert got.status=='REPLAN_REQUIRED' and 'REQUEST_TIME_WINDOW_NOT_COVERED' in got.replan_reasons

def test_static_advisory_publication_old_is_not_universally_stale(context):
    old=context.evaluation_time-timedelta(days=100)
    v=context.verification.model_copy(update={'supporting_evidence':tuple(e.model_copy(update={'published_at':old}) for e in context.verification.supporting_evidence)})
    assert evaluate(context.model_copy(update={'verification':v})).status=='PASS'

@pytest.mark.parametrize('kind,code',[('missing','EVIDENCE_TIME_MISSING'),('future','SOURCE_TIME_INCONSISTENT'),('stale','REQUIRED_EVIDENCE_STALE')])
def test_evidence_times_have_distinct_reasons(context,kind,code):
    now=context.evaluation_time
    time=None if kind=='missing' else now+timedelta(minutes=6) if kind=='future' else now-timedelta(days=31)
    v=context.verification.model_copy(update={'supporting_evidence':tuple(e.model_copy(update={'retrieved_at':time}) for e in context.verification.supporting_evidence)})
    got=evaluate(context.model_copy(update={'verification':v}))
    assert got.status=='REPLAN_REQUIRED' and code in got.replan_reasons

def test_current_inventory_and_verification_have_separate_ttl(context):
    obj=context.objective.model_copy(update={'requires_current':True})
    ctx=context.model_copy(update={'objective':obj,'evaluation_time':context.evaluation_time+timedelta(days=2)})
    got=evaluate(ctx)
    assert {'VERIFICATION_STALE','INVENTORY_SNAPSHOT_STALE'}<=set(got.replan_reasons)

@pytest.mark.parametrize('blocks,expected',[((), 'PASS'),(('NONE',),'PASS_WITH_WARNINGS'),(('REPLAN',),'REPLAN_REQUIRED'),
    (('REPLAN','HUMAN'),'HUMAN_REVIEW_REQUIRED'),(('HUMAN','FATAL'),'FAILED')])
def test_priority_is_explicit_and_retains_all_blockers(context,blocks,expected):
    extra=tuple(GateCheck(gate='objective',code='TEST_'+b,outcome='WARNING' if b=='NONE' else 'BLOCKED',blocking=b,message='synthetic issue') for b in blocks)
    got=evaluate(context.model_copy(update={'capture_checks':extra}))
    assert got.status==expected
    assert all('TEST_'+b in (*got.blocking_issues,*got.warnings) for b in blocks)

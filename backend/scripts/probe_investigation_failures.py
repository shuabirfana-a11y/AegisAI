"""Phase12D.2 owned HTTP scenarios and read-only failure diagnostics, not a benchmark."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from uuid import UUID, uuid4
import argparse
import json
import os
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.investigation_api.projection import public_copy

RULE_NEEDS = {
    'ASSET_SCOPE_MISSING': ('C', 'Owner-bound asset and exact component context'),
    'OBJECTIVE_VERSION_MISMATCH': ('C', 'Original version and deployed inventory version must agree'),
    'OBJECTIVE_PACKAGE_MISMATCH': ('C', 'Original package and resolved inventory identity must agree'),
    'OBJECTIVE_COMPONENT_MISMATCH': ('C', 'Select the exact original inventory component'),
    'OBJECTIVE_ASSET_MISMATCH': ('C', 'Keep original owner-bound asset identity'),
    'REQUIRED_TASK_INCOMPLETE': ('DATA', 'Complete the required upstream result without changing WAITING_REVIEW'),
    'OBJECTIVE_NOT_COVERED': ('DATA', 'Provide evidence/context for the original required outcome'),
    'UNRESOLVED_ANALYSIS': ('DATA', 'Eligible version-impact evidence and resolved inventory'),
    'UNRESOLVED_VERIFICATION': ('DATA', 'Current direct claim-bound evidence'),
    'SOURCE_CONFLICT': ('DATA', 'Independently review disagreeing current same-scope source values'),
}


def analyze_case(snapshot):
    """Describe native results; never replace decisions, merge artifacts, or infer safety."""
    if snapshot['execution_mode'] != 'REAL':
        raise ValueError('REAL_EXECUTION_REQUIRED')
    gate = snapshot.get('gate')
    artifacts = snapshot.get('artifacts', [])
    selected = snapshot.get('selected_artifact_id')
    chosen = next((a for a in artifacts if a['artifact_id'] == selected), {})
    observed = [a['artifact_id'] for a in artifacts if a.get('version_match')]
    dropped = bool(observed and not chosen.get('version_match'))
    verification = snapshot.get('verification') or {}
    analysis = snapshot.get('analysis') or {}
    asset = snapshot.get('asset_snapshot') or {}
    missing = []
    if asset.get('context_status') == 'MISSING':
        missing.append('asset_id')
    elif asset and asset.get('context_status') != 'RESOLVED':
        missing.append('resolved exact component inventory')
    if verification and verification.get('verification_status') != 'CONFIRMED':
        missing.append('eligible claim-bound evidence')
    if dropped:
        missing.append('handoff of requested version task observation')
    artifact_ids = list(dict.fromkeys([a['artifact_id'] for a in artifacts] +
        [a['artifact_id'] for a in (verification, analysis) if a.get('artifact_id')]))
    conflicts = {json.dumps(c,sort_keys=True) for a in artifacts for c in a.get('conflicts', [])}
    checks = []
    for check in (gate or {}).get('checks', []):
        if check['blocking'] == 'NONE':
            continue
        category, need = RULE_NEEDS.get(check['code'], ('UNCLASSIFIED', 'Inspect native check and original referenced artifacts'))
        checks.append({**check, 'classification': category, 'needs': need,
                       'involved_artifacts': artifact_ids,
                       'selected_investigation_artifact_id': selected})
    classes = {c['classification'] for c in checks}
    if dropped:
        classes.add('C')
    if 'eligible claim-bound evidence' in missing:
        classes.add('DATA')
    classification = 'C_AND_DATA' if {'C', 'DATA'} <= classes else '_AND_'.join(sorted(classes)) or 'NO_BLOCKING_FINDING'
    if gate is None and snapshot.get('planner_validation') == 'PLANNING_FAILED':
        classification = 'PLANNER_OUTPUT_OR_PROVIDER'
        missing.append('validated plan before downstream business diagnosis')
    elif gate is None and snapshot.get('planner_validation') == 'VALIDATED':
        classification = 'UPSTREAM_NOT_INTEGRATED'
    status = (gate or {}).get('status')
    accepted = status in ('PASS', 'PASS_WITH_WARNINGS')
    value = {
        'schema_version': 'phase12d2-failure-v1', 'benchmark': False,
        'security_accuracy_evaluated': False,
        'id': snapshot['id'], 'question': snapshot['question'], 'model': snapshot['model'],
        'execution_mode': 'REAL', 'data_origin': snapshot['data_origin'],
        'failed_stage': None if accepted else snapshot.get('last_work_stage'),
        'gate_executed': gate is not None, 'gate_status': status,
        'reason': 'See preserved native checks and source artifacts; no verdict was repaired',
        'classification': classification, 'missing_information': missing,
        'possible_fix': 'C/business changes require separate authorization; complete DATA evidence/context first',
        'planner_run_id': snapshot.get('planner_run_id'), 'integration_id': (gate or {}).get('integration_id'),
        'planner_validation': snapshot.get('planner_validation'),
        'planner_error_codes': snapshot.get('planner_error_codes', []),
        'chain_error_code': snapshot.get('chain_error_code'),
        'upstream_unresolved_items': snapshot.get('upstream_unresolved_items', []),
        'run_ids': snapshot.get('run_ids', {}),
        'artifact_availability': snapshot.get('artifact_availability', {}),
        'objective': snapshot.get('objective'), 'plan_tasks': snapshot.get('plan_tasks', []),
        'gate_rules': checks, 'asset_snapshot': asset,
        'artifact_states': [{k: a.get(k) for k in ('artifact_id','task_id','status','runtime_status')} for a in artifacts],
        'verification': verification, 'analysis': snapshot.get('analysis'),
        'version_observation_handoff': {'selected_artifact_id': selected,
            'selected_has_version': bool(chosen.get('version_match')), 'observed_artifact_ids': observed},
        'recorded_source_conflict_count': len(conflicts),
        'verified_conflict_count': len(verification.get('conflicts', [])),
    }
    return public_copy(value)


def collect_snapshot(engine, investigation_id, actor, case):
    from sqlalchemy import select
    from app.db import models as m
    from app.db.session import transaction
    from app.orchestration.store import PostgresInvestigationStore
    from app.planner.trace import PlannerTraceStore
    from app.agents.investigation.reader import InvestigationReader
    from app.agents.verification.reader import VerificationReader
    from app.agents.analysis.reader import AnalysisReader
    from app.agents.analysis.context_store import AnalysisContextStore
    from app.integration.reader import IntegrationReader
    context, _ = PostgresInvestigationStore(engine).read_audit(investigation_id, actor=actor)
    audit = PlannerTraceStore(engine).read(context.planner_run_id, actor) if context.planner_run_id else None
    model = audit.model.model if audit else None
    mode = 'REAL' if audit and not audit.model.is_mock and audit.attempts else 'UNCONFIRMED'
    raw = audit.generated_plan.model_dump(mode='json') if audit and hasattr(audit.generated_plan,'model_dump') else audit.generated_plan if audit else None
    tasks = [{'task_id': t['task_id'], 'type': t['type'], 'dependencies': t.get('dependencies', []),
              'tools': [s['name'] for s in t['input_data']['steps']]} for t in (raw or {}).get('tasks', [])]
    artifacts = [a.model_dump(mode='json') for a in InvestigationReader(engine).read(
        context.investigation_run_id, actor=actor).artifacts] if context.investigation_run_id else []
    verification = None; v = None; available = {'investigation':len(artifacts),'verification':0,'analysis':0}
    if context.verification_run_id:
        found = VerificationReader(engine).read(context.verification_run_id, actor=actor)
        available['verification'] = len(found.artifacts)
        v = found.artifacts[0] if found.artifacts else None
    if v is not None:
        verification = {'artifact_id': str(v.artifact_id), 'verification_status': v.verification_status,
            'execution_status': v.execution_status,
            'claim_status_counts': dict(Counter(c.status for c in v.claims)),
            'claims': [{'claim_id': c.claim.claim_id, 'claim_type': c.claim.claim_type, 'status': c.status,
                'reason': c.reason_summary, 'supporting_evidence_ids': list(c.supporting_evidence_ids),
                'conflicting_evidence_ids': list(c.conflicting_evidence_ids),
                'exclusions': c.score_components.get('excluded', [])} for c in v.claims],
            'conflicts': [c.model_dump(mode='json') for c in v.conflicts],
            'unresolved_items': list(v.unresolved_items)}
    risk = None; asset = None; selected = None; r = None
    if context.analysis_run_id:
        found = AnalysisReader(engine).read(context.analysis_run_id, actor=actor)
        available['analysis'] = len(found.artifacts)
        r = found.artifacts[0] if found.artifacts else None
    if r is not None:
        risk = {k: r.model_dump(mode='json')[k] for k in
                ('artifact_id','risk_level','priority','verification_status','version_match_status','affected','unresolved_items')}
        with transaction(engine) as db:
            run = db.get(m.AgentRun, context.analysis_run_id)
            cid = run.details['runtime_v1']['plan']['route']['analysis_v1']['context_id']
        saved = AnalysisContextStore(engine).read(cid, actor=actor)
        asset = saved.inputs.asset.model_dump(mode='json')
        selected = str(saved.request.investigation_artifact_id)
    elif v is not None:
        selected = str(v.source_artifact_id)
    gate = IntegrationReader(engine).read(context.integration_result_id, actor=actor).model_dump(mode='json') if context.integration_result_id else None
    work = [e.stage for e in context.events if e.stage in
            ('PLANNING','INVESTIGATING','VERIFYING','ANALYZING','INTEGRATING')]
    return {'id': str(context.logical_investigation_id), 'question': context.original_request.user_query,
        'execution_mode': mode, 'model': model, 'data_origin': case['data_origin'],
        'current_stage': context.current_stage, 'last_work_stage': work[-1] if work else context.current_stage,
        'planner_run_id': str(context.planner_run_id) if context.planner_run_id else None,
        'planner_validation': audit.validation_status if audit else None,
        'planner_error_codes': list(dict.fromkeys(i.code for attempt in audit.attempts for i in attempt.issues)) if audit else [],
        'chain_error_code': context.error_code,
        'upstream_unresolved_items': list(context.unresolved_items),
        'run_ids': {key:str(value) if value else None for key,value in (
            ('investigation',context.investigation_run_id),('verification',context.verification_run_id),
            ('analysis',context.analysis_run_id))},
        'artifact_availability': available,
        'objective': context.resolved_scope.objective.model_dump(mode='json'),
        'selected_artifact_id': selected, 'plan_tasks': tasks, 'artifacts': artifacts,
        'asset_snapshot': asset, 'verification': verification, 'analysis': risk, 'gate': gate}


def add_diagnostic(entry, engine, actor, case):
    """An unavailable read is explicit and does not stop the next independent case."""
    if not entry['receipt'].get('investigation_id'):
        return
    try:
        snapshot = collect_snapshot(engine,entry['receipt']['investigation_id'],actor,case)
        if snapshot['execution_mode']=='REAL':
            entry['diagnostic']=analyze_case(snapshot)
        else:
            entry['diagnostic_error']='REAL_EXECUTION_UNCONFIRMED'
    except Exception:
        entry['diagnostic_error']='OWNED_DIAGNOSTIC_UNAVAILABLE'


class SceneAdmissionError(ValueError):
    pass


def resolve_case_actor(engine, case, configured_owner):
    """Authority comes from operator configuration, never the target inventory row."""
    asset_id=case.get('request',{}).get('asset_scope',{}).get('asset_id')
    if not asset_id:
        return 'phase12d2-'+uuid4().hex
    if not isinstance(configured_owner,str) or not configured_owner.strip():
        raise SceneAdmissionError('AUTHORIZED_OWNER_REQUIRED')
    from app.orchestration.contracts import valid_actor
    from app.db import models as m
    from app.db.session import transaction
    try:
        valid_actor(configured_owner)
        id=UUID(asset_id)
    except ValueError:
        raise SceneAdmissionError('INVALID_CONFIGURED_OWNER_OR_ASSET_ID') from None
    with transaction(engine) as db:
        asset=db.get(m.Asset,id)
        if asset is None or asset.deleted_at:
            raise SceneAdmissionError('FIXED_ASSET_NOT_AVAILABLE')
        if asset.owner_principal!=configured_owner:
            raise SceneAdmissionError('ASSET_OWNERSHIP_MISMATCH')
        if case['data_origin']=='REAL_SOURCE_WITH_DEMO_INVENTORY' and not asset.is_demo:
            raise SceneAdmissionError('INVENTORY_ORIGIN_MISMATCH')
    return configured_owner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=ROOT/'demo/phase12d2/cases.json')
    parser.add_argument('--profile', type=Path, default=ROOT/'demo/phase12d1/local-real-profile.json')
    parser.add_argument('--output', type=Path, default=ROOT/'work/phase12d2/scene-receipts.json')
    parser.add_argument('--ollama-executable', type=Path)
    args = parser.parse_args()
    output = {'phase':'12D.2','benchmark':False,'security_accuracy_evaluated':False,
              'status':'RUNNING','started_at_utc':datetime.now(timezone.utc).isoformat(),'cases':[]}
    def save():
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(public_copy(output),ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    from app.db.session import make_engine, transaction
    from app.db import models as m
    from app.llm.config import ModelConfig
    from app.llm.gateway import ModelGateway
    from app.main import create_app
    from app.planner.trace import PlannerTraceStore
    from scripts.probe_planner_stability import owned_http_client, run_stability_case, initial_receipt, prewarm_model
    original={k:os.environ.get(k) for k in ('AEGIS_ASSET_OWNER','AEGIS_ASSET_TOKEN')}
    engine = None; gateway = None
    try:
        cases=json.loads(args.cases.read_text(encoding='utf-8'))['cases']
        profile=json.loads(args.profile.read_text(encoding='utf-8'))
        config=ModelConfig.from_env({**os.environ,**profile})
        if config.provider=='mock':raise ValueError('REAL_PROVIDER_REQUIRED')
        output['model']=config.model;output['prompt_unchanged']='investigation-plan-v4'
        output['provider_timeout_seconds']=config.timeout_seconds
        output['structured_mode']=config.structured_mode
        engine=make_engine()
        for case in cases:
            entry={'case_id':case['case_id'],'receipt':initial_receipt(case,chain=True),'diagnostic':None}
            output['cases'].append(entry);save()
            try:
                actor=resolve_case_actor(engine,case,original['AEGIS_ASSET_OWNER'])
            except SceneAdmissionError as exc:
                entry['receipt'].update(measurement_status='REJECTED_BEFORE_EXECUTION',
                    chain_attempted=False,error_code=str(exc),elapsed_ms=0)
                entry['diagnostic_error']=str(exc);save()
                continue
            if gateway is None:
                if args.ollama_executable:prewarm_model(args.ollama_executable,config.model)
                gateway=ModelGateway(config)
            token=secrets.token_urlsafe(32)
            os.environ.update(AEGIS_ASSET_OWNER=actor,AEGIS_ASSET_TOKEN=token)
            with owned_http_client(create_app(engine,investigation_gateway=gateway),token) as client:
                receipt=run_stability_case(client,case,lambda id:PlannerTraceStore(engine).read(id,actor),
                    receipt=entry['receipt'],on_progress=save)
                entry['receipt']=receipt
                add_diagnostic(entry,engine,actor,case)
                save()
            print(json.dumps({'case':case['case_id'],'gate':receipt.get('integration_status'),
                              'error':receipt.get('error_code'),'elapsed_ms':receipt['elapsed_ms']}),flush=True)
        output.update(status='COMPLETED',finished_at_utc=datetime.now(timezone.utc).isoformat());save()
        return 0
    except BaseException as exc:
        output.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',
                      error_code='SCENE_PROBE_FAILED',finished_at_utc=datetime.now(timezone.utc).isoformat());save()
        return 1
    finally:
        if gateway:gateway.close()
        if engine:engine.dispose()
        for key,value in original.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value


if __name__=='__main__':
    raise SystemExit(main())

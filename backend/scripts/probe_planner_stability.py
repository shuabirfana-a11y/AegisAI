"""Fixed-case, real-HTTP Planner reliability audit; never a security accuracy benchmark."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

import httpx
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from app.agents.investigation.planning import InvestigationPlan
from app.agents.investigation.planner import InvestigationPlannerAdapter
from app.db.session import make_engine
from app.investigation_api.schemas import (
    InvestigationCreateRequest, TraceResponse, ArtifactResponse, IntegrationResponse, AnswerResponse,
)
from app.investigation_api.projection import public_copy
from app.llm.config import ModelConfig
from app.llm.gateway import ModelGateway
from app.llm.schemas import strict_json
from app.main import create_app
from app.planner.trace import PlannerTraceStore
from app.planner.schemas import PlanningOutcome
from app.planner.llm_planner import issue
from app.planner.context import build_context
from app.orchestration.scope import resolve_scope
from app.runtime.contracts import RuntimePolicy
from scripts.probe_investigation_http import run_probe


def classify_attempt(attempt):
    """Read only the owned persisted diagnostic; export booleans and call metadata."""
    diagnostic = attempt.get('diagnostic') or {}
    available = bool(diagnostic.get('raw_output') and not diagnostic.get('redacted')
                     and not diagnostic.get('truncated'))
    json_valid = schema_valid = False
    if available:
        try:
            parsed = strict_json(diagnostic['raw_output'])
            json_valid = True
            Draft202012Validator(InvestigationPlan.model_json_schema(), format_checker=FormatChecker()).validate(parsed)
            InvestigationPlan.model_validate(parsed)
            schema_valid = True
        except (ValueError, TypeError, RecursionError, ValidationError):
            pass
    call = attempt.get('model_call') or {}
    return {
        'attempt_index': attempt.get('attempt_index'), 'diagnostic_available': available,
        'json_valid': json_valid, 'schema_valid': schema_valid,
        'task_legal': bool(schema_valid and attempt.get('validation_status') == 'VALIDATED'),
        'validation_status': attempt.get('validation_status'),
        'error_codes': [i['code'] for i in attempt.get('issues', [])],
        'request_id': call.get('request_id'), 'provider': call.get('provider'),
        'model': call.get('model'), 'is_mock': call.get('is_mock'),
        'duration_ms': call.get('duration_ms'), 'usage': call.get('usage'),
    }


def case_sequence(cases):
    if len(cases) != 3 or len({c['case_id'] for c in cases}) != 3:
        raise ValueError('EXACTLY_THREE_DISTINCT_CASES_REQUIRED')
    return [cases[i % 3] for i in range(20)]


def summarize(receipts):
    attempts = [a for run in receipts for a in run['attempts']]
    chains = [r for r in receipts if r.get('chain_attempted', True)]
    def rate(items, predicate):
        return sum(bool(predicate(x)) for x in items) / len(items) if items else None
    return {
        'logical_runs': len(receipts), 'provider_attempts': len(attempts), 'full_chain_attempts':len(chains),
        'provider_attempt_accounting_complete':all(r.get('attempt_accounting_complete',True) for r in receipts),
        'attempts': {
            'json_success_rate': rate(attempts, lambda a: a['json_valid']),
            'schema_pass_rate': rate(attempts, lambda a: a['schema_valid']),
            'task_legal_rate': rate(attempts, lambda a: a['task_legal']),
        },
        'runs': {
            'json_success_rate': rate(receipts, lambda r: any(a['json_valid'] for a in r['attempts'])),
            'schema_pass_rate': rate(receipts, lambda r: any(a['schema_valid'] for a in r['attempts'])),
            'task_legal_rate': rate(receipts, lambda r: r['planner_validated'] and r['real_mode_confirmed']),
            'full_chain_execution_rate': rate(chains, lambda r: r['full_chain_executed'] and r['real_mode_confirmed']),
            'full_chain_success_rate': rate(chains, lambda r: r['gate_accepted'] and r['real_mode_confirmed']),
        },
        'mean_elapsed_ms': sum(r['elapsed_ms'] for r in receipts)/len(receipts) if receipts else None,
        'total_tokens': sum((a.get('usage') or {}).get('total_tokens') or 0 for a in attempts),
        'case_distribution': {k: sum(r['case_id'] == k for r in receipts)
                              for k in sorted({r['case_id'] for r in receipts})},
        'benchmark': False, 'security_accuracy_evaluated': False,
    }


def public_plan_tasks(plan):
    return public_copy([{'task_id':t['task_id'],'type':t['type'],
        'task_type':t.get('task_type','tool_sequence'),'dependencies':t.get('dependencies',[]),
        'tools':[s['name'] for s in t['input_data'].get('steps',[])]} for t in (plan or {}).get('tasks',[])])


def initial_receipt(case, *, chain):
    return {'case_id':case['case_id'],'elapsed_ms':0.,'attempts':[], 'error_codes':[],
        'measurement_status':'RUNNING','planner_validated':False,'real_mode_confirmed':False,
        'chain_attempted':chain,'full_chain_executed':False,'gate_accepted':False,
        'attempt_accounting_complete':False}


def run_planner_case(engine, gateway, actor, case, *, receipt=None, on_progress=None):
    """Same scope, Planner adapter and persistence as HTTP; no Runtime execution here."""
    started = time.monotonic()
    receipt = initial_receipt(case,chain=False) if receipt is None else receipt
    request = InvestigationCreateRequest.model_validate(case['request']).model_copy(
        update={'idempotency_key':'phase12d1-plan-'+uuid4().hex})
    input = resolve_scope(request.to_internal(),actor=actor).planner_input
    store = PlannerTraceStore(engine)
    planner = InvestigationPlannerAdapter(gateway,store)
    policy = RuntimePolicy()
    saved, fresh = store.create(input,actor,policy,model_identity=planner.model_identity,
        prompt_version=planner.prompt_version,registry_version=planner.registry_version)
    if not fresh:
        raise RuntimeError('PROBE_PLANNER_ID_REUSED')
    receipt.update(planner_run_id=str(saved.planner_run_id),measurement_status='RUNNING')
    if on_progress:on_progress()
    context = build_context(input,actor,policy,saved.planner_run_id,saved.trace_id)
    try:
        outcome = planner.plan(input,context)
        store.complete(saved.planner_run_id,actor,outcome)
    except BaseException as exc:
        # Only this owned standalone audit is finalized. No Runtime has been started.
        interrupted=isinstance(exc,KeyboardInterrupt)
        receipt.update(measurement_status='INTERRUPTED' if interrupted else 'FAILED',
            error_codes=['PROBE_INTERRUPTED' if interrupted else 'PROBE_EXECUTION_FAILED'],
            attempt_accounting_complete=False,elapsed_ms=round((time.monotonic()-started)*1000,3))
        try:
            audit=store.read(saved.planner_run_id,actor)
            receipt['attempts']=[classify_attempt(a.model_dump(mode='json')) for a in audit.attempts]
            store.complete(saved.planner_run_id,actor,PlanningOutcome(status='PLANNING_FAILED',
                issues=(issue(receipt['error_codes'][0]),),attempts=tuple(audit.attempts)))
            receipt['audit_cleanup_complete']=True
        except Exception:
            receipt['audit_cleanup_complete']=False
        if on_progress:on_progress()
        raise
    audit = store.read(saved.planner_run_id,actor)
    attempts = [classify_attempt(a.model_dump(mode='json')) for a in audit.attempts]
    receipt.update({
        'case_id':case['case_id'],'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'transport':'INTERNAL_PRODUCTION_PLANNER','data_origin':case.get('data_origin','REAL_SOURCE'),
        'benchmark':False,'planner_run_id':str(audit.planner_run_id),'prompt_version':audit.prompt_version,
        'attempts':attempts,'planner_validated':audit.validation_status=='VALIDATED',
        'real_mode_confirmed':bool(attempts and all(a['is_mock'] is False for a in attempts)),
        'chain_attempted':False,'full_chain_executed':False,'gate_accepted':False,
        'measurement_status':'COMPLETED','attempt_accounting_complete':True,
        'elapsed_ms':round((time.monotonic()-started)*1000,3),
        'error_codes':[i.code for i in audit.error],
        'plan_tasks':public_plan_tasks(audit.generated_plan),
    })
    return receipt


def capture_owned_audit(receipt, trace, audit_reader):
    if not trace.planner:
        receipt['attempt_accounting_complete']=False
        return
    audit=audit_reader(trace.planner.planner_run_id)
    receipt.update(planner_run_id=str(trace.planner.planner_run_id),prompt_version=trace.planner.prompt_version,
        planner_validated=trace.planner.validation_status=='VALIDATED',
        attempts=[classify_attempt(a.model_dump(mode='json')) for a in audit.attempts],
        plan_tasks=public_plan_tasks(audit.generated_plan),
        attempt_accounting_complete=audit.validation_status!='PLANNING')


def run_stability_case(client, case, audit_reader, *, receipt=None, on_progress=None):
    started = time.monotonic()
    request = InvestigationCreateRequest.model_validate(case['request'])
    # Every repeat creates a new model run, never an idempotently reused success.
    request = request.model_copy(update={'idempotency_key': 'phase12d1-' + uuid4().hex})
    bound = {**case, 'request': request, 'data_origin': case.get('data_origin','REAL_SOURCE'), 'requested_mode': 'REAL'}
    receipt = initial_receipt(case,chain=True) if receipt is None else receipt
    receipt.update({
        'case_id': case['case_id'], 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'data_origin': case.get('data_origin', 'REAL_SOURCE'), 'transport': 'LOOPBACK_HTTP',
        'benchmark': False, 'attempts': [], 'planner_validated': False,
        'chain_attempted': True,
        'real_mode_confirmed': False, 'full_chain_executed': False, 'gate_accepted': False,
        'answer_frozen_read_verified': False, 'error_code': None,
    })
    try:
        probe = run_probe(client, bound, timeout_seconds=120, poll_interval=.4, requested_mode='REAL')
        receipt['http_probe'] = probe
        receipt['error_code'] = probe.get('error_code') or probe.get('chain_error_code')
        id = probe.get('investigation_id')
        if not id:
            return receipt
        receipt['investigation_id'] = id
        if on_progress:on_progress()
        prefix = '/api/investigations/' + id
        if probe.get('error_code') == 'PROBE_POLL_TIMEOUT':
            # This logical run was just created by this audit, never another user's work.
            client.post(prefix + '/cancel', json={})
            # Bounded read of this run only; missing audit is an incomplete count.
            try:
                saved=client.get(prefix+'/trace')
                if saved.is_success:
                    capture_owned_audit(receipt,TraceResponse.model_validate(saved.json()),audit_reader)
            except Exception:
                receipt['attempt_accounting_complete']=False
            receipt['measurement_status']='TIMED_OUT'
            return receipt
        raw_trace = client.get(prefix + '/trace')
        if not raw_trace.is_success:
            return receipt
        trace = TraceResponse.model_validate(raw_trace.json())
        capture_owned_audit(receipt,trace,audit_reader)
        receipt['real_mode_confirmed'] = bool(trace.model_execution
            and trace.model_execution.execution_mode == 'REAL'
            and trace.model_execution.source == 'PERSISTED_PLANNER_CALL'
            and receipt['attempts'] and all(a['is_mock'] is False for a in receipt['attempts']))
        receipt['agent_runs'] = [{'run_id':str(r.run_id), 'status':r.status,
            'task_statuses':r.task_statuses, 'artifact_ids':[str(a.artifact_id) for a in r.artifact_references],
            'tool_calls':[c.model_dump(mode='json') for c in r.tool_calls]} for r in trace.agent_runs]
        receipt['integration_id'] = str(trace.integration_result_id) if trace.integration_result_id else None
        raw_artifacts = client.get(prefix + '/artifacts')
        raw_gate = client.get(prefix + '/integration')
        raw_answer = client.get(prefix + '/answer')
        artifacts = ArtifactResponse.model_validate(raw_artifacts.json()) if raw_artifacts.is_success else None
        gate = IntegrationResponse.model_validate(raw_gate.json()) if raw_gate.is_success else None
        answer = AnswerResponse.model_validate(raw_answer.json()) if raw_answer.is_success else None
        receipt['artifact_ids'] = {name:str(getattr(artifacts,name).artifact_id) for name in
            ('investigation','verification','analysis') if artifacts and getattr(artifacts,name)}
        receipt['integration_status'] = gate.status if gate else None
        receipt['answer_id'] = str(answer.answer_id) if answer else None
        receipt['answer_status'] = answer.answer_status if answer else None
        receipt['full_chain_executed'] = bool(receipt['planner_validated'] and len(trace.agent_runs)==3
            and len(receipt['artifact_ids'])==3 and gate and answer)
        if answer:
            before = len(audit_reader(trace.planner.planner_run_id).attempts) if trace.planner else 0
            repeated = client.get(prefix + '/answer')
            after = len(audit_reader(trace.planner.planner_run_id).attempts) if trace.planner else 0
            receipt['answer_frozen_read_verified'] = bool(repeated.is_success
                and repeated.json()==raw_answer.json() and before==after)
            receipt['answer_read_extra_planner_calls'] = after-before
        receipt['gate_accepted'] = bool(probe.get('chain_verified') and receipt['real_mode_confirmed']
            and receipt['full_chain_executed'] and receipt['answer_frozen_read_verified'])
        receipt['measurement_status']='COMPLETED'
        return receipt
    except (httpx.HTTPError, ValueError, TypeError):
        receipt['error_code'] = 'PROBE_PROTOCOL_FAILED'
        receipt['measurement_status']='FAILED'
        return receipt
    finally:
        receipt['elapsed_ms'] = round((time.monotonic()-started)*1000,3)


@contextmanager
def owned_http_client(app, token):
    import uvicorn
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1',0))
        server = uvicorn.Server(uvicorn.Config(app,loop='asyncio',http='h11',ws='none',
            lifespan='on',access_log=False,log_level='warning'))
        thread = threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True)
        thread.start()
        try:
            deadline = time.monotonic()+15
            while not server.started:
                if not thread.is_alive() or time.monotonic()>deadline:
                    raise RuntimeError('OWNED_SERVER_START_FAILED')
                time.sleep(.02)
            with httpx.Client(base_url=f'http://127.0.0.1:{listener.getsockname()[1]}',
                headers={'Authorization':'Bearer '+token},trust_env=False,timeout=10) as client:
                yield client
        finally:
            server.should_exit = True
            thread.join(150)
            if thread.is_alive():
                raise RuntimeError('OWNED_SERVER_STOP_FAILED')


def prewarm_model(executable, model):
    flags = subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    options = dict(capture_output=True,text=True,encoding='utf-8',errors='replace',
                   timeout=180,creationflags=flags)
    # `show` never downloads weights; a miss must not reach `run`.
    installed = subprocess.run([str(executable),'show',model],**options)
    if installed.returncode:
        raise RuntimeError('MODEL_NOT_INSTALLED')
    result = subprocess.run([str(executable),'run',model,'--keepalive','30m'],input='',**options)
    if result.returncode:
        raise RuntimeError('MODEL_PREWARM_FAILED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', action='append', required=True)
    parser.add_argument('--cases', type=Path, default=ROOT/'demo/phase12d1/cases.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ollama-executable', type=Path)
    parser.add_argument('--planner-stability',action='store_true',
        help='20 persisted production-Planner runs plus three separate full HTTP runs per model')
    parser.add_argument('--planner-timeout-seconds',type=float,default=20,
        help='Per-provider timeout for --planner-stability after explicit model prewarm')
    args = parser.parse_args()
    output = {'started_at_utc':datetime.now(timezone.utc).isoformat(), 'models':[],
              'status':'RUNNING','report_version':'phase12d1-probe-v2',
              'benchmark':False, 'security_accuracy_evaluated':False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():
        for entry in output['models']:
            entry['summary']=summarize(entry['receipts'])
            if 'planner_receipts' in entry:
                entry['planner_summary']=summarize(entry['planner_receipts'])
        temporary=args.output.with_name(args.output.name+'.tmp')
        temporary.write_text(json.dumps(public_copy(output),ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        temporary.replace(args.output)
    # Replace stale success before any fallible setup/configuration/prewarm.
    save()
    engine=None;active=None;active_started=None
    original={k:os.environ.get(k) for k in ('AEGIS_ASSET_TOKEN','AEGIS_ASSET_OWNER')}
    try:
        cases = json.loads(args.cases.read_text(encoding='utf-8'))['cases']
        sequence = case_sequence(cases)
        token = secrets.token_urlsafe(32)
        os.environ['AEGIS_ASSET_TOKEN'] = token
        actor = 'phase12d1-stability-' + uuid4().hex
        os.environ['AEGIS_ASSET_OWNER'] = actor
        engine = make_engine()
        for name in args.model:
            entry={'receipts':[],'measurement_status':'CONFIGURING'}
            output['models'].append(entry);save()
            model_env = {**os.environ,'MODEL_NAME':name}
            if args.planner_stability:
                model_env['MODEL_TIMEOUT_SECONDS'] = str(args.planner_timeout_seconds)
            cfg = ModelConfig.from_env(model_env)
            if cfg.provider=='mock':
                raise ValueError('REAL_PROVIDER_REQUIRED')
            entry.update(provider=cfg.provider,model=cfg.model,structured_mode=cfg.structured_mode,
                reasoning_effort=cfg.reasoning_effort,temperature=0.0,
                timeout_seconds=cfg.timeout_seconds,max_output_tokens=cfg.max_output_tokens)
            save()
            # Empty stdin preloads existing weights, not a supplied plan or answer.
            if args.ollama_executable:
                prewarm_model(args.ollama_executable,name)
            gateway = ModelGateway(cfg)
            entry['measurement_status']='RUNNING';save()
            try:
                http_cases = sequence
                if args.planner_stability:
                    entry['planner_receipts'] = []
                    for index,case in enumerate(sequence,1):
                        active=initial_receipt(case,chain=False);active_started=time.monotonic()
                        entry['planner_receipts'].append(active);save()
                        receipt = run_planner_case(engine,gateway,actor,case,receipt=active,on_progress=save)
                        active.update(receipt);active['measurement_status']='COMPLETED';save()
                        print(json.dumps(public_copy({'model':name,'planner_run':index,'case':case['case_id'],
                            'plan_valid':receipt['planner_validated'],'errors':receipt['error_codes'],
                            'elapsed_ms':receipt['elapsed_ms']})),flush=True)
                        active=None
                    http_cases = cases
                with owned_http_client(create_app(engine,investigation_gateway=gateway),token) as client:
                    read = lambda id: PlannerTraceStore(engine).read(id,actor)
                    for index,case in enumerate(http_cases,1):
                        active=initial_receipt(case,chain=True);active_started=time.monotonic()
                        entry['receipts'].append(active);save()
                        receipt = run_stability_case(client,case,read,receipt=active,on_progress=save)
                        active.update(receipt);save()
                        print(json.dumps(public_copy({'model':name,'run':index,'case':case['case_id'],
                            'plan_valid':receipt['planner_validated'],'gate':receipt.get('integration_status'),
                            'error':receipt['error_code'],'elapsed_ms':receipt['elapsed_ms']})),flush=True)
                        active=None
                entry['measurement_status']='COMPLETED'
            finally:
                gateway.close()
        output['status']='COMPLETED'
        output['finished_at_utc'] = datetime.now(timezone.utc).isoformat();save()
    except BaseException as exc:
        interrupted=isinstance(exc,KeyboardInterrupt)
        output['status']='INTERRUPTED' if interrupted else 'FAILED'
        known={'MODEL_NOT_INSTALLED','MODEL_PREWARM_FAILED','REAL_PROVIDER_REQUIRED','PROBE_PLANNER_ID_REUSED'}
        output['error_code']='PROBE_INTERRUPTED' if interrupted else str(exc) if str(exc) in known else 'PROBE_EXECUTION_FAILED'
        if active is not None:
            active.update(measurement_status=output['status'],planner_validated=False,gate_accepted=False,
                attempt_accounting_complete=False,error_codes=[output['error_code']],
                elapsed_ms=round((time.monotonic()-active_started)*1000,3))
        if output['models']:output['models'][-1]['measurement_status']=output['status']
        output['finished_at_utc']=datetime.now(timezone.utc).isoformat();save()
        raise
    finally:
        if engine is not None:engine.dispose()
        for key,value in original.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value


if __name__=='__main__':
    main()

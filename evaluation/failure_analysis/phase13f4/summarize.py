"""Read saved protocol diagnostics only. No HTTP, inference or scoring."""
import json
from pathlib import Path
from collections import Counter


def summarize(root):
    folder=root/'evaluation/failure_analysis/phase13f4/diagnostic5'
    receipt=json.loads((folder/'receipt.json').read_text(encoding='utf-8'))
    audit=json.loads((folder/'planner-audit.json').read_text(encoding='utf-8'))
    assert len(receipt['results'])==5 and receipt['protected_files_changed']==[]
    planners={r['id']:r for r in audit['records']};cases=[]
    for saved in receipt['results']:
        packet=json.loads((folder/(saved['id']+'.json')).read_text(encoding='utf-8'))
        native=packet['native_http_record'];created=native['created'];planner=planners.get(saved['id'])
        context=created.get('status')=='NEED_CONTEXT';gate=native.get('integration') or {}
        if context:
            assert saved['request_status']==200 and not saved['investigation_id'] and planner is None
            assert created['investigation_created'] is False and created['execution_mode']=='NOT_STARTED'
            assert packet['prediction']['status']=='NOT_EVALUATED' and packet['prediction']['abstained'] is True
            assert not any(k in packet['prediction']['answer'] for k in ('affected','risk_level','priority'))
        reached=bool(planner and planner['validation_status']=='VALIDATED' and planner['runtime_run_id']
                     and gate.get('integration_id') and saved['answer_status'])
        cases.append({**saved,'legal_handling':context or reached,
            'handling':'NEED_CONTEXT' if context else 'FULL_CHAIN' if reached else 'FAILED',
            'planner_status':planner['validation_status'] if planner else 'NOT_STARTED',
            'missing_fields':created.get('missing_fields',[]),
            'model_attempts':len(planner['attempts']) if planner else 0,
            'runtime_run_id':planner['runtime_run_id'] if planner else None,
            'integration_id':gate.get('integration_id'),'artifact_refs':gate.get('artifact_references',[]),
            'blocked_checks':[c for c in gate.get('checks',[]) if c['outcome']=='BLOCKED']})
    assert len(audit['records'])==audit['run_counts']['investigation-orchestrator-v1']==receipt['new_investigations']
    attempts=[t for r in audit['records'] for t in r['attempts']]
    result={'status':'CONTEXT_HANDLING_READY' if all(c['legal_handling'] for c in cases) else 'PARTIAL_NOT_READY',
        'technical_admission_restored':all(c['legal_handling'] for c in cases),
        'http_requests':5,'actual_investigations':receipt['new_investigations'],
        'full_chains':sum(c['handling']=='FULL_CHAIN' for c in cases),
        'need_context':sum(c['handling']=='NEED_CONTEXT' for c in cases),
        'model_calls':len(attempts),'gate_status_counts':dict(Counter(c['gate_status'] or 'NOT_STARTED' for c in cases)),
        'protected_files_checked':receipt['protected_files_checked'],'protected_files_changed':[],
        'formal_39_rerun':False,'accuracy_calculated':False,'scorer_modified':False,
        'unknown_risk_answer_fabricated':False,'need_context_remains_not_evaluated':True,
        'token_usage':{k:sum(t['model_call']['usage'][k] for t in attempts) for k in ('input_tokens','output_tokens','total_tokens')},
        'model_duration_ms':sum(t['model_call']['duration_ms'] for t in attempts),
        'limitations':['NEED_CONTEXT is a lawful preflight response, not a completed investigation or correct risk answer.',
            'The formal scorer still marks a no-answer case unavailable; no denominator/metric changes.',
            'Five fixed diagnostics do not establish full39 planning stability or semantic accuracy.'],
        'cases':cases}
    (folder/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__=='__main__':
    result=summarize(Path(__file__).resolve().parents[3])
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))

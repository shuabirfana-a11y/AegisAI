"""Summarize saved diagnostics only; never run models, APIs or a scorer."""
import json
from collections import Counter
from pathlib import Path


def summarize(root):
    folder=root/'evaluation/failure_analysis/phase13f3/diagnostic5'
    receipt=json.loads((folder/'receipt.json').read_text(encoding='utf-8'))
    audit=json.loads((folder/'planner-audit.json').read_text(encoding='utf-8'))
    assert len(receipt['results'])==len(audit['records'])==5
    assert audit['run_counts']['investigation-orchestrator-v1']==5
    assert receipt['protected_files_changed']==[]
    records={r['id']:r for r in audit['records']};cases=[]
    for saved in receipt['results']:
        row=records[saved['id']]
        packet=json.loads((folder/(saved['id']+'.json')).read_text(encoding='utf-8'))
        native=packet['native_http_record'];gate=native.get('integration') or {}
        arts=native.get('artifacts') or {}
        reached=bool(row['validation_status']=='VALIDATED' and row['runtime_run_id']
                     and gate.get('integration_id') and saved['answer_status'])
        cases.append({**saved,'planner_status':row['validation_status'],'runtime_run_id':row['runtime_run_id'],
            'normalized_goal':row['normalized_goal'],'task_template':row['task_template'],
            'model_attempts':len(row['attempts']),'entered_chain':reached,
            'integration_id':gate.get('integration_id'),
            'artifact_refs':gate.get('artifact_references',[]),
            'verification_status':(arts.get('verification') or {}).get('verification_status'),
            'blocked_checks':[c for c in gate.get('checks',[]) if c['outcome']=='BLOCKED']})
    attempts=[t for r in audit['records'] for t in r['attempts']]
    ready=all(c['entered_chain'] for c in cases)
    result={'status':'CHAIN_READY_FOR_NEXT_AUTHORIZED_EXPERIMENT' if ready else 'PARTIAL_NOT_READY',
        'formal_evaluation_conditions_restored':ready,'new_http_investigations':5,
        'chains_reached':sum(c['entered_chain'] for c in cases),'model_calls':len(attempts),
        'planner_status_counts':dict(Counter(r['validation_status'] for r in audit['records'])),
        'strict_json_rejections':sum(bool(t['strict_json_error']) for t in attempts),
        'gate_status_counts':dict(Counter(c['gate_status'] or 'NOT_REACHED' for c in cases)),
        'answer_status_counts':dict(Counter(c['answer_status'] for c in cases)),
        'token_usage':{k:sum(t['model_call']['usage'][k] for t in attempts)
                       for k in ('input_tokens','output_tokens','total_tokens')},
        'model_duration_ms':sum(t['model_call']['duration_ms'] for t in attempts),
        'formal_39_rerun':False,'accuracy_calculated':False,'ground_truth_changed':False,
        'model_changed':False,'protected_files_checked':receipt['protected_files_checked'],
        'protected_files_changed':[],
        'limitations':['Five fixed diagnostics are not repeated stability tests or formal scores.',
            'Raw JSON success and HTTP SUCCEEDED do not establish fact/risk correctness.',
            'UNKNOWN case failed original VERSION_INPUT_REQUIRED validation; no runtime fallback.',
            'Gate replan/human review outcomes are preserved, with partial verification/risk artifacts.'],
        'cases':cases}
    (folder/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__=='__main__':
    result=summarize(Path(__file__).resolve().parents[3])
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))

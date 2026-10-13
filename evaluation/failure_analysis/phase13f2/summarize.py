"""Offline diagnostic accounting only. No model/API calls or accuracy scoring."""
import json
from collections import Counter
from pathlib import Path


def summarize(root):
    folder=root/'evaluation/failure_analysis/phase13f2/diagnostic5'
    receipt=json.loads((folder/'receipt.json').read_text(encoding='utf-8'))
    audit=json.loads((folder/'planner-audit.json').read_text(encoding='utf-8'))
    assert len(receipt['results'])==len(audit['records'])==5
    assert audit['run_counts']['investigation-orchestrator-v1']==5
    assert receipt['protected_files_changed']==[]
    states=Counter(r['validation_status'] for r in audit['records'])
    attempts=[t for r in audit['records'] for t in r['attempts']]
    result={
        'status':'PARTIAL_NOT_READY',
        'formal_evaluation_conditions_restored':False,
        'new_http_investigations':5,
        'model_calls':len(attempts),
        'planner_status_counts':dict(states),
        'duplicate_json_key_rejections':sum(t['strict_json_error']=='Duplicate JSON key' for t in attempts),
        'gate_status_counts':dict(Counter(r['gate_status'] or 'NOT_REACHED' for r in receipt['results'])),
        'answer_status_counts':dict(Counter(r['answer_status'] for r in receipt['results'])),
        'formal_39_rerun':False,
        'accuracy_calculated':False,
        'ground_truth_changed':False,
        'model_changed':False,
        'protected_files_checked':receipt['protected_files_checked'],
        'protected_files_changed':[],
        'limitations':['Five purposively selected diagnostics are not a stability benchmark.',
            'Real conflict case failed before Runtime; conflict handoff has automated coverage only.',
            'No gold comparison or semantic accuracy claim.'],
        'cases':receipt['results'],
    }
    (folder/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    result=summarize(Path(__file__).resolve().parents[3])
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))

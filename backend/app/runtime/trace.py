"""Derived legacy views; runtime_v1 remains the authoritative task protocol."""
from copy import deepcopy
import json
from app.llm.schemas import CallRecord


LEGACY_STATES={'RUNNING':'started','SUCCESS':'success','WAITING_REVIEW':'partial',
               'FAILED':'failed','BLOCKED':'blocked'}


def project(details: dict, run_status: str) -> dict:
    result = deepcopy(details)
    ns = result['runtime_v1']
    result['ui_status'] = {'queued':'PLANNING', 'running':'RUNNING',
        'succeeded':'COMPLETED', 'partial':'WAITING_REVIEW'}.get(run_status, 'FAILED')
    result['route'] = ns['plan']['route']
    result['plan'] = [{**t, 'goal':t['description']} for t in ns['plan']['tasks']]
    order=[t['task_id'] for t in ns['plan']['tasks']]
    result['events'] = []
    planning_calls=[]
    if result['route'].get('planner_run_id'):
        # Strict metadata-only projection; private output/prompt fields cannot pass.
        planning_calls=[CallRecord.model_validate_json(json.dumps(c)).model_dump(mode='json')
                        for c in result['route'].get('planning_model_calls', [])]
        result['events'].extend({'state':'model_called','phase':'planning',
                                 'at':c['finished_at'],'model_call':c} for c in planning_calls)
    for key in order:
        trace=ns['traces'][key]
        result['events'].extend({**event, 'task_id':trace['task_id'],
                                'runtime_state':event['state'],
                                'state':LEGACY_STATES.get(event['state'],event['state'])}
                                for event in trace['transitions'])
        if trace['artifact_id']:
            result['events'].append({**trace, 'at':trace['end_time']})
    result['events'].sort(key=lambda e:e['at'])
    artifacts = [ns['artifacts'][key] for key in order if key in ns['artifacts']]
    result['result'] = None if run_status in ('queued','running') else {
        'answer':'任务执行摘要；安全事实和不确定性以实际工具结果为准。',
        'artifacts':artifacts, 'task_traces':[ns['traces'][key] for key in order],
        'evidence_refs':[ref for a in artifacts for ref in a['evidence']],
        'warnings':[w for a in artifacts for w in a['warnings']],
        'unresolved':[u for a in artifacts for u in a['unresolved_questions']],
        'generation_calls':sum(c['attempt_count'] for c in planning_calls)}
    return result

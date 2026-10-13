"""Offline formal-data admission check. Never invokes a model, HTTP or scorer."""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .data import load_benchmark, sha256
from .adapters import corpus_fingerprint
from .e2e import checked_output
from .runner import DEFAULT_MANIFEST, ROOT


def workflow_file_counts():
    counts=Counter(); root=ROOT/'evaluation/ground_truth/samples'
    for path in root.rglob('*.json'):
        row=json.loads(path.read_text(encoding='utf-8-sig'))
        if row.get('record_kind')=='HUMAN_RECORD':counts[row.get('annotation',{}).get('status') or 'UNSET']+=1
    tasks=Counter()
    for path in (ROOT/'evaluation/ground_truth/annotation_tasks/tasks').glob('*.json'):
        row=json.loads(path.read_text(encoding='utf-8-sig'))
        if row.get('record_kind')=='ANNOTATION_TASK_NOT_GROUND_TRUTH':tasks[row.get('status') or 'UNSET']+=1
    return {'manual_workflow_file_counts':{k:counts[k] for k in ('DRAFT','REVIEWING','APPROVED','REJECTED')},
            'task_card_state_counts':dict(tasks),
            'count_semantics':'Workflow files and task cards do not grant benchmark admission; frozen manifest only.'}


def inspect_readiness(manifest=DEFAULT_MANIFEST,*,minimum=10):
    if isinstance(minimum,bool) or not isinstance(minimum,int) or minimum<10:
        raise ValueError('Minimum human-gold count cannot be lower than 10')
    path=Path(manifest);data=load_benchmark(path)
    statuses=Counter(a.review_status for a in data['annotations'])
    count=len(data['eligible_gold']);passed=count>=minimum
    return {'schema_version':'aegisbench-formal-preflight-v1',
        'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'READY_FOR_DATA_FREEZE' if passed else 'BLOCKED_MINIMUM_GOLD',
        'dataset_version':data['manifest']['dataset_version'],'sample_count':len(data['questions']),
        'manifest_sha256':sha256(path),'dataset_fingerprint':corpus_fingerprint(data['sources']),
        'questions_sha256':data['manifest']['questions_sha256'],
        'annotations_sha256':data['manifest']['annotations_sha256'],
        'annotation_status_counts':dict(statuses),'eligible_gold_count':count,
        'eligible_completed_state_counts':dict(Counter(a.review_status for a in data['eligible_gold'])),
        'excluded_gold_count':len(data['excluded_gold']),
        'exclusion_reason_counts':dict(Counter(row['reason'] for row in data['excluded_gold'])),
        'minimum_approved':minimum,'data_gate_passed':passed,
        'eligible_by_category':dict(Counter(next(q.category for q in data['questions'] if q.id==a.id) for a in data['eligible_gold'])),
        'formal_experiment_executed':False,'http_executed':False,'model_calls':0,
        'quality_status':'NOT_EVALUATED','model_freeze_status':'NOT_FROZEN',
        'prompt_freeze_status':'NOT_FROZEN','inventory_equivalence':'NOT_INDEPENDENTLY_ATTESTED',
        'baselines':{'rag_only':'NOT_IMPLEMENTED','agent_without_verification':'NOT_IMPLEMENTED',
                     'aegisai':'HTTP_ENTRY_IMPLEMENTED_NOT_EXECUTED'},
        'output_semantic_audit':'REQUIRED_AFTER_OUTPUT_FOR_EVIDENCE_AND_HALLUCINATION',
        'scope':'Data admission only, not experiment readiness or evidence correctness certification'}


def write_preflight(report,output):
    output.mkdir(parents=True,exist_ok=True)
    (output/'readiness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    text=(f"# AegisBench 正式实验准入检查\n\n状态：{report['status']}。\n\n"
          f"候选：{report.get('sample_count','UNKNOWN')}；合格人工标准答案：{report.get('eligible_gold_count','UNKNOWN')}；"
          f"首批门槛：{report.get('minimum_approved',10)}。\n\n"
          "这只检查数据准入，不执行实验。没有 HTTP、模型调用或准确率；模型/Prompt/正式数据集及库存仍需冻结。"
          "任务卡 DRAFT 不算人工答案。RAG 与无核验对照仍未接入，不能输出公平对照结论。\n")
    (output/'readiness.md').write_text(text,encoding='utf-8',newline='\n')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=DEFAULT_MANIFEST)
    parser.add_argument('--minimum',type=int,default=10)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv);output=checked_output(args.output,args.manifest)
    try:
        report=inspect_readiness(args.manifest,minimum=args.minimum)
        report.update(workflow_file_counts())
    except (ValueError,OSError):
        report={'status':'BLOCKED_INVALID_DATASET','data_gate_passed':False,
                'formal_experiment_executed':False,'http_executed':False,'model_calls':0,'quality_status':'NOT_EVALUATED'}
    write_preflight(report,output)
    print(json.dumps({'status':report['status'],'eligible_gold_count':report.get('eligible_gold_count'),
                      'minimum':args.minimum,'formal_experiment_executed':False,'output':str(output)},ensure_ascii=False))
    return 0 if report['data_gate_passed'] else 3

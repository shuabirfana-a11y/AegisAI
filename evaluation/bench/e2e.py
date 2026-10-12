"""Approved-question admission, full HTTP evaluation and frozen answer replay."""
import argparse,json,os,sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
import httpx
from .schema import Prediction,OutcomeAudit,reject_labels
from .data import load_benchmark,annotation_exclusion,sha256,read_jsonl,canonical
from .runner import (DEFAULT_MANIFEST,ROOT,evaluate_dataset,write_report,recorded_adapters,clean)
from .http_investigation import InvestigationHTTPAdapter


class UnavailableControl:
    def __init__(self,name,code):self.name=name;self.code=code;self.records={};self.configuration={}
    def run(self,question,sources):
        return Prediction(question_id=question.id,baseline=self.name,status='NOT_EVALUATED',error_code=self.code)


class ApprovedAdapter:
    """Only IDs are shared with transport; labels stay in the final scorer."""
    def __init__(self,inner,approved):
        self.inner=inner;self.approved=frozenset(approved);self.name=inner.name
        self.recorded=getattr(inner,'recorded',False);self.configuration=getattr(inner,'configuration',{})
    def run(self,question,sources):
        if question.id not in self.approved:
            return Prediction(question_id=question.id,baseline=self.name,status='NOT_EVALUATED',error_code='GROUND_TRUTH_NOT_APPROVED')
        result=self.inner.run(question,sources)
        if result.status=='SUCCEEDED' and self.name=='aegisai' and result.metadata.get('is_mock') is not False:
            return Prediction(question_id=question.id,baseline=self.name,status='NOT_EVALUATED',
                error_code='MOCK_OUTPUT_NOT_FORMAL',metadata=result.metadata)
        return result


def evaluate_http(data,adapter,*,run_id=None,audits=None,adapters=None):
    by_id={q.id:q for q in data['questions']}
    approved={a.id for a in data['eligible_gold'] if a.id in by_id and annotation_exclusion(by_id[a.id],a) is None}
    controls=adapters or [UnavailableControl('rag_only','INDEPENDENT_RAG_CONTROL_NOT_IMPLEMENTED'),
        UnavailableControl('agent_without_verification','INDEPENDENT_ABLATION_NOT_IMPLEMENTED'),adapter]
    wrapped=[ApprovedAdapter(a,approved) for a in controls]
    report=evaluate_dataset(data,adapters=wrapped,audits=audits,run_id=run_id)
    report['parameters'].update(evaluation_mode='ONLINE',default_mode='EXPLICIT_HTTP_APPROVED_QUESTIONS',
        http_executed=bool(getattr(adapter,'records',{})),business_rules_modified=False,
        annotation_input_policy='ONLY_APPROVAL_IDS_TO_GATE; LABELS_FINAL_SCORER_ONLY')
    report['limitations']+=[
        'Online uses public Investigation API; no internal Orchestrator/Agent/model calls.',
        'Raw database source UUIDs and citation hashes are retained, not relabelled as frozen corpus evidence.',
        'Normalized source/inventory equivalence across baselines is not independently attested; no fair ablation claim.',
        'Missing native fact fields remain missing; human expected answers are not adjusted to system output.',
        'No-verification is an independent experimental control, never a production bypass switch.']
    # Actual persisted model/prompt identifiers, not local evaluator environment defaults.
    observed={canonical({k:p['metadata'].get(k) for k in ('provider','model','prompt_version','is_mock')})
              for p in report['variants'].get('aegisai',{}).get('predictions',[]) if p['metadata'].get('model')}
    report['observed_model_configurations']=[json.loads(x) for x in sorted(observed)]
    return report


def checked_output(path,manifest):
    output=Path(path).resolve()
    evaluation_root=Path(manifest).resolve().parents[2]
    for tree in (ROOT/'evaluation',evaluation_root):
        for name in ('ground_truth','datasets','source_contracts'):
            if output.is_relative_to((tree/name).resolve()):raise ValueError('Report output cannot modify data or annotation directories')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Experiment output already exists; use a new directory')
    return output


def checked_base_url(value):
    u=urlsplit(value)
    if u.scheme not in {'http','https'} or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError('Credential-free HTTP API base URL required')
    if u.scheme!='https' and u.hostname not in {'localhost','127.0.0.1','::1'}:
        raise ValueError('Remote authenticated API requires HTTPS')
    return value


def write_e2e(report,output,records):
    write_report(report,output)
    records=clean(records)
    path=output/'native-http-records.json'
    path.write_text(json.dumps(records,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    lines=['','## Risk and abstention (reviewed gold required)','',
           '| Baseline | Risk Accuracy | Priority Accuracy | Abstention Quality |',
           '|---|---|---|---|']
    def pct(v):return 'NOT_EVALUATED' if v is None else f'{v*100:.2f}%'
    for name,v in report['variants'].items():
        m=v['metrics'];lines.append(f"| {name} | {pct(m['risk_accuracy'])} | {pct(m['priority_accuracy'])} | {pct(m['abstention']['quality_accuracy'])} |")
    with (output/'report.md').open('a',encoding='utf-8',newline='\n') as f:f.write('\n'.join(lines)+'\n')
    receipt={k:report[k] for k in ('run_id','dataset_version','dataset_fingerprint','dataset_manifest','git',
        'evaluator_file_hashes','parameters','observed_model_configurations')}
    receipt.update(report_sha256=sha256(output/'report.json'),predictions_sha256=sha256(output/'predictions.jsonl'),
        native_records_sha256=sha256(path),annotation_gate='EXISTING_INDEPENDENT_HUMAN_GOLD',
        outcome_audit_gate='EXISTING_COMPLETE_INDEPENDENT_SEMANTIC_AUDIT')
    (output/'experiment.json').write_text(json.dumps(clean(receipt),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def main(argv=None):
    parser=argparse.ArgumentParser(description='Full HTTP AegisBench preparation; approved human gold required')
    parser.add_argument('--mode',choices=['online','offline'],required=True)
    parser.add_argument('--manifest',type=Path,default=DEFAULT_MANIFEST)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--bindings',type=Path)
    parser.add_argument('--timeout',type=float,default=180)
    parser.add_argument('--outcome-audit',type=Path)
    parser.add_argument('--rescore-report',type=Path)
    args=parser.parse_args(argv)
    if args.mode=='offline' and not args.rescore_report:parser.error('Offline mode requires --rescore-report')
    if args.mode=='online' and args.rescore_report:parser.error('Online execution and recorded replay are separate modes')
    data=load_benchmark(args.manifest);run_id=str(uuid4())
    output=checked_output(args.output or ROOT/'work/aegisbench-e2e'/run_id,args.manifest)
    audits=[OutcomeAudit.model_validate(x) for x in read_jsonl(args.outcome_audit)] if args.outcome_audit else []
    client=None;records={}
    try:
        if args.mode=='offline':
            old=json.loads(args.rescore_report.read_text(encoding='utf-8-sig'))
            if old['parameters'].get('evaluation_mode') not in {'ONLINE','OFFLINE'}:
                raise ValueError('Replay requires a full HTTP evaluation record')
            receipt=json.loads((args.rescore_report.parent/'experiment.json').read_text(encoding='utf-8-sig'))
            native_path=args.rescore_report.parent/'native-http-records.json'
            if receipt.get('native_records_sha256')!=sha256(native_path):raise ValueError('Native HTTP record hash mismatch')
            adapters,rescore_of=recorded_adapters(args.rescore_report,data)
            records=json.loads(native_path.read_text(encoding='utf-8-sig'))
            native=next((a for a in adapters if a.name=='aegisai'),UnavailableControl('aegisai','MISSING_RECORDED_FULL_SYSTEM'))
            report=evaluate_http(data,native,run_id=run_id,audits=audits,adapters=adapters)
            report['rescore_of']=rescore_of;report['parameters'].update(evaluation_mode='OFFLINE',http_executed=False,
                default_mode='FROZEN_FULL_HTTP_RECORDS')
        else:
            bindings=json.loads(args.bindings.read_text(encoding='utf-8-sig')) if args.bindings else {}
            reject_labels(bindings)
            if not isinstance(bindings,dict):raise ValueError('Question-to-inventory binding object required')
            if data['eligible_gold']:
                client=httpx.Client(base_url=checked_base_url(args.base_url),follow_redirects=False,trust_env=False)
                native=InvestigationHTTPAdapter(client=client,token=os.environ.get('AEGIS_ASSET_TOKEN',''),
                    bindings=bindings,timeout=args.timeout)
            else:native=UnavailableControl('aegisai','GROUND_TRUTH_NOT_APPROVED')
            report=evaluate_http(data,native,run_id=run_id,audits=audits)
            records=native.records
        report['parameters'].update(client_timeout_seconds=args.timeout,
            binding_file_sha256=sha256(args.bindings) if args.bindings else None,
            source_inventory_equivalence='NOT_INDEPENDENTLY_ATTESTED')
        write_e2e(report,output,records)
        print(json.dumps({'mode':args.mode,'samples':report['sample_count'],'approved':report['eligible_gold_count'],
            'quality_status':report['quality_status'],'http_executed':report['parameters']['http_executed'],'output':str(output)}))
        return 0
    finally:
        if client:client.close()

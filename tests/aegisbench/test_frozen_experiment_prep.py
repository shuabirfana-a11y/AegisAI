"""Preparation only: real supplied human approvals, no model/API/scoring work."""
import hashlib,json
from pathlib import Path
import pytest
from evaluation.bench.data import load_benchmark,canonical
from evaluation.bench.runner import ROOT,DEFAULT_MANIFEST
from evaluation.bench.readiness import inspect_readiness
from evaluation.bench.http_investigation import build_request
from tests.aegisbench.test_data import bundle
from uuid import uuid4

MANIFEST=ROOT/'evaluation/datasets/AegisBench-v0.3-human39-20261013/manifest.json'
CONFIG=ROOT/'experiments/config/experiment-001-prepared.json'


def config():return json.loads(CONFIG.read_text(encoding='utf-8'))


def test_config_dataset_version_count_and_file_pins_are_consistent():
    c=config();data=load_benchmark(MANIFEST)
    assert c['dataset']['version']==data['manifest']['dataset_version']
    assert c['dataset']['approved_count']==len(data['eligible_gold'])==39
    assert c['dataset']['manifest_sha256']==hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert c['admission']['minimum_approved']==10 and c['admission']['data_gate_passed'] is True
    assert c['execution']['authorized_for_this_stage'] is False and c['execution']['formal_experiment_executed'] is False


def test_approved_and_rejected_signed_originals_and_answer_projection_are_immutable():
    data=load_benchmark(MANIFEST)
    assert len(data['questions'])==49 and len(data['annotations'])==39
    assert all(a.review_status=='APPROVED' and a.origin=='HUMAN_GOLD' for a in data['eligible_gold'])
    approvals=list((ROOT/'evaluation/ground_truth/samples/approved').glob('*.json'))
    rejected=list((ROOT/'evaluation/ground_truth/samples/rejected').glob('*.json'))
    assert len(approvals)==39 and len(rejected)==10
    by_id={a.id:a for a in data['annotations']}
    for path in approvals:
        row=json.loads(path.read_text(encoding='utf-8'))
        content={k:v for k,v in row.items() if k not in ('content_sha256','annotation','history')}
        digest=hashlib.sha256(canonical(content).encode()).hexdigest()
        assert digest==row['content_sha256']==row['annotation']['reviewed_content_sha256']
        assert row['annotation']['annotator']!=row['annotation']['reviewer']
        assert by_id[row['id']].expected_answer=={k:row['expected_answer'][k] for k in row['evaluation']['scored_fields']}
        assert row['evaluation']['export_status']=='NOT_PREPARED'
    assert not {json.loads(p.read_text(encoding='utf-8'))['id'] for p in rejected}&set(by_id)


def test_old_frozen_manifest_is_kept_and_new_readiness_never_calls_network(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Preparation must not run a model/API/scorer')
    monkeypatch.setattr('httpx.Client',forbidden)
    monkeypatch.setattr('evaluation.bench.quality.score_variant',forbidden)
    assert inspect_readiness(DEFAULT_MANIFEST)['eligible_gold_count']==0
    new=inspect_readiness(MANIFEST)
    assert new['eligible_gold_count']==39 and new['data_gate_passed'] is True
    assert new['formal_experiment_executed'] is False and new['quality_status']=='NOT_EVALUATED'


def test_runtime_requests_include_no_human_answer_or_approval_metadata():
    data=load_benchmark(MANIFEST);admitted={a.id for a in data['eligible_gold']}
    for q in data['questions']:
        if q.id not in admitted:continue
        body=build_request(q,{'asset_id':str(uuid4()),'component_id':str(uuid4())})
        text=json.dumps(body)
        assert all(k not in text for k in ('expected_answer','evidence_refs','review_status','annotator','reviewer'))
        assert q.id not in text


def test_missing_gold_still_refuses_data_admission(tmp_path):
    report=inspect_readiness(bundle(tmp_path))
    assert report['eligible_gold_count']==0 and report['data_gate_passed'] is False
    assert report['formal_experiment_executed'] is False


def test_model_prompt_and_source_configuration_are_frozen_without_answer_llm():
    c=config()
    assert c['model']['provider']=='openai_compatible' and c['model']['temperature']==0.0
    assert c['model']['timeout_seconds']==40.0
    assert c['model']['manifest_digest'].startswith('sha256:') and c['model']['blobs_verified'] is True
    for p in c['prompt']['source_files']:
        current=hashlib.sha256((ROOT/p['path']).read_bytes()).hexdigest()
        if p['path']=='backend/app/agents/investigation/planner.py':
            # This v4 experiment is preserved history, never the active v5 profile.
            exception=json.loads((ROOT/'docs/phase13f2/source_hash_exceptions.json').read_text(encoding='utf-8'))['changes'][p['path']]
            assert exception['authorization']=='PHASE13F2_USER_AUTHORIZED_INPUT_PLANNER_AND_CONFLICT_HANDOFF'
            assert exception['previous_sha256']==p['sha256']
            assert exception['current_sha256']==current
        else:assert current==p['sha256']
    assert c['prompt']['planner_version']=='investigation-plan-v4'
    assert c['prompt']['answer_prompt_version']=='NOT_APPLICABLE_DETERMINISTIC_TEMPLATE'
    assert c['system']['git_commit']=='c636c51111c64f04f0eec5c003d15df380a27a54'


def test_published_model_manifest_bytes_match_the_pinned_artifact_digest():
    c=config();path=ROOT/'experiments/config/model-manifest.json'
    assert 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()==c['model']['manifest_digest']
    model=json.loads(path.read_text(encoding='utf-8'))
    receipt=json.loads((ROOT/'docs/phase13e2/MODEL_ARTIFACT.json').read_text(encoding='utf-8'))
    assert {r['digest'] for r in receipt['blobs']}=={r['digest'] for r in [model['config'],*model['layers']]}


def test_report_template_has_no_fabricated_result_and_baselines_are_not_ready():
    c=config();report=json.loads((ROOT/'experiments/config/report-template.json').read_text(encoding='utf-8'))
    assert c['baselines']['rag_only']['status']=='NOT_READY'
    assert c['baselines']['agent_without_verification']['status']=='NOT_READY'
    assert report['record_kind']=='REPORT_TEMPLATE_NOT_EXECUTED'
    assert report['formal_experiment_executed'] is False
    assert all(x is None for x in report['metrics'].values())


def test_manifest_reports_partial_human_approval_and_policy_scope():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert manifest['gold_status']=='PARTIALLY_APPROVED_39_REJECTED_10'
    assert (manifest['approved_count'],manifest['rejected_count'])==(39,10)
    risk_scope=next(x for x in manifest['limitations'] if 'risk labels' in x)
    assert 'Human-approved' in risk_scope and 'drafts' not in risk_scope
    assert 'policy conformance' in risk_scope and 'not production risk ground truth' in risk_scope


def test_report_scopes_approval_checks_to_approved_records_only():
    report=(ROOT/'PHASE_13E2_PREP_RESULT.md').read_text(encoding='utf-8')
    assert '49条结构、题目/内容摘要与来源定位检查通过' in report
    assert '39条批准记录的复核绑定摘要和完整批准清单通过' in report
    assert '10条退回记录不计入批准门禁' in report
    rejected=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'evaluation/ground_truth/samples/rejected').glob('*.json')]
    assert all(row['annotation']['reviewed_content_sha256'] is None for row in rejected)

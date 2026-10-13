"""Synthetic admission controls; no human answers or formal experiment are created."""
import hashlib
import importlib
import json
from pathlib import Path
import pytest
from tests.aegisbench.test_data import bundle, question, annotation
from evaluation.bench.runner import DEFAULT_MANIFEST


def module():
    try:return importlib.import_module('evaluation.bench.readiness')
    except ModuleNotFoundError:pytest.fail('Formal readiness preflight is missing')


def approved_bundle(tmp_path,count=10):
    path=bundle(tmp_path); manifest=json.loads(path.read_text(encoding='utf-8'))
    questions=[question(id=f'q{i}',origin='REAL_SOURCE',input_context={'target':'CVE-2099-0001','version':None}) for i in range(count)]
    answers=[annotation(id=f'q{i}',origin='HUMAN_GOLD',review_status='APPROVED',annotator_type='HUMAN',
                        reviewer_type='HUMAN',annotator='SYNTHETIC A',reviewer='SYNTHETIC B') for i in range(count)]
    for name,rows in [('questions.jsonl',questions),('annotations.jsonl',answers)]:
        target=path.parent/name;target.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
        manifest[name.split('.')[0]+'_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    manifest['sample_count']=count;path.write_text(json.dumps(manifest),encoding='utf-8')
    return path


@pytest.mark.parametrize('count,ready',[(0,False),(9,False),(10,True)])
def test_only_valid_human_gold_meets_the_ten_sample_data_gate(tmp_path,count,ready):
    report=module().inspect_readiness(approved_bundle(tmp_path,count))
    assert report['eligible_gold_count']==count and report['data_gate_passed'] is ready
    assert report['formal_experiment_executed'] is False
    assert report['quality_status']=='NOT_EVALUATED'


def test_tampered_source_cannot_be_counted_as_approved(tmp_path):
    path=approved_bundle(tmp_path)
    (path.parent/'source.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='hash'):module().inspect_readiness(path)


def test_same_person_approval_is_excluded(tmp_path):
    path=approved_bundle(tmp_path)
    rows=[json.loads(line) for line in (path.parent/'annotations.jsonl').read_text(encoding='utf-8').splitlines()]
    for row in rows:row['reviewer']=row['annotator']
    target=path.parent/'annotations.jsonl';target.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    m=json.loads(path.read_text(encoding='utf-8'));m['annotations_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    path.write_text(json.dumps(m),encoding='utf-8')
    assert module().inspect_readiness(path)['eligible_gold_count']==0


def test_real_candidate_empty_gold_exits_blocked_without_any_network_or_scoring(monkeypatch,tmp_path):
    def forbidden(*args,**kwargs):raise AssertionError('Preflight must not invoke HTTP or score_variant')
    monkeypatch.setattr('httpx.Client',forbidden)
    monkeypatch.setattr('evaluation.bench.quality.score_variant',forbidden)
    output=tmp_path/'readiness'
    assert module().main(['--output',str(output)])==3
    report=json.loads((output/'readiness.json').read_text(encoding='utf-8'))
    assert report['sample_count']==49 and report['eligible_gold_count']==0
    assert report['status']=='BLOCKED_MINIMUM_GOLD' and report['http_executed'] is False
    assert 'expected_answer' not in json.dumps(report) and 'accuracy' not in report
    assert (output/'readiness.md').is_file()


def test_preflight_records_fingerprints_but_never_runtime_answers_or_null_version_completion(tmp_path):
    report=module().inspect_readiness(approved_bundle(tmp_path))
    assert report['annotation_status_counts']['APPROVED']==10
    assert len(report['manifest_sha256'])==64 and len(report['dataset_fingerprint'])==64
    assert 'expected_answer' not in json.dumps(report) and 'CVE-2099-0001' not in json.dumps(report)
    assert report['model_freeze_status']=='NOT_FROZEN'
    assert report['baselines']['rag_only']=='NOT_IMPLEMENTED'


def test_minimum_cannot_be_weakened_and_report_cannot_overwrite_gold_or_old_run(tmp_path):
    with pytest.raises(ValueError):module().inspect_readiness(DEFAULT_MANIFEST,minimum=1)
    existing=tmp_path/'existing';existing.mkdir();(existing/'keep').write_text('keep')
    with pytest.raises(ValueError):module().main(['--output',str(existing)])
    from evaluation.bench.runner import ROOT
    with pytest.raises(ValueError):module().main(['--output',str(ROOT/'evaluation/ground_truth/samples/approved')])


@pytest.mark.parametrize('payload',['{}','[]'])
def test_malformed_manifest_always_leaves_a_blocked_audit_report(tmp_path,payload):
    root=tmp_path/'evaluation/datasets/broken';root.mkdir(parents=True)
    manifest=root/'manifest.json';manifest.write_text(payload,encoding='utf-8')
    output=tmp_path/'blocked'
    assert module().main(['--manifest',str(manifest),'--minimum','49','--output',str(output)])==3
    report=json.loads((output/'readiness.json').read_text(encoding='utf-8'))
    assert report['status']=='BLOCKED_INVALID_DATASET' and report['minimum_approved']==49
    assert report['formal_experiment_executed'] is False


def test_invalid_manual_workflow_shape_also_produces_blocked_report(monkeypatch,tmp_path):
    import evaluation.bench.readiness as readiness
    monkeypatch.setattr(readiness,'ROOT',tmp_path)
    samples=tmp_path/'evaluation/ground_truth/samples/draft';samples.mkdir(parents=True)
    (samples/'invalid.json').write_text('[]',encoding='utf-8')
    output=tmp_path/'blocked'
    assert readiness.main(['--output',str(output)])==3
    report=json.loads((output/'readiness.json').read_text(encoding='utf-8'))
    assert report['status']=='BLOCKED_INVALID_DATASET' and report['http_executed'] is False

"""Temporary synthetic signoffs validate the gate, never populate human gold."""
import hashlib,importlib,json
from pathlib import Path
import pytest
from evaluation.bench.data import load_benchmark,canonical
from evaluation.bench.runner import DEFAULT_MANIFEST
from evaluation.bench.schema import Prediction,Annotation


def module():
    try:return importlib.import_module('evaluation.bench.e2e')
    except ModuleNotFoundError:pytest.fail('HTTP end-to-end evaluation mode is missing')


class NeverCalled:
    name='aegisai';records={};configuration={}
    def run(self,*args):raise AssertionError('No unapproved question may initiate HTTP/model work')


def test_real_49_unapproved_questions_trigger_no_http_or_quality_numbers():
    report=module().evaluate_http(load_benchmark(DEFAULT_MANIFEST),NeverCalled(),run_id='synthetic-admission-control')
    assert report['sample_count']==49 and report['eligible_gold_count']==0
    m=report['variants']['aegisai']['metrics']
    assert m['accuracy'] is None and m['risk_accuracy'] is None and m['hallucination_rate'] is None
    assert m['execution']['NOT_EVALUATED']==49
    assert report['quality_status']=='NOT_EVALUATED' and report['comparison_status']=='NOT_COMPARABLE'


def test_single_admitted_control_keeps_gold_out_of_adapter_and_uses_existing_metrics():
    data=load_benchmark(DEFAULT_MANIFEST);q=data['questions'][0]
    reference=data['annotations'][0].evidence_refs[0]
    gold=Annotation(id=q.id,expected_answer={'risk_level':'HIGH','priority':'P2','private_golden_marker':'SYNTHETIC_LABEL_ONLY'},
        evidence_refs=[reference],confidence='HIGH',review_status='APPROVED',annotator_type='HUMAN',reviewer_type='HUMAN',
        annotator='SYNTHETIC annotator',reviewer='SYNTHETIC reviewer',annotation_note='In-memory protocol fixture, never benchmark gold',
        should_abstain=False,origin='HUMAN_GOLD')
    data={**data,'questions':[q],'annotations':[gold],'eligible_gold':[gold]}
    captured=[]
    class Controlled:
        name='aegisai';records={};configuration={}
        def run(self,question,sources):
            captured.append(question.model_dump())
            return Prediction(question_id=question.id,baseline=self.name,status='SUCCEEDED',
                answer={'risk_level':'HIGH','priority':'P2'},abstained=False,metadata={'is_mock':False})
    report=module().evaluate_http(data,Controlled(),run_id='SYNTHETIC_CONTROL_NOT_BENCHMARK')
    assert len(captured)==1 and 'SYNTHETIC_LABEL_ONLY' not in canonical(captured)
    m=report['variants']['aegisai']['metrics']
    assert m['risk_accuracy']==1 and m['priority_accuracy']==1
    assert m['accuracy']==0 and m['evidence_coverage'] is None


def test_mock_output_cannot_enter_formal_metric_gate():
    # Admission metadata alone never turns a Mock transport fixture into a real run.
    class Mock:
        name='aegisai';records={};configuration={}
        def run(self,q,sources):return Prediction(question_id=q.id,baseline=self.name,status='SUCCEEDED',
            answer={'risk_level':'HIGH'},metadata={'is_mock':True})
    data=load_benchmark(DEFAULT_MANIFEST);q=data['questions'][0]
    gold=data['annotations'][0].model_copy(update={'origin':'HUMAN_GOLD','review_status':'APPROVED',
        'annotator_type':'HUMAN','reviewer_type':'HUMAN','annotator':'Synthetic A','reviewer':'Synthetic B',
        'annotation_note':'Synthetic in-memory gate test'})
    data={**data,'questions':[q],'annotations':[gold],'eligible_gold':[gold]}
    report=module().evaluate_http(data,Mock(),run_id='SYNTHETIC_MOCK_ADMISSION_TEST')
    assert report['variants']['aegisai']['metrics']['accuracy'] is None
    assert report['variants']['aegisai']['predictions'][0]['error_code']=='MOCK_OUTPUT_NOT_FORMAL'


def test_online_cli_with_zero_approved_never_constructs_network_client(monkeypatch,tmp_path):
    def prohibited(*args,**kwargs):raise AssertionError('Client construction should be avoided before human admission')
    monkeypatch.setattr('httpx.Client',prohibited)
    output=tmp_path/'preparation'
    assert module().main(['--mode','online','--output',str(output)])==0
    report=json.loads((output/'report.json').read_text(encoding='utf-8'))
    assert report['parameters']['evaluation_mode']=='ONLINE'
    assert report['parameters']['http_executed'] is False
    assert report['eligible_gold_count']==0
    assert (output/'experiment.json').is_file() and 'NOT_EVALUATED' in (output/'report.md').read_text(encoding='utf-8')


def test_offline_replay_checks_report_and_native_receipt_hashes(tmp_path):
    output=tmp_path/'recorded'
    assert module().main(['--mode','online','--output',str(output)])==0
    replay=tmp_path/'replay'
    assert module().main(['--mode','offline','--rescore-report',str(output/'report.json'),'--output',str(replay)])==0
    assert json.loads((replay/'report.json').read_text(encoding='utf-8'))['parameters']['evaluation_mode']=='OFFLINE'
    with (output/'native-http-records.json').open('a',encoding='utf-8') as f:f.write(' ')
    with pytest.raises(ValueError,match='hash'):
        module().main(['--mode','offline','--rescore-report',str(output/'report.json'),'--output',str(tmp_path/'tampered')])


def test_output_directory_cannot_overwrite_gold_or_existing_experiment(tmp_path):
    from evaluation.bench.runner import ROOT
    with pytest.raises(ValueError):module().main(['--mode','online','--output',str(ROOT/'evaluation/ground_truth/samples/approved')])
    existing=tmp_path/'existing';existing.mkdir();(existing/'keep.json').write_text('{}')
    with pytest.raises(ValueError):module().main(['--mode','online','--output',str(existing)])
    assert (existing/'keep.json').read_text()=='{}'


def test_default_cli_dispatch_stays_offline_and_explicit_mode_selects_new_runner(monkeypatch):
    import evaluate
    calls=[]
    monkeypatch.setattr(evaluate,'legacy_main',lambda argv:calls.append(('legacy',argv)) or 0)
    monkeypatch.setattr(module(),'main',lambda argv:calls.append(('e2e',argv)) or 0)
    assert evaluate.main(['--output','test-legacy'])==0
    assert evaluate.main(['--mode','online','--output','test-new'])==0
    assert [c[0] for c in calls]==['legacy','e2e']

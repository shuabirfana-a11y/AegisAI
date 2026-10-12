"""Synthetic failure/denominator tests; these are not real-model measurements."""
from copy import deepcopy
import json
from uuid import uuid4

import pytest
from app.agents.investigation.planning import InvestigationPlan
from tests.planner.fixtures import valid_plan
from scripts.probe_planner_stability import classify_attempt, summarize, case_sequence, run_stability_case


def attempt(value, status='VALIDATED', **kwargs):
    return {
        'attempt_index': 1, 'validation_status': status, 'issues': [],
        'model_call': {'duration_ms': 10., 'provider': 'openai_compatible',
                       'model': 'SYNTHETIC-non-mock-protocol', 'is_mock': False,
                       'status': 'success', 'usage': {'total_tokens': 5}},
        'diagnostic': {'raw_output': json.dumps(value)}, **kwargs,
    }


def test_classification_keeps_json_schema_and_validation_separate():
    candidate = valid_plan()
    assert classify_attempt(attempt(candidate))['task_legal']
    candidate['tasks'][0]['type'] = 'unknown_action'
    result = classify_attempt(attempt(candidate, 'REJECTED'))
    assert result['json_valid'] and not result['schema_valid'] and not result['task_legal']


@pytest.mark.parametrize('raw', ['invalid', '{"tasks":[],"tasks":[]}', '{"confidence":NaN}', '[]'])
def test_invalid_model_output_cannot_be_counted_as_schema_success(raw):
    record = attempt(valid_plan(), 'REJECTED')
    record['diagnostic']['raw_output'] = raw
    got = classify_attempt(record)
    assert not got['schema_valid'] and not got['task_legal']


def test_no_text_and_redacted_diagnostic_are_explicitly_unmeasured():
    record = attempt(valid_plan(), 'REJECTED', diagnostic=None)
    got = classify_attempt(record)
    assert not got['json_valid'] and not got['schema_valid']
    assert got['diagnostic_available'] is False
    record['diagnostic'] = {'raw_output': json.dumps(valid_plan()), 'redacted': True}
    assert classify_attempt(record)['diagnostic_available'] is False


def test_schema_success_does_not_undo_semantic_rejection():
    got = classify_attempt(attempt(valid_plan(), 'REJECTED'))
    assert got['json_valid'] and got['schema_valid'] and not got['task_legal']


def test_retry_and_failed_logical_run_remain_in_denominators():
    ok = classify_attempt(attempt(valid_plan()))
    no = classify_attempt(attempt({'wrong': True}, 'REJECTED'))
    report = summarize([
        {'case_id': 'one', 'elapsed_ms': 100, 'attempts': [no, ok], 'planner_validated': True,
         'real_mode_confirmed': True, 'full_chain_executed': True, 'gate_accepted': True},
        {'case_id': 'two', 'elapsed_ms': 200, 'attempts': [no, no], 'planner_validated': False,
         'real_mode_confirmed': True, 'full_chain_executed': False, 'gate_accepted': False},
        {'case_id': 'three', 'elapsed_ms': 300, 'attempts': [], 'planner_validated': False,
         'real_mode_confirmed': False, 'full_chain_executed': False, 'gate_accepted': False},
    ])
    assert report['logical_runs'] == 3 and report['provider_attempts'] == 4
    assert report['attempts']['schema_pass_rate'] == .25
    assert report['runs']['task_legal_rate'] == pytest.approx(1/3)
    assert report['runs']['full_chain_success_rate'] == pytest.approx(1/3)
    assert report['mean_elapsed_ms'] == 200


def test_replan_is_not_gate_acceptance_even_when_every_stage_ran():
    report = summarize([{'case_id':'version', 'elapsed_ms':1, 'attempts':[],
        'planner_validated':True, 'real_mode_confirmed':True,
        'full_chain_executed':True, 'gate_accepted':False}])
    assert report['runs']['full_chain_execution_rate'] == 1.
    assert report['runs']['full_chain_success_rate'] == 0.


def test_fixed_case_sequence_covers_20_without_random_filtering():
    cases = [{'case_id': x} for x in ('fact','version','multi')]
    seq = case_sequence(cases)
    assert len(seq) == 20
    assert [x['case_id'] for x in seq].count('fact') == 7
    assert [x['case_id'] for x in seq].count('version') == 7
    assert [x['case_id'] for x in seq].count('multi') == 6
    assert seq == case_sequence(cases)


def test_empty_measurement_reports_missing_values():
    report = summarize([])
    assert report['logical_runs'] == report['provider_attempts'] == 0
    assert report['runs']['task_legal_rate'] is None
    assert report['mean_elapsed_ms'] is None


def test_planner_only_runs_do_not_inflate_full_chain_denominator():
    report = summarize([{'case_id':'fact','elapsed_ms':1,'attempts':[],
        'planner_validated':True,'real_mode_confirmed':True,'chain_attempted':False,
        'full_chain_executed':False,'gate_accepted':False}])
    assert report['full_chain_attempts'] == 0
    assert report['runs']['task_legal_rate'] == 1.
    assert report['runs']['full_chain_success_rate'] is None


def test_attempt_receipt_never_exports_raw_output_or_prompt():
    result = classify_attempt(attempt(valid_plan()))
    assert 'raw_output' not in json.dumps(result) and 'objective' not in json.dumps(result)


def test_runner_retains_failure_and_does_not_read_other_histories(monkeypatch):
    import scripts.probe_planner_stability as module
    def failed(client, case, **kwargs):
        return {'case_id':case['case_id'],'error_code':'PLANNING_FAILED', 'endpoints':{}}
    monkeypatch.setattr(module, 'run_probe', failed)
    class Client:
        def get(self, *args, **kwargs):
            pytest.fail('Failed creation must not load unrelated runs')
    got = run_stability_case(Client(), {'case_id':'fact','request':{'user_query':'SYNTHETIC create failure'}}, lambda id: None)
    assert not got['planner_validated'] and not got['gate_accepted']
    assert got['error_code'] == 'PLANNING_FAILED'


def test_interrupted_run_records_failure_and_cancels_only_its_own_id(monkeypatch):
    import scripts.probe_planner_stability as module
    owned = str(uuid4())
    monkeypatch.setattr(module, 'run_probe', lambda *a,**k: {
        'investigation_id':owned,'error_code':'PROBE_POLL_TIMEOUT','endpoints':{}})
    class Response:
        is_success = False
    class Client:
        posts = []
        def post(self, path, **kwargs):
            self.posts.append(path)
            return Response()
        def get(self, *a, **k):
            return Response()
    client = Client()
    got = run_stability_case(client, {'case_id':'fact','request':{'user_query':'SYNTHETIC timeout'}}, lambda id: None)
    assert client.posts == [f'/api/investigations/{owned}/cancel']
    assert got['error_code'] == 'PROBE_POLL_TIMEOUT' and not got['gate_accepted']


def test_prewarm_uses_utf8_and_never_downloads_an_unknown_model(monkeypatch):
    from types import SimpleNamespace
    import scripts.probe_planner_stability as module
    calls = []
    def native(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess, 'run', native)
    module.prewarm_model('SYNTHETIC-ollama', 'SYNTHETIC-model')
    assert calls[0][0][1] == 'show' and calls[1][0][1] == 'run'
    assert calls[1][1]['input'] == ''
    assert calls[1][1]['encoding'] == 'utf-8' and calls[1][1]['errors'] == 'replace'
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=1))
    with pytest.raises(RuntimeError, match='MODEL_NOT_INSTALLED'):
        module.prewarm_model('SYNTHETIC-ollama', 'missing')

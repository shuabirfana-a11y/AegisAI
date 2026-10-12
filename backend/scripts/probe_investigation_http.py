"""Bounded loopback HTTP audit. Never generates answers or evaluates model quality."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.investigation_api.schemas import (
    ApiError, InvestigationCreateRequest, InvestigationCreateResponse,
    InvestigationStatusResponse, TraceResponse, ArtifactResponse,
    IntegrationResponse, AnswerResponse, HistoryResponse,
)


class ProbeCase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    case_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    data_origin: Literal['REAL_SOURCE', 'SYNTHETIC_TEST']
    requested_mode: Literal['MOCK', 'REAL']
    description: str
    request: InvestigationCreateRequest


def load_case(path):
    case = ProbeCase.model_validate_json(Path(path).read_text(encoding='utf-8'))
    return {**case.model_dump(), 'request': case.request}


def checked_origin(value):
    try:
        url = urlsplit(value)
        if (url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost', '::1')
                or url.username or url.password or url.query or url.fragment
                or url.path not in ('', '/') or (url.port is not None and not 1 <= url.port <= 65535)):
            raise ValueError()
    except ValueError:
        raise ValueError('LOOPBACK_ORIGIN_REQUIRED') from None
    return value.rstrip('/')


def check_mode(requested, provider, is_mock):
    if requested not in ('MOCK', 'REAL') or (provider == 'mock') != is_mock:
        raise ValueError('MODEL_METADATA_INCONSISTENT')
    matched = is_mock if requested == 'MOCK' else not is_mock
    return {'requested': requested, 'provider': provider, 'is_mock': is_mock,
            'observed': 'MOCK' if is_mock else 'NON_MOCK', 'matched': matched,
            'error_code': None if matched else 'MODEL_MODE_MISMATCH',
            'model_quality_evaluated': False}


def check_persisted_mode(requested, saved):
    if saved is None:
        return {'requested': requested, 'observed': 'UNKNOWN', 'matched': False,
                'source': None, 'error_code': 'MODEL_EXECUTION_UNCONFIRMED',
                'model_quality_evaluated': False}
    value = check_mode(requested, saved.provider, saved.execution_mode == 'MOCK')
    return {**value, 'source': saved.source, 'model': saved.model,
            'planner_attempt_count': saved.attempt_count}


def run_probe(client, case, *, timeout_seconds=45, poll_interval=.1, requested_mode=None):
    """Client must be a TCP httpx.Client; reports contain only allowlisted metadata."""
    checked_origin(str(client.base_url))
    if not 0 < timeout_seconds <= 120 or not 0 < poll_interval <= 5:
        raise ValueError('INVALID_POLL_LIMIT')
    report = {'case_id': case['case_id'], 'data_origin': case['data_origin'],
              'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'transport': 'LOOPBACK_HTTP', 'benchmark': False, 'endpoints': {},
              'chain_verified': False, 'ready': False, 'error_code': None}

    def call(name, method, path, schema, **kwargs):
        response = client.request(method, path, **kwargs)
        body = response.json()
        value = schema.model_validate(body) if response.is_success else ApiError.model_validate(body)
        report['endpoints'][name] = {'http_status': response.status_code, 'schema_valid': True}
        if not response.is_success:
            report['endpoints'][name]['error_code'] = value.error_code
        return value if response.is_success else None

    body = case['request'].model_dump(mode='json')
    key = body.get('idempotency_key') or 'phase12c-' + uuid4().hex
    created = call('create', 'POST', '/api/investigations', InvestigationCreateResponse,
                   json=body, headers={'Idempotency-Key': key})
    if created is None:
        report['error_code'] = report['endpoints']['create']['error_code']
        return report
    id = str(created.investigation_id)
    prefix = '/api/investigations/' + id
    report['investigation_id'] = id
    report['model_mode'] = check_mode(requested_mode or case['requested_mode'], created.model_provider, created.is_mock)
    deadline = time.monotonic() + timeout_seconds
    while True:
        status = call('status', 'GET', prefix + '/status', InvestigationStatusResponse)
        if status is None or status.overall_status != 'RUNNING':
            break
        if time.monotonic() >= deadline:
            report['error_code'] = 'PROBE_POLL_TIMEOUT'
            # Do not cancel user work or read an incomplete run as a final answer.
            return report
        time.sleep(min(poll_interval, max(0, deadline - time.monotonic())))
    trace = call('trace', 'GET', prefix + '/trace', TraceResponse)
    report['creation_model_mode'] = report['model_mode']
    report['model_mode'] = check_persisted_mode(requested_mode or case['requested_mode'],
                                              trace.model_execution if trace else None)
    artifacts = call('artifacts', 'GET', prefix + '/artifacts', ArtifactResponse)
    gate = call('integration', 'GET', prefix + '/integration', IntegrationResponse)
    answer = call('answer', 'GET', prefix + '/answer', AnswerResponse)
    call('history', 'GET', '/api/investigations/history?limit=10', HistoryResponse)
    if status is not None and status.overall_status != 'RUNNING':
        call('cancel', 'POST', prefix + '/cancel', InvestigationStatusResponse, json={})
    report.update(overall_status=status.overall_status if status else None,
                  current_stage=status.current_stage if status else None,
                  planner_present=bool(trace and trace.planner),
                  planner_validation=trace.planner.validation_status if trace and trace.planner else None,
                  chain_error_code=trace.error_code if trace else None,
                  agent_run_count=len(trace.agent_runs) if trace else 0,
                  tool_call_count=sum(len(run.tool_calls) for run in trace.agent_runs) if trace else 0,
                  artifact_count=sum(getattr(artifacts, key) is not None for key in
                                     ('investigation', 'verification', 'analysis')) if artifacts else 0,
                  integration_status=gate.status if gate else None,
                  answer_status=answer.answer_status if answer else None,
                  citation_count=len(answer.citations) if answer else 0)
    report['chain_verified'] = bool(
        status and status.overall_status in ('SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS')
        and trace and trace.planner and trace.planner.validation_status == 'VALIDATED' and len(trace.agent_runs) == 3
        and report['artifact_count'] == 3 and gate and answer
        and gate.status in ('PASS', 'PASS_WITH_WARNINGS')
        and all(item['http_status'] < 300 for item in report['endpoints'].values())
        and len(report['endpoints']) == 8)
    report['ready'] = report['chain_verified'] and report['model_mode']['matched']
    report['error_code'] = (report['model_mode']['error_code'] or
                            (trace.error_code if trace else None) or
                            (None if report['chain_verified'] else 'CHAIN_NOT_COMPLETE'))
    return report


class ProbeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # Do not echo arbitrary argument values; main writes a fresh failure report.
        raise ValueError('INVALID_PROBE_ARGUMENT')


def main():
    default_output = ROOT / 'work/phase12c/live-http-report.json'
    parser = ProbeArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--base-url', default='http://127.0.0.1:8769')
    parser.add_argument('--case', type=Path, default=ROOT / 'demo/phase12c/real-source-case.json')
    parser.add_argument('--mode', choices=['MOCK', 'REAL'])
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--output', type=Path, default=default_output)
    output = default_output
    try:
        # Locate the user's report before validating other CLI options. Otherwise
        # argparse would exit and leave a previous ready=true report unchanged.
        output_parser = ProbeArgumentParser(add_help=False, allow_abbrev=False)
        output_parser.add_argument('--output', type=Path, default=default_output)
        output = output_parser.parse_known_args()[0].output
        args = parser.parse_args()
        origin = checked_origin(args.base_url)
        headers = {'Origin': origin}
        token = os.environ.get('AEGIS_ASSET_TOKEN')
        if token:
            headers['Authorization'] = 'Bearer ' + token
        with httpx.Client(base_url=origin, headers=headers, trust_env=False,
                          follow_redirects=False, timeout=5) as client:
            report = run_probe(client, load_case(args.case), timeout_seconds=args.timeout, requested_mode=args.mode)
    except (OSError, ValueError, httpx.HTTPError):
        # Exception objects can contain request data or headers; never serialize them.
        report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'ready': False,
                  'chain_verified': False, 'benchmark': False, 'error_code': 'HTTP_PROBE_FAILED'}
        exit_code = 2
    else:
        exit_code = 0 if report['ready'] else 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())

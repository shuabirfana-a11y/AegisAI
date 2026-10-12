"""Bounded Gateway/Planner connectivity probe. No execution or accuracy evaluation."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.llm.config import ModelConfig
from app.llm.gateway import ModelGateway
from app.llm.schemas import CallRecord, Message, TextRequest, StructuredRequest
from app.planner.context import build_context
from app.planner.llm_planner import LLMTaskPlanner
from app.planner.schemas import PlannerInput, PROMPT_VERSION
from app.runtime.contracts import RuntimePolicy
from app.investigation_api.schemas import InvestigationCreateRequest


class StrictReport(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)


class VulnerabilityAnalysis(StrictReport):
    """SYNTHETIC protocol shape, not a vulnerability assessment."""
    cve: str = Field(pattern=r'^CVE-\d{4}-\d{4,}$')
    risk: Literal['high', 'medium', 'low', 'unknown']
    evidence: list[str] = Field(max_length=5)


class PlannerCheck(StrictReport):
    status: Literal['VALIDATED', 'PLANNING_FAILED']
    attempt_count: int = Field(ge=0, le=2)
    error_codes: tuple[str, ...] = ()
    task_types: tuple[str, ...] = ()


class Section(StrictReport):
    kind: str
    success: bool
    call_records: tuple[CallRecord, ...] = ()
    planner: PlannerCheck | None = None
    error_code: str | None = None


class ProviderProbeReport(StrictReport):
    schema_version: Literal['phase12d-provider-probe-v1'] = 'phase12d-provider-probe-v1'
    checked_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider: str
    model: str
    execution_mode: Literal['MOCK', 'REAL']
    data_origin: str = 'UNVERIFIED_SERVICE'
    structured_data_origin: Literal['SYNTHETIC_PROTOCOL'] = 'SYNTHETIC_PROTOCOL'
    embedding_provider: str
    embedding_exercised: Literal[False] = False
    benchmark: Literal[False] = False
    prompt_version: str = PROMPT_VERSION
    ready: bool
    structured_attempted: int
    structured_passed: int
    planner_attempted: int
    planner_validated: int
    planner_checks: tuple[PlannerCheck, ...]
    call_records: tuple[CallRecord, ...]
    sections: tuple[Section, ...]
    error_code: str | None = None


class AttemptSink:
    def record_attempt(self, context, attempt):
        # The existing Planner keeps diagnostics in its local outcome.
        # This standalone probe never exports them or executes its plan.
        pass


def call_record(result):
    return CallRecord.model_validate({key: value for key, value in result.model_dump().items()
                                     if key in CallRecord.model_fields})


def run_section(gateway, kind, *, planner_input=None):
    if kind == 'health':
        result = gateway.health_check()
    elif kind == 'text':
        result = gateway.generate_text(TextRequest(max_output_tokens=64, messages=[
            Message(role='user', content='请用一句中文说明可以输出JSON。这是接口检查，不是安全结论。')]))
    elif kind == 'structured':
        result = gateway.generate_structured(StructuredRequest(max_output_tokens=128, messages=[
            Message(role='user', content='这是合成协议检查。仅返回JSON：cve为CVE-2099-9999001，risk为unknown，evidence为空数组。不是安全事实。')]),
            output_model=VulnerabilityAnalysis)
    elif kind == 'planner':
        context = build_context(planner_input, 'phase12d-connectivity-probe', RuntimePolicy(), uuid4(), uuid4())
        outcome = LLMTaskPlanner(gateway, AttemptSink()).plan(planner_input, context)
        calls = tuple(CallRecord.model_validate_json(json.dumps(a.model_call, allow_nan=False))
                      for a in outcome.attempts)
        tasks = () if not outcome.validated_plan else tuple(
            task['type'] for task in json.loads(outcome.validated_plan.candidate_json)['tasks'])
        check = PlannerCheck(status=outcome.status, attempt_count=len(outcome.attempts),
                             error_codes=tuple(dict.fromkeys(i.code for i in outcome.issues)),
                             task_types=tasks)
        return Section(kind=kind, success=outcome.status == 'VALIDATED', call_records=calls,
                       planner=check, error_code=None if outcome.status == 'VALIDATED' else 'PLANNING_FAILED')
    else:
        raise ValueError('INVALID_PROBE_SECTION')
    return Section(kind=kind, success=result.status == 'success', call_records=(call_record(result),),
                   error_code=result.error.code if result.error else None)


def assemble(config, sections, *, data_origin='UNVERIFIED_SERVICE'):
    structured = tuple(s for s in sections if s.kind == 'structured')
    planning = tuple(s.planner for s in sections if s.planner is not None)
    ready = bool(len(sections) >= 9 and all(s.success for s in sections))
    return ProviderProbeReport(provider=config.provider, model=config.model,
        execution_mode='MOCK' if config.provider == 'mock' else 'REAL', data_origin=data_origin,
        embedding_provider=config.embedding_provider, ready=ready,
        structured_attempted=len(structured), structured_passed=sum(s.success for s in structured),
        planner_attempted=len(planning), planner_validated=sum(p.status == 'VALIDATED' for p in planning),
        planner_checks=planning, call_records=tuple(c for s in sections for c in s.call_records),
        sections=tuple(sections), error_code=None if ready else next(
            (s.error_code for s in sections if not s.success), 'PROBE_NOT_COMPLETE'))


def run_provider_probe(gateway: ModelGateway, planner_inputs: tuple[PlannerInput, ...]) -> ProviderProbeReport:
    sections = [run_section(gateway, 'health')]
    if sections[-1].success:
        sections.append(run_section(gateway, 'text'))
        if sections[-1].success:
            sections.extend(run_section(gateway, 'structured') for _ in range(5))
            sections.extend(run_section(gateway, 'planner', planner_input=i) for i in planner_inputs)
    return assemble(gateway.config, sections)


def run_bounded_worker(command, *, timeout_seconds):
    if not 0 < timeout_seconds <= 180:
        raise ValueError('INVALID_WORKER_LIMIT')
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding='utf-8', errors='replace',
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=5)
        raise TimeoutError('PROVIDER_PROBE_TIMEOUT') from None
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def planner_inputs(path):
    document = json.loads(path.read_text(encoding='utf-8-sig'))
    request = InvestigationCreateRequest.model_validate(document['request'])
    request = request.model_copy(update={'idempotency_key': 'phase12d-probe-' + uuid4().hex})
    complex_input = request.to_internal().planner_input
    target = request.asset_scope.target
    if not target:
        raise ValueError('FIXED_TARGET_REQUIRED')
    simple = PlannerInput(query={'question': target + '是什么？', 'target': target,
                                 'request_key': 'phase12d-probe-' + uuid4().hex})
    return (simple, complex_input)


class ProbeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('INVALID_PROVIDER_PROBE_ARGUMENT')


def write_report(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def main():
    default_output = ROOT / 'work/phase12d/provider-report.json'
    output = default_output
    parser = ProbeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--output', type=Path, default=default_output)
    parser.add_argument('--case', type=Path, default=ROOT / 'demo/phase12c/real-source-case.json')
    parser.add_argument('--mode', choices=['MOCK', 'REAL'], default='MOCK')
    parser.add_argument('--worker', choices=['health', 'text', 'structured', 'planner'])
    parser.add_argument('--planner-index', type=int, choices=[0, 1], default=0)
    try:
        output_parser = ProbeParser(add_help=False, allow_abbrev=False)
        output_parser.add_argument('--output', type=Path, default=default_output)
        output = output_parser.parse_known_args()[0].output
        args = parser.parse_args()
        config = ModelConfig.from_env()
        observed = 'MOCK' if config.provider == 'mock' else 'REAL'
        if observed != args.mode:
            raise ValueError('MODEL_MODE_MISMATCH')
        if observed == 'REAL' and urlsplit(config.api_base or '').hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('LOCAL_MODEL_SERVICE_REQUIRED')
        if args.worker:
            inputs = planner_inputs(args.case) if args.worker == 'planner' else ()
            with ModelGateway(config) as gateway:
                section = run_section(gateway, args.worker,
                    planner_input=inputs[args.planner_index] if inputs else None)
            write_report(output, section.model_dump(mode='json'))
            return 0
        sections = []
        deadline = time.monotonic() + 900
        jobs = [('health', 0), ('text', 0)] + [('structured', 0)] * 5 + [('planner', 0), ('planner', 1)]
        work = output.parent / 'provider-sections' / uuid4().hex
        work.mkdir(parents=True, exist_ok=True)
        for index, (kind, planner_index) in enumerate(jobs):
            destination = work / (str(index) + '.json')
            command = [sys.executable, str(Path(__file__).resolve()), '--worker', kind,
                       '--case', str(args.case.resolve()), '--mode', args.mode,
                       '--planner-index', str(planner_index), '--output', str(destination)]
            try:
                result = run_bounded_worker(command, timeout_seconds=min(180, max(.01, deadline - time.monotonic())))
                if result.returncode != 0:
                    raise ValueError('PROVIDER_WORKER_FAILED')
                section = Section.model_validate_json(destination.read_text(encoding='utf-8'))
            except (OSError, TimeoutError, ValueError):
                section = Section(kind=kind, success=False, error_code='PROVIDER_WORKER_FAILED')
            sections.append(section)
            if kind in ('health', 'text') and not section.success:
                break
            if time.monotonic() >= deadline:
                break
        report = assemble(config, sections, data_origin='MOCK' if observed == 'MOCK' else 'LOCAL_MODEL_SERVICE')
        value = report.model_dump(mode='json')
        exit_code = 0 if report.ready else 1
    except (OSError, ValueError, TypeError):
        value = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'ready': False,
                 'benchmark': False, 'error_code': 'PROVIDER_PROBE_FAILED'}
        exit_code = 2
    write_report(output, value)
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())

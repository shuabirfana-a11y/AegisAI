"""Deterministic, no-DB reproductions of the whole-branch review findings."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.agents.investigation.schemas import InvestigationArtifact, InvestigationRunResult
from app.assistant.contracts import QueryRequest
from app.investigation_api.errors import ApiFailure
from app.investigation_api.projection import public_artifact
from app.investigation_api.schemas import PublicInvestigationArtifact
from app.investigation_api.service import InvestigationApiService
from app.orchestration.contracts import InvestigationContext, InvestigationRequest, request_fingerprint
from app.orchestration.handoff import artifact_ref
from app.orchestration.scope import resolve_scope
from app.orchestration.trace import AgentTrace, InvestigationTrace, ToolSummary
from app.planner.schemas import PlannerInput
from app.utils.time import utcnow


def context():
    request = InvestigationRequest(planner_input=PlannerInput(query=QueryRequest(
        question='查询 CVE-2099-1234', target='CVE-2099-1234', request_key='SYNTHETIC-review')))
    now = utcnow()
    return InvestigationContext(logical_investigation_id=uuid4(), owner='SYNTHETIC-owner',
        original_request=request, request_hash=request_fingerprint(request),
        resolved_scope=resolve_scope(request, actor='SYNTHETIC-owner'),
        created_at=now, updated_at=now, deadline_at=now+timedelta(seconds=30))


def artifact(**fields):
    return InvestigationArtifact(artifact_id=uuid4(), task_id='lookup', run_id=uuid4(),
        canonical_id='CVE-2099-1234', status='COMPLETE', runtime_status='SUCCESS', **fields)


@pytest.mark.parametrize('private_text,hidden', [
    ('Authorization: Basic U1lOVEhFVElDOlNFQ1JFVA==', 'U1lOVEhFVElDOlNFQ1JFVA=='),
    ('local file /opt/aegis/private.env', '/opt/aegis/private.env'),
    (r'local file C:\Program Files\Private App\secret.txt', r'Private App\secret.txt'),
])
def test_public_artifact_redacts_credentials_and_paths_without_changing_verdict(private_text, hidden):
    original = artifact(description=private_text, evidence=[{
        'content': private_text, 'Config': {'APIBase': 'https://private.invalid/internal'},
        'source_url': 'https://example.invalid/advisory'}])
    public = public_artifact(original, PublicInvestigationArtifact)
    assert hidden not in public.model_dump_json()
    assert 'private.invalid' not in public.model_dump_json()
    assert public.status == 'COMPLETE' and public.canonical_id == 'CVE-2099-1234'
    assert public.evidence[0]['source_url'] == 'https://example.invalid/advisory'
    assert original.description == private_text


def trace_for(c, calls=()):
    return InvestigationTrace(logical_investigation_id=c.logical_investigation_id,
        original_question=c.original_request.user_query, planner=None, events=(),
        agent_runs=(AgentTrace(run_id=uuid4(), status='SUCCESS', artifact_references=(),
                               task_statuses={'lookup': 'SUCCESS'}, tool_calls=calls),),
        integration_result_id=None, integration_status=None, answer_id=None,
        warnings=(), unresolved_items=(), error_code=None)


def test_trace_keeps_safe_tool_summary_without_raw_tool_arguments(monkeypatch):
    import app.orchestration.trace as trace_module
    c = context()
    call = ToolSummary(record_id=uuid4(), task_id='lookup', tool='get_vulnerability',
                       status='success', duration_ms=12, evidence_ids=('SYNTHETIC-evidence',))
    service = object.__new__(InvestigationApiService)
    service.reader = SimpleNamespace(store=object(), get_result=lambda *a, **k: SimpleNamespace(context=c))
    service.supplements = SimpleNamespace(read=lambda *a, **k: None, summary=lambda *a, **k: None)
    monkeypatch.setattr(trace_module, 'build_trace', lambda *a, **k: trace_for(c, (call,)))
    response = service.trace(c.logical_investigation_id, actor=c.owner)
    assert response.agent_runs[0].tool_calls == (call,)
    assert 'arguments' not in response.model_dump_json()


@pytest.mark.parametrize('progresses', [True, False])
def test_trace_retries_changed_root_but_never_masks_stable_binding_corruption(monkeypatch, progresses):
    import app.orchestration.trace as trace_module
    old = context()
    new = old.model_copy(update={'revision': old.revision+1, 'investigation_run_id': uuid4()})
    reads, builds = [], []
    def read(*a, **k):
        reads.append(True)
        return SimpleNamespace(context=old if len(reads) == 1 or not progresses else new)
    def build(store, result, **kwargs):
        builds.append(result.context.revision)
        if result.context.revision == old.revision:
            raise ValueError('TRACE_PLANNER_RUN_MISMATCH')
        return trace_for(result.context)
    service = object.__new__(InvestigationApiService)
    service.reader = SimpleNamespace(store=object(), get_result=read)
    service.supplements = SimpleNamespace(read=lambda *a, **k: None, summary=lambda *a, **k: None)
    monkeypatch.setattr(trace_module, 'build_trace', build)
    if progresses:
        assert service.trace(old.logical_investigation_id, actor=old.owner).revision == new.revision
        assert len(builds) == 2
    else:
        with pytest.raises(ValueError, match='TRACE_PLANNER_RUN_MISMATCH'):
            service.trace(old.logical_investigation_id, actor=old.owner)
        assert len(builds) == 1


@pytest.mark.parametrize('substitution', ['run', 'target'])
def test_pre_gate_artifact_must_match_root_run_and_scope(monkeypatch, substitution):
    import app.investigation_api.service as module
    c, art = context(), artifact()
    if substitution == 'target':
        art = art.model_copy(update={'canonical_id': 'CVE-2099-5678'})
    c = c.model_copy(update={'investigation_run_id': uuid4() if substitution == 'run' else art.run_id,
                             'artifact_references': (artifact_ref(art),)})
    result = InvestigationRunResult(run_id=art.run_id, runtime_status='SUCCESS', artifacts=(art,))
    monkeypatch.setattr(module, 'InvestigationReader', lambda engine: SimpleNamespace(read=lambda *a, **k: result))
    service = object.__new__(InvestigationApiService)
    service.engine = object()
    with pytest.raises(ValueError, match='API_ARTIFACT_BINDING_INVALID'):
        service._sources(c, c.owner)


def test_shutdown_carries_cancellation_to_late_claim_before_execution(monkeypatch):
    import app.investigation_api.service as module
    entered, release, shutdown = Event(), Event(), Event()
    c = context()
    cancelled, executed = [], []
    receipt = SimpleNamespace(logical_id=c.logical_investigation_id, fresh=True)
    class Store:
        def claim(self, request, *, actor):
            entered.set()
            assert release.wait(3)
            return receipt
        def request_cancel(self, id, *, actor):
            cancelled.append(id)
    class Orchestrator:
        def __init__(self, *args):
            self.store = Store()
        def cancel(self, id, *, actor):
            self.store.request_cancel(id, actor=actor)
        def investigate(self, request, *, actor):
            self.store.claim(request, actor=actor)
            if not cancelled:
                executed.append('PLANNING')
            return SimpleNamespace(context=c)
    class Repository:
        def __init__(self, *args): pass
        def by_key(self, *args): return None
    monkeypatch.setattr(module, 'InvestigationOrchestrator', Orchestrator)
    monkeypatch.setattr(module, 'InvestigationRepository', Repository)
    service = InvestigationApiService(object(), SimpleNamespace(), ack_timeout=0.01)
    class Pool:
        def __init__(self, original): self.original = original
        def submit(self, *a, **k): return self.original.submit(*a, **k)
        def shutdown(self, *a, **k):
            shutdown.set()
            return self.original.shutdown(*a, **k)
    service.pool = Pool(service.pool)
    try:
        with pytest.raises(ApiFailure, match='CREATION_ACK_TIMEOUT'):
            service.create(c.original_request, actor=c.owner)
        assert entered.wait(3)
        with ThreadPoolExecutor(max_workers=1) as pool:
            closing = pool.submit(service.close)
            assert shutdown.wait(3)
            release.set()
            closing.result(timeout=3)
        assert cancelled == [c.logical_investigation_id]
        assert executed == []
    finally:
        release.set()
        if not service.closed:
            service.close()


def exporter():
    root = Path(__file__).resolve().parents[3]
    spec = spec_from_file_location('phase12b_export', root/'scripts/export_investigation_api.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dedicated_openapi_resolves_info_and_security():
    result = exporter().exports()
    schema = next(value for path, value in result.items() if path.name == 'investigation-http.openapi.json')
    assert schema['info']['title'] and schema['info']['version']
    assert schema['components']['securitySchemes']['HTTPBearer']['scheme'] == 'bearer'


def test_export_preserves_legacy_proxy_restrictions():
    result = exporter().exports()
    inventory = next(value for path, value in result.items() if path.name == 'http-apis.json')
    blocked = [entry for entry in inventory['operations'] if entry['browser_access'] == 'PROXY_BLOCKED']
    assert len(blocked) == 7
    assert any(entry['url'] == '/api/v1/assets' and entry['method'] == 'POST' for entry in blocked)
    assert all(entry['browser_access'] == 'AVAILABLE' for entry in inventory['operations']
               if entry['url'].startswith('/api/investigations'))

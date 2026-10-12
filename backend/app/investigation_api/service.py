"""Transport orchestration, not security business logic or a second Runtime."""
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import BoundedSemaphore, Event, Lock
from app.assistant.storage import IdempotencyConflict
from app.llm.gateway import ModelGateway
from app.orchestration.service import InvestigationOrchestrator, InvestigationBusy
from app.orchestration.contracts import capture_request, request_fingerprint, TERMINAL_STAGES
from app.orchestration.store import status_snapshot
from app.orchestration.answer_sources import AnswerSourcesLoader
from app.orchestration.handoff import artifact_ref
from app.agents.investigation.reader import InvestigationReader
from app.agents.verification.reader import VerificationReader
from app.agents.analysis.reader import AnalysisReader
from app.investigation_api.repository import InvestigationRepository
from app.investigation_api.model_execution import read_model_execution
from app.investigation_api.errors import ApiFailure, not_ready
from app.investigation_api.projection import public_copy, public_text, public_artifact
from app.investigation_api.schemas import (
    InvestigationStatusResponse, InvestigationCreateResponse, TraceResponse, TraceStage,
    ArtifactResponse, PublicInvestigationArtifact, PublicVerificationArtifact, PublicRiskAnalysisArtifact,
    IntegrationResponse, AnswerResponse, HistoryResponse, HistoryItem,
)

logger = logging.getLogger('aegisai.investigation_api')


@dataclass
class Pending:
    request_hash: str
    actor: str
    event: Event = field(default_factory=Event)
    cancel_requested: Event = field(default_factory=Event)
    receipt: object = None
    error: Exception | None = None


class ClaimAcknowledgementStore:
    """Delegate everything; emit ACK only after the original committed claim."""
    def __init__(self, store, pending, lock):
        self.store, self.pending, self.lock = store, pending, lock

    def __getattr__(self, name):
        return getattr(self.store, name)

    def claim(self, request, *, actor):
        receipt = self.store.claim(request, actor=actor)
        # Coordinate ACK publication with close(). A claim that commits after
        # shutdown must observe the cancellation intent before starting stages.
        with self.lock:
            self.pending.receipt = receipt
            if self.pending.cancel_requested.is_set():
                self.store.request_cancel(receipt.logical_id, actor=actor)
            self.pending.event.set()
        return receipt


class InvestigationApiService:
    def __init__(self, engine, gateway=None, *, max_workers=2, ack_timeout=10):
        if max_workers not in (1, 2):
            raise ValueError('API worker capacity must match existing Runtime bounds')
        self.engine = engine
        self.gateway = gateway or ModelGateway()
        self.owns_gateway = gateway is None
        self.reader = InvestigationOrchestrator(engine, self.gateway)
        self.repository = InvestigationRepository(engine)
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='investigation-api')
        self.slots, self.lock = BoundedSemaphore(max_workers), Lock()
        self.pending, self.closed = {}, False
        self.ack_timeout = ack_timeout

    def _status(self, context, ns):
        status = status_snapshot(context, ns)
        data = status.model_dump(mode='json')
        data['warnings'] = [public_text(x) for x in data['warnings']]
        return InvestigationStatusResponse(**data, investigation_id=context.logical_investigation_id,
            status=context.current_stage, created_at=context.created_at, finished_at=context.finished_at)

    def status(self, id, *, actor):
        return self._status(*self.reader.store.read_audit(id, actor=actor))

    def _created(self, id, actor, reused):
        status = self.status(id, actor=actor)
        return InvestigationCreateResponse(**status.model_dump(), reused=reused,
            model_provider=self.gateway.config.provider, is_mock=self.gateway.config.provider == 'mock')

    def create(self, request, *, actor):
        request = capture_request(request)
        request_hash = request_fingerprint(request)
        existing = self.repository.by_key(actor, request.request_key)
        if existing:
            context, ns = existing
            if context.request_hash != request_hash:
                raise IdempotencyConflict('Request fingerprint mismatch')
            return self._created(context.logical_investigation_id, actor, True)
        key = (actor, request.request_key)
        with self.lock:
            if self.closed:
                raise ApiFailure('SERVICE_UNAVAILABLE', '调查服务正在关闭。', status=503, retryable=True)
            pending = self.pending.get(key)
            reused = pending is not None
            if pending and pending.request_hash != request_hash:
                raise IdempotencyConflict('Request fingerprint mismatch')
            if not pending:
                if not self.slots.acquire(blocking=False):
                    raise InvestigationBusy('INVESTIGATION_BUSY')
                pending = Pending(request_hash, actor)
                self.pending[key] = pending
                try:
                    self.pool.submit(self._run, key, request, pending)
                except Exception:
                    self.pending.pop(key, None)
                    self.slots.release()
                    raise
        if not pending.event.wait(self.ack_timeout):
            # The request may subsequently persist. Retrying the same key is safe.
            raise ApiFailure('CREATION_ACK_TIMEOUT', '创建确认超时，请使用同一幂等键重试。', status=503, retryable=True)
        if pending.error:
            raise pending.error
        if not pending.receipt:
            raise ApiFailure('CREATION_NOT_STORED', '调查未能保存。', status=503, retryable=True)
        return self._created(pending.receipt.logical_id, actor, reused or not pending.receipt.fresh)

    def _run(self, key, request, pending):
        orchestrator = InvestigationOrchestrator(self.engine, self.gateway)
        orchestrator.store = ClaimAcknowledgementStore(orchestrator.store, pending, self.lock)
        try:
            result = orchestrator.investigate(request, actor=pending.actor)
            if pending.receipt is None:
                # Existing process-wide capacity path returns an owned result.
                existing = self.repository.by_key(pending.actor, request.request_key)
                if existing and existing[0].request_hash == pending.request_hash:
                    from types import SimpleNamespace
                    pending.receipt = SimpleNamespace(logical_id=result.context.logical_investigation_id, fresh=False)
                else:
                    pending.error = ApiFailure('CREATION_NOT_STORED', '调查未能保存。', status=503, retryable=True)
        except Exception as exc:
            if pending.receipt is None:
                pending.error = exc
            logger.error('Investigation worker stopped; exception_type=%s', type(exc).__name__)
        finally:
            pending.event.set()
            with self.lock:
                if self.pending.get(key) is pending:
                    self.pending.pop(key)
                self.slots.release()

    def trace(self, id, *, actor):
        result = self.reader.get_result(id, actor=actor)
        from app.orchestration.trace import build_trace
        for attempt in range(3):
            try:
                trace = build_trace(self.reader.store, result, actor=actor)
                break
            except ValueError as exc:
                if str(exc) not in ('TRACE_PLANNER_RUN_MISMATCH', 'TRACE_ARTIFACT_REFERENCE_INVALID'):
                    raise
                latest_result = self.reader.get_result(id, actor=actor)
                if latest_result.context.revision <= result.context.revision:
                    # Stable corruption remains an error; do not repair references.
                    raise
                if attempt == 2:
                    raise ApiFailure('SNAPSHOT_BUSY', '调查正在更新，请稍后刷新。', status=503, retryable=True) from None
                result = latest_result
        context = result.context
        ids = {'PLANNING': context.planner_run_id, 'INVESTIGATING': context.investigation_run_id,
               'VERIFYING': context.verification_run_id, 'ANALYZING': context.analysis_run_id,
               'INTEGRATING': context.integration_result_id}
        agents = {'INVESTIGATING': 'investigation_agent', 'VERIFYING': 'verification_agent',
                  'ANALYZING': 'security_analysis_agent'}
        runs = {run.run_id: run for run in trace.agent_runs}
        latest = {event.stage: event for event in trace.events}
        stages = []
        for stage, event in latest.items():
            run = runs.get(ids.get(stage))
            stages.append(TraceStage(agent=agents.get(stage), stage=stage, time=event.at,
                status=run.status if run else event.code, run_id=ids.get(stage),
                artifact_ids=tuple(ref.artifact_id for ref in context.artifact_references if ref.run_id == ids.get(stage))))
        data = public_copy(trace.model_dump(mode='json'))
        # Artifact tool_calls contain private receipts. Trace tool_calls have a
        # different, already-validated ToolSummary schema and remain useful.
        for public_run, original_run in zip(data['agent_runs'], trace.agent_runs):
            public_run['tool_calls'] = [public_copy(call.model_dump(mode='json')) for call in original_run.tool_calls]
        return TraceResponse(**data, investigation_id=id, stages=tuple(stages), revision=context.revision,
                             model_execution=read_model_execution(self.engine, context, actor=actor))

    def _sources(self, context, actor):
        if context.integration_result_id:
            source, gate, _ = AnswerSourcesLoader(self.engine).load(context, actor=actor)
            return source.investigation, source.verification, source.analysis
        readers = {'investigation-artifact-v1': InvestigationReader(self.engine),
                   'verification-artifact-v1': VerificationReader(self.engine),
                   'risk-analysis-artifact-v1': AnalysisReader(self.engine)}
        expected_runs = {'investigation-artifact-v1': context.investigation_run_id,
                         'verification-artifact-v1': context.verification_run_id,
                         'risk-analysis-artifact-v1': context.analysis_run_id}
        found = {}
        for ref in context.artifact_references:
            if (ref.schema_version not in readers or ref.schema_version in found or
                    expected_runs[ref.schema_version] is None or ref.run_id != expected_runs[ref.schema_version]):
                raise ValueError('API_ARTIFACT_BINDING_INVALID')
            reader = readers[ref.schema_version]
            result = reader.read(ref.run_id, actor) if ref.schema_version == 'investigation-artifact-v1' else reader.read(ref.run_id, actor=actor)
            artifacts = [art for art in result.artifacts if artifact_ref(art) == ref]
            if result.run_id != ref.run_id or len(artifacts) != 1:
                raise ValueError('API_ARTIFACT_BINDING_INVALID')
            found[ref.schema_version] = artifacts[0]
        inv, ver, analysis = (found.get(key) for key in readers)
        if inv and (context.resolved_scope.targets != (inv.canonical_id,)):
            raise ValueError('API_ARTIFACT_BINDING_INVALID')
        if ver and (inv is None or (ver.source_run_id, ver.source_artifact_id) != (inv.run_id, inv.artifact_id)):
            raise ValueError('API_ARTIFACT_BINDING_INVALID')
        if analysis and (inv is None or ver is None or
                         analysis.input_artifact_ids != (inv.artifact_id, ver.artifact_id) or
                         analysis.asset_id != context.resolved_scope.planner_input.query.asset_id):
            raise ValueError('API_ARTIFACT_BINDING_INVALID')
        return inv, ver, analysis

    def artifacts(self, id, *, actor):
        result = self.reader.get_result(id, actor=actor)
        inv, ver, analysis = self._sources(result.context, actor)
        return ArtifactResponse(investigation_id=id, revision=result.context.revision,
            investigation=public_artifact(inv, PublicInvestigationArtifact) if inv else None,
            verification=public_artifact(ver, PublicVerificationArtifact) if ver else None,
            analysis=public_artifact(analysis, PublicRiskAnalysisArtifact) if analysis else None)

    def integration(self, id, *, actor):
        result = self.reader.get_result(id, actor=actor)
        if result.context.integration_result_id is None:
            if result.context.current_stage in TERMINAL_STAGES:
                raise ApiFailure('RESULT_UNAVAILABLE', '该调查已终止，没有产生 Gate 结果。', status=409)
            raise not_ready()
        _, gate, _ = AnswerSourcesLoader(self.engine).load(result.context, actor=actor)
        return IntegrationResponse.model_validate(public_copy(gate.model_dump(mode='json')))

    def answer(self, id, *, actor):
        result = self.reader.get_result(id, actor=actor)
        if result.answer is None:
            raise not_ready()
        return AnswerResponse.model_validate(public_copy(result.answer.model_dump(mode='json')))

    def cancel(self, id, *, actor):
        self.reader.cancel(id, actor=actor)
        return self.status(id, actor=actor)

    def history(self, *, actor, status=None, offset=0, limit=20, sort='created_desc'):
        records, total = self.repository.history(actor, status=status, offset=offset, limit=limit, sort=sort)
        items = [HistoryItem(**self._status(context, ns).model_dump(),
            original_question=public_text(context.original_request.user_query), answer_id=context.answer_id,
            integration_result_id=context.integration_result_id) for context, ns in records]
        return HistoryResponse(items=tuple(items), total=total, offset=offset, limit=limit, sort=sort, status_filter=status)

    def close(self):
        with self.lock:
            self.closed = True
            pending = list(self.pending.values())
            for item in pending:
                item.cancel_requested.set()
        for item in pending:
            if item.receipt:
                try:
                    self.reader.cancel(item.receipt.logical_id, actor=item.actor)
                except Exception:
                    logger.error('Unable to request cancellation during shutdown')
        self.pool.shutdown(wait=True, cancel_futures=False)
        if self.owns_gateway:
            self.gateway.close()

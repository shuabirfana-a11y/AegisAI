"""Explicit opt-in upper service; no Planner/replan/agent invocation or HTTP route."""
from dataclasses import dataclass
import logging,time
from threading import Event
from app.assistant.storage import IdempotencyConflict
from app.integration.contracts import IntegrationRequest
from app.integration.snapshot import IntegrationSnapshotReader
from app.integration.evaluator import IntegrationGateEvaluator
from app.integration.store import PostgresIntegrationStore,failure_context
from app.integration.reader import IntegrationReader

logger=logging.getLogger(__name__)
class GateAbort(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)

@dataclass(frozen=True)
class GateControl:
    cancel_event: Event|None=None
    deadline_monotonic: float|None=None
    def check(self):
        if self.cancel_event is not None and self.cancel_event.is_set():raise GateAbort('GATE_CANCELLED')
        if self.deadline_monotonic is not None and time.monotonic()>=self.deadline_monotonic:raise GateAbort('GATE_DEADLINE_EXCEEDED')

class IntegrationService:
    def __init__(self,engine):
        self.loader=IntegrationSnapshotReader(engine);self.evaluator=IntegrationGateEvaluator()
        self.store=PostgresIntegrationStore(engine);self.reader=IntegrationReader(engine)
    def evaluate(self,request,*,actor,control=None):
        if not isinstance(actor,str) or not 1<=len(actor)<=150:raise ValueError('Authenticated actor required')
        request=IntegrationRequest.model_validate_json(request.model_dump_json())
        control=control or GateControl()
        try:return self.store.evaluate_once(request,actor=actor,loader=self.loader,evaluator=self.evaluator,control=control)
        except IdempotencyConflict:raise
        except Exception as exc:
            code=exc.code if isinstance(exc,GateAbort) else 'GATE_STORE_FAILED'
            context=failure_context(request,actor,code)
            result=self.evaluator.evaluate(context).model_copy(update={'persistence':'NOT_STORED'})
            logger.error('Integration acceptance not stored: integration_id=%s code=%s',result.integration_id,code)
            return result
    def read(self,id,*,actor):return self.reader.read(id,actor=actor)
    def read_trace(self,id,*,actor):return self.reader.read_trace(id,actor=actor)

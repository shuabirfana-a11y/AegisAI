"""Professional verifier delegates all data/model work to original tool workers."""
import threading
import time
from uuid import UUID
from app.agents.interfaces import VerificationAgent
from app.agents.artifacts import AgentExecutionRequest
from app.agents.verification.roles import TOOLS,IMPLEMENTATION_KEY
from app.agents.verification.schemas import VerificationAssessment
from app.runtime.contracts import ExecutionOutcome,TaskInput,TaskState
from app.runtime.executor import failure,validate_outcome
from app.runtime.process import ProcessSupervisor
from app.utils.time import utcnow


class EvidenceVerificationAgent(VerificationAgent):
    implementation_key=IMPLEMENTATION_KEY

    def __init__(self,*,supervisor_factory=ProcessSupervisor,run_id=None):
        self._factory=supervisor_factory
        self.supervisor=supervisor_factory()
        self._run_id=UUID(str(run_id)) if run_id else None
        self._lock=threading.Lock()
        self._cancelled=threading.Event()

    def for_run(self,run_id):
        return type(self)(supervisor_factory=self._factory,run_id=run_id)

    def cancel_all(self):
        self._cancelled.set();self.supervisor.cancel_all()

    def verify(self,request,*,database_url=None):
        request=AgentExecutionRequest.model_validate_json(request.model_dump_json())
        task=request.task;context=request.context;started=utcnow();receipts=();clean=True
        def failed(code):return ExecutionOutcome(artifact=failure(task,context,code,started=started,receipts=receipts),
                                                 receipts=receipts,cleanup_verified=clean)
        with self._lock:
            if self._run_id is None:self._run_id=context.run_id
            if self._run_id!=context.run_id:return failed('AGENT_RUN_MISMATCH')
        if self._cancelled.is_set():return failed('RUN_CANCELLED')
        if time.monotonic()>=context.deadline:return failed('TASK_TIMEOUT')
        steps=TaskInput.model_validate(task.input_data).steps
        if (task.task_type!='tool_sequence' or task.dependencies or len(steps)!=1 or
            steps[0].name not in TOOLS.values() or set(task.allowed_tools)!={steps[0].name}):
            return failed('AGENT_TOOL_FORBIDDEN')
        try:
            outcome=self.supervisor.execute(task,context,{},database_url=database_url)
            outcome=validate_outcome(task,context,outcome)
            receipts=outcome.receipts;clean=outcome.cleanup_verified
            if self._cancelled.is_set():return failed('RUN_CANCELLED')
            if time.monotonic()>=context.deadline:return failed('TASK_TIMEOUT')
            if outcome.artifact.status==TaskState.SUCCESS:
                if len(outcome.receipts)!=1:raise ValueError('Exact verification receipt required')
                data=outcome.receipts[0].envelope.data
                if data.get('context_id')!=str(steps[0].arguments['context_id']):raise ValueError('Verification context changed')
                result=VerificationAssessment.model_validate(data['assessment'])
                if result.verification_status not in ('CONFIRMED','REJECTED') or result.partial_result:
                    art=outcome.artifact.model_copy(update={'status':TaskState.WAITING_REVIEW,
                        'unresolved_questions':list(result.unresolved_items) or ['Verification remains unresolved']})
                    outcome=outcome.model_copy(update={'artifact':art})
            return validate_outcome(task,context,outcome)
        except (ValueError,TypeError,KeyError):return failed('VERIFICATION_OUTPUT_INVALID')
        except Exception:return failed('VERIFICATION_EXECUTION_FAILED')

"""One capability implementation, delegating all calls to original tool workers."""
import threading,time
from uuid import UUID
from app.agents.interfaces import InvestigationAgent
from app.agents.artifacts import AgentExecutionRequest
from app.agents.investigation.roles import ROLES,IMPLEMENTATION_KEY
from app.agents.investigation.normalize import normalize_investigation
from app.runtime.contracts import TaskContract,TaskInput,TaskArtifact,TaskPlan,RuntimePolicy,ExecutionOutcome,TaskState
from app.runtime.process import ProcessSupervisor
from app.runtime.graph import compile_graph
from app.runtime.executor import failure,evidence,call_summaries,acceptance,validate_receipts,validate_outcome
from app.utils.time import utcnow

class IntelligenceInvestigationAgent(InvestigationAgent):
    implementation_key=IMPLEMENTATION_KEY
    def __init__(self,*,supervisor_factory=ProcessSupervisor,run_id=None):
        self._factory=supervisor_factory;self.supervisor=supervisor_factory()
        self._run_id=UUID(str(run_id)) if run_id else None
        self._lock=threading.Lock();self._cancelled=threading.Event()
    def for_run(self,run_id):
        return type(self)(supervisor_factory=self._factory,run_id=run_id)
    def cancel_all(self):
        self._cancelled.set();self.supervisor.cancel_all()
    def investigate(self,request,*,database_url=None):
        request=AgentExecutionRequest.model_validate_json(request.model_dump_json())
        task=request.task; context=request.context;started=utcnow();receipts=[];clean=True
        def failed(code):
            return ExecutionOutcome(artifact=failure(task,context,code,started=started,receipts=receipts),
                                    receipts=receipts,cleanup_verified=clean)
        with self._lock:
            if self._run_id is None:self._run_id=context.run_id
            if self._run_id!=context.run_id:return failed('AGENT_RUN_MISMATCH')
        if self._cancelled.is_set():return failed('RUN_CANCELLED')
        context=context.model_copy(update={'deadline':min(context.deadline,time.monotonic()+min(task.timeout_seconds,30))})
        if time.monotonic()>=context.deadline:return failed('TASK_TIMEOUT')
        allowed=set().union(*(r.tools for r in ROLES.values()))
        if task.task_type!='tool_sequence' or not set(task.allowed_tools)<=allowed:return failed('AGENT_TOOL_FORBIDDEN')
        try:
            standalone=TaskContract.model_validate({**task.model_dump(),'dependencies':()})
            compile_graph(TaskPlan(tasks=[standalone]),RuntimePolicy(permissions=context.permissions))
            steps=TaskInput.model_validate(task.input_data).steps
            for index,step in enumerate(steps,1):
                if self._cancelled.is_set():return failed('RUN_CANCELLED')
                if time.monotonic()>=context.deadline:return failed('TASK_TIMEOUT')
                child=TaskContract.model_validate({**task.model_dump(),'dependencies':(),
                    'input_data':{'steps':[step.model_dump()]},'allowed_tools':(step.name,),'max_tool_calls':1})
                got=self.supervisor.execute(child,context,{},database_url=database_url)
                clean=clean and got.cleanup_verified
                got=validate_outcome(child,context,got)
                if len(got.receipts)!=1:
                    return failed(got.artifact.errors[0].get('code','INCOMPLETE_TOOL_RECEIPT') if got.artifact.errors else 'INCOMPLETE_TOOL_RECEIPT')
                receipts.append(got.receipts[0].model_copy(update={'call_index':index}))
                validate_receipts(task,context,receipts)
                if not clean:return failed('TASK_CLEANUP_FAILED')
            if self._cancelled.is_set():return failed('RUN_CANCELLED')
            if time.monotonic()>=context.deadline:return failed('TASK_TIMEOUT')
            state,unresolved=acceptance(task,receipts)
            artifact=TaskArtifact(run_id=context.run_id,task_id=task.task_id,status=state,
                start_time=started,end_time=utcnow(),evidence=evidence(receipts),tool_calls=call_summaries(receipts),
                unresolved_questions=unresolved,
                result={'outputs':[{'tool':r.name,'status':r.envelope.status,'data':r.envelope.data} for r in receipts],
                        'dependencies':{a.task_id:str(a.artifact_id) for a in request.input_artifacts}},
                warnings=[w for r in receipts for w in r.envelope.warnings],errors=[e for r in receipts for e in r.envelope.errors])
            outcome=ExecutionOutcome(artifact=artifact,receipts=receipts,cleanup_verified=clean)
            projected=normalize_investigation(task,outcome,request.input_artifacts)
            if state==TaskState.SUCCESS and projected.status!='COMPLETE':
                artifact=artifact.model_copy(update={'status':TaskState.WAITING_REVIEW,'unresolved_questions':projected.uncertainties})
                outcome=outcome.model_copy(update={'artifact':artifact})
            return validate_outcome(task,context,outcome)
        except (ValueError,TypeError):return failed('INVESTIGATION_OUTPUT_INVALID')
        except Exception:return failed('INVESTIGATION_EXECUTION_FAILED')

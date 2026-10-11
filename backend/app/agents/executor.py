"""Scheduler-compatible dispatch without business logic or new tool authority."""
import threading
import time
from app.agents.artifacts import AgentArtifact, AgentExecutionRequest, build_handoff, validate_artifact_json, validate_persisted_extension
from app.agents.contracts import BoundAgentPlan, AgentFrameworkError, fingerprint
from app.agents.registry import RegistrySnapshot
from app.agents.router import AgentRouter
from app.runtime.contracts import TaskArtifact, TaskContract, TaskPlan, RuntimePolicy, WorkerContext, ExecutionOutcome, TaskState
from app.runtime.executor import failure, validate_outcome, validate_receipts, evidence_reference, call_summaries
from app.runtime.graph import compile_graph
from app.runtime.process import ProcessSupervisor
from app.utils.time import utcnow


class AgentExecutor:
    def __init__(self, bound: BoundAgentPlan, registry: RegistrySnapshot, *, task_registry=None):
        if bound.registry_fingerprint != registry.fingerprint:
            raise AgentFrameworkError('AGENT_PLAN_INVALID')
        self.bound = bound
        self.registry = registry
        self.task_registry = task_registry
        self._lock = threading.Lock()
        self._cancelled = threading.Event()
        self._owner = None
        self._instances = {}
        self._input_supervisor = ProcessSupervisor()

    def cancel_all(self):
        self._cancelled.set()
        self._input_supervisor.cancel_all()
        with self._lock: instances = tuple(self._instances.values())
        for instance in instances:
            instance.cancel_all()

    def _instance(self, binding, context):
        registration = self.registry.get(binding.agent_id)
        if registration is None: raise AgentFrameworkError('AGENT_NOT_FOUND')
        if registration.implementation is None: raise AgentFrameworkError('AGENT_NOT_IMPLEMENTED')
        with self._lock:
            if self._cancelled.is_set(): raise AgentFrameworkError('RUN_CANCELLED')
            if binding.agent_id not in self._instances:
                instance = registration.implementation.for_run(context.run_id)
                if (instance is registration.implementation or not isinstance(instance, registration.interface) or
                    instance.implementation_key != registration.implementation_key):
                    raise AgentFrameworkError('AGENT_IMPLEMENTATION_INVALID')
                self._instances[binding.agent_id] = instance
            return self._instances[binding.agent_id]

    def execute(self, task: TaskContract, context: WorkerContext, dependencies, *, database_url=None) -> ExecutionOutcome:
        started = utcnow()
        receipts = ()
        cleanup_verified = True
        def failed(code):
            artifact = failure(task,context,code,started=started,receipts=receipts)
            binding = self.bound.binding(task.task_id)
            if binding is not None:
                try:
                    validate_persisted_extension(artifact,binding,receipts)
                except AgentFrameworkError:
                    errors = list(artifact.errors)
                    if not any(e.get('code')=='ARTIFACT_SIZE_LIMIT' for e in errors):
                        errors.append({'code':'ARTIFACT_SIZE_LIMIT','message':'See complete tool receipt evidence'})
                    artifact = TaskArtifact(run_id=context.run_id,task_id=task.task_id,status=TaskState.FAILED,
                        start_time=started,end_time=utcnow(),result=evidence_reference(receipts),
                        tool_calls=call_summaries(receipts),errors=errors,
                        warnings=['Complete evidence retained in immutable tool receipts; bounded Artifact references it'])
                    validate_persisted_extension(artifact,binding,receipts)
            return ExecutionOutcome(artifact=artifact,
                                    receipts=receipts,cleanup_verified=cleanup_verified)
        try:
            task = TaskContract.model_validate_json(task.model_dump_json())
            context = WorkerContext.model_validate_json(context.model_dump_json())
            with self._lock:
                if self._owner is None: self._owner = context.run_id
                if self._owner != context.run_id: raise AgentFrameworkError('AGENT_RUN_MISMATCH')
            if self._cancelled.is_set(): return failed('RUN_CANCELLED')
            if time.monotonic() >= context.deadline: return failed('TASK_TIMEOUT')
            expected = next((t for t in self.bound.captured_plan.tasks if t.task_id == task.task_id),None)
            if expected is None or fingerprint(expected.model_dump(mode='json')) != fingerprint(task.model_dump(mode='json')):
                raise AgentFrameworkError('AGENT_PLAN_INVALID')
            if task.task_type == 'input_required':
                return self._input_supervisor.execute(task,context,dependencies,database_url=database_url)
            binding = self.bound.binding(task.task_id)
            if binding is None: raise AgentFrameworkError('AGENT_NOT_FOUND')
            current = AgentRouter(self.registry,task_registry=self.task_registry).route(task,binding.semantic_type)
            if current != binding: raise AgentFrameworkError('AGENT_PLAN_INVALID')
            standalone = TaskContract.model_validate({**task.model_dump(),'dependencies':()})
            compile_graph(TaskPlan(tasks=[standalone]),RuntimePolicy(permissions=context.permissions))
            context = WorkerContext.model_validate({**context.model_dump(),
                'deadline':min(context.deadline,time.monotonic()+min(task.timeout_seconds,binding.contract.timeout_seconds))})
            inputs = build_handoff(task,context,dependencies,self.bound.bindings)
            request = AgentExecutionRequest(task=task,context=context,input_artifacts=inputs)
            request = AgentExecutionRequest.model_validate_json(request.model_dump_json())
            instance = self._instance(binding,context)
            try:
                outcome = instance.execute(request,database_url=database_url)
            except Exception:
                return failed('AGENT_EXECUTION_FAILED')
            try:
                validate_receipts(task,context,outcome.receipts)
                receipts = tuple(outcome.receipts)
                cleanup_verified = outcome.cleanup_verified
                validate_artifact_json(outcome.artifact)
                if not cleanup_verified: raise ValueError('Cleanup not verified')
                outcome = validate_outcome(task,context,outcome)
                if outcome.artifact.status == TaskState.SUCCESS:
                    if self._cancelled.is_set(): return failed('RUN_CANCELLED')
                    if time.monotonic() >= context.deadline: return failed('TASK_TIMEOUT')
                    wanted = {'outputs':[{'tool':r.name,'status':r.envelope.status,'data':r.envelope.data} for r in receipts],
                              'dependencies':{key:str(dependencies[key].artifact_id) for key in task.dependencies}}
                    if fingerprint(outcome.artifact.result) != fingerprint(wanted):
                        raise ValueError('Result changed after authorized tool execution')
                AgentArtifact.from_task_artifact(outcome.artifact,binding)
                try:
                    validate_persisted_extension(outcome.artifact,binding,receipts)
                except AgentFrameworkError:
                    return failed('ARTIFACT_SIZE_LIMIT')
                return outcome
            except Exception:
                return failed('AGENT_OUTPUT_INVALID')
        except AgentFrameworkError as exc:
            return failed(exc.code)
        except PermissionError:
            return failed('PERMISSION_DENIED')
        except (ValueError,TypeError):
            return failed('AGENT_PLAN_INVALID')
        except Exception:
            return failed('AGENT_EXECUTION_FAILED')

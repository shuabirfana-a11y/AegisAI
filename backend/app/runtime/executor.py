"""Execute typed tool steps only; version matching and risk logic stay in tools.

The supervisor validates the receipt-backed Artifact again at the process
boundary. Future task kinds need explicit protocols, never arbitrary callbacks.
"""
import time
from hashlib import sha256
from pydantic import ValidationError
from app.runtime.contracts import (TaskArtifact, TaskContract, TaskInput,
                                   WorkerContext, ToolReceipt, ExecutionOutcome,
                                   TaskState as S, RuntimePolicy, TaskPlan)
from app.runtime.graph import compile_graph
from app.tooling.gateway import ToolGateway, ToolContext
from app.tooling.contracts import ToolEnvelope
from app.tooling.attestation import evidence_key
from app.utils.time import utcnow


def evidence(receipts):
    found = {}
    for receipt in receipts:
        for ref in receipt.envelope.evidence_refs:
            found.setdefault(evidence_key(ref), ref)
    return list(found.values())


def call_summaries(receipts):
    return [{'call_index': r.call_index, 'tool_name': r.name,
             'status': r.envelope.status, 'duration_ms': r.envelope.duration_ms}
            for r in receipts]


def evidence_reference(receipts):
    """Reference full evidence held in receipts; never trim individual facts."""
    refs=evidence(receipts)
    return {'evidence_storage':'tool_receipts','evidence_count':len(refs),
            'evidence_sha256':sha256(evidence_key(refs).encode('utf-8')).hexdigest()}


def failure(task, context, code, *, started=None, receipts=()):
    values=dict(run_id=context.run_id, task_id=task.task_id, status=S.FAILED,
                start_time=started, end_time=utcnow(), evidence=evidence(receipts),
                tool_calls=call_summaries(receipts),
                errors=[{'code': code, 'message': 'Task failed; inspect scoped execution records'}])
    try:
        return TaskArtifact(**values)
    except ValidationError:
        # The full receipt remains authoritative and is stored unmodified.
        # A bounded failure references it explicitly instead of failing twice.
        values.update(evidence=[],result=evidence_reference(receipts),
            warnings=['Evidence exceeds Artifact limit; complete evidence retained in tool receipts'])
        if code!='ARTIFACT_SIZE_LIMIT':
            values['errors'].append({'code':'ARTIFACT_SIZE_LIMIT','message':'See complete tool receipt evidence'})
        return TaskArtifact(**values)


def acceptance(task, receipts):
    if any(r.envelope.status == 'failed' for r in receipts):
        return S.FAILED, []
    missing = []
    if any(r.envelope.status in ('partial', 'no_result') for r in receipts):
        missing.append('Tool returned partial data or no result')
    if 'tools_succeeded' in task.acceptance_criteria and (
            not receipts or any(r.envelope.status != 'success' for r in receipts)):
        missing.append('Required tools did not all succeed')
    if 'output_nonempty' in task.acceptance_criteria:
        for r in receipts:
            data = r.envelope.data
            if not data or (isinstance(data, dict) and 'items' in data and not data['items']):
                missing.append('Required output is unavailable; absence does not prove safety')
    if 'evidence_present' in task.acceptance_criteria and not evidence(receipts):
        missing.append('Required evidence was not returned by a tool')
    return (S.WAITING_REVIEW if missing else S.SUCCESS), missing


class WorkerExecutor:
    def __init__(self, gateway=None, emit=None):
        self.gateway = gateway or ToolGateway()
        self.emit = emit or (lambda event: None)

    def execute(self, task: TaskContract, context: WorkerContext,
                dependencies: dict[str, TaskArtifact]) -> TaskArtifact:
        task = TaskContract.model_validate_json(task.model_dump_json())
        for dep in task.dependencies:
            value = dependencies.get(dep)
            if value is None or value.task_id != dep or value.run_id != context.run_id or value.status != S.SUCCESS:
                raise ValueError('Accepted dependency identity required')
        started = utcnow()
        if task.task_type == 'input_required':
            return TaskArtifact(run_id=context.run_id, task_id=task.task_id,
                                status=S.WAITING_REVIEW, start_time=started, end_time=utcnow(),
                                result={'required_fields': task.input_data['required_fields']},
                                unresolved_questions=['Required input: ' + ', '.join(task.input_data['required_fields'])])
        # Enforce policy even if an internal caller bypassed graph compilation.
        try:
            standalone = task.model_copy(update={'dependencies': ()})
            compile_graph(TaskPlan(tasks=[standalone]), RuntimePolicy(permissions=context.permissions))
        except PermissionError:
            return failure(task, context, 'PERMISSION_DENIED', started=started)
        except ValueError:
            return failure(task, context, 'INVALID_TASK', started=started)
        tool_context = ToolContext(actor=context.actor, permissions=context.permissions,
                                   max_calls=task.max_tool_calls,
                                   timeout=task.timeout_seconds, deadline=context.deadline,
                                   trace_id=str(context.trace_id), run_id=str(context.run_id))
        receipts = []
        for index, step in enumerate(TaskInput.model_validate(task.input_data).steps, 1):
            if time.monotonic() >= context.deadline:
                return failure(task, context, 'TASK_TIMEOUT', started=started, receipts=receipts)
            begin = utcnow()
            self.emit({'kind': 'tool_started', 'call_index': index, 'name': step.name,
                       'arguments': step.arguments, 'started_at': begin.isoformat()})
            try:
                output = self.gateway.invoke(step.name, step.arguments, tool_context,
                                             timeout=max(0, context.deadline-time.monotonic()))
                receipt = ToolReceipt(call_index=index, name=step.name,
                                      arguments=step.arguments, started_at=begin,
                                      finished_at=utcnow(), envelope=output)
                receipts.append(receipt)
                self.emit({'kind': 'tool_finished', 'receipt': receipt.model_dump(mode='json')})
            except Exception:
                receipt = ToolReceipt(call_index=index, name=step.name, arguments=step.arguments,
                    started_at=begin, finished_at=utcnow(), envelope=ToolEnvelope(
                        tool=step.name, trace_id=str(context.trace_id), status='failed', duration_ms=0,
                        errors=[{'code': 'GATEWAY_FAILURE', 'message': 'Gateway failed without exposing internal details'}]))
                receipts.append(receipt)
                self.emit({'kind': 'tool_finished', 'receipt': receipt.model_dump(mode='json')})
                return failure(task, context, 'GATEWAY_FAILURE', started=started, receipts=receipts)
            if output.status == 'failed':
                break
        status, unresolved = acceptance(task, receipts)
        try:
            return TaskArtifact(run_id=context.run_id, task_id=task.task_id, status=status,
                start_time=started, end_time=utcnow(), evidence=evidence(receipts),
                tool_calls=call_summaries(receipts), unresolved_questions=unresolved,
                result={'outputs': [{'tool': r.name, 'status': r.envelope.status, 'data': r.envelope.data}
                                    for r in receipts],
                        'dependencies': {key: str(dependencies[key].artifact_id) for key in task.dependencies}},
                warnings=[w for r in receipts for w in r.envelope.warnings],
                errors=[e for r in receipts for e in r.envelope.errors])
        except ValidationError:
            return failure(task, context, 'ARTIFACT_SIZE_LIMIT', started=started, receipts=receipts)


def validate_receipts(task: TaskContract, context: WorkerContext, receipts):
    """Validate complete audit records even when the Artifact protocol fails."""
    steps = TaskInput.model_validate(task.input_data).steps
    if len(receipts) > min(len(steps), task.max_tool_calls):
        raise ValueError('Receipt call budget exceeded')
    for index, receipt in enumerate(receipts, 1):
        step = steps[index-1]
        if (receipt.call_index != index or receipt.name != step.name or
                evidence_key(receipt.arguments) != evidence_key(step.arguments) or
                receipt.envelope.tool != step.name or
                receipt.envelope.trace_id != str(context.trace_id) or
                receipt.started_at.utcoffset() is None or receipt.finished_at < receipt.started_at):
            raise ValueError('Receipt does not match authorized execution')


def validate_outcome(task: TaskContract, context: WorkerContext,
                     outcome: ExecutionOutcome) -> ExecutionOutcome:
    """Preserve exact provenance; shape-valid JSON is not trusted by itself."""
    artifact = TaskArtifact.model_validate_json(outcome.artifact.model_dump_json())
    if artifact.run_id != context.run_id or artifact.task_id != task.task_id:
        raise ValueError('Artifact identity mismatch')
    validate_receipts(task,context,outcome.receipts)
    steps = TaskInput.model_validate(task.input_data).steps
    if [evidence_key(ref) for ref in artifact.evidence] != [evidence_key(ref) for ref in evidence(outcome.receipts)]:
        referenced=(artifact.status==S.FAILED and not artifact.evidence and
            any(e.get('code')=='ARTIFACT_SIZE_LIMIT' for e in artifact.errors) and
            artifact.result==evidence_reference(outcome.receipts) and artifact.confidence is None)
        if not referenced:
            raise ValueError('Artifact evidence is not receipt-backed')
    if artifact.status == S.SUCCESS:
        expected, _ = acceptance(task, outcome.receipts)
        if expected != S.SUCCESS or len(outcome.receipts) != len(steps) or task.task_type != 'tool_sequence':
            raise ValueError('Unaccepted success artifact')
        outputs = [{'tool': r.name, 'status': r.envelope.status, 'data': r.envelope.data} for r in outcome.receipts]
        if evidence_key(artifact.result.get('outputs')) != evidence_key(outputs):
            raise ValueError('Artifact output was changed after tool execution')
    return outcome.model_copy(update={'artifact': artifact})

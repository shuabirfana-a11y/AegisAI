import time
from uuid import uuid4
import pytest
from .test_contracts_plan import task


def context(**changes):
    from app.runtime.contracts import WorkerContext
    return WorkerContext(**{**dict(run_id=uuid4(), trace_id=uuid4(), actor='unit-owner',
                                   deadline=time.monotonic()+5), **changes})


def execute(payload, *, task_=None, context_=None):
    from app.runtime.executor import WorkerExecutor
    from app.tooling.gateway import ToolGateway
    events = []
    gateway = ToolGateway(executor=lambda n, a, c: payload)
    worker = WorkerExecutor(gateway=gateway, emit=events.append)
    artifact = worker.execute(task_ or task(), context_ or context(), {})
    return artifact, events


def test_success_carries_real_tool_data_and_untrusted_provenance():
    ref = {'raw_document_id': str(uuid4()), 'url': 'https://example.invalid/advisory',
           'locator': {'line': 1}, 'verified': False}
    artifact, events = execute({'status': 'success', 'data': {'affected': 'unknown'}, 'evidence_refs': [ref]})
    assert artifact.status == 'SUCCESS' and artifact.confidence is None
    assert artifact.result['outputs'][0]['data']['affected'] == 'unknown'
    assert artifact.evidence == [ref]
    assert [e['kind'] for e in events] == ['tool_started', 'tool_finished']


@pytest.mark.parametrize('status,want', [('partial', 'WAITING_REVIEW'), ('no_result', 'WAITING_REVIEW'), ('failed', 'FAILED')])
def test_non_success_envelopes_preserve_failure_or_uncertainty(status, want):
    artifact, _ = execute({'status': status, 'data': {}, 'errors': [{'code': 'NOT_FOUND'}] if status == 'failed' else []})
    assert artifact.status == want
    assert len(artifact.tool_calls) == 1


def test_gateway_exception_becomes_artifact_and_never_discloses_secret():
    from app.runtime.executor import WorkerExecutor
    class Broken:
        def invoke(self, *args, **kwargs):
            raise RuntimeError('private-connection-password')
    result = WorkerExecutor(gateway=Broken()).execute(task(), context(), {})
    assert result.status == 'FAILED' and result.errors[0]['code'] == 'GATEWAY_FAILURE'
    assert 'private-connection-password' not in result.model_dump_json()


def test_server_permission_denial_cannot_execute_a_write_tool():
    item = task(allowed_tools=['match_component_vulnerabilities'],
                input_data={'steps': [{'name': 'match_component_vulnerabilities',
                                       'arguments': {'component_id': str(uuid4())}}]})
    artifact, events = execute({'status': 'success', 'data': {'forbidden': True}}, task_=item)
    assert artifact.status == 'FAILED'
    assert artifact.errors[0]['code'] == 'PERMISSION_DENIED'
    assert not events


def test_required_evidence_missing_is_waiting_review():
    artifact, _ = execute({'status': 'success', 'data': {'exists': True}},
                          task_=task(acceptance_criteria=['tools_succeeded', 'evidence_present']))
    assert artifact.status == 'WAITING_REVIEW' and artifact.unresolved_questions


def test_input_required_has_no_gateway_work():
    item = task(task_type='input_required', input_data={'required_fields': ['asset_id']},
                allowed_tools=[], max_tool_calls=0, acceptance_criteria=[])
    artifact, events = execute({'status': 'success'}, task_=item)
    assert artifact.status == 'WAITING_REVIEW' and not events
    assert 'asset_id' in artifact.unresolved_questions[0]


def test_dependency_identity_and_status_are_required():
    from app.runtime.executor import WorkerExecutor
    from app.runtime.contracts import TaskArtifact
    from app.utils.time import utcnow
    ctx = context()
    item = task(dependencies=['previous'])
    bad = TaskArtifact(task_id='previous', run_id=uuid4(), status='SUCCESS', end_time=utcnow())
    with pytest.raises(ValueError):
        WorkerExecutor().execute(item, ctx, {'previous': bad})


def test_parent_rejects_forged_evidence_and_wrong_task_artifact():
    from app.runtime.executor import validate_outcome
    from app.runtime.contracts import ExecutionOutcome
    ctx = context()
    good, events = execute({'status': 'success', 'data': {'x': 1}}, context_=ctx)
    from app.runtime.contracts import ToolReceipt
    receipt = ToolReceipt.model_validate(events[1]['receipt'])
    forged = good.model_copy(update={'evidence': [{'verified': True, 'claim_id': str(uuid4())}]})
    with pytest.raises(ValueError):
        validate_outcome(task(), ctx, ExecutionOutcome(artifact=forged, receipts=[receipt]))
    with pytest.raises(ValueError):
        validate_outcome(task(), ctx, ExecutionOutcome(artifact=good.model_copy(update={'task_id': 'wrong'}), receipts=[receipt]))


def test_artifact_limit_returns_explicit_failure_without_truncating_facts():
    result, _ = execute({'status': 'success', 'data': {'large': 'x' * 600000}})
    assert result.status == 'FAILED' and result.errors[0]['code'] == 'ARTIFACT_SIZE_LIMIT'
    assert not result.result


def test_size_failure_still_retains_receipt_backed_evidence():
    from app.runtime.executor import validate_outcome
    from app.runtime.contracts import ToolReceipt, ExecutionOutcome
    ref = {'raw_document_id': str(uuid4()), 'verified': False}
    ctx = context()
    result, events = execute({'status': 'success', 'data': {'large': 'x' * 600000},
                              'evidence_refs': [ref]}, context_=ctx)
    receipt = ToolReceipt.model_validate(events[1]['receipt'])
    assert result.evidence == [ref] and result.tool_calls
    assert validate_outcome(task(), ctx, ExecutionOutcome(artifact=result, receipts=[receipt])).artifact.status == 'FAILED'


def test_gateway_exception_emits_finished_audit_receipt():
    from app.runtime.executor import WorkerExecutor
    class Broken:
        def invoke(self, *args, **kwargs):
            raise RuntimeError('private')
    events = []
    result = WorkerExecutor(gateway=Broken(), emit=events.append).execute(task(), context(), {})
    assert result.errors[0]['code'] == 'GATEWAY_FAILURE'
    assert [e['kind'] for e in events] == ['tool_started', 'tool_finished']
    assert events[1]['receipt']['envelope']['status'] == 'failed'


def test_overflow_evidence_reference_cannot_change_receipt_provenance():
    from app.runtime.executor import validate_outcome
    from app.runtime.contracts import ToolReceipt,ExecutionOutcome
    ctx=context()
    ref={'raw_document_id':str(uuid4()),'locator':{'excerpt':'x'*600000},'verified':False}
    artifact,events=execute({'status':'success','data':{'found':True},'evidence_refs':[ref]},context_=ctx)
    receipt=ToolReceipt.model_validate(events[1]['receipt'])
    assert validate_outcome(task(),ctx,ExecutionOutcome(artifact=artifact,receipts=[receipt]))
    for field,value in [('evidence_count',0),('evidence_sha256','0'*64)]:
        changed=artifact.model_copy(update={'result':{**artifact.result,field:value}})
        with pytest.raises(ValueError):
            validate_outcome(task(),ctx,ExecutionOutcome(artifact=changed,receipts=[receipt]))
    promoted=receipt.model_copy(update={'envelope':receipt.envelope.model_copy(
        update={'evidence_refs':[{**ref,'verified':True}]})})
    with pytest.raises(ValueError):
        validate_outcome(task(),ctx,ExecutionOutcome(artifact=artifact,receipts=[promoted]))

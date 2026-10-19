"""Diagnostic hooks must reveal rejection boundaries without changing decisions."""
import json
from uuid import uuid4
import pytest
from tests.agents.test_executor import make_executor
from tests.agents.fixtures import context,outcome


def observer_module():
    from tests.diagnostics import artifact_observer
    return artifact_observer


@pytest.mark.parametrize('mutation,expected',[('cleanup','Cleanup not verified'),('output','Artifact output was changed after tool execution'),('evidence','Artifact evidence is not receipt-backed')])
def test_rejected_output_records_exact_boundary_with_original_rejection(mutation,expected,tmp_path):
    module=observer_module();sink=module.Observer(tmp_path/'events.jsonl')
    def action(request):
        got=outcome(request.task,request.context)
        if mutation=='cleanup':return got.model_copy(update={'cleanup_verified':False})
        if mutation=='output':return got.model_copy(update={'artifact':got.artifact.model_copy(update={'result':{'outputs':[{'changed':True}],'dependencies':{}}})})
        return got.model_copy(update={'artifact':got.artifact.model_copy(update={'evidence':[{'changed':True}]})})
    executor,item,_=make_executor(action=action);ctx=context()
    with module.installed(sink):got=executor.execute(item,ctx,{})
    assert got.artifact.status=='FAILED' and got.artifact.errors[0]['code']=='AGENT_OUTPUT_INVALID'
    events=[json.loads(x) for x in (tmp_path/'events.jsonl').read_text().splitlines()]
    errors=[e for e in events if e.get('exact_validation_failure')]
    assert any(expected in e['exact_validation_failure']['reason'] for e in errors)
    assert all(e['trace_id']==str(ctx.trace_id) and e['runtime_run_id']==str(ctx.run_id) for e in errors)
    assert any(e['event']=='VALIDATION_REJECTED' and e['rejected_artifact_id'] for e in events)


def test_sensitive_payload_and_exception_text_are_never_written(tmp_path):
    module=observer_module();sink=module.Observer(tmp_path/'events.jsonl');ctx=context()
    def action(request):
        got=outcome(request.task,request.context)
        payload={'password':'PRIVATE_PASSWORD','cookie':'PRIVATE_COOKIE','token':'PRIVATE_TOKEN','secret':'PRIVATE_KEY'}
        return got.model_copy(update={'artifact':got.artifact.model_copy(update={'result':{'outputs':[payload],'dependencies':{}}})})
    executor,item,_=make_executor(action=action)
    with module.installed(sink):executor.execute(item,ctx,{})
    text=(tmp_path/'events.jsonl').read_text()
    assert all(secret not in text for secret in ('PRIVATE_PASSWORD','PRIVATE_COOKIE','PRIVATE_TOKEN','PRIVATE_KEY'))
    record=module.failure_detail(ValueError('PRIVATE_TOKEN cookie=PRIVATE_COOKIE'))
    assert 'PRIVATE' not in json.dumps(record)


def test_diagnostic_write_failure_cannot_change_accepted_outcome(tmp_path,monkeypatch):
    module=observer_module();sink=module.Observer(tmp_path/'events.jsonl')
    monkeypatch.setattr(sink,'_write',lambda record:(_ for _ in ()).throw(OSError('PRIVATE filesystem failure')))
    executor,item,_=make_executor()
    with module.installed(sink):got=executor.execute(item,context(),{})
    assert got.artifact.status=='SUCCESS' and sink.dropped_events>0


def test_content_hash_preserves_payload_across_receipt_reference_expansion():
    module=observer_module();source=outcome().artifact
    stored=source.model_copy(update={'tool_calls':[{'record_id':str(uuid4()),'sequence_no':1}]})
    assert module.artifact_hash(source)==module.artifact_hash(stored)
    changed=source.model_copy(update={'result':{'wrong_asset':str(uuid4())}})
    assert module.artifact_hash(source)!=module.artifact_hash(changed)


def test_schema_error_keeps_field_type_but_redacts_input_values():
    from pydantic import ValidationError
    from app.runtime.contracts import TaskArtifact
    module=observer_module()
    try:TaskArtifact.model_validate({'artifact_id':'PRIVATE_TOKEN','unexpected_secret':'PRIVATE_PASSWORD'})
    except ValidationError as exc:details=module.failure_detail(exc)
    assert details['type']=='ValidationError' and details['schema_violations']
    assert 'PRIVATE' not in json.dumps(details)

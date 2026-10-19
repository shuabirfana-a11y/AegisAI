"""Controlled engineering cases; real validators, never benchmark/model results."""
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime.contracts import TaskArtifact
from tests.agents.fixtures import context, outcome
from tests.agents.test_executor import make_executor


def record(name, **values):
    folder = os.environ.get('AEGIS_C18_2_AUDIT')
    if folder:
        path = Path(folder) / (name + '.json')
        path.write_text(json.dumps({'scenario': name, 'engineering_only': True, **values},
                                   ensure_ascii=False, indent=2, default=str), encoding='utf8')


def test_valid_output_uses_real_shared_validator():
    executor, item, _ = make_executor()
    ctx = context()
    result = executor.execute(item, ctx, {})
    assert result.artifact.status == 'SUCCESS'
    assert result.artifact.run_id == ctx.run_id
    assert len(result.receipts) == 1
    assert result.artifact.result['outputs'][0]['data'] == result.receipts[0].envelope.data
    record('A-unit', output=result.model_dump(mode='json'))


@pytest.mark.parametrize('field', ['run_id', 'task_id', 'end_time'])
def test_missing_required_field_is_diagnosed_and_rejected(field):
    captured = {}
    def action(request):
        result = outcome(request.task, request.context)
        payload = result.artifact.model_dump()
        del payload[field]
        with pytest.raises(ValidationError) as exc:
            TaskArtifact.model_validate(payload)
        captured['diagnostics'] = exc.value.errors(include_context=False, include_url=False)
        assert any(e['loc'] == (field,) and e['type'] == 'missing' for e in captured['diagnostics'])
        # Bypass construction ONLY to simulate a corrupt implementation at the trust boundary.
        bad = result.artifact.model_copy()
        object.__delattr__(bad, field)
        return result.model_copy(update={'artifact': bad})
    executor, item, _ = make_executor(action=action)
    ctx = context()
    result = executor.execute(item, ctx, {})
    assert result.artifact.status == 'FAILED'
    assert result.artifact.run_id == ctx.run_id
    assert result.artifact.errors[0]['code'] == 'AGENT_OUTPUT_INVALID'
    assert result.artifact.result == {}
    record('B-' + field, diagnostics=captured['diagnostics'], output=result.model_dump(mode='json'))


@pytest.mark.parametrize(('field', 'value'), [('result', ['not an object']),
                                            ('status', 'CONFIRMED_SAFE'),
                                            ('confidence', {'not': 'a number'})])
def test_wrong_field_type_cannot_become_security_fact(field, value):
    captured = {}
    def action(request):
        result = outcome(request.task, request.context)
        payload = {**result.artifact.model_dump(), field: value}
        with pytest.raises(ValidationError) as exc:
            TaskArtifact.model_validate(payload)
        captured['diagnostics'] = exc.value.errors(include_context=False, include_url=False)
        assert any(e['loc'] == (field,) for e in captured['diagnostics'])
        return result.model_copy(update={'artifact': result.artifact.model_copy(update={field: value})})
    executor, item, _ = make_executor(action=action)
    ctx = context()
    result = executor.execute(item, ctx, {})
    assert result.artifact.status == 'FAILED'
    assert result.artifact.errors[0]['code'] == 'AGENT_OUTPUT_INVALID'
    assert result.artifact.result == {}
    record('C-' + field, diagnostics=captured['diagnostics'], output=result.model_dump(mode='json'))


def test_validator_exception_fails_closed_and_is_run_bound(monkeypatch):
    import app.agents.executor as module
    original = module.validate_artifact_json
    seen = []
    def broken(artifact):
        if artifact.status == 'SUCCESS':
            seen.append(artifact.run_id)
            raise RuntimeError('CONTROLLED_VALIDATOR_EXCEPTION secret=DO_NOT_PUBLISH')
        return original(artifact)
    monkeypatch.setattr(module, 'validate_artifact_json', broken)
    executor, item, _ = make_executor()
    ctx = context()
    result = executor.execute(item, ctx, {})
    assert seen == [ctx.run_id]
    assert result.artifact.run_id == ctx.run_id
    assert result.artifact.status == 'FAILED' and result.artifact.result == {}
    assert result.artifact.errors[0]['code'] == 'AGENT_OUTPUT_INVALID'
    assert 'DO_NOT_PUBLISH' not in result.model_dump_json()
    record('D-unit', observed_run_ids=seen, output=result.model_dump(mode='json'))


def test_prior_run_output_is_rejected_on_fresh_executor():
    previous = {}
    def action(request):
        if not previous:
            previous['output'] = outcome(request.task, request.context)
        return previous['output']
    first, item, _ = make_executor(action=action)
    one = first.execute(item, context(), {})
    second, item, _ = make_executor(action=action)
    ctx = context()
    two = second.execute(item, ctx, {})
    assert one.artifact.status == 'SUCCESS'
    assert two.artifact.status == 'FAILED' and two.artifact.result == {}
    assert two.artifact.run_id == ctx.run_id != one.artifact.run_id
    assert two.artifact.artifact_id != one.artifact.artifact_id
    record('F-prior-run', previous=one.model_dump(mode='json'), current=two.model_dump(mode='json'))


def test_foreign_dependency_cannot_enter_current_run():
    from app.agents.artifacts import build_handoff
    from app.agents.contracts import AgentFrameworkError
    from tests.agents.fixtures import task
    executor, root, _ = make_executor()
    old = outcome(root, context()).artifact
    child = task('child', deps=('lookup',))
    with pytest.raises(AgentFrameworkError) as exc:
        build_handoff(child, context(run_id=uuid4()), {'lookup': old}, executor.bound.bindings)
    assert exc.value.code == 'AGENT_HANDOFF_INVALID'
    record('E-foreign-dependency', rejected_code=exc.value.code, old_run=old.run_id)

"""Actual PostgreSQL/runtime/tools/Gate/published-answer boundary integration.

Only model planning uses existing SYNTHETIC engineering fixtures. Invalid agent
outputs and validator exceptions are injected solely in these tests.
"""
from uuid import uuid4

import pytest

from app.agents.executor import AgentExecutor
from app.db import models as m
from app.db.session import transaction
from app.orchestration.answer_sources import AnswerSourcesLoader
from app.orchestration.service import InvestigationOrchestrator
from app.runtime.store import PostgresRuntimeStore
from tests.agents.test_artifact_boundary_c18_2 import record
from tests.orchestration.fixtures import scenario


def scoped_bad_output(monkeypatch, actor, mode, target=None):
    original = AgentExecutor._instance
    events = []
    class Proxy:
        def __init__(self, delegate): self.delegate = delegate
        def execute(self, request, *, database_url=None):
            result = self.delegate.execute(request, database_url=database_url)
            if request.task.task_id != 'lookup': return result
            if target is not None and request.task.input_data['steps'][0]['arguments'].get('target') != target:
                return result
            events.append({'run_id': request.context.run_id, 'task_id': request.task.task_id,
                           'original_artifact_id': result.artifact.artifact_id})
            bad = result.artifact.model_copy()
            if mode == 'missing': object.__delattr__(bad, 'end_time')
            elif mode == 'type': bad = bad.model_copy(update={'result': ['untrusted conclusion']})
            return result.model_copy(update={'artifact': bad})
    def instance(self, binding, ctx):
        got = original(self, binding, ctx)
        return Proxy(got) if ctx.actor == actor and binding.agent_id == 'investigation_agent' else got
    monkeypatch.setattr(AgentExecutor, '_instance', instance)
    return events


def assert_safe_failure(engine, result, actor):
    assert result.answer is not None
    assert result.answer.integration_status not in ('PASS', 'PASS_WITH_WARNINGS')
    assert not result.answer.verified_claims
    assert result.answer.risk_assessment is None
    assert result.context.verification_run_id is None
    assert result.context.analysis_run_id is None
    trace = PostgresRuntimeStore(engine).read_trace(result.context.investigation_run_id, actor)
    bad = next(a for a in trace.artifacts if a.task_id == 'lookup')
    assert bad.status == 'FAILED' and bad.result == {}
    assert any(e['code'] == 'AGENT_OUTPUT_INVALID' for e in bad.errors)
    assert next(t for t in trace.tasks if t.task_id == 'lookup').artifact_id == bad.artifact_id
    stored = InvestigationOrchestrator(engine, None).get_result(result.context.logical_investigation_id, actor=actor)
    assert stored.answer == result.answer
    return trace


def test_valid_artifact_persistence_consumer_and_published_answer(engine):
    seed, request, gateway, _, _ = scenario(engine)
    try:
        service = InvestigationOrchestrator(engine, gateway)
        result = service.investigate(request, actor=seed.actor)
        assert result.answer.integration_status in ('PASS', 'PASS_WITH_WARNINGS')
        source, _, _ = AnswerSourcesLoader(engine).load(result.context, actor=seed.actor)
        trace = PostgresRuntimeStore(engine).read_trace(result.context.investigation_run_id, seed.actor)
        artifact = next(a for a in trace.artifacts if a.artifact_id == source.investigation.artifact_id)
        assert artifact.run_id == source.investigation.run_id == result.context.investigation_run_id
        assert next(t for t in trace.tasks if t.task_id == artifact.task_id).artifact_id == artifact.artifact_id
        assert result.answer.verified_claims and result.answer.evidence_references
        assert source.analysis.asset_id == seed.asset_id
        assert service.get_result(result.context.logical_investigation_id, actor=seed.actor).answer == result.answer
        record('A-persist-consume-publish', asset_id=seed.asset_id, result=result.model_dump(mode='json'),
               artifact=artifact.model_dump(mode='json'), source=source.model_dump(mode='json'))
    finally: gateway.close()


@pytest.mark.parametrize('mode', ['missing', 'type'])
def test_invalid_output_cannot_persist_as_success_or_publish_risk(engine, monkeypatch, mode):
    seed, request, gateway, _, _ = scenario(engine)
    events = scoped_bad_output(monkeypatch, seed.actor, mode)
    try:
        result = InvestigationOrchestrator(engine, gateway).investigate(request, actor=seed.actor)
        assert events
        trace = assert_safe_failure(engine, result, seed.actor)
        record('B-published' if mode == 'missing' else 'C-published', injection=events,
               asset_id=seed.asset_id, result=result.model_dump(mode='json'), trace=trace.model_dump(mode='json'))
    finally: gateway.close()


def test_validator_exception_cannot_publish_or_reuse_previous_answer(engine, monkeypatch):
    import app.agents.executor as module
    from tests.planner.fixtures import gateway_with_responses
    from tests.agents.investigation.test_end_to_end import plan_for
    from tests.planner.fixtures import task
    seed, request, gateway, _, _ = scenario(engine)
    service = InvestigationOrchestrator(engine, gateway)
    try:
        old = service.investigate(request, actor=seed.actor)
        assert old.answer.verified_claims
    finally: gateway.close()
    original = module.validate_artifact_json
    observed = []
    def broken(artifact):
        if artifact.task_id == 'lookup' and artifact.status == 'SUCCESS':
            observed.append(artifact.run_id)
            raise RuntimeError('CONTROLLED_EXCEPTION_NOT_A_SECURITY_FACT')
        return original(artifact)
    plan = plan_for(seed, 'version')
    plan['tasks'].append(task('asset_lookup', 'asset', 'get_asset', {'asset_id': str(seed.asset_id)}))
    raw = request.model_dump(mode='json')
    raw['planner_input']['query']['request_key'] = 'C18_2-' + uuid4().hex
    retry = type(request).model_validate(raw)
    gw, _, _ = gateway_with_responses([plan])
    try:
        with monkeypatch.context() as patch:
            patch.setattr(module, 'validate_artifact_json', broken)
            bad = InvestigationOrchestrator(engine, gw).investigate(retry, actor=seed.actor)
        assert observed
        assert_safe_failure(engine, bad, seed.actor)
        assert bad.context.logical_investigation_id != old.context.logical_investigation_id
        assert bad.context.investigation_run_id != old.context.investigation_run_id
        assert not set(bad.answer.accepted_source_run_references) & set(old.answer.accepted_source_run_references)
        # Idempotent retry returns this failed investigation, never old success.
        replay = InvestigationOrchestrator(engine, gw).investigate(retry, actor=seed.actor)
        assert replay.context.logical_investigation_id == bad.context.logical_investigation_id
        assert replay.answer == bad.answer
        # Original immutable success remains readable and unchanged.
        assert service.get_result(old.context.logical_investigation_id, actor=seed.actor).answer == old.answer
        record('D-F-persistent-retry', asset_id=seed.asset_id, old=old.model_dump(mode='json'),
               failed=bad.model_dump(mode='json'), replay=replay.model_dump(mode='json'), observed_runs=observed)
    finally: gw.close()


@pytest.mark.parametrize('same_owner', [False, True])
def test_invalid_asset_investigation_cannot_contaminate_independent_success(engine, monkeypatch, same_owner):
    bad_seed, bad_request, bad_gw, _, _ = scenario(engine)
    good_seed, good_request, good_gw, _, _ = scenario(engine)
    if same_owner:
        good_seed.actor = bad_seed.actor
        with transaction(engine) as db:
            db.get(m.Asset, good_seed.asset_id).owner_principal = bad_seed.actor
    events = scoped_bad_output(monkeypatch, bad_seed.actor, 'type', target=bad_seed.cve)
    try:
        bad = InvestigationOrchestrator(engine, bad_gw).investigate(bad_request, actor=bad_seed.actor)
        good = InvestigationOrchestrator(engine, good_gw).investigate(good_request, actor=good_seed.actor)
        assert events
        assert_safe_failure(engine, bad, bad_seed.actor)
        assert good.answer.integration_status in ('PASS', 'PASS_WITH_WARNINGS')
        source, _, _ = AnswerSourcesLoader(engine).load(good.context, actor=good_seed.actor)
        assert source.analysis.asset_id == good_seed.asset_id != bad_seed.asset_id
        assert good.answer.verified_claims and good.answer.evidence_references
        assert not set(good.answer.evidence_references) & set(bad.answer.evidence_references)
        assert not {c.claim_id for c in good.answer.verified_claims} & {c.claim_id for c in bad.answer.verified_claims}
        assert good.context.logical_investigation_id != bad.context.logical_investigation_id
        if not same_owner:
            with pytest.raises(LookupError):
                InvestigationOrchestrator(engine, good_gw).get_result(good.context.logical_investigation_id, actor=bad_seed.actor)
        # Stored runtime rows, not only DTOs, retain investigation ownership.
        with transaction(engine) as db:
            assert db.get(m.AgentRun, good.context.investigation_run_id).actor_principal == good_seed.actor
            assert db.get(m.AgentRun, bad.context.investigation_run_id).actor_principal == bad_seed.actor
        record('E-isolation-' + ('same-owner' if same_owner else 'different-owner'), bad_asset=bad_seed.asset_id, good_asset=good_seed.asset_id,
               failed=bad.model_dump(mode='json'), valid=good.model_dump(mode='json'), source=source.model_dump(mode='json'))
    finally:
        bad_gw.close()
        good_gw.close()


def test_verification_validator_exception_never_promotes_confirmed_tool_receipt(engine, monkeypatch):
    """Recreate the historical *boundary shape*, without claiming its lost cause."""
    import app.agents.executor as module
    from app.agents.verification.service import EvidenceVerificationService
    seed, request, gateway, _, _ = scenario(engine)
    original = module.validate_artifact_json
    injected = []
    def broken(artifact):
        if artifact.task_id == 'verify' and artifact.status == 'SUCCESS':
            injected.append(artifact.model_dump(mode='json'))
            raise RuntimeError('CONTROLLED_VERIFICATION_VALIDATOR_FAILURE')
        return original(artifact)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(module, 'validate_artifact_json', broken)
            result = InvestigationOrchestrator(engine, gateway).investigate(request, actor=seed.actor)
        assert len(injected) == 1
        assert injected[0]['result']['outputs'][0]['data']['assessment']['verification_status'] == 'CONFIRMED'
        assert result.context.verification_run_id is not None
        assert result.context.analysis_run_id is None
        verification = EvidenceVerificationService(engine).read_results(result.context.verification_run_id, actor=seed.actor)
        art = verification.artifacts[0]
        assert art.execution_status == 'FAILED'
        assert art.verification_status == 'INSUFFICIENT_EVIDENCE' and art.partial_result
        assert 'RUNTIME_INCOMPLETE' in art.unresolved_items
        assert result.answer.integration_status not in ('PASS', 'PASS_WITH_WARNINGS')
        assert not result.answer.verified_claims and result.answer.risk_assessment is None
        persisted = PostgresRuntimeStore(engine).read_trace(result.context.verification_run_id, seed.actor)
        assert persisted.artifacts[0].status == 'FAILED'
        assert persisted.artifacts[0].errors[0]['code'] == 'AGENT_OUTPUT_INVALID'
        assert persisted.artifacts[0].artifact_id == art.artifact_id
        assert result.context.logical_investigation_id == InvestigationOrchestrator(engine, None).get_result(
            result.context.logical_investigation_id, actor=seed.actor).context.logical_investigation_id
        record('D-verification-confirmed-receipt-rejected', asset_id=seed.asset_id,
               injected=injected, result=result.model_dump(mode='json'),
               verification=verification.model_dump(mode='json'), trace=persisted.model_dump(mode='json'))
    finally: gateway.close()

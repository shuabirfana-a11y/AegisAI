"""Persisted model identity survives process/provider switches; synthetic protocol only."""
from contextlib import contextmanager
from copy import deepcopy
from uuid import uuid4
import httpx
import pytest
from app.db import models as m
from app.db.session import transaction
from app.investigation_api.service import InvestigationApiService
from app.llm.config import ModelConfig
from app.llm.gateway import ModelGateway
from app.llm.providers.openai_compatible import OpenAICompatibleProvider
from app.orchestration.contracts import InvestigationRequest
from app.planner.schemas import PlannerInput


def gateway(real=False, model='SYNTHETIC-local-model', returned_model=None):
    if not real:
        return ModelGateway(ModelConfig())
    config = ModelConfig(provider='openai_compatible', model=model,
                         api_base='http://127.0.0.1:11434/v1', allow_keyless_local=True,
                         embedding_provider='mock')
    def response(request):
        return httpx.Response(200, json={'model': returned_model or model, 'choices': [{
            'message': {'role': 'assistant', 'content': '{"invalid_plan":true}'},
            'finish_reason': 'stop'}]})
    return ModelGateway(config, text_provider=OpenAICompatibleProvider(
        config, capability='text', transport=httpx.MockTransport(response)))


def request():
    target = 'CVE-2099-9999001'
    return InvestigationRequest(planner_input=PlannerInput(query={
        'question': target + '是什么？', 'target': target,
        'request_key': 'phase12d-SYNTHETIC-' + uuid4().hex}))


@contextmanager
def failed_investigation(engine, real=False, model='SYNTHETIC-local-model', returned_model=None):
    owner = 'phase12d-SYNTHETIC-' + uuid4().hex
    with gateway(real, model, returned_model) as gw:
        api = InvestigationApiService(engine, gw)
        try:
            req = request()
            result = api.reader.investigate(req, actor=owner)
            assert result.context.error_code == 'PLANNING_FAILED'
            yield api, req, owner, result
        finally:
            api.close()


def metadata(api, result, owner):
    trace = api.trace(result.context.logical_investigation_id, actor=owner)
    value = getattr(trace, 'model_execution', None)
    assert value is not None, 'Public persisted model execution metadata is not implemented'
    return value


def test_mock_history_stays_mock_after_real_switch(engine):
    with failed_investigation(engine) as (api, req, owner, result), gateway(True) as real:
        api.gateway = real
        value = metadata(api, result, owner)
        assert value.execution_mode == 'MOCK'
        assert value.provider == 'mock' and value.model == 'mock-text-v1'


def test_real_history_stays_real_after_mock_switch(engine):
    with failed_investigation(engine, True) as (api, req, owner, result), gateway() as mock:
        api.gateway = mock
        value = metadata(api, result, owner)
        assert value.execution_mode == 'REAL'
        assert value.provider == 'openai_compatible' and value.model == 'SYNTHETIC-local-model'


def test_requested_alias_and_consistent_actual_model_are_preserved(engine):
    with failed_investigation(engine, True, 'SYNTHETIC-alias', 'SYNTHETIC-alias:latest') as (api, req, owner, result):
        assert metadata(api, result, owner).model == 'SYNTHETIC-alias:latest'


def test_failed_real_call_is_real_but_not_success(engine):
    with failed_investigation(engine, True) as (api, req, owner, result):
        value = metadata(api, result, owner)
        assert value.execution_mode == 'REAL' and value.attempt_count == 2
        assert value.source == 'PERSISTED_PLANNER_CALL'
        assert api.answer(result.context.logical_investigation_id, actor=owner).answer_status == 'FAILED'


def test_reused_investigation_uses_persisted_identity(engine):
    with failed_investigation(engine) as (api, req, owner, result), gateway(True) as real:
        api.gateway = real
        receipt = api.create(req, actor=owner)
        assert receipt.reused and receipt.investigation_id == result.context.logical_investigation_id
        assert metadata(api, result, owner).execution_mode == 'MOCK'


def test_no_completed_call_means_unknown_metadata(engine):
    from app.investigation_api import model_execution
    from app.planner.trace import PlannerTraceStore
    from app.planner.schemas import ModelIdentity
    from app.runtime.contracts import RuntimePolicy
    with gateway() as gw:
        api = InvestigationApiService(engine, gw)
        try:
            owner = 'phase12d-SYNTHETIC-' + uuid4().hex
            req = request()
            context = api.reader.store.claim(req, actor=owner).context
            assert model_execution.read_model_execution(engine, context, actor=owner) is None
            saved, _ = PlannerTraceStore(engine).create(req.planner_input, owner, RuntimePolicy(),
                model_identity=ModelIdentity(provider='mock', model='mock-text-v1', is_mock=True),
                prompt_version='task-plan-v1', registry_version='planner-registry-v1')
            context = context.model_copy(update={'planner_run_id': saved.planner_run_id})
            assert model_execution.read_model_execution(engine, context, actor=owner) is None
        finally:
            api.close()


def test_unowned_planner_trace_cannot_be_read(engine):
    from app.investigation_api import model_execution
    with failed_investigation(engine) as (api, req, owner, result):
        with pytest.raises(LookupError):
            model_execution.read_model_execution(engine, result.context, actor='SYNTHETIC-other-owner')


def test_identity_mismatch_is_not_repaired(engine):
    from app.investigation_api import model_execution
    with failed_investigation(engine) as (api, req, owner, result):
        with transaction(engine) as db:
            row = db.get(m.AgentRun, result.context.planner_run_id)
            details = deepcopy(row.details)
            details['planner_v1']['attempts'][0]['model_call']['model'] = 'SYNTHETIC-mismatched'
            row.details = details
        with pytest.raises(ValueError, match='MODEL_EXECUTION_IDENTITY_MISMATCH'):
            model_execution.read_model_execution(engine, result.context, actor=owner)
        with transaction(engine) as db:
            assert db.get(m.AgentRun, result.context.planner_run_id).details == details


def test_public_metadata_has_no_secrets_or_raw_output(engine, monkeypatch):
    with failed_investigation(engine, True, 'SYNTHETIC-local-secret') as (api, req, owner, result):
        monkeypatch.setenv('MODEL_API_KEY', 'SYNTHETIC-local-secret')
        value = metadata(api, result, owner)
        assert set(value.model_dump()) == {'execution_mode', 'provider', 'model', 'source', 'attempt_count'}
        assert 'SYNTHETIC-local-secret' not in value.model_dump_json()
        trace = api.trace(result.context.logical_investigation_id, actor=owner).model_dump_json()
        assert 'raw_output' not in trace and 'api_base' not in trace


def test_public_metadata_preserves_a_gateway_valid_long_model_name(engine):
    model = 'SYNTHETIC-' + 'a' * 160
    with failed_investigation(engine, True, model) as (api, req, owner, result):
        assert metadata(api, result, owner).model == model

"""Real TCP/service execution with synthetic fixtures, not a real-model result."""
from app.main import create_app
from app.planner.trace import PlannerTraceStore
from scripts.probe_planner_stability import run_stability_case, run_planner_case, summarize
from tests.investigation_api.test_tcp_chain import tcp_client, bound_case, TOKEN
from tests.orchestration.fixtures import scenario


def test_complete_synthetic_chain_is_never_counted_as_a_real_model_success(engine, monkeypatch):
    seed, request, gateway, calls, _ = scenario(engine)
    monkeypatch.setenv('AEGIS_ASSET_TOKEN', TOKEN)
    monkeypatch.setenv('AEGIS_ASSET_OWNER', seed.actor)
    try:
        with tcp_client(create_app(engine, investigation_gateway=gateway)) as client:
            case = bound_case(seed, request)
            case['request'] = case['request'].model_dump(mode='json')
            read = lambda id: PlannerTraceStore(engine).read(id, seed.actor)
            receipt = run_stability_case(client, case, read)
            assert receipt['full_chain_executed'] and receipt['planner_validated']
            assert receipt['integration_status'] == 'PASS'
            assert receipt['error_code'] == 'MODEL_MODE_MISMATCH'
            assert receipt['data_origin'] == 'SYNTHETIC_TEST'
            assert not receipt['real_mode_confirmed'] and not receipt['gate_accepted']
            assert receipt['answer_frozen_read_verified']
            assert receipt['answer_read_extra_planner_calls'] == 0 and len(calls) == 1
            assert summarize([receipt])['runs']['full_chain_success_rate'] == 0.
            assert all(a['is_mock'] for a in receipt['attempts'])
    finally:
        gateway.close()


def test_planner_repetition_persists_original_audit_without_executing_runtime(engine):
    from sqlalchemy import select, func
    from app.db.session import transaction
    from app.db import models as m

    seed, request, gateway, calls, _ = scenario(engine)
    case = bound_case(seed, request)
    case['request'] = case['request'].model_dump(mode='json')
    try:
        receipt = run_planner_case(engine, gateway, seed.actor, case)
        audit = PlannerTraceStore(engine).read(receipt['planner_run_id'],seed.actor)
        assert receipt['planner_validated'] and audit.validation_status == 'VALIDATED'
        assert audit.runtime_run_id is None and len(calls) == 1
        assert not receipt['chain_attempted'] and not receipt['real_mode_confirmed']
        assert receipt['transport'] == 'INTERNAL_PRODUCTION_PLANNER'
        assert summarize([receipt])['runs']['full_chain_success_rate'] is None
        with transaction(engine) as db:
            assert db.scalar(select(func.count()).select_from(m.AgentRun).where(
                m.AgentRun.actor_principal==seed.actor,m.AgentRun.agent_type=='runtime-v1')) == 0
    finally:
        gateway.close()


def test_actual_store_finalizes_interrupted_synthetic_planner(engine, monkeypatch):
    import pytest
    seed, request, gateway, _, _ = scenario(engine)
    case=bound_case(seed,request)
    case['request']=case['request'].model_dump(mode='json')
    def interrupted(*args,**kwargs):raise KeyboardInterrupt()
    monkeypatch.setattr(gateway.text_provider,'generate_structured',interrupted)
    receipt={}
    try:
        with pytest.raises(KeyboardInterrupt):
            run_planner_case(engine,gateway,seed.actor,case,receipt=receipt)
        audit=PlannerTraceStore(engine).read(receipt['planner_run_id'],seed.actor)
        assert audit.validation_status=='PLANNING_FAILED' and audit.runtime_run_id is None
        assert audit.error[0].code=='PROBE_INTERRUPTED'
        assert receipt['audit_cleanup_complete'] and not receipt['attempt_accounting_complete']
    finally:gateway.close()

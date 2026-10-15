"""Run the documented portable baseline, refusing DB fixtures before execution."""
import os
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
TESTS = [
    "tests/test_phase14b3_graph.py::test_graph_budget_is_explicit_and_has_no_dangling_edges",
    "tests/test_phase14b3_graph.py::test_openapi_graph_and_query_are_typed",
    "tests/model_gateway", "tests/test_schema_contract.py", "tests/test_normalizers.py",
    "tests/test_ingestion_units.py", "tests/test_phase7_rules.py",
    "tests/runtime/test_contracts_plan.py", "tests/runtime/test_graph_states.py",
    "tests/runtime/test_scheduler.py", "tests/agents/test_contracts_registry.py",
    "tests/agents/test_artifacts.py", "tests/agents/test_router.py",
    "tests/planner/test_schemas_registry.py", "tests/planner/test_validation.py",
    "tests/planner/test_task_input_schema.py",
    "tests/integration/test_contracts.py", "tests/agents/investigation/test_planning.py",
    "tests/agents/investigation/test_model_schema.py",
    "tests/agents/investigation/test_normalize.py", "tests/agents/verification/test_schemas.py",
    "tests/agents/analysis/test_schemas.py", "tests/orchestration/test_contracts_scope.py",
    "tests/orchestration/test_legacy_compat.py::test_old_api_and_business_source_hashes_are_unchanged",
    "tests/investigation_api/test_contract.py",
    "tests/investigation_api/test_multi_asset.py",
    "tests/investigation_api/test_service.py", "tests/investigation_api/test_review_regressions.py",
    "tests/investigation_api/test_http_probe.py",
    "tests/investigation_api/test_planner_stability.py",
    "tests/investigation_api/test_stability_failures.py",
    "tests/investigation_api/test_failure_diagnostics.py",
    "tests/orchestration/test_asset_handoff.py", "tests/orchestration/test_impact_input.py",
    "tests/orchestration/test_asset_nonimpact.py", "tests/orchestration/test_observation_proof.py",
    "tests/orchestration/test_demo_case_export.py",
    "tests/agents/investigation/test_scope_schema.py",
    "tests/agents/verification/test_conflict_artifact.py",
    "tests/orchestration/test_conflict_handoff.py",
    "tests/agents/investigation/test_normalization.py",
    "tests/agents/investigation/test_task_templates.py",
    "tests/investigation_api/test_missing_context.py",
    "tests/test_phase14_sources.py", "tests/test_phase14_cli.py",
    "tests/test_phase14_api.py::test_intelligence_openapi_schema_documents_source_and_poc_states",
    "tests/test_phase14b1_poc.py::test_invalid_reference_is_rejected",
    "tests/test_phase14b1_poc.py::test_invalid_state_or_missing_evidence_is_rejected",
    "tests/test_phase14b1_poc.py::test_poc_openapi_has_all_fields_and_exact_states",
    "tests/test_phase14b2_pipeline.py::test_configuration_is_bounded_before_network",
    "tests/test_phase14b2_pipeline.py::test_registry_covers_existing_categories_without_automatic_mock_fallback",
    "tests/test_phase14b2_pipeline.py::test_scheduler_stop_prevents_extra_cycles_and_does_not_force_every_refresh",
    "tests/test_phase14b2_pipeline.py::test_mock_is_rejected_for_a_development_database_before_any_work",
    "tests/test_phase14b2_pipeline.py::test_pipeline_openapi_is_typed_and_keeps_availability_distinct_from_verification",
    "tests/test_phase14b2_pipeline.py::test_invalid_pipeline_deadline_is_rejected_before_db_or_http",
    "tests/test_phase14b2_pipeline.py::test_guard_invalidates_on_uncertain_acquisition_commit",
    "tests/test_phase14b2_pipeline.py::test_pipeline_cli_preserves_explicit_zero_budget",
    "tests/test_phase14b2_pipeline.py::test_automation_adapter_does_not_replace_zero_with_six",
    "tests/agents/verification/test_source_formats.py::test_package_less_vendor_confirmation_binds_exact_repository",
]


class NoDatabaseFixtures:
    def pytest_collection_modifyitems(self, items):
        blocked = [item.nodeid for item in items if
                   {"engine", "db", "seed", "runtime_seed", "completed_chain"} &
                   set(item.fixturenames)]
        if blocked:
            raise pytest.UsageError("Database-dependent tests entered the unit baseline: " +
                                    ", ".join(blocked))


def main():
    for name in ("AEGIS_DATABASE_URL", "AEGIS_TEST_DATABASE_URL", "AEGIS_RUNTIME_TEST_DATABASE_URL",
                 "MODEL_API_KEY", "MODEL_EMBEDDING_API_KEY", "MODEL_API_BASE"):
        os.environ.pop(name, None)
    os.environ.update(MODEL_PROVIDER="mock", MODEL_EMBEDDING_PROVIDER="mock",
                      MODEL_NAME="mock-text-v1", MODEL_EMBEDDING_NAME="mock-embedding-v1",
                      HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    (ROOT / "work").mkdir(exist_ok=True)
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    print("Portable unit baseline; no DB credentials or real model calls. "
          "Cached-real-embedding test is excluded explicitly.")
    return pytest.main(["-q", *TESTS, "-k",
                       "not test_cached_real_local_embedding_through_gateway"],
                       plugins=[NoDatabaseFixtures()])


if __name__ == "__main__":
    raise SystemExit(main())

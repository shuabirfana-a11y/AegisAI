"""Compare current Python contracts with exports without lifespan or DB access."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ContractMismatch(ValueError):
    pass


def assert_json_matches(actual, path):
    if actual != json.loads(path.read_text(encoding="utf-8")):
        raise ContractMismatch("Contract export differs from current code: " + str(path))


def source_contracts():
    from pydantic.json_schema import models_json_schema
    from app.main import app
    from app.api.assets import NewAsset, NewComponent, UpdateVersion
    from app.api.enrichment import Decision
    from app.assistant.contracts import QueryRequest, TaskContract as LegacyTaskContract, TaskArtifact as LegacyTaskArtifact
    from app.tooling.contracts import ToolEnvelope, REGISTRY
    from app.orchestration.contracts import InvestigationRequest, InvestigationStatus, InvestigationResult, StageEvent
    from app.orchestration.answer_contracts import AnswerEnvelope, Citation, EvidenceObservation
    from app.orchestration.trace import InvestigationTrace
    from app.agents.contracts import AgentContract, AgentRunTrace
    from app.runtime.contracts import TaskArtifact, TaskTrace, RunSnapshot, TraceSnapshot
    from app.agents.investigation.schemas import InvestigationArtifact, InvestigationRunResult
    from app.agents.verification.schemas import VerificationArtifact, VerificationRequest, VerificationClaim, VerificationEvidence, VerificationRun, VerificationRunResult
    from app.agents.analysis.schemas import RiskAnalysisArtifact, AnalysisRequest, AnalysisRun, AnalysisRunResult
    from app.integration.contracts import IntegrationResult, IntegrationRequest, IntegrationTrace, ArtifactRef

    groups = {
        "http-input": ({"QueryRequest": QueryRequest, "Decision": Decision,
                       "NewAsset": NewAsset, "NewComponent": NewComponent,
                       "UpdateVersion": UpdateVersion}, "validation"),
        "tool-input": ({cls.__name__: cls for cls in dict.fromkeys(s.input for s in REGISTRY.values())}, "validation"),
        "internal-input": ({"InvestigationRequest": InvestigationRequest,
                           "VerificationRequest": VerificationRequest,
                           "AnalysisRequest": AnalysisRequest,
                           "IntegrationRequest": IntegrationRequest}, "validation"),
        "internal-output": ({
            "InvestigationStatus": InvestigationStatus, "InvestigationResult": InvestigationResult,
            "AnswerEnvelope": AnswerEnvelope, "IntegrationResult": IntegrationResult,
            "InvestigationTrace": InvestigationTrace, "AgentContract": AgentContract,
            "AgentRunTrace": AgentRunTrace, "RuntimeTaskArtifact": TaskArtifact,
            "RuntimeTaskTrace": TaskTrace, "RuntimeRunSnapshot": RunSnapshot,
            "RuntimeTraceSnapshot": TraceSnapshot, "InvestigationArtifact": InvestigationArtifact,
            "InvestigationRunResult": InvestigationRunResult, "VerificationArtifact": VerificationArtifact,
            "VerificationClaim": VerificationClaim, "VerificationEvidence": VerificationEvidence,
            "VerificationRun": VerificationRun, "VerificationRunResult": VerificationRunResult,
            "RiskAnalysisArtifact": RiskAnalysisArtifact, "AnalysisRun": AnalysisRun,
            "AnalysisRunResult": AnalysisRunResult, "IntegrationTrace": IntegrationTrace,
            "ArtifactRef": ArtifactRef, "EvidenceReference": Citation,
            "EvidenceObservation": EvidenceObservation, "StageEvent": StageEvent}, "serialization"),
        "legacy-output": ({"LegacyTaskContract": LegacyTaskContract,
                          "LegacyTaskArtifact": LegacyTaskArtifact,
                          "ToolEnvelope": ToolEnvelope}, "serialization"),
    }
    result = {}
    for name, (roots, mode) in groups.items():
        refs, common = models_json_schema([(cls, mode) for cls in roots.values()],
                                         ref_template="#/$defs/{model}")
        result[name] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "x-contract-origin": "CURRENT_PYTHON_CODE",
            "x-http-exposed": name == "http-input",
            "$defs": common.get("$defs", {}),
            "x-roots": {key: refs[(cls, mode)] for key, cls in roots.items()},
        }
    return app.openapi(), result, groups


def main():
    sys.path.insert(0, str(ROOT / "backend"))
    from jsonschema import Draft202012Validator
    openapi, current, groups = source_contracts()
    folders = [ROOT / "docs/frontend-contracts",
               ROOT / "AegisAI_FRONTEND_HANDOFF_PACKAGE/api/reference"]
    for folder in folders:
        assert_json_matches(openapi, folder / "openapi.json")
        for name, schema in current.items():
            Draft202012Validator.check_schema(schema)
            assert_json_matches(schema, folder / (name + ".schemas.json"))
        # This export is a manual ORM column shape, not a Pydantic HTTP response.
        column_schema = json.loads((folder / "http-data-columns.schemas.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(column_schema)
    assert_json_matches(json.loads((folders[0] / "http-data-columns.schemas.json").read_text(encoding="utf-8")),
                        folders[1] / "http-data-columns.schemas.json")
    methods = {"get", "post", "patch", "put", "delete", "options", "head"}
    operations = {(path, method.upper()) for path, entry in openapi["paths"].items()
                  for method in entry if method in methods}
    for folder in folders:
        inventory = json.loads((folder / "http-apis.json").read_text(encoding="utf-8"))["operations"]
        if {(item["url"], item["method"]) for item in inventory} != operations:
            raise ContractMismatch("HTTP operation inventory differs: " + str(folder))
    mock = ROOT / "AegisAI_FRONTEND_HANDOFF_PACKAGE/mock"
    models = {
        "investigation-demo.json": (groups["internal-input"][0]["InvestigationRequest"],
                                    groups["internal-output"][0]["InvestigationStatus"]),
        "agent-trace-demo.json": (groups["internal-output"][0]["InvestigationTrace"],),
        "answer-demo.json": (groups["internal-output"][0]["AnswerEnvelope"],),
    }
    checked = 0
    for name, types in models.items():
        fixture = json.loads((mock / name).read_text(encoding="utf-8"))
        if fixture["api_status"] != "MOCK_ONLY" or fixture["production_data"] is not False:
            raise ContractMismatch("Fixture lost its Mock label: " + name)
        for obj in fixture["scenarios"].values():
            if len(types) == 2:
                types[0].model_validate(obj["request"])
                types[1].model_validate(obj["status"])
                checked += 2
            else:
                types[0].model_validate(obj)
                checked += 1
    print(json.dumps({"status": "PASS", "http_operations": len(operations),
                      "current_python_schema_groups": len(current),
                      "manual_column_schema": "VALIDATED_AND_MIRRORED_ONLY",
                      "synthetic_objects_validated": checked,
                      "database_connected": False, "exports_modified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

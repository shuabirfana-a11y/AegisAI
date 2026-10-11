from types import MappingProxyType
from app.planner.registry import TaskRole

TOOLS=MappingProxyType({'evidence_verification':'evaluate_evidence_snapshot',
                       'claim_validation':'validate_claim_snapshot','conflict_detection':'compare_claim_snapshot'})
ROLES=MappingProxyType({kind:TaskRole(frozenset({tool})) for kind,tool in TOOLS.items()})
REGISTRY_VERSION='verification-registry-v1'
IMPLEMENTATION_KEY='evidence-verification-v1'

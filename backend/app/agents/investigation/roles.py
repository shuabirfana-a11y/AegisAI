from types import MappingProxyType
from app.planner.registry import TaskRole

ROLES=MappingProxyType({
    'vulnerability_lookup':TaskRole(frozenset({'get_vulnerability','search_vulnerabilities','inspect_component_version'})),
    'evidence_search':TaskRole(frozenset({'get_evidence','get_claims','relation_query','semantic_search'}),
                               frozenset({'tools_succeeded','output_nonempty','evidence_present'})),
    'asset_lookup':TaskRole(frozenset({'get_asset'})),
})
PROMPT_VERSION='investigation-plan-v1'
REGISTRY_VERSION='investigation-registry-v1'
IMPLEMENTATION_KEY='intelligence-investigation-v1'


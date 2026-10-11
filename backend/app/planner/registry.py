from dataclasses import dataclass
from types import MappingProxyType

@dataclass(frozen=True)
class TaskRole:
    tools: frozenset[str]
    criteria: frozenset[str] = frozenset({'tools_succeeded', 'output_nonempty'})

TASK_REGISTRY = MappingProxyType({
    'vulnerability_lookup': TaskRole(frozenset({'get_vulnerability','search_vulnerabilities'})),
    'version_match': TaskRole(frozenset({'resolve_component','relation_query','match_component_vulnerabilities'})),
    'evidence_search': TaskRole(frozenset({'get_evidence','get_claims','relation_query','semantic_search'}),
                              frozenset({'tools_succeeded','output_nonempty','evidence_present'})),
    'patch_analysis': TaskRole(frozenset({'find_vendor_advisories','find_patch_candidates'})),
    'risk_analysis': TaskRole(frozenset({'get_asset_risks','explain_asset_risk','get_epss','get_known_exploitation'})),
})
MISSING_FIELDS = frozenset({'target','asset_id','component_id','snapshot_id','version','write_authorization'})

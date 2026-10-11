from types import MappingProxyType
from app.planner.registry import TaskRole

TOOLS=MappingProxyType({'risk_analysis':'analyze_risk_snapshot',
    'asset_impact_analysis':'analyze_asset_impact_snapshot',
    'remediation_prioritization':'prioritize_remediation_snapshot'})
ROLES=MappingProxyType({kind:TaskRole(frozenset({tool})) for kind,tool in TOOLS.items()})
REGISTRY_VERSION='analysis-registry-v1'
IMPLEMENTATION_KEY='security-analysis-v1'

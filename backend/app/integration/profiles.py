"""Closed acceptance requirements; original explicit questions cannot be narrowed."""
import re
REQUIREMENTS={
    'overview_v1':('identity','overview'),
    'asset_impact_v1':('identity','asset','version_impact','remediation_status'),
    'asset_risk_v1':('identity','asset','version_impact','remediation_status','risk','priority'),
}

def minimum_outcomes(profile,question):
    required=list(REQUIREMENTS[profile])
    if re.search(r'是否.*(?:受|影响)|受.*影响|如何.*(?:修复|处置)',question):
        for value in REQUIREMENTS['asset_impact_v1']:
            if value not in required:required.append(value)
    if re.search(r'风险(?:分析|判断|等级|评估)|优先级',question):
        for value in REQUIREMENTS['asset_risk_v1']:
            if value not in required:required.append(value)
    return tuple(required)

def is_overview(context):
    return bool(context.objective and not {'asset','version_impact','risk','priority'}&set(context.objective.required_outcomes))

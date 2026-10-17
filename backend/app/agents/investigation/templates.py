"""Generic intent guidance; no concrete TaskContract is created by this module."""
from copy import deepcopy

TASK_TEMPLATES={
 'vulnerability_fact':{'template_id':'vulnerability-fact-v1','roles':['vulnerability_lookup','evidence_search'],
  'instruction':'One root lookup per target. Requested facts/claims use a separate evidence_search task, not lookup-role tools.'},
 'version_impact':{'template_id':'version-impact-v1','roles':['vulnerability_lookup','asset_lookup','evidence_search'],
  'instruction':'One root lookup includes version inspection in the same task when supplied. Independently read the supplied asset. Never repeat get_vulnerability in another task.'},
 'asset_risk':{'template_id':'asset-risk-v1','roles':['asset_lookup','vulnerability_lookup','evidence_search'],
  'instruction':'Read the actual bound asset; one root vulnerability lookup with supplied version inspection. Discover source evidence. Verification/risk/Gate remain downstream server stages.'},
 'evidence_conflict':{'template_id':'evidence-conflict-v1','roles':['vulnerability_lookup','evidence_search'],
  'instruction':'One root lookup plus typed evidence/claim discovery. Preserve source disagreement for downstream independent verification; never resolve it in the plan.'},
}


def template_guidance(normalized):
    return deepcopy(TASK_TEMPLATES[normalized.task_type])

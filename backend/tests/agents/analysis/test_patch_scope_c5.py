"""Availability/release objects never imply installation or cross-scope applicability."""
import pytest
from tests.agents.analysis.helpers import context,verified,module
from tests.agents.analysis.test_rules import severity
from tests.agents.analysis.test_recommendations import actions

@pytest.mark.parametrize('case',['correct','other_package','other_branch','reference_only','unknown_version','conflict','pending','uncollected'])
def test_existing_patch_scope_contract_remains_conservative(case):
 fix=verified('FIXED_VERSION','fix',{'version':'0.7.0','ecosystem':'PyPI','package':'vllm'})
 kwargs={}
 if case=='other_package':fix=verified('FIXED_VERSION','fix',{'version':'0.7.0','ecosystem':'PyPI','package':'other'},package='other-package')
 if case=='other_branch':fix=fix.model_copy(update={'claim':fix.claim.model_copy(update={'branch':'release-other'})})
 if case=='pending':fix=verified('FIXED_VERSION','fix',{'version':'0.7.0','ecosystem':'PyPI','package':'vllm'},status='PENDING')
 if case=='reference_only':fix=verified('PATCH_EXISTS','patch',{'url':'https://github.com/vendor/project/commit/'+'a'*40},package=None)
 if case=='unknown_version':kwargs['version']=None
 if case=='conflict':kwargs['verification_status']='CONFLICT'
 if case=='uncollected':fix=None;kwargs['patch_candidates']=[{'status':'CONFIRMED','release_version':'0.7.0'}]
 value=context([verified(),severity()]+([fix] if fix else []),**kwargs)
 result=actions(value);risk=module('rules').assess_risk(value)
 assert risk.patch_availability.applied=='UNKNOWN'
 assert not any(a.action_type=='APPLY_VERIFIED_PATCH' for a in result)
 if case=='correct':assert any(a.action_type=='UPGRADE_VERIFIED_RELEASE' and a.fixed_version=='0.7.0' for a in result)
 elif case=='reference_only':assert any(a.action_type=='INSPECT_PATCH_REFERENCE' and a.applicability=='UNKNOWN' for a in result)
 else:assert not any(a.fixed_version for a in result)

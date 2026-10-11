"""Breaks caught: distribution confusion, wrong interval endpoints and unsupported versions."""
import pytest
from tests.agents.analysis.helpers import context,verified,module
from tests.agents.analysis.test_rules import severity


@pytest.mark.parametrize('version,status,level,priority,affected',[
    ('0.6.0','AFFECTED','HIGH','P1',True),('0.7.0','NOT_AFFECTED','LOW','DEFER',False),
    ('0.7.0rc1','AFFECTED','HIGH','P1',True),('0.7.0+cu124','NOT_AFFECTED','LOW','DEFER',False),
    (None,'UNKNOWN','UNKNOWN','REVIEW_REQUIRED',None),('0.6.0-custom','UNKNOWN','UNKNOWN','REVIEW_REQUIRED',None)])
def test_version_boundaries(version,status,level,priority,affected):
    result=module('rules').assess_risk(context([verified(),severity()],version=version))
    assert result.version_match_status==status and result.affected is affected
    assert (result.risk_level,result.priority)==(level,priority)


def test_exact_package_not_display_product_match():
    result=module('rules').assess_risk(context([verified(),severity()],package='pkg-langchain-core'))
    assert result.asset_match_status=='NOT_MATCHED' and result.affected is False
    assert result.risk_level=='LOW' and result.priority=='DEFER'


def test_unsupported_ecosystem_unknown():
    c=verified(value={'ecosystem':'npm','package':'vllm','range':'<0.7.0'})
    result=module('rules').assess_risk(context([c,severity()]))
    assert result.version_match_status=='UNKNOWN' and result.affected is None


def test_branch_specific_range_without_asset_branch_abstains():
    result=module('rules').assess_risk(context([verified(branch='stable'),severity()]))
    assert result.risk_level=='UNKNOWN' and result.affected is None

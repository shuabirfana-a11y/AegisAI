"""Do not change the risk decision: align scoped non-match summary fields."""
from tests.agents.analysis.helpers import context
from app.tooling.analysis import base_assessment
from uuid import uuid4


def test_different_distribution_stays_scoped_nonimpact_in_output():
    c=context()
    asset=c.inputs.asset.model_copy(update={'package_identifier_id':'other-package','package_name':'other-package',
        'version_observation_id':uuid4()})
    c=c.model_copy(update={'inputs':c.inputs.model_copy(update={'asset':asset})})
    r=base_assessment(c)
    assert r.asset_match_status=='NOT_MATCHED' and r.affected is False and r.risk_level=='LOW'
    assert r.version_match_status=='NOT_AFFECTED'
    assert r.version_match_result.affected is False

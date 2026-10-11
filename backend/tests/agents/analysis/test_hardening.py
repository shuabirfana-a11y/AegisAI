"""Review-focus cases: incomplete investigation and contradictory distribution identity."""
import pytest
from app.agents.contracts import fingerprint
from tests.agents.analysis.helpers import context,verified,module
from tests.agents.analysis.test_rules import kev


@pytest.mark.parametrize('changes',[{'runtime_status':'FAILED'},{'runtime_status':'BLOCKED'},
    {'status':'PARTIAL','partial_result':True}])
def test_incomplete_investigation_cannot_yield_definite_risk(changes):
    ctx=context([verified(),kev()]);original=type(ctx.inputs.investigation).model_validate({
        **ctx.inputs.investigation.model_dump(),**changes})
    inputs=ctx.inputs.model_copy(update={'investigation':original})
    ctx=ctx.model_copy(update={'inputs':inputs,'input_snapshot_hash':fingerprint(inputs.model_dump(mode='json'))})
    got=module('rules').assess_risk(ctx)
    assert got.affected is None and got.risk_level=='UNKNOWN' and got.priority=='REVIEW_REQUIRED'


def test_vendor_announcement_is_not_confirmed_patch():
    ctx=context([verified(),kev(),verified('VENDOR_CONFIRMED','vendor',{'url':'https://example.invalid/SYNTHETIC'})])
    got=module('rules').assess_risk(ctx)
    assert got.patch_availability.status=='UNKNOWN' and not got.patch_availability.claim_ids
    assert got.risk_level=='CRITICAL'


def test_mismatched_range_ecosystem_or_name_is_unknown():
    wrong=verified(value={'ecosystem':'PyPI','package':'unrelated-package','raw_expression':'<0.7.0'})
    got=module('rules').assess_risk(context([wrong,kev()]))
    assert got.affected is None and got.risk_level=='UNKNOWN'

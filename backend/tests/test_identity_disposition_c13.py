"""Existing conservative identity and branch contracts; synthetic, no benchmark truth."""
import pytest
from app.enrichment.context import EnrichmentContext
from tests.agents.analysis.test_scope_applicability_c12 import material
from app.agents.analysis.rules import match_asset,match_version

@pytest.mark.parametrize('name,ecosystem,repo,status',[
    ('sample-lib','PyPI',None,'EXACT_MATCH'),
    ('Sample.Lib','PyPI',None,'VERIFIED_ALIAS'),
    ('downstream-sample','Debian','sample/project','RELATED_PACKAGE'),
    ('sample-libs','PyPI',None,'IDENTITY_UNKNOWN'),
    (None,'PyPI',None,'IDENTITY_UNKNOWN'),
    ('sample-lib',None,None,'IDENTITY_UNKNOWN'),
    ('sample-lib','npm',None,'IDENTITY_CONFLICT'),
])
def test_explicit_identity_is_not_replaced_by_product_similarity(name,ecosystem,repo,status):
    ctx=EnrichmentContext(None,'SYNTHETIC',packages=[{'name':'sample-lib','ecosystem':'PyPI',
        'repository':'sample/project','package_id':'one','product_id':'one-product'}])
    r=ctx.resolve_package(name,ecosystem,repository=repo)
    assert r['status']==status
    if status in ('EXACT_MATCH','VERIFIED_ALIAS'):assert r['package']['package_id']=='one'
    else:assert r['package'] is None
    if status=='VERIFIED_ALIAS':assert r['basis_reference']=='https://packaging.python.org/en/latest/specifications/name-normalization/'

def test_independent_distribution_namespace_cannot_use_upstream_union():
    c=material();asset=c.inputs.asset.model_copy(update={'namespace':'separate-maintainer'})
    c=c.model_copy(update={'inputs':c.inputs.model_copy(update={'asset':asset})})
    assert match_version(c,match_asset(c)).status=='UNKNOWN'

def test_conflicting_source_unions_cannot_be_selected_for_a_known_package():
    from copy import deepcopy
    c=material();refs=list(c.inputs.verification.supporting_evidence);e=refs[0];details=deepcopy(e.details)
    details['normalized_version_scope']['record_union']=[[None,True,'99',False]]
    refs[0]=e.model_copy(update={'details':details})
    v=c.inputs.verification.model_copy(update={'supporting_evidence':tuple(refs)})
    c=c.model_copy(update={'inputs':c.inputs.model_copy(update={'verification':v})})
    assert match_version(c,match_asset(c)).status=='UNKNOWN'

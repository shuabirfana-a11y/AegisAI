"""Only already-verified, bound complete-record scopes may cover parallel entries."""
from copy import deepcopy
import pytest
from tests.agents.analysis.helpers import context,verified
from app.agents.analysis.rules import match_asset,match_version
from app.enrichment.version_scope import VersionScopeNormalizer

def material(version='4.1',include_fixes=False):
    doc={'vulnerabilities':[
        {'package':{'ecosystem':'pip','name':'vllm'},'vulnerable_version_range':'<3.8','patched_versions':'3.8'},
        {'package':{'ecosystem':'pip','name':'vllm'},'vulnerable_version_range':'>=4.0,<4.2','patched_versions':'4.2'}]}
    values=[{'range':'<3.8'},{'range':'>=4.0,<4.2'},{'ranges':[{'range':'<3.8'},{'range':'>=4.0,<4.2'}]}]
    rows=[verified(identifier='scope'+str(i),value={'ecosystem':'PyPI','package':'vllm',**v}) for i,v in enumerate(values)]
    if include_fixes:
        rows.extend(verified('FIXED_VERSION','fix'+str(i),{'ecosystem':'PyPI','package':'vllm','version':v}) for i,v in enumerate(('3.8','4.2')))
    c=context(rows,version=version);refs=[]
    for i,e in enumerate(c.inputs.verification.supporting_evidence):
        kind=rows[i].claim.claim_type
        field='patched_versions' if kind=='FIXED_VERSION' else 'vulnerable_version_range'
        proof=VersionScopeNormalizer().normalize(kind,e.observed_value,document=doc,
            locator={'json_pointer':f'/vulnerabilities/{1 if i in (1,4) else 0}/{field}'},
            evidence_id=e.evidence_id,raw_document_id=str(e.raw_document_id),raw_hash=e.hash,integrity_verified=True)
        assert proof is not None
        refs.append(e.model_copy(update={'details':{**e.details,'normalized_version_scope':proof.model_dump(mode='json')}}))
    v=c.inputs.verification.model_copy(update={'supporting_evidence':tuple(refs)})
    return c.model_copy(update={'inputs':c.inputs.model_copy(update={'verification':v})})

@pytest.mark.parametrize('version,status',[
    ('4.1','AFFECTED'),('3.7','AFFECTED'),('3.8','NOT_AFFECTED'),('3.9','NOT_AFFECTED'),('4.2','NOT_AFFECTED'),(None,'UNKNOWN')])
def test_union_and_source_entries_are_not_competing_global_claims(version,status):
    c=material(version);result=match_version(c,match_asset(c))
    assert result.status==status
    if status=='AFFECTED':assert result.normalization['scope_resolution']['method']=='VERIFIED_RECORD_UNION'
    assert len(result.claim_ids)==3

@pytest.mark.parametrize('damage',['no_proof','raw_hash','foreign_component','different_union','not_current','excluded','wrong_value'])
def test_unbound_or_incomparable_claims_still_abstain(damage):
    c=material();refs=list(c.inputs.verification.supporting_evidence);e=refs[0];d=deepcopy(e.details)
    updates={}
    if damage=='no_proof':d.pop('normalized_version_scope')
    elif damage=='raw_hash':updates['hash']='f'*64
    elif damage=='foreign_component':d['normalized_version_scope']['component']='other-lib'
    elif damage=='different_union':d['normalized_version_scope']['record_union']=[[None,True,'3.9',False]]
    elif damage=='not_current':updates['is_current']=False
    elif damage=='excluded':updates['exclusion_reasons']=('STALE_EVIDENCE',)
    else:updates['observed_value']={'ecosystem':'PyPI','package':'vllm','range':'<99'}
    refs[0]=e.model_copy(update={'details':d,**updates})
    v=c.inputs.verification.model_copy(update={'supporting_evidence':tuple(refs)})
    c=c.model_copy(update={'inputs':c.inputs.model_copy(update={'verification':v})})
    assert match_version(c,match_asset(c)).status=='UNKNOWN'

def test_explicit_branch_and_missing_range_still_abstain():
    c=context([verified(branch='downstream')]);assert match_version(c,match_asset(c)).status=='UNKNOWN'
    c=context([verified(value={'ecosystem':'PyPI','package':'vllm','range':'unparsed'})]);assert match_version(c,match_asset(c)).status=='UNKNOWN'

def test_same_package_two_assets_do_not_share_version_outcomes():
    a=material('4.1');b=material('4.2')
    assert a.inputs.asset.asset_id!=b.inputs.asset.asset_id
    assert match_version(a,match_asset(a)).status=='AFFECTED'
    assert match_version(b,match_asset(b)).status=='NOT_AFFECTED'

@pytest.mark.parametrize('qualifier',['condition','platform','architecture'])
def test_claim_constraints_cannot_be_erased_by_interval_equivalence(qualifier):
    c=material();rows=list(c.inputs.verification.claims)
    changed=rows[0].claim.model_copy(update={'value':{**rows[0].claim.value,qualifier:'unresolved applicability'}})
    rows[0]=rows[0].model_copy(update={'claim':changed})
    v=c.inputs.verification.model_copy(update={'claims':tuple(rows)})
    originals=list(c.inputs.source_claims);originals[0]=changed
    c=c.model_copy(update={'inputs':c.inputs.model_copy(update={'verification':v,'source_claims':tuple(originals)})})
    assert match_version(c,match_asset(c)).status=='UNKNOWN'

@pytest.mark.parametrize('version,expected',[('3.7',['3.8']),('4.1',['4.2'])])
def test_remediation_must_match_the_deployed_maintenance_entry(version,expected):
    from app.agents.analysis.recommendations import build_actions
    c=material(version,include_fixes=True);am=match_asset(c);vm=match_version(c,am)
    actions=build_actions(c,asset_match=am,version_match=vm,risk_level='HIGH',priority='P1')
    assert [x.fixed_version for x in actions if x.fixed_version]==expected

def test_remediation_never_recommends_a_downgrade():
    from app.agents.analysis.recommendations import build_actions
    c=context([verified(),verified('FIXED_VERSION','oldfix',{'ecosystem':'PyPI','package':'vllm','version':'0.4'})])
    am=match_asset(c);vm=match_version(c,am)
    assert vm.status=='AFFECTED'
    actions=build_actions(c,asset_match=am,version_match=vm,risk_level='HIGH',priority='P1')
    assert not any(x.fixed_version for x in actions)

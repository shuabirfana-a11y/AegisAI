"""Synthetic parallel maintenance branches; no Gold or special-case identifiers."""
from copy import deepcopy
import pytest
from app.enrichment.rules import compare_claims
from app.enrichment.version_scope import VersionScopeNormalizer,compare_scopes

def record():
    return {'vulnerabilities':[
        {'package':{'ecosystem':'pip','name':'example-engine'},'vulnerable_version_range':'>= 2.0.0, < 2.4.2','first_patched_version':'2.4.2'},
        {'package':{'ecosystem':'pip','name':'example-engine'},'vulnerable_version_range':'< 1.8.4','first_patched_version':'1.8.4'}]}

def assertion(kind,value,index=0,document=None):
    document=document or record()
    return {'scope':'PyPI:example-engine','type':kind,'value':{'ecosystem':'PyPI','package':'example-engine',**value},
        'version_source_contexts':[{'document':deepcopy(document),'locator':{'json_pointer':f'/vulnerabilities/{index}'},
                                  'evidence_id':'synthetic-proof-'+str(index),'raw_document_id':'synthetic-record','integrity_verified':True}]}

def test_parallel_first_patched_versions_are_not_mutually_exclusive():
    left=assertion('FIXED_VERSION',{'version':'2.4.2'},0)
    right=assertion('FIXED_VERSION',{'version':'1.8.4'},1)
    assert compare_claims(left,right) is None

def test_record_union_does_not_contradict_one_source_entry():
    complete=assertion('AFFECTS_VERSION',{'ranges':[{'events':[{'introduced':'2.0.0'},{'fixed':'2.4.2'}]},
                         {'events':[{'introduced':'0'},{'fixed':'1.8.4'}]}]})
    partial=assertion('AFFECTS_VERSION',{'range':'>= 2.0.0, < 2.4.2'},0)
    assert compare_claims(complete,partial) is None

def test_boundary_differences_are_still_conflicts():
    left=assertion('AFFECTS_VERSION',{'range':'< 1.8.4'},1)
    doc=record();doc['vulnerabilities'][1]['vulnerable_version_range']='<= 1.8.3'
    right=assertion('AFFECTS_VERSION',{'range':'<= 1.8.3'},1,doc)
    assert compare_claims(left,right)=='VERSION_CONFLICT'

def test_different_first_patched_on_same_range_remains_real_conflict():
    left=assertion('FIXED_VERSION',{'version':'2.4.2'},0)
    doc=record();doc['vulnerabilities'][0]['first_patched_version']='2.4.3'
    right=assertion('FIXED_VERSION',{'version':'2.4.3'},0,doc)
    assert compare_claims(left,right)=='FIXED_VERSION_CONFLICT'

def normal(assertion):
    source=assertion['version_source_contexts'][0]
    return VersionScopeNormalizer().normalize(assertion['type'],assertion['value'],**source)

def test_same_branch_same_scope():
    a=assertion('AFFECTS_VERSION',{'range':'>= 2.0.0, < 2.4.2'})
    assert compare_scopes(a,deepcopy(a)).result=='SAME_SCOPE'
    assert compare_claims(a,deepcopy(a)) is None

def test_same_branch_different_ranges_keeps_boundary_difference():
    a=assertion('AFFECTS_VERSION',{'range':'>= 2.0.0, < 2.4.2'})
    doc=record();doc['vulnerabilities'][0]['vulnerable_version_range']='>= 2.0.0, < 2.4.3'
    b=assertion('AFFECTS_VERSION',{'range':'>= 2.0.0, < 2.4.3'},0,doc)
    assert compare_scopes(a,b).result=='BOUNDARY_DIFFERENCE'
    assert compare_claims(a,b)=='VERSION_CONFLICT'

@pytest.mark.parametrize(('expressions','fixes'),[
    (['>= 2.0.0, < 2.4.2','< 1.8.4'],['2.4.2','1.8.4']),
    (['>= 2.1.0, < 2.1.4','>= 2.0.0, < 2.0.8'],['2.1.4','2.0.8'])])
def test_major_and_minor_maintenance_branches_are_source_associated(expressions,fixes):
    doc=record()
    for entry,expression,fixed in zip(doc['vulnerabilities'],expressions,fixes):
        entry.update(vulnerable_version_range=expression,first_patched_version=fixed)
    a=assertion('FIXED_VERSION',{'version':fixes[0]},0,doc)
    b=assertion('FIXED_VERSION',{'version':fixes[1]},1,doc)
    assert compare_scopes(a,b).result=='BRANCH_DIFFERENCE'
    assert compare_claims(a,b) is None
    assert normal(a).branch['source_entries'] and normal(a).entries[0]['release_parts'][0]['major'] is not None

def test_affected_and_corresponding_fixed_boundary_are_compatible():
    a=assertion('AFFECTS_VERSION',{'range':'>= 2.0.0, < 2.4.2'})
    b=assertion('FIXED_VERSION',{'version':'2.4.2'})
    assert compare_claims(a,b) is None

def test_last_affected_does_not_invent_a_first_patched_release():
    doc={'affected':[{'package':{'ecosystem':'PyPI','name':'example-engine'},
        'ranges':[{'type':'ECOSYSTEM','events':[{'introduced':'2.0.0'},{'last_affected':'2.4.2'}]}]}]}
    a=assertion('FIXED_VERSION',{'version':'2.4.3'},document=doc)
    a['version_source_contexts'][0]['locator']={'json_pointer':'/affected/0/ranges/0'}
    assert normal(a) is None

def test_exactly_equivalent_expression_uses_existing_version_order():
    a=assertion('AFFECTS_VERSION',{'range':'>= 2.0.0, < 2.4.2'})
    b=assertion('AFFECTS_VERSION',{'range':'>= 2.0, < 2.4.2.0'})
    assert compare_claims(a,b) is None
    assert compare_scopes(a,b).result=='SAME_SCOPE'

@pytest.mark.parametrize('key',['product','package'])
def test_product_and_component_identity_differences_not_compared(key):
    a=assertion('AFFECTS_VERSION',{'range':'< 1.8.4'},1)
    b=deepcopy(a);a['value'][key]='first';b['value'][key]='different'
    assert compare_scopes(a,b).result=='NOT_COMPARABLE'
    assert compare_claims(a,b) is None

@pytest.mark.parametrize('change',['missing_source','bad_locator','bad_identity','unverified','condition'])
def test_incomplete_context_never_waives_a_conflict(change):
    a=assertion('FIXED_VERSION',{'version':'2.4.2'},0)
    b=assertion('FIXED_VERSION',{'version':'1.8.4'},1)
    if change=='missing_source':a.pop('version_source_contexts')
    elif change=='bad_locator':a['version_source_contexts'][0]['locator']={'json_pointer':'/elsewhere'}
    elif change=='bad_identity':a['version_source_contexts'][0]['document']['vulnerabilities'][0]['package']['name']='other-package'
    elif change=='unverified':a['version_source_contexts'][0]['integrity_verified']=False
    else:a['value']['condition']='unknown deploy option'
    assert compare_claims(a,b)=='FIXED_VERSION_CONFLICT'

def test_raw_input_is_immutable_and_evidence_binding_is_retained():
    a=assertion('AFFECTS_VERSION',{'range':'>= 2.0.0, < 2.4.2'})
    before=deepcopy(a);scope=normal(a)
    assert a==before and scope.raw_expression==a['value']['range']
    assert scope.evidence_id=='synthetic-proof-0' and scope.raw_document_id=='synthetic-record'
    with pytest.raises(Exception):scope.fixed_version='invented'

def test_missing_branch_is_not_guessed_from_different_version_numbers():
    a={'scope':'PyPI:example-engine','type':'FIXED_VERSION','value':{'ecosystem':'PyPI','package':'example-engine','version':'1.8.4'}}
    b={**a,'value':{**a['value'],'version':'2.4.2'}}
    assert compare_scopes(a,b).result=='INSUFFICIENT_CONTEXT'
    assert compare_claims(a,b)=='FIXED_VERSION_CONFLICT'

def test_multiple_assets_use_the_same_ranges_without_sharing_results():
    from app.assets.versions import compare_version
    union={'ecosystem':'PyPI','ranges':[{'events':[{'introduced':'2.0.0'},{'fixed':'2.4.2'}]},
                                    {'events':[{'introduced':'0'},{'fixed':'1.8.4'}]}]}
    results=[compare_version(v,union)['affected'] for v in ['1.8.3','1.8.4','1.9.0','2.0.0','2.4.2']]
    assert results==[True,False,False,True,False]

def test_historical_generated_counter_retained_but_not_a_cross_branch_contradiction():
    from tests.agents.verification.helpers import claim,evidence,context
    from app.agents.verification.rules import evaluate_snapshot
    a=assertion('FIXED_VERSION',{'version':'2.4.2'},0);b=assertion('FIXED_VERSION',{'version':'1.8.4'},1)
    c=claim('C1',claim_type='FIXED_VERSION',value=a['value'],scope_key=a['scope'])
    support=evidence('synthetic-proof-0','C1',observed_value=a['value'],scope_key=a['scope'])
    counter=evidence('synthetic-proof-1','C1',observed_value=b['value'],scope_key=a['scope'],stance='contradict')
    def bound(e,ass):
        source=ass['version_source_contexts'][0]
        scope=VersionScopeNormalizer().normalize(ass['type'],ass['value'],**{**source,'evidence_id':e.evidence_id,
            'raw_document_id':str(e.raw_document_id),'raw_hash':e.hash})
        return e.model_copy(update={'details':{**e.details,'normalized_version_scope':scope.model_dump(mode='json')}})
    support=bound(support,a);counter=bound(counter,b)
    counter=counter.model_copy(update={'details':{**counter.details,'conflict_id':'historical-derived-record'}})
    ctx=context([c],[support,counter]);before=ctx.model_dump_json()
    got=evaluate_snapshot(ctx)
    assert got.claims[0].status=='CONFIRMED' and not got.conflicts
    assert got.claims[0].score_components['excluded'][0]['evidence_id']==counter.evidence_id
    assert len(ctx.snapshot.evidence)==2 and ctx.model_dump_json()==before

def test_direct_counter_without_pipeline_derivation_is_not_suppressed():
    from tests.agents.verification.helpers import claim,evidence,context
    from app.agents.verification.rules import evaluate_snapshot
    value={'ecosystem':'PyPI','package':'vllm','version':'1.0.0'}
    c=claim('C1',claim_type='FIXED_VERSION',value=value)
    got=evaluate_snapshot(context([c],[evidence(observed_value=value),evidence('E2','C1',stance='contradict',observed_value={**value,'version':'2.0.0'})]))
    assert got.claims[0].status=='CONFLICT'

def test_multi_episode_event_log_is_not_flattened_into_one_fix_scope():
    doc={'affected':[{'package':{'ecosystem':'PyPI','name':'example-engine'},'ranges':[{'type':'ECOSYSTEM',
        'events':[{'introduced':'1.0.0'},{'fixed':'1.2.0'},{'introduced':'2.0.0'},{'fixed':'2.4.2'}]}]}]}
    a=assertion('FIXED_VERSION',{'version':'1.2.0'},document=doc)
    a['version_source_contexts'][0]['locator']={'json_pointer':'/affected/0/ranges/0'}
    assert normal(a) is None

def test_snapshot_rebuilds_reserved_scope_metadata_instead_of_trusting_stored_details():
    import json
    from hashlib import sha256
    from types import SimpleNamespace
    from uuid import uuid4
    from app.db import models as m
    from app.agents.verification.snapshot import _evidence
    from tests.agents.verification.helpers import claim,evidence
    c=claim('C1',claim_type='FIXED_VERSION',value={'ecosystem':'PyPI','package':'example-engine','version':'2.4.2'})
    sample=evidence('E1','C1',observed_value=c.value)
    payload=json.dumps({'statement':'does not establish a source-entry range'}).encode()
    raw=SimpleNamespace(id=sample.raw_document_id,source_id=sample.source_id,raw_payload=payload,content_hash=sha256(payload).hexdigest())
    obs=SimpleNamespace(id=sample.observation_id,source_id=sample.source_id,raw_document_id=raw.id,
        parse_status='parsed',normalized_payload={},lineage_key='original',external_id='SYNTHETIC')
    quoted=json.dumps('does not establish a source-entry range')
    stored=SimpleNamespace(id=uuid4(),source_id=sample.source_id,raw_document_id=raw.id,observation_id=obs.id,
        claim_id='C1',scope_key=c.scope_key,excerpt=quoted,excerpt_hash=sha256(quoted.encode()).hexdigest(),
        locator={'json_pointer':'/statement'},source_url='https://example.invalid/advisory',retrieved_at=sample.retrieved_at,
        published_at=sample.published_at,publisher='SYNTHETIC',evidence_type='official_vendor_advisory',
        observed_value=c.value,stance='support',details={'explicit':True,'normalized_version_scope':{'forged':True}})
    class ReadOnly:
        def get(self,model,key):return raw if model is m.RawDocument else obs if model is m.SourceObservation else None
        def scalar(self,query):return obs.id
    got=_evidence(ReadOnly(),stored,c,{'source_key':'SYNTHETIC_vendor','authority_level':'official',
        'authority_scope':'vulnerability affected versions','is_current':True},sample.retrieved_at)
    assert got.integrity_status=='VALID'
    assert 'normalized_version_scope' not in got.details
    assert stored.details['normalized_version_scope']=={'forged':True}

def test_additional_parallel_proof_does_not_hide_same_scope_affected_fixed_conflict():
    doc1={'vulnerabilities':[{'package':{'ecosystem':'pip','name':'example-engine'},
          'vulnerable_version_range':'< 2.0.0','first_patched_version':'1.0.0'}]}
    doc2={'vulnerabilities':[{'package':{'ecosystem':'pip','name':'example-engine'},
          'vulnerable_version_range':'< 1.0.0','first_patched_version':'1.0.0'},
          {'package':{'ecosystem':'pip','name':'example-engine'},
           'vulnerable_version_range':'>= 1.0.0, < 2.0.0','first_patched_version':'2.0.0'}]}
    affected=assertion('AFFECTS_VERSION',{'range':'< 2.0.0'},document=doc1)
    fixed=assertion('FIXED_VERSION',{'version':'1.0.0'},document=doc1)
    fixed['version_source_contexts'].extend(assertion('FIXED_VERSION',{'version':'1.0.0'},document=doc2)['version_source_contexts'])
    assert compare_claims(affected,fixed)=='VERSION_CONFLICT'

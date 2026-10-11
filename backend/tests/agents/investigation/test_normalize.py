import copy
from uuid import uuid4
import pytest
from tests.agents.investigation.helpers import execution, detail, source, CVE

def normalize(item,outcome,deps=()):
    from app.agents.investigation.normalize import normalize_investigation
    return normalize_investigation(item,outcome,deps)

def test_cve_artifact_preserves_provenance():
    data=detail(); ref=source(); item,ctx,out=execution(data,[ref])
    got=normalize(item,out)
    assert got.artifact_id==out.artifact.artifact_id and got.run_id==ctx.run_id
    assert got.agent_id=='investigation_agent' and got.task_id==item.task_id
    assert got.status=='COMPLETE' and got.runtime_status=='SUCCESS'
    assert got.vulnerability_id==data['id'] and got.canonical_id==CVE
    assert got.cvss==data['cvss_assessments'] and got.cwe==data['cwe']
    assert got.description==data['description'] and got.evidence==[ref]
    assert got.confidence is None and got.information_status=='CANDIDATE'

def test_poc_is_candidate_even_when_existing_status_confirmed():
    item,_,out=execution(); got=normalize(item,out)
    assert got.poc_candidates[0]['status']=='CANDIDATE'
    assert got.poc_candidates[0]['observed_status']=='confirmed'
    assert got.poc_candidates[0]['usability_status']=='not_evaluated'

@pytest.mark.parametrize('changes',[{'authority_level':'community'},{'is_current':False},
    {'authority_level':None},{'raw_document_id':None},{'url':None},{'locator':None}])
def test_no_authoritative_current_traceable_source_is_insufficient(changes):
    item,_,out=execution(refs=[source(**changes)]); got=normalize(item,out)
    assert got.status=='INSUFFICIENT_EVIDENCE' and got.confidence is None
    assert got.evidence==out.artifact.evidence

def test_existing_current_conflict_preserves_both_claims():
    data=detail(); data['intelligence']['conflicts']=[{'status':'open','scope_key':'PyPI:vllm',
        'claim_a_id':str(uuid4()),'claim_b_id':str(uuid4()),'conflict_type':'VERSION_CONFLICT'}]
    item,_,out=execution(data); got=normalize(item,out)
    assert got.status=='CONFLICT' and got.conflicts==data['intelligence']['conflicts']

def test_partial_keeps_failed_tool_and_available_data():
    item,_,out=execution(names=['get_vulnerability','get_evidence'],statuses=['success','failed'])
    got=normalize(item,out)
    assert got.status=='PARTIAL' and got.partial_result and got.runtime_status=='FAILED'
    assert got.canonical_id==CVE and got.failed_tools[0]['tool']=='get_evidence'
    assert got.failed_tools[0]['errors'][0]['code']=='SYNTHETIC_FAILURE'

def test_no_data_is_insufficient_not_safe():
    item,_,out=execution(data={},refs=[],statuses=['no_result']); got=normalize(item,out)
    assert got.status=='INSUFFICIENT_EVIDENCE' and got.vulnerability_id is None
    assert got.uncertainties

def test_cvss_multiple_sources_are_retained():
    data=detail(); data['cvss_assessments'].append({'version':'4.0','base_score':7.5,'provider':'OTHER'})
    item,_,out=execution(data); assert normalize(item,out).cvss==data['cvss_assessments']

def test_projection_does_not_mutate_inputs():
    item,_,out=execution(); saved=out.model_dump(mode='json'); normalize(item,out)
    assert out.model_dump(mode='json')==saved

def test_mismatched_target_is_rejected():
    data=detail(); data['canonical_id']='CVE-2099-1111111'; item,_,out=execution(data)
    with pytest.raises(ValueError,match='target'):normalize(item,out)

def test_dependency_identity_must_match_exact_run():
    item,_,out=execution(); other=out.artifact.model_copy(update={'run_id':uuid4()})
    item=item.model_copy(update={'dependencies':('prior',)})
    with pytest.raises(ValueError):normalize(item,out,(other,))

def test_projection_size_reference_keeps_full_receipt():
    data=detail(); data['description']='x'*260000
    item,_,out=execution(data); got=normalize(item,out)
    assert len(got.model_dump_json().encode())<=512*1024
    assert out.receipts[0].envelope.data['description']==data['description']

def test_semantic_hit_alone_does_not_confirm_vulnerability():
    item,_,out=execution(data={'items':[{'content':'CVE mention','score':0.99}]},
                         names=['semantic_search'],refs=[source(authority_level='community')])
    got=normalize(item,out)
    assert got.status=='INSUFFICIENT_EVIDENCE' and got.information_status!='CONFIRMED'

def test_official_source_is_not_automatic_confirmation():
    item,_,out=execution(refs=[source(verified=False)])
    assert normalize(item,out).information_status=='CANDIDATE'


def test_size_fallback_is_explicit_and_points_to_complete_receipts():
    data=detail(); data['affected_versions'][0]['fixed']='SYNTHETIC-'+'x'*270000
    item,_,out=execution(data)
    got=normalize(item,out)
    assert got.status=='PARTIAL' and got.evidence_storage=='tool_receipts'
    assert got.receipt_references and got.uncertainties
    assert len(got.model_dump_json().encode())<=512*1024
    assert out.receipts[0].envelope.data==data


def confirmed_claim(superseded=False):
    claim={'id':str(uuid4()),'revision':1,'claim_type':'AFFECTS_VERSION','scope_key':'PyPI:vllm',
        'value_json':{'raw_expression':'>=0.5,<0.7'},'trusted':True,
        'verification_status':'CONFIRMED','details':{'superseded':superseded}}
    ref=source(claim_id=claim['id'],claim_revision=1,stance='support',verified=True)
    return claim,ref


def test_existing_current_confirmed_claim_is_preserved():
    claim,ref=confirmed_claim();data=detail();data['intelligence']['claims']=[claim]
    item,_,out=execution(data,[ref])
    assert normalize(item,out).information_status=='CONFIRMED'


def test_superseded_claim_is_not_current_confirmation():
    claim,ref=confirmed_claim(True);data=detail();data['intelligence']['claims']=[claim]
    item,_,out=execution(data,[ref])
    assert normalize(item,out).information_status=='CANDIDATE'


def test_current_same_scope_assertions_conflict_without_verification():
    a,ar=confirmed_claim();b,br=confirmed_claim()
    for c in (a,b):c.update(trusted=False,verification_status='UNVERIFIED')
    for r in (ar,br):r['verified']=False
    b['value_json']={'raw_expression':'>=0.5,<0.8'}
    data=detail();data['intelligence']['claims']=[a,b]
    item,_,out=execution(data,[ar,br]);got=normalize(item,out)
    assert got.status=='CONFLICT' and got.conflicts
    assert {got.conflicts[0]['claim_a']['id'],got.conflicts[0]['claim_b']['id']}=={a['id'],b['id']}


def test_historical_assertion_does_not_create_current_conflict():
    a,ar=confirmed_claim();b,br=confirmed_claim();br['is_current']=False
    b['value_json']={'raw_expression':'>=0.5,<0.8'}
    data=detail();data['intelligence']['claims']=[a,b]
    item,_,out=execution(data,[ar,br]);assert normalize(item,out).status=='COMPLETE'

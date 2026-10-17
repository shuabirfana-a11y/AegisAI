"""SYNTHETIC behavior cases; no Gold, model or approved data mutation."""
from copy import deepcopy
from datetime import timedelta
import json,sys
from pathlib import Path
from uuid import uuid4
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.append(str(ROOT))
from tests.agents.verification.helpers import claim,evidence,context
from app.agents.verification.rules import evaluate_snapshot
from app.orchestration.composer import project_fact_value,safe_value
from evaluation.bench.http_investigation import project_answer
from evaluation.bench.schema import Question

VECTOR3='CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
VECTOR4='CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N'
def fact(kind='CWE',value=None,identifier='C1'):
    return claim(identifier,claim_type=kind,value=value or {'cwe':'CWE-79'},package_identifier_id=None,scope_key='SYNTHETIC-fact')
def proof(c,id='E1',**changes):
    values={'claim_id':c.claim_id,'observed_value':c.value,'scope_key':c.scope_key};values.update(changes)
    return evidence(id,**values)
def raw():return json.loads((ROOT/'AegisAI_FRONTEND_HANDOFF_PACKAGE/mock/answer-demo.json').read_text(encoding='utf-8'))['scenarios']['PASS']
def q():return Question(id='SYNTHETIC-projection',category='facts',question='Read the supplied authoritative facts',origin='TEST_FIXTURE',source_ids=['SYNTHETIC'],input_context={})
def answer(kind,value):
    r=raw();r['verified_claims'][0].update(claim_type=kind,value=value)
    # The carrier already contains a legacy demo metric. Keep this fixture's
    # metric population explicit instead of inheriting an unrelated partial one.
    if kind=='CVSS_SCORE':
        for f in r['verified_claims']:
            if f['claim_type']=='CVSS_SCORE':f['value']=deepcopy(value)
    return r
def add_fact(r,kind,value,suffix):
    f=deepcopy(r['verified_claims'][0]);old=f['claim_id'];old_e=f['evidence_ids'][0]
    cid='SYNTHETIC-claim-'+suffix;eid='SYNTHETIC-evidence-'+suffix
    f.update(claim_id=cid,claim_type=kind,value=value,evidence_ids=[eid]);r['verified_claims'].append(f)
    citation=deepcopy(next(x for x in r['citations'] if x['evidence_id']==old_e));citation.update(claim_id=cid,evidence_id=eid);r['citations'].append(citation)
    observation=deepcopy(next(x for x in r['evidence_observations'] if x['evidence_id']==old_e));observation.update(claim_id=cid,evidence_id=eid);r['evidence_observations'].append(observation)
    r['evidence_references'].append(eid)
    return r

def test_single_evidence_single_atomic_claim():
    c=fact();a=evaluate_snapshot(context([c],[proof(c)]))
    assert a.claims[0].status=='CONFIRMED' and a.claims[0].supporting_evidence_ids==('E1',)

def test_multiple_independent_evidence_can_support_one_atomic_claim():
    c=fact();e1=proof(c,evidence_type='structured_source',lineage_key='origin-a',authority_level='authoritative')
    e2=proof(c,'E2',evidence_type='structured_source',lineage_key='origin-b',authority_level='authoritative')
    a=evaluate_snapshot(context([c],[e1,e2]))
    assert a.claims[0].status=='CONFIRMED' and set(a.claims[0].supporting_evidence_ids)=={'E1','E2'}

def test_one_immutable_source_can_support_two_separately_bound_atomic_claims():
    c1=fact();c2=fact('SOURCE_FACT',{'field':'summary','text':'SYNTHETIC literal fact'},'C2')
    e1=proof(c1);e2=proof(c2,'E2',raw_document_id=e1.raw_document_id,observation_id=e1.observation_id,source_id=e1.source_id)
    a=evaluate_snapshot(context([c1,c2],[e1,e2]))
    assert [(x.claim.claim_id,x.status,x.supporting_evidence_ids) for x in a.claims]==[('C1','CONFIRMED',('E1',)),('C2','CONFIRMED',('E2',))]

def test_partial_fact_support_does_not_complete_a_larger_claim():
    c=fact('SOURCE_FACT',{'field':'summary','text':'SYNTHETIC complete factual statement'})
    a=evaluate_snapshot(context([c],[proof(c,observed_value={'field':'summary','text':'SYNTHETIC'})]))
    assert a.claims[0].status=='INSUFFICIENT_EVIDENCE' and not a.claims[0].supporting_evidence_ids

def test_absent_evidence_stays_insufficient():
    assert evaluate_snapshot(context([fact()],[])).verification_status=='INSUFFICIENT_EVIDENCE'

def test_real_cvss_source_conflict_is_retained():
    c=fact('CVSS_SCORE',{'version':'3.1','score':9.8,'vector':VECTOR3,'severity':'critical'})
    e1=proof(c);e2=proof(c,'E2',observed_value={**c.value,'score':7.5},lineage_key='origin-b')
    a=evaluate_snapshot(context([c],[e1,e2]))
    assert a.verification_status=='CONFLICT' and a.conflicts and a.claims[0].status=='CONFLICT'

def test_version_evidence_uses_existing_rules():
    c=claim();a=evaluate_snapshot(context([c],[evidence()]))
    assert a.claims[0].status=='CONFIRMED' and a.claims[0].claim.value['raw_expression']=='<=0.6'

def test_confirmed_cwe_reaches_benchmark_with_evidence_reference():
    r=answer('CWE',{'cwe':'CWE-79'});a=project_answer(q(),r)
    assert a.answer['cwes']==['CWE-79'] and a.answer['native_citations'][0]['evidence_id']==r['citations'][0]['evidence_id']

def test_cvss_vector_survives_typed_answer_projection_without_opening_generic_allowlist():
    c=fact('CVSS_SCORE',{'version':'3.1','score':9.8,'vector':VECTOR3,'severity':'critical','private_prompt':'SYNTHETIC_PRIVATE'})
    value=project_fact_value(c,verification_state='CONFIRMED',confidence=.95)
    assert value=={'version':'3.1','score':9.8,'vector':VECTOR3,'severity':'critical'}
    assert safe_value({'vector':VECTOR3,'private_prompt':'SYNTHETIC_PRIVATE'})=={}

@pytest.mark.parametrize(('version','vector','field'),[('3.1',VECTOR3,'cvss_v3'),('4.0',VECTOR4,'cvss_v4')])
def test_cvss_metric_projects_only_its_supplied_version(version,vector,field):
    r=answer('CVSS_SCORE',{'version':version,'score':9.8,'vector':vector,'severity':'critical'})
    a=project_answer(q(),r)
    assert a.answer[field]=={'score':9.8,'vector_string':vector}
    assert ('cvss_v4' if field=='cvss_v3' else 'cvss_v3') not in a.answer

def test_summary_is_literal_confirmed_source_fact_not_generated_answer_summary():
    r=answer('SOURCE_FACT',{'field':'summary','text':'SYNTHETIC source words'})
    r['summary']='SYNTHETIC presentation sentence'
    assert project_answer(q(),r).answer['summary']=='SYNTHETIC source words'

def test_fixed_version_keeps_existing_projection():
    a=project_answer(q(),answer('FIXED_VERSION',{'version':'2.3.4','package':'synthetic-component','ecosystem':'PyPI'}))
    assert a.answer['fixed_versions']==['2.3.4'] and a.answer['patch_status']=='CONFIRMED_FIX'

def test_affected_range_is_not_rewritten_by_fact_serializer():
    c=claim();assert project_fact_value(c,verification_state='CONFIRMED',confidence=.95)=={'ecosystem':'PyPI','package':'vllm','raw_expression':'<=0.6'}

def test_missing_source_metadata_cannot_gain_confirmation():
    c=fact();a=evaluate_snapshot(context([c],[proof(c,authority_level=None,authority_scope=None)]))
    assert a.claims[0].status!='CONFIRMED' and not a.supporting_evidence

def test_evidence_id_handoff_is_exact():
    c=fact();a=evaluate_snapshot(context([c],[proof(c,'SYNTHETIC-EID')]))
    assert a.claims[0].supporting_evidence_ids==('SYNTHETIC-EID',) and a.supporting_evidence[0].evidence_id=='SYNTHETIC-EID'

def test_claim_id_handoff_is_exact():
    c=fact(identifier='SYNTHETIC-CID');a=evaluate_snapshot(context([c],[proof(c)]))
    assert a.claims[0].claim.claim_id=='SYNTHETIC-CID' and a.supporting_evidence[0].claim_id=='SYNTHETIC-CID'

def test_verification_unknown_status_is_not_overwritten_by_factual_output():
    r=answer('CWE',{'cwe':'CWE-79'});r.update(answer_status='INCOMPLETE',integration_status='REPLAN_REQUIRED')
    r['risk_assessment'].update(risk_level='UNKNOWN',priority='REVIEW_REQUIRED',affected=None,version_match_status='UNKNOWN',conclusion_scope='OBSERVATION')
    for action in r['recommended_actions']:action['conclusion_scope']='OBSERVATION'
    a=project_answer(q(),r)
    assert a.answer['risk_level']=='UNKNOWN' and a.answer['native_gate_status']=='REPLAN_REQUIRED' and a.answer['cwes']==['CWE-79']

def test_verification_to_answer_projection_keeps_cwe_and_summary():
    for c in [fact(),fact('SOURCE_FACT',{'field':'summary','text':'SYNTHETIC source words'})]:
        a=evaluate_snapshot(context([c],[proof(c)]));checked=a.claims[0]
        assert checked.status=='CONFIRMED' and project_fact_value(checked.claim,verification_state=checked.status,confidence=checked.confidence)==c.value

def test_verification_to_benchmark_projection_reads_the_same_confirmed_value():
    c=fact();a=evaluate_snapshot(context([c],[proof(c)]));checked=a.claims[0]
    r=answer(checked.claim.claim_type,project_fact_value(checked.claim,verification_state=checked.status,confidence=checked.confidence))
    assert project_answer(q(),r).answer['cwes']==['CWE-79']

def test_two_asset_answer_projections_do_not_share_state():
    a=answer('SOURCE_FACT',{'field':'summary','text':'SYNTHETIC asset A'});b=answer('SOURCE_FACT',{'field':'summary','text':'SYNTHETIC asset B'})
    a['affected_assets'][0]['asset_id']=str(uuid4());b['affected_assets'][0]['asset_id']=str(uuid4())
    assert project_answer(q(),a).answer['summary']=='SYNTHETIC asset A'
    assert project_answer(q(),b).answer['summary']=='SYNTHETIC asset B'
    assert project_answer(q(),a).answer['summary']=='SYNTHETIC asset A'

@pytest.mark.parametrize('change',['product','component'])
def test_other_product_or_component_cannot_supply_claim_support(change):
    c=claim();updates={'observed_value':{**c.value,'package':'SYNTHETIC-other'}} if change=='product' else {'scope_key':'SYNTHETIC-other-component'}
    a=evaluate_snapshot(context([c],[evidence().model_copy(update=updates)]))
    assert a.claims[0].status!='CONFIRMED' and not a.supporting_evidence

def test_historical_evidence_is_not_made_current_by_projection_changes():
    c=fact();e=proof(c);e=e.model_copy(update={'retrieved_at':e.retrieved_at-timedelta(days=31)})
    a=evaluate_snapshot(context([c],[e]));assert a.claims[0].status!='CONFIRMED' and not a.supporting_evidence

def test_unknown_evidence_stays_unverified():
    c=fact();a=evaluate_snapshot(context([c],[proof(c,directness='unknown',details={'explicit':False})]))
    assert a.claims[0].status!='CONFIRMED'

def test_human_traceability_keeps_original_citations_and_claims():
    r=answer('CWE',{'cwe':'CWE-79'});a=project_answer(q(),r)
    assert a.answer['native_citations']==r['citations'] and a.claims[0].claim_id==r['verified_claims'][0]['claim_id']

@pytest.mark.parametrize('change',[{'hash':None},{'raw_document_id':None},{'integrity_status':'INVALID'}])
def test_invalid_provenance_never_gains_confirmation(change):
    c=fact();a=evaluate_snapshot(context([c],[proof(c,**change)]));assert a.claims[0].status!='CONFIRMED' and not a.supporting_evidence

def test_disputed_fact_does_not_become_a_benchmark_fact():
    r=raw();base=r['verified_claims'][0]
    r['disputed_claims'].append({'claim_id':'SYNTHETIC-PENDING','claim_type':'CWE','verification_status':'INSUFFICIENT_EVIDENCE',
        'value':{'cwe':'CWE-79'},'scope_key':'SYNTHETIC','supporting_evidence_ids':[],'conflicting_evidence_ids':[],
        'verification_artifact':base['source_artifact']})
    assert 'cwes' not in project_answer(q(),r).answer

def test_missing_metric_is_not_filled_from_question_or_zero_placeholder():
    a=project_answer(q().model_copy(update={'question':'SYNTHETIC asks about CVSS 9.8'}),answer('CWE',{'cwe':'CWE-79'}))
    assert 'cvss_v3' not in a.answer and 'cvss_v4' not in a.answer

def test_ambiguous_confirmed_summaries_are_not_arbitrarily_selected():
    r=answer('SOURCE_FACT',{'field':'summary','text':'SYNTHETIC A'});add_fact(r,'SOURCE_FACT',{'field':'summary','text':'SYNTHETIC B'},'b')
    assert 'summary' not in project_answer(q(),r).answer

def test_ambiguous_same_version_cvss_values_are_not_arbitrarily_selected():
    r=answer('CVSS_SCORE',{'version':'3.1','score':9.8,'vector':VECTOR3})
    add_fact(r,'CVSS_SCORE',{'version':'3.1','score':7.5,'vector':VECTOR3},'b')
    assert 'cvss_v3' not in project_answer(q(),r).answer

def test_incomplete_confirmed_metric_cannot_be_silently_discarded_to_choose_another():
    r=answer('CVSS_SCORE',{'version':'3.1','score':9.8,'vector':VECTOR3})
    add_fact(r,'CVSS_SCORE',{'version':'3.1','score':7.5},'partial')
    assert 'cvss_v3' not in project_answer(q(),r).answer

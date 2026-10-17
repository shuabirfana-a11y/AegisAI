"""C5 regressions: real DTO and HTTP boundaries, never benchmark answers."""
import json,sys
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.investigation_api.schemas import InvestigationCreateRequest
from app.investigation_api.projection import public_copy
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R))
from evaluation.bench.schema import Question
from evaluation.bench.http_investigation import build_request,project_answer

URL='https://github.com/example/project/commit/'+'a'*40
VECTOR='CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:L/A:N'

def question(url=URL):
 return Question(id='SYNTHETIC_C5',question='此链接能否确认已验证补丁？',category='poc_patch',
  origin='TEST_FIXTURE',source_ids=['SYNTHETIC'],input_context={'target':'CVE-2099-12345','candidate_reference':url,'candidate_kind':'patch'})

def test_reference_reaches_formal_request_and_internal_snapshot():
 body=build_request(question())
 assert body['asset_scope']['candidate_reference']==URL
 internal=InvestigationCreateRequest.model_validate(body).to_internal()
 assert internal.planner_input.candidate_reference==URL
 assert 'candidate_reference' not in build_request(question().model_copy(update={'input_context':{'target':'CVE-2099-12345'}}))['asset_scope']

@pytest.mark.parametrize('bad',['http://127.0.0.1/commit/x','https://localhost/x','https://github.com@127.0.0.1/x',
 'https://github.com/example/project/commit/'+('a'*40)+'?redirect=http://127.0.0.1',
 'https://github.com/example/project/commit/'+('a'*40)+'#x','https://api.github.com/repos/example/project/commits/'+('a'*40),
 'https://github.com/example/project/commit/short'])
def test_bad_candidate_is_rejected_before_any_investigation(bad):
 with pytest.raises(ValueError):build_request(question(bad))

def test_public_cvss_projection_preserves_only_typed_supplied_metric():
 native={'claim_type':'CVSS_SCORE','value':{'version':'3.1','score':3.1,'vector':VECTOR,'severity':'low','api_key':'SYNTHETIC-secret'}}
 result=public_copy(native)
 assert result['value']=={'version':'3.1','score':3.1,'vector':VECTOR,'severity':'low'}
 assert 'vector' not in public_copy({'value':native['value']})['value']

@pytest.mark.parametrize('value',[{'score':3.1,'version':'3.1'}, {'score':None,'version':None,'vector':None},
 {'score':3.1,'version':'9.0','vector':'CVSS:9.0/AV:N'}, {'score':3.1,'version':'3.1','vector':'invalid'}])
def test_cvss_partial_invalid_fields_do_not_gain_a_verdict(value):
 result=public_copy({'claim_type':'CVSS_SCORE','status':'PENDING','value':value})
 assert result['status']=='PENDING'
 if 'vector' not in value:assert 'vector' not in result['value']
 assert result['value'].get('score')==value['score']

def test_actual_http_answer_retains_verified_vector_and_evidence_identity(engine,monkeypatch):
 from tests.orchestration.fixtures import scenario
 from tests.investigation_api.test_live_chain import terminal,HEADERS
 from app.main import create_app
 from app.db.session import transaction
 from app.db import models as m
 from sqlalchemy import select
 seed,request,gateway,calls,_=scenario(engine)
 monkeypatch.setenv('AEGIS_ASSET_TOKEN','SYNTHETIC-test-token');monkeypatch.setenv('AEGIS_ASSET_OWNER',seed.actor)
 with transaction(engine) as db:
  c=db.scalar(select(m.Claim).where(m.Claim.vulnerability_id==seed.vulnerability_id,m.Claim.claim_type=='CVSS_SCORE'))
  value={**c.value_json,'vector':VECTOR};c.details={**c.details,'superseded':True}
  import hashlib
  from app.utils.time import utcnow
  from app.enrichment.evidence import EvidenceService
  now=utcnow();src=m.Source(source_key='C5_SYNTHETIC_'+uuid4().hex,name='SYNTHETIC CVSS primary',source_type='vendor_advisory',
   category='vulnerability',authority_level='official',authority_scope='vulnerability severity',acquisition_method='fixture',base_url='https://example.invalid/c5')
  db.add(src);db.flush();payload=json.dumps({'metric':value}).encode()
  raw=m.RawDocument(source_id=src.id,external_id=seed.cve,source_url=src.base_url,publisher=src.name,retrieved_at=now,content_type='application/json',raw_payload=payload,content_hash=hashlib.sha256(payload).hexdigest())
  db.add(raw);db.flush();obs=m.SourceObservation(source_id=src.id,raw_document_id=raw.id,external_id=seed.cve,publisher=src.name,record_type='vulnerability',retrieved_at=now,parse_status='parsed',normalizer_version='SYNTHETIC',lineage_key=src.source_key)
  db.add(obs);db.flush();new=m.Claim(claim_key='C5_SYNTHETIC_'+uuid4().hex,vulnerability_id=seed.vulnerability_id,claim_type='CVSS_SCORE',predicate='CVSS_SCORE',scope_key=c.scope_key,value_json=value)
  db.add(new);db.flush();EvidenceService.add(db,new,obs,value,{'json_pointer':'/metric'},evidence_type='official_vendor_advisory')
 try:
  with TestClient(create_app(engine,investigation_gateway=gateway)) as client:
   body={'user_query':request.user_query,'asset_scope':{'target':seed.cve,'asset_id':str(seed.asset_id),'component_id':str(seed.component_id),'component':seed.component},'idempotency_key':uuid4().hex}
   response=client.post('/api/investigations',json=body,headers=HEADERS);assert response.status_code==202,response.text
   identifier=response.json()['investigation_id'];terminal(client,identifier)
   answer=client.get(f'/api/investigations/{identifier}/answer',headers=HEADERS)
   assert answer.status_code==200,answer.text
   metrics=[f for f in answer.json()['verified_claims'] if f['claim_type']=='CVSS_SCORE']
   assert len(metrics)==1 and metrics[0]['value']['vector']==VECTOR,answer.text
   assert metrics[0]['evidence_ids'] and all(e in {c['evidence_id'] for c in answer.json()['citations']} for e in metrics[0]['evidence_ids'])
   count=len(calls);assert client.get(f'/api/investigations/{identifier}/answer',headers=HEADERS).json()==answer.json();assert len(calls)==count
   artifacts=client.get(f'/api/investigations/{identifier}/artifacts',headers=HEADERS).json()
   checked=[c for c in artifacts['verification']['claims'] if c['claim']['claim_id']==metrics[0]['claim_id']]
   assert checked[0]['claim']['value']['vector']==VECTOR
   projection=project_answer(question(),answer.json(),artifacts=artifacts)
   assert projection.answer.get('patch_status')!='CONFIRMED_FIX', 'A release must not verify the specified commit'
   nested=question().model_copy(update={'input_context':{'asset':{'target':seed.cve,'candidate_reference':URL}}})
   assert build_request(nested)['asset_scope']['candidate_reference']==URL
   assert project_answer(nested,answer.json(),artifacts=artifacts).answer.get('patch_status')!='CONFIRMED_FIX'
 finally:gateway.close()

def seed_reference(engine,seed,url):
 import hashlib
 from app.db import models as m
 from app.db.session import transaction
 from app.utils.time import utcnow
 from app.enrichment.evidence import EvidenceService
 with transaction(engine) as db:
  now=utcnow();src=m.Source(source_key='C5_REFERENCE_'+uuid4().hex,name='SYNTHETIC candidate origin',source_type='vendor_advisory',category='vulnerability',authority_level='official',authority_scope='vulnerability summary',acquisition_method='fixture',base_url='https://example.invalid/c5/'+uuid4().hex)
  db.add(src);db.flush();payload={'id':seed.cve,'summary':'SYNTHETIC reference fixture','references':[{'url':url}]};encoded=json.dumps(payload).encode()
  raw=m.RawDocument(source_id=src.id,external_id=seed.cve,source_url=src.base_url,publisher=src.name,retrieved_at=now,content_type='application/json',raw_payload=encoded,content_hash=hashlib.sha256(encoded).hexdigest())
  db.add(raw);db.flush();obs=m.SourceObservation(source_id=src.id,raw_document_id=raw.id,external_id=seed.cve,publisher=src.name,record_type='vulnerability',retrieved_at=now,parse_status='parsed',normalizer_version='SYNTHETIC',lineage_key=src.source_key,normalized_payload=payload)
  obs.raw_locator={'json_pointer':''};db.add(obs);db.flush();db.add(m.AiRelevanceAssessment(vulnerability_id=seed.vulnerability_id,method='rule',result='relevant',reason_summary='SYNTHETIC',evaluated_at=now,observation_id=obs.id))
  c=m.Claim(claim_key='C5_REFERENCE_'+uuid4().hex,vulnerability_id=seed.vulnerability_id,claim_type='SOURCE_FACT',predicate='SOURCE_FACT',scope_key='source-fact:summary',value_json={'field':'summary','text':payload['summary']})
  db.add(c);db.flush();e=EvidenceService.add(db,c,obs,c.value_json,{'json_pointer':'/summary'},evidence_type='official_vendor_advisory')
  return str(e.id),str(raw.id)

def test_actual_tcp_candidate_tool_evidence_handoff_and_no_cross_target_leak(engine,monkeypatch):
 from tests.orchestration.fixtures import scenario
 from tests.planner.fixtures import task,gateway_with_responses
 from tests.investigation_api.test_tcp_chain import tcp_client,TOKEN
 from app.main import create_app
 from app.tooling.candidate_evidence import candidate_evidence
 from app.tooling.adapters import evidence_refs
 from app.db.session import transaction
 from app.db import models as m
 from sqlalchemy import select
 seed,_,old,_,_=scenario(engine);old.close()
 eid,raw=seed_reference(engine,seed,URL)
 second,_,old,_,_=scenario(engine);old.close()
 with transaction(engine) as db:
  data,refs=candidate_evidence(db,second.vulnerability_id,URL,evidence_refs(db,second.vulnerability_id))
  assert not data['candidate_reference']['reference_evidence'] and not refs and not data['items']
 plan={'plan_id':str(uuid4()),'objective':'SYNTHETIC inspect reference','tasks':[task(arguments={'target':seed.cve,'candidate_reference':URL}),task('evidence_search','candidate','get_evidence',{'target':seed.cve,'candidate_reference':URL},['lookup'])],'reasoning_summary':'Read collected source references','confidence':0.5}
 plan['tasks'][1]['acceptance_criteria'].append('evidence_present')
 gateway,calls,_=gateway_with_responses([plan]);monkeypatch.setenv('AEGIS_ASSET_TOKEN',TOKEN);monkeypatch.setenv('AEGIS_ASSET_OWNER',seed.actor)
 try:
  with tcp_client(create_app(engine,investigation_gateway=gateway)) as client:
   q=question().model_copy(update={'input_context':{'target':seed.cve,'candidate_reference':URL}})
   body=build_request(q);response=client.post('/api/investigations',json=body);assert response.status_code==202,response.text
   identifier=response.json()['investigation_id']
   from tests.investigation_api.test_tcp_chain import terminal
   terminal(client,identifier)
   artifacts=client.get(f'/api/investigations/{identifier}/artifacts');assert artifacts.status_code==200,artifacts.text
   patches=artifacts.json()['investigation']['patch_information'];candidate=next(p for p in patches if p.get('reference')==URL)
   assert candidate['status']=='CANDIDATE' and candidate['patch_applied'] is None and candidate['applicability']=='UNKNOWN'
   assert eid in candidate['evidence_ids'] and candidate['reference_evidence'][0]['raw_document_id']==raw
   assert artifacts.json()['verification'] is not None
   assert eid in {e['evidence_id'] for e in artifacts.json()['verification']['supporting_evidence']}
   with transaction(engine) as db:
    records=list(db.scalars(select(m.ToolCallRecord).where(m.ToolCallRecord.tool_name=='get_evidence')))
    actual=[r for r in records if r.input_summary.get('arguments',r.input_summary).get('candidate_reference')==URL]
    assert actual and any(e['evidence_id']==eid for r in actual for e in r.output_summary.get('evidence_refs',[]))
   answer=client.get(f'/api/investigations/{identifier}/answer').json()
   projection=project_answer(q,answer,artifacts=artifacts.json())
   assert projection.answer['patch_status']=='PATCH_CANDIDATE'
 finally:gateway.close()

def test_planner_rejects_other_candidate_and_missing_required_candidate():
 from tests.planner.fixtures import context_for,valid_plan,task
 from app.agents.investigation.validation import validate_investigation_plan
 from app.agents.investigation.planning import InvestigationPlan
 context=context_for();context=context.model_copy(update={'scope_json':json.dumps({**context.scope,'candidate_reference':URL})})
 with pytest.raises(ValueError,match='CANDIDATE_REFERENCE_REQUIRED'):
  only=valid_plan();only['tasks'][0]['input_data']['steps'][0]['arguments']['candidate_reference']=URL
  validate_investigation_plan(InvestigationPlan.model_validate(only),context)
 plan=valid_plan();plan['tasks'][0]['input_data']['steps'][0]['arguments']['candidate_reference']=URL
 node=task('evidence_search','candidate','get_evidence',{'target':context.scope['targets'][0],'candidate_reference':URL.replace('a'*40,'b'*40)},['lookup']);node['acceptance_criteria'].append('evidence_present');plan['tasks'].append(node)
 with pytest.raises(ValueError,match='CANDIDATE_SCOPE_MISMATCH'):
  validate_investigation_plan(InvestigationPlan.model_validate(plan),context)
 plan['tasks'][0]['input_data']['steps'][0]['arguments'].pop('candidate_reference')
 plan['tasks'][1]['input_data']['steps'][0]['arguments']['candidate_reference']=URL
 with pytest.raises(ValueError,match='CANDIDATE_LOOKUP_REQUIRED'):
  validate_investigation_plan(InvestigationPlan.model_validate(plan),context)

@pytest.mark.parametrize('bad',['http://169.254.169.254/latest/meta-data','https://github.com/example/project/commit/'+'a'*40+'?redirect=http://localhost'])
def test_formal_http_denies_invalid_url_without_model_or_worker(engine,monkeypatch,bad):
 from app.main import create_app
 from app.llm.gateway import ModelGateway
 monkeypatch.setenv('AEGIS_ASSET_TOKEN','SYNTHETIC-test-token');gateway=ModelGateway()
 try:
  with TestClient(create_app(engine,investigation_gateway=gateway)) as client:
   response=client.post('/api/investigations',headers={'Authorization':'Bearer SYNTHETIC-test-token'},json={'user_query':'查看候选引用','asset_scope':{'target':'CVE-2099-12345','candidate_reference':bad},'idempotency_key':uuid4().hex})
   assert response.status_code==422
 finally:gateway.close()

@pytest.mark.parametrize('format',['shared_other','shared_target','cve5','summary_only'])
def test_candidate_raw_record_boundary_and_standard_source_formats(monkeypatch,format):
 from types import SimpleNamespace
 from hashlib import sha256
 from app.tooling import candidate_evidence as module
 source=uuid4();rid=uuid4();target=uuid4();a='CVE-2099-55551';b='CVE-2099-55552'
 prefix='';payload={'vulnerabilities':[{'cve':{'id':a,'references':[]}},{'cve':{'id':b,'references':[{'url':URL}]}}]}
 if format=='shared_target':payload['vulnerabilities'][0]['cve']['references']=[{'url':URL}]
 if format.startswith('shared'):prefix='/vulnerabilities/0'
 elif format=='cve5':payload={'cveMetadata':{'cveId':a},'containers':{'cna':{'references':[{'url':URL}]}}}
 else:payload={'id':a,'summary':URL,'references':[]}
 encoded=json.dumps(payload).encode();raw=SimpleNamespace(id=rid,source_id=source,raw_payload=encoded,content_hash=sha256(encoded).hexdigest(),source_url='https://example.invalid/source')
 class Session:
  def get(self,model,identifier):return raw
 monkeypatch.setattr(module,'vulnerability_detail',lambda *args:{'canonical_id':a,'external_identifiers':[{'identifier_value':a,'normalized_value':a,'identifier_type':'CVE'}],
  'source_documents':[{'id':str(rid),'locator':{'json_pointer':prefix}}]})
 data,refs=module.candidate_evidence(Session(),target,URL,[])
 item=data['candidate_reference'];assert not refs and not data['items']
 if format in ('shared_other','summary_only'):assert item['status']=='INSUFFICIENT_EVIDENCE'
 else:
  assert item['status']=='CANDIDATE' and item['content_checked'] is False
  expected='/vulnerabilities/0/cve/references/0/url' if format=='shared_target' else '/containers/cna/references/0/url'
  assert item['reference_evidence'][0]['locator']['json_pointer']==expected

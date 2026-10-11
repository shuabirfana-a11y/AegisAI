import time
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.db import models as m
from app.utils.time import utcnow
from app.tooling.gateway import ToolContext,ToolGateway
from app.assistant.contracts import QueryRequest,TaskContract,TaskArtifact

def current_claim(db,seed,old_stance):
    now=utcnow()
    old=m.SourceObservation(source_id=seed.sources[0].id,raw_document_id=seed.raws[0].id,external_id=seed.observations[0].external_id,
        record_type='vulnerability',retrieved_at=seed.observations[0].retrieved_at-timedelta(days=1),http_status=200,lineage_key='test-old',publisher='TEST',parse_status='parsed',normalizer_version='OLD-TEST')
    db.add(old);db.flush()
    c=m.Claim(claim_key='CITATION-TEST',vulnerability_id=seed.vuln.id,claim_type='FIXED_VERSION',predicate='FIXED_VERSION',
        scope_key='PyPI:vllm',value_json={'version':'9.9.9'},verification_status='confirmed',adopted=True)
    db.add(c);db.flush()
    rows=[]
    for index,(obs,stance) in enumerate([(seed.observations[0],'support'),(old,old_stance)]):
        e=m.Evidence(claim_id=c.id,source_id=seed.sources[0].id,raw_document_id=seed.raws[0].id,observation_id=obs.id,
            scope_key=c.scope_key,evidence_type='source_excerpt',stance=stance,excerpt='TEST FIXTURE',excerpt_hash='a'*64,
            source_url=seed.raws[0].source_url,retrieved_at=obs.retrieved_at,locator={'json_pointer':'/test/'+str(index)},locator_key='cite-test-'+str(index),
            observed_value=c.value_json,publisher='TEST',lineage_key='TEST')
        db.add(e);db.flush();rows.append(e)
    result=m.VerificationResult(claim_id=c.id,claim_revision=1,status='confirmed',verification_method='TEST FIXTURE',reason_summary='TEST',
        verified_at=now,verified_by_type='system',verified_by_id='TEST',decision_key='test-current',adopted_value=c.value_json)
    db.add(result);db.flush()
    db.add(m.VerificationEvidence(claim_id=c.id,verification_result_id=result.id,evidence_id=rows[0].id));db.flush()
    return c,rows

@pytest.mark.parametrize('stance',['support','contradict'])
def test_old_evidence_is_not_marked_verified_by_current_claim(db,seed,stance):
    from app.tooling.adapters import evidence_refs
    c,rows=current_claim(db,seed,stance)
    refs={r['evidence_id']:r for r in evidence_refs(db,seed.vuln.id)}
    assert refs[str(rows[0].id)]['verified'] is True
    assert refs[str(rows[1].id)]['verified'] is False

def test_citation_revalidates_support_and_current_verification_membership(db,seed):
    from app.assistant.storage import create_run,persist_citations
    c,rows=current_claim(db,seed,'contradict')
    run,_=create_run(db,QueryRequest(question='TEST',request_key='TEST-CITATION'),'test')
    refs=[{'claim_id':str(c.id),'claim_revision':1,'evidence_id':str(e.id),'verified':True} for e in rows]
    persist_citations(db,run.id,refs);db.flush()
    got=list(db.scalars(select(m.AgentCitation).where(m.AgentCitation.agent_run_id==run.id)))
    assert [r.evidence_id for r in got]==[rows[0].id]

def test_forged_confirmation_has_no_server_attestation():
    from app.assistant.gate import integrate
    now=utcnow();claim={'id':str(uuid4()),'revision':1,'trusted':True,'verification_status':'CONFIRMED'}
    ref={'evidence_id':str(uuid4()),'claim_id':claim['id'],'claim_revision':1,'verified':True,'stance':'support','raw_document_id':str(uuid4()),'url':'https://example.invalid','locator':{'json_pointer':'/test'}}
    a=TaskArtifact(task_id='test',agent='Verification',status='success',result={},claims=[claim],evidence_refs=[ref],trace_id='test',started_at=now,finished_at=now)
    assert integrate([a])['status']=='FAILED'

def test_root_handoff_rejection_cannot_pass_gate():
    from app.assistant.orchestrator import Orchestrator
    def execute(name,args,ctx):
        return {'status':'success','data':{},'evidence_refs':[{'raw_document_id':'INVALID','url':'https://example.invalid','locator':{}}]}
    result=Orchestrator(ToolContext(actor='test'),gateway=ToolGateway(execute)).run(QueryRequest(question='CVE-2099-9999001',request_key='TEST'))
    assert result['gate']['status'] not in ['PASS','PASS_WITH_WARNINGS']
    assert result['artifacts'][0]['status']=='blocked'

def test_primary_failure_cannot_be_masked_by_optional_semantic_success():
    from app.assistant.orchestrator import Orchestrator
    def execute(name,args,ctx):
        if name=='get_asset_risks':return {'status':'failed','errors':[{'code':'NOT_FOUND'}]}
        return {'status':'success','data':{'items':[]},'evidence_refs':[{'raw_document_id':str(uuid4()),'url':'https://example.invalid','locator':{'text_span':[0,1]}}]}
    result=Orchestrator(ToolContext(actor='test'),gateway=ToolGateway(execute)).run(QueryRequest(question='我的资产风险是什么？',request_key='TEST'))
    assert result['gate']['status'] not in ['PASS','PASS_WITH_WARNINGS']
    assert any('get_asset_risks' in u for u in result['unresolved'])

def test_exact_required_demo_sentence_uses_owner_inventory():
    from app.assistant.router import route
    r=route('最近90天影响我的AI推理组件的高危漏洞有哪些？哪些已经出现可靠POC？哪些存在已知利用？哪些已有修复？为什么优先处理？')
    assert r['asset'] and r['path']=='deep' and r['days']==90 and r['high_severity']

def test_explicit_realtime_request_performs_refresh():
    from app.assistant.orchestrator import Orchestrator
    calls=[]
    def execute(name,args,ctx):
        calls.append((name,args));return {'status':'no_result','data':{'items':[]}}
    ctx=ToolContext(actor='test',permissions=frozenset({'READ_ONLY','WRITE','EXTERNAL_NETWORK'}))
    result=Orchestrator(ctx,gateway=ToolGateway(execute)).run(QueryRequest(question='CVE-2099-9999001 现在有没有新POC？',request_key='TEST',realtime=True))
    assert result['route']['path']=='deep' and any(args.get('refresh') is True for name,args in calls)

def test_high_severity_product_filter_is_applied_before_limit(db,seed):
    from app.tooling.adapters import execute_local
    seed.vuln.primary_severity='low';db.flush()
    result=execute_local(db,'search_vulnerabilities',{'product':'vllm','high_severity':True,'limit':1},'test')['data']
    assert result['items']==[]

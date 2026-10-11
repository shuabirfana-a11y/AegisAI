from datetime import timedelta
import json,base64
import httpx,pytest
from sqlalchemy import select,func
from app.db import models as m
from app.enrichment.repository import ClaimStore,ensure_review
from app.enrichment.evidence import EvidenceService,current_evidence
from app.enrichment.verification import VerificationService
from app.enrichment.review import ReviewWorkflow
from app.enrichment.conflict import ConflictDetectionService
from app.enrichment.integration import IntelligenceIntegrationService
from test_phase7_trust import claim_with_evidence
from test_phase7_enrichers import acquire,context
from conftest import NOW

def decide(db,c,e,key,task=None):
    task=task or ensure_review(db,c,'VERSION_CONFLICT','TEST analyst comparison')
    return ReviewWorkflow.resolve(db,task_id=task.id,actor='TEST-analyst',expected_revision=task.revision,
        expected_claim_revision=c.revision,request_key=key,status='confirmed',value=c.value_json,
        reason='TEST analyst selected this supported scoped value',evidence_ids=[e.id])

def test_final_version_conjunction_order_preserves_bounded_membership():
    from app.enrichment.versions import intervals,contains,canonical_value
    a={'ecosystem':'PyPI','range':'<0.8.4,>=0.8.0'};b={**a,'range':'>=0.8.0,<0.8.4'}
    assert intervals(a)==intervals(b) and canonical_value('AFFECTS_VERSION',a)==canonical_value('AFFECTS_VERSION',b)
    assert contains(a,'0.7.0') is False and contains(a,'0.8.2') is True and contains(a,'0.9.0') is False

def test_final_successful_identical_refresh_has_fresh_observation_not_duplicate_raw(db,seed,monkeypatch):
    dates=iter([NOW,NOW+timedelta(days=31)])
    monkeypatch.setattr('app.enrichment.acquisition.utcnow',lambda:next(dates))
    acq=acquire(db,lambda req:httpx.Response(200,json={'version':'0.8.4'}))
    a=acq.fetch('EPSS','https://api.first.org/data/v1/epss','TEST-refresh','first:epss')
    c=ClaimStore.add(db,seed.vuln.id,'FIXED_VERSION','TEST-refresh',{'version':'0.8.4'})
    e=EvidenceService.add(db,c,db.get(m.SourceObservation,a.observation_id),c.value_json,{'json_pointer':'/version'},evidence_type='official_vendor_advisory')
    b=acq.fetch('EPSS','https://api.first.org/data/v1/epss','TEST-refresh','first:epss')
    e2=EvidenceService.add(db,c,db.get(m.SourceObservation,b.observation_id),c.value_json,{'json_pointer':'/version'},evidence_type='official_vendor_advisory')
    assert a.raw_id==b.raw_id and a.observation_id!=b.observation_id and e2.retrieved_at==NOW+timedelta(days=31)
    assert VerificationService.verify(db,c,now=NOW+timedelta(days=31)).status=='confirmed'
    assert db.get(m.RawDocument,a.raw_id).retrieved_at==NOW and db.get(m.Evidence,e.id)

def test_final_a_b_a_content_restores_a_current_observation(db,seed,monkeypatch):
    dates=iter([NOW,NOW+timedelta(minutes=1),NOW+timedelta(minutes=2)]);payloads=iter([{'version':'0.8.4'},{'version':'0.8.5'},{'version':'0.8.4'}])
    monkeypatch.setattr('app.enrichment.acquisition.utcnow',lambda:next(dates))
    acq=acquire(db,lambda req:httpx.Response(200,json=next(payloads)));claims={};docs=[]
    for i in range(3):
        d=acq.fetch('EPSS','https://api.first.org/data/v1/epss','TEST-a-b-a','first:epss');docs.append(d)
        c=ClaimStore.add(db,seed.vuln.id,'FIXED_VERSION','TEST-a-b-a',d.payload);claims[d.payload['version']]=c
        EvidenceService.add(db,c,db.get(m.SourceObservation,d.observation_id),d.payload,{'json_pointer':'/version'})
    assert docs[0].raw_id==docs[2].raw_id and docs[0].observation_id!=docs[2].observation_id
    assert [e['is_current'] for e in current_evidence(db,claims['0.8.4'])]==[False,True]
    assert not any(e['is_current'] for e in current_evidence(db,claims['0.8.5']))

def test_final_human_replacement_keeps_one_adopted_value_and_audit(db,seed):
    a,e=claim_with_evidence(db,seed,index=0);decide(db,a,e,'TEST-adopt-A')
    b,e2=claim_with_evidence(db,seed,{**a.value_json,'version':'0.8.5'},index=2)
    audit=decide(db,b,e2,'TEST-adopt-B')
    assert b.adopted and not a.adopted and audit.verification_result_id
    assert db.scalar(select(func.count()).select_from(m.Claim).where(m.Claim.scope_key=='PyPI:vllm',m.Claim.adopted.is_(True)))==1
    assert db.scalar(select(m.AuditLog).where(m.AuditLog.claim_id==a.id,m.AuditLog.action=='claim_adoption_replaced'))

def test_final_same_readme_with_new_official_reference_reverifies_consistently(db,seed):
    from app.enrichment.enrichers.poc import PocEnricher
    from app.enrichment.parsing import parse_advisory
    repo='TEST-research/poc';url='https://github.com/'+repo
    readme=f'{seed.vuln.canonical_id} vllm 0.8.2 remote code execution PoC steps to reproduce'
    advisory={'cve_id':seed.vuln.canonical_id,'ghsa_id':'GHSA-test-test-test','state':'published','description':'PoC '+url,'vulnerabilities':[]}
    def handler(req):
        if '/search/' in req.url.path:return httpx.Response(200,json={'total_count':1,'incomplete_results':False,'items':[{'full_name':repo,'owner':{'login':'TEST-research'},'fork':False}]})
        if '/security-advisories/' in req.url.path:return httpx.Response(200,json=advisory)
        return httpx.Response(200,json={'size':len(readme),'encoding':'base64','content':base64.b64encode(readme.encode()).decode()})
    acq=acquire(db,handler);ctx=context(db,seed)
    ClaimStore.add(db,seed.vuln.id,'AFFECTS_VERSION','PyPI:vllm',{'ecosystem':'PyPI','package':'vllm','range':'<0.8.4'})
    first=PocEnricher().investigate(ctx,db,acq)
    c=db.get(m.Claim,first.claims[0]);assert VerificationService.verify(db,c).status=='pending'
    doc=acq.fetch('VENDOR_VLLM','https://api.github.com/repos/vllm-project/vllm/security-advisories/GHSA-test-test-test','TEST-official-poc','github:vllm-project/vllm')
    ctx.vendor_documents=[{'document':doc,'parsed':parse_advisory(advisory,'vllm-project/vllm',ctx.canonical_id,ctx.aliases),'repository':'vllm-project/vllm'}]
    second=PocEnricher().investigate(ctx,db,acq);c=db.get(m.Claim,second.claims[0]);result=VerificationService.verify(db,c)
    assert db.get(m.PocCandidate,second.candidates[0]).status=='confirmed' and result.status=='confirmed'
    assert IntelligenceIntegrationService.adopt(db,c,result)['adopted']
    assert db.scalar(select(m.IntelligenceEvent).where(m.IntelligenceEvent.event_type=='POC_CONFIRMED'))

def test_final_resolved_pair_new_opposing_raw_requires_one_recheck(db,seed):
    from app.db.persistence import store_raw
    a,e=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<0.8.4'},'AFFECTS_VERSION',0)
    b,e2=claim_with_evidence(db,seed,{'package':'vllm','ecosystem':'PyPI','range':'<0.8.5'},'AFFECTS_VERSION',2)
    conflict=ConflictDetectionService.detect(db,seed.vuln.id,now=NOW)[0]
    chosen=db.get(m.Claim,conflict.claim_a_id);support=db.scalar(select(m.Evidence).where(m.Evidence.claim_id==chosen.id,m.Evidence.stance=='support'))
    decide(db,chosen,support,'TEST-resolve-old',db.get(m.ReviewTask,conflict.review_task_id))
    opposing=b if chosen.id==a.id else a;obs=seed.observations[2 if opposing.id==b.id else 0]
    raw=store_raw(db,source_id=obs.source_id,external_id=obs.external_id,source_url='https://example.invalid/new-revision',retrieved_at=NOW+timedelta(minutes=1),
        content_type='application/json',raw_payload=json.dumps({'range':opposing.value_json['range'],'additional_context':'TEST NEW SOURCE REVISION'}).encode(),publisher='TEST')
    new=m.SourceObservation(source_id=obs.source_id,raw_document_id=raw.id,external_id=obs.external_id,record_type='vulnerability',retrieved_at=raw.retrieved_at,
        lineage_key=obs.lineage_key,publisher=obs.publisher,parse_status='parsed',normalizer_version='TEST-new-revision')
    db.add(new);db.flush();EvidenceService.add(db,opposing,new,opposing.value_json,{'json_pointer':'/range'},evidence_type='official_vendor_advisory')
    before=db.scalar(select(func.count()).select_from(m.ReviewTask))
    ConflictDetectionService.detect(db,seed.vuln.id,now=NOW+timedelta(minutes=2));VerificationService.verify(db,chosen,now=NOW+timedelta(minutes=2))
    assert chosen.adopted and db.scalar(select(func.count()).select_from(m.ReviewTask))==before+1
    assert db.scalar(select(func.count()).select_from(m.ConflictRecord).where(m.ConflictRecord.status=='open'))==1
    ConflictDetectionService.detect(db,seed.vuln.id,now=NOW+timedelta(minutes=2));VerificationService.verify(db,chosen,now=NOW+timedelta(minutes=2))
    assert db.scalar(select(func.count()).select_from(m.ReviewTask))==before+1

def test_final_patch_checked_reference_limit_includes_failures(db,seed):
    from app.enrichment.enrichers.patch import PatchEnricher
    ctx=context(db,seed);ctx.references=[{'url':'https://github.com/vllm-project/vllm/commit/'+format(i,'040x')} for i in range(1,11)]
    count=[0]
    def handler(req):count[0]+=1;return httpx.Response(403,json={'message':'TEST rate limit'})
    PatchEnricher().investigate(ctx,db,acquire(db,handler))
    assert count[0]==5

def test_final_vendor_publication_timestamp_is_evidence_time(db,seed):
    from app.enrichment.enrichers.vendor import VendorEnricher
    payload={'cve_id':seed.vuln.canonical_id,'ghsa_id':'GHSA-test-test-test','published_at':NOW.isoformat(),'state':'published','vulnerabilities':[]}
    out=VendorEnricher().investigate(context(db,seed),db,acquire(db,lambda req:httpx.Response(200,json=payload)))
    assert db.get(m.Evidence,out.evidence[0]).published_at==NOW

def test_final_existing_patch_candidate_refreshes_after_vendor_recovery(db,seed):
    from app.enrichment.enrichers.patch import PatchEnricher
    from app.enrichment.parsing import parse_advisory
    ctx=context(db,seed);sha='a'*40;url='https://github.com/vllm-project/vllm/commit/'+sha
    advisory={'cve_id':ctx.canonical_id,'ghsa_id':'GHSA-test-test-test','state':'published','description':'Fix '+url,'vulnerabilities':[]}
    def handler(req):return httpx.Response(200,json=advisory if '/security-advisories/' in req.url.path else {'sha':sha,'html_url':url})
    acq=acquire(db,handler);ctx.references=[{'url':url}]
    out=PatchEnricher().investigate(ctx,db,acq);row=db.get(m.PatchCandidate,out.candidates[0]);assert row.status=='candidate'
    doc=acq.fetch('VENDOR_VLLM','https://api.github.com/repos/vllm-project/vllm/security-advisories/GHSA-test-test-test','TEST-patch-advisory','github:vllm-project/vllm')
    ctx.vendor_documents=[{'document':doc,'parsed':parse_advisory(advisory,'vllm-project/vllm',ctx.canonical_id,ctx.aliases),'repository':'vllm-project/vllm'}]
    PatchEnricher().investigate(ctx,db,acq)
    assert row.status=='confirmed' and row.details['association_reason']=='Explicit official advisory reference'

def test_real_api_unsupported_patched_expression_is_unknown_not_fixed_conflict(db,seed):
    from app.enrichment.rules import compare_claims,evaluate_claim
    a={'type':'FIXED_VERSION','scope':'PyPI:vllm','value':{'package':'vllm','ecosystem':'PyPI','version':None,'raw_expression':'>=0.24.0'}}
    b={**a,'value':{'package':'vllm','ecosystem':'PyPI','version':'0.24.0'}}
    assert compare_claims(a,b) is None
    c,e=claim_with_evidence(db,seed,a['value'],index=0)
    c2,e2=claim_with_evidence(db,seed,b['value'],index=2)
    assert ConflictDetectionService.detect(db,seed.vuln.id,now=NOW)==[]
    assert VerificationService.verify(db,c,now=NOW).status=='insufficient'

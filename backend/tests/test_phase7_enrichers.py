from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4
import json,base64
import httpx,pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.db import models as m
from app.core.config import Settings
from app.core.http import HttpClient
from conftest import NOW

def acquire(db,handler):
    from app.enrichment.acquisition import EnrichmentAcquisition,validate_enrichment_url
    conn=db.connection()
    @contextmanager
    def factory():
        with Session(conn,join_transaction_mode='create_savepoint') as s:
            with s.begin():yield s
    http=HttpClient(Settings(request_interval=0,retries=0),transport=httpx.MockTransport(handler),url_validator=validate_enrichment_url)
    return EnrichmentAcquisition(factory,http)

def context(db,seed):
    from app.enrichment.context import EnrichmentContext
    return EnrichmentContext(target_id=seed.vuln.id,canonical_id=seed.vuln.canonical_id,aliases=['GHSA-test-test-test'],
        packages=[{'name':'vllm','ecosystem':'PyPI','product_id':seed.products[0].id,'package_id':seed.packages[0].id,'repository':'vllm-project/vllm'}],
        current_observation_ids=[seed.observations[0].id],references=[],trace_id=uuid4(),task_id=uuid4())

def test_phase7_http_policy_rejects_arbitrary_reference_targets():
    from app.enrichment.acquisition import validate_enrichment_url
    for url in ['http://api.github.com/repos/test/repo','https://127.0.0.1/a','https://api.github.com/user',
                'https://api.github.com/repos/test/repo/actions/runs','https://evil.test/poc','https://api.first.org/data/v1/other',
                'https://api.github.com/repos/test/../readme']:
        with pytest.raises(ValueError):validate_enrichment_url(url)

def test_malformed_external_json_remains_in_raw_when_parse_fails(db,seed):
    acq=acquire(db,lambda req:httpx.Response(200,content=b'<html>not JSON</html>'))
    with pytest.raises(ValueError):acq.fetch('EPSS','https://api.first.org/data/v1/epss?cve='+seed.vuln.canonical_id,'epss-test','first:epss')
    raw=db.scalar(select(m.RawDocument).join(m.Source).where(m.Source.source_key=='EPSS'))
    assert raw is not None and raw.raw_payload==b'<html>not JSON</html>' and raw.details['content_trust_level']=='UNTRUSTED_EXTERNAL_CONTENT'

def test_epss_two_dates_remain_snapshots_and_unknown_model_is_not_api_version(db,seed):
    from app.enrichment.enrichers.epss import EpssEnricher
    days=iter(['2026-10-02','2026-10-03'])
    def handler(req):return httpx.Response(200,json={'status':'OK','status-code':200,'version':'1.0','total':1,'offset':0,'limit':100,
        'data':[{'cve':seed.vuln.canonical_id,'epss':'0.43210000','percentile':'0.95000000','date':next(days)}]})
    acq=acquire(db,handler);ctx=context(db,seed)
    a=EpssEnricher().investigate(ctx,db,acq);b=EpssEnricher().investigate(ctx,db,acq)
    rows=list(db.scalars(select(m.EpssSnapshot)))
    assert a.status==b.status=='SUCCESS' and {str(r.score_date) for r in rows}=={'2026-10-02','2026-10-03'}
    assert all(r.model_version=='unknown_api_not_reported' for r in rows)
    assert db.scalar(select(m.IntelligenceEvent).where(m.IntelligenceEvent.event_type=='EPSS_CHANGED'))

def test_epss_missing_record_is_no_result_without_zero_score(db,seed):
    from app.enrichment.enrichers.epss import EpssEnricher
    acq=acquire(db,lambda req:httpx.Response(200,json={'status':'OK','data':[],'total':0}))
    result=EpssEnricher().investigate(context(db,seed),db,acq)
    assert result.status=='NO_RESULT' and db.scalar(select(func.count()).select_from(m.EpssSnapshot))==0

def test_epss_wrong_cve_or_invalid_score_refuses_snapshot(db,seed):
    from app.enrichment.enrichers.epss import EpssEnricher
    acq=acquire(db,lambda req:httpx.Response(200,json={'status':'OK','data':[{'cve':'CVE-2099-9999002','epss':'1.2','percentile':'.9','date':'2026-10-03'}]}))
    with pytest.raises(ValueError):EpssEnricher().investigate(context(db,seed),db,acq)
    assert db.scalar(select(func.count()).select_from(m.EpssSnapshot))==0

def test_vendor_mismatching_identifier_is_not_confirmed(db,seed):
    from app.enrichment.enrichers.vendor import VendorEnricher
    acq=acquire(db,lambda req:httpx.Response(200,json={'ghsa_id':'GHSA-test-test-test','cve_id':'CVE-2099-9999002','state':'published','vulnerabilities':[]}))
    result=VendorEnricher().investigate(context(db,seed),db,acq)
    assert result.status=='NO_RESULT'
    assert not db.scalar(select(m.Claim).where(m.Claim.claim_type=='VENDOR_CONFIRMED'))

def test_vendor_fixed_claim_has_original_advisory_evidence(db,seed):
    from app.enrichment.enrichers.vendor import VendorEnricher
    advisory={'ghsa_id':'GHSA-test-test-test','cve_id':seed.vuln.canonical_id,'state':'published','published_at':NOW.isoformat(),
        'vulnerabilities':[{'package':{'ecosystem':'pip','name':'vllm'},'vulnerable_version_range':'<0.8.4','patched_versions':'0.8.4'}]}
    result=VendorEnricher().investigate(context(db,seed),db,acquire(db,lambda req:httpx.Response(200,json=advisory)))
    c=db.scalar(select(m.Claim).where(m.Claim.claim_type=='FIXED_VERSION'))
    e=db.scalar(select(m.Evidence).where(m.Evidence.claim_id==c.id))
    assert result.status=='SUCCESS' and c.value_json['version']=='0.8.4' and e.locator['json_pointer']=='/vulnerabilities/0/patched_versions'
    assert json.loads(db.get(m.RawDocument,e.raw_document_id).raw_payload)['cve_id']==seed.vuln.canonical_id

def test_poc_empty_search_is_no_result_and_search_snapshot_is_saved(db,seed):
    from app.enrichment.enrichers.poc import PocEnricher
    result=PocEnricher().investigate(context(db,seed),db,acquire(db,lambda req:httpx.Response(200,json={'total_count':0,'incomplete_results':False,'items':[]})))
    assert result.status=='NO_RESULT' and result.checked[0]['checked_at']
    assert db.scalar(select(m.RawDocument).join(m.Source).where(m.Source.source_key=='GITHUB'))

def test_incomplete_search_with_zero_results_is_partial_not_no_poc(db,seed):
    from app.enrichment.enrichers.poc import PocEnricher
    result=PocEnricher().investigate(context(db,seed),db,acquire(db,lambda req:httpx.Response(200,json={'total_count':0,'incomplete_results':True,'items':[]})))
    assert result.status=='PARTIAL' and result.unresolved

def test_poc_readme_missing_retains_candidate_with_insufficient_status(db,seed):
    from app.enrichment.enrichers.poc import PocEnricher
    repo={'full_name':'research/CVE-2099-9999001','owner':{'login':'research'},'html_url':'https://github.com/research/CVE-2099-9999001',
        'created_at':NOW.isoformat(),'updated_at':NOW.isoformat(),'description':'CVE demo','fork':False}
    def handler(req):
        if '/search/' in req.url.path:return httpx.Response(200,json={'total_count':1,'incomplete_results':False,'items':[repo]})
        return httpx.Response(404,json={'message':'Not Found'})
    result=PocEnricher().investigate(context(db,seed),db,acquire(db,handler))
    candidates=list(db.scalars(select(m.PocCandidate).where(m.PocCandidate.repository=='research/CVE-2099-9999001')))
    assert result.status=='PARTIAL' and len(candidates)==1 and candidates[0].status=='unknown'
    assert candidates[0].details['verification_status']=='INSUFFICIENT_EVIDENCE'

def test_kev_reuses_complete_original_catalog_without_network(db,seed):
    from app.enrichment.enrichers.kev import KevEnricher
    from app.db.persistence import store_raw
    source=m.Source(source_key='CISA_KEV',name='TEST KEV',source_type='catalog',category='test',authority_level='official',
        authority_scope='TEST',acquisition_method='fixture',base_url='https://example.invalid')
    db.add(source);db.flush()
    p={'catalogVersion':'TEST-2026-10-03','dateReleased':NOW.isoformat(),'count':1,'vulnerabilities':[{'cveID':seed.vuln.canonical_id,
        'dateAdded':'2026-10-02','dueDate':'2026-10-23','requiredAction':'TEST update','vendorProject':'TEST','product':'vllm'}]}
    store_raw(db,source_id=source.id,external_id='kev-catalog',source_url=source.base_url,retrieved_at=NOW,
        content_type='application/json',raw_payload=json.dumps(p).encode(),publisher='CISA',completeness='complete')
    acq=acquire(db,lambda req:(_ for _ in ()).throw(AssertionError('KEV must reuse existing full catalog')))
    result=KevEnricher().investigate(context(db,seed),db,acq)
    c=db.scalar(select(m.Claim).where(m.Claim.claim_type=='KNOWN_EXPLOITED'))
    assert result.status=='SUCCESS' and c.value_json['known_exploited'] is True
    k=db.scalar(select(m.KnownExploitation))
    assert str(k.date_added)=='2026-10-02' and k.required_action=='TEST update'

def test_base64_readme_size_is_bounded_and_never_executes(db,seed):
    from app.enrichment.acquisition import decode_readme
    payload={'encoding':'base64','content':base64.b64encode(b'x'*524289).decode(),'size':524289}
    with pytest.raises(ValueError):decode_readme(payload)

def test_patch_explicit_advisory_commit_retains_raw_link_and_full_sha(db,seed):
    from app.enrichment.enrichers.vendor import VendorEnricher
    from app.enrichment.enrichers.patch import PatchEnricher
    sha='a'*40
    advisory={'ghsa_id':'GHSA-test-test-test','cve_id':seed.vuln.canonical_id,'state':'published','vulnerabilities':[],
        'description':'Fix: https://github.com/vllm-project/vllm/commit/'+sha}
    def handler(req):
        if '/security-advisories/' in req.url.path:return httpx.Response(200,json=advisory)
        return httpx.Response(200,json={'sha':sha,'html_url':'https://github.com/vllm-project/vllm/commit/'+sha,'commit':{'message':'TEST explicit fix','committer':{'date':NOW.isoformat()}},'files':[{'filename':'vllm/test.py'}]})
    ctx=context(db,seed);acq=acquire(db,handler)
    VendorEnricher().investigate(ctx,db,acq)
    result=PatchEnricher().investigate(ctx,db,acq)
    candidate=db.scalar(select(m.PatchCandidate))
    assert result.status=='SUCCESS' and candidate.commit_sha==sha and candidate.status=='confirmed'
    claim=db.scalar(select(m.Claim).where(m.Claim.claim_type=='FIX_COMMIT'))
    assert db.scalar(select(m.Evidence).where(m.Evidence.claim_id==claim.id))

def test_version_enrichment_uses_explicit_fixed_event_without_guessing(db,seed):
    from app.enrichment.enrichers.version import VersionEnricher
    from app.normalizers import osv
    from app.db.persistence import store_raw
    payload={'id':'GHSA-test-test-test','modified':NOW.isoformat(),'aliases':[seed.vuln.canonical_id],
        'affected':[{'package':{'ecosystem':'PyPI','name':'vllm'},'ranges':[{'type':'ECOSYSTEM','events':[{'introduced':'0'},{'fixed':'0.8.4'}]}]}]}
    raw=store_raw(db,source_id=seed.sources[1].id,external_id=payload['id'],source_url='https://example.invalid/osv',
        retrieved_at=NOW,content_type='application/json',raw_payload=json.dumps(payload).encode(),publisher='TEST')
    o=m.SourceObservation(source_id=raw.source_id,raw_document_id=raw.id,external_id=payload['id'],record_type='vulnerability',
        retrieved_at=NOW,lineage_key='github:vllm-project/vllm',publisher='TEST',parse_status='parsed',
        normalizer_version='TEST-normalized',normalized_payload=osv.normalize(payload,raw.id,NOW).model_dump(mode='json'))
    db.add(o);db.flush();ctx=context(db,seed);ctx.current_observation_ids=[o.id]
    result=VersionEnricher().investigate(ctx,db,acquire(db,lambda req:(_ for _ in ()).throw(AssertionError('No version network call'))))
    fixed=db.scalar(select(m.Claim).where(m.Claim.claim_type=='FIXED_VERSION'))
    assert result.status=='SUCCESS' and fixed.value_json['version']=='0.8.4'

def test_reenrichment_after_no_result_detects_new_repository_and_event(db,seed):
    from app.enrichment.enrichers.poc import PocEnricher
    step=[0]
    def handler(req):
        if '/search/' in req.url.path:
            step[0]+=1
            repo={'full_name':'TEST-research/new-poc','owner':{'login':'TEST-research'},'fork':False,'description':'TEST'}
            return httpx.Response(200,json={'total_count':0 if step[0]==1 else 1,'incomplete_results':False,'items':[] if step[0]==1 else [repo]})
        content=f'{seed.vuln.canonical_id} vllm 0.8.2 remote code execution PoC steps to reproduce'
        return httpx.Response(200,json={'encoding':'base64','size':len(content),'content':base64.b64encode(content.encode()).decode()})
    acq=acquire(db,handler);ctx=context(db,seed)
    first=PocEnricher().investigate(ctx,db,acq);second=PocEnricher().investigate(ctx,db,acq)
    assert first.status=='NO_RESULT' and second.status=='SUCCESS' and second.candidates
    assert db.scalar(select(m.IntelligenceEvent).where(m.IntelligenceEvent.event_type=='POC_CANDIDATE_FOUND'))

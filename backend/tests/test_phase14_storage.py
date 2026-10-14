"""Real PostgreSQL, synthetic transport; no live sources or assessment claims."""
import json,hashlib
from contextlib import contextmanager
from sqlalchemy import select,func
from sqlalchemy.orm import Session
import httpx
import pytest
from app.db import models as m
from app.services.sync import SyncService
from app.core.http import HttpClient
from app.core.config import Settings
from test_phase14_sources import ghsa

class Embed:
    model='SYNTHETIC-PHASE14';dimension=2
    def passages(self,texts):return [[1.0,0.0] for _ in texts]

def factory(db):
    connection=db.connection()
    @contextmanager
    def session():
        with Session(connection,join_transaction_mode='create_savepoint') as s:
            with s.begin():yield s
    return session

def test_native_collector_preserves_raw_and_replay_is_idempotent(db):
    from app.monitoring.collectors import GitHubCollector
    from app.monitoring.catalog import validate_url
    native=ghsa();body=json.dumps(native).encode()
    def transport(request):
        if request.url.path=='/advisories':return httpx.Response(200,json=[native])
        return httpx.Response(200,content=body)
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(transport),url_validator=validate_url)
    try:
        collector=GitHubCollector(client,bootstrap_ids=[])
        service=SyncService(None,session_factory=factory(db));first=service.sync(collector,1);again=service.sync(collector,1)
        assert first['created']==1 and again['skipped']==1
        raw=db.scalar(select(m.RawDocument).where(m.RawDocument.external_id==native['ghsa_id']))
        assert raw.raw_payload==body and raw.content_hash==hashlib.sha256(body).hexdigest()
        assert db.scalar(select(func.count()).select_from(m.Vulnerability))==1
    finally:client.close()

def test_feed_ingestion_indexes_without_confirming_document_association(db,seed):
    from app.monitoring.knowledge import FeedSyncService
    from app.monitoring.catalog import validate_url
    body=b'<rss><channel><item><guid>synthetic-paper-link</guid><title>Analysis of CVE-2099-9999001</title><link>https://blog.trailofbits.com/test/</link><description>TEST ONLY vllm technical discussion.</description><pubDate>Tue, 13 Oct 2026 00:00:00 GMT</pubDate></item></channel></rss>'
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(lambda request:httpx.Response(200,content=body,headers={'etag':'"fixture"'})),url_validator=validate_url)
    try:
        service=FeedSyncService(factory(db),http=client,embed=Embed())
        first=service.sync('RSS_TRAIL_OF_BITS',limit=3);again=service.sync('RSS_TRAIL_OF_BITS',limit=3)
        assert first['created']==1 and again['skipped']==1
        document=db.scalar(select(m.KnowledgeDocument).where(m.KnowledgeDocument.external_id=='synthetic-paper-link'))
        assert document.document_type=='blog' and document.details['content_trust_level']=='UNTRUSTED_EXTERNAL_CONTENT'
        assert db.scalar(select(func.count()).select_from(m.KnowledgeChunk).where(m.KnowledgeChunk.document_id==document.id))==1
        link=db.scalar(select(m.KnowledgeVulnerabilityRelation).where(m.KnowledgeVulnerabilityRelation.knowledge_document_id==document.id))
        claim=db.get(m.Claim,link.claim_id)
        assert link.vulnerability_id==seed.vuln.id and claim.adopted is False and claim.verification_status!='confirmed'
        evidence=db.scalar(select(m.Evidence).where(m.Evidence.claim_id==claim.id))
        raw=db.get(m.RawDocument,document.raw_document_id)
        assert raw.raw_payload==body and evidence.raw_document_id==raw.id
        assert evidence.locator=={'xml_path':'/rss/channel/item[1]'}
    finally:client.close()

def test_invalid_feed_keeps_raw_but_does_not_create_knowledge_or_success(db):
    from app.monitoring.knowledge import FeedSyncService
    from app.monitoring.catalog import validate_url
    body=b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///secret">]><rss/>'
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(lambda r:httpx.Response(200,content=body)),url_validator=validate_url)
    try:
        result=FeedSyncService(factory(db),http=client,embed=Embed()).sync('RSS_TRAIL_OF_BITS')
        assert result['status']=='failed' and db.scalar(select(func.count()).select_from(m.KnowledgeDocument))==0
        assert db.scalar(select(m.RawDocument)).raw_payload==body
        source=db.scalar(select(m.Source));assert source.last_success_at is None and source.status=='failed'
    finally:client.close()

def test_projection_never_turns_poc_name_or_association_into_verified_exploit(db,seed):
    from app.monitoring.views import vulnerability_view
    seed.poc.status='confirmed';seed.poc.usability_status='not_evaluated';db.flush()
    view=vulnerability_view(db,str(seed.vuln.id))
    assert view.poc_status=='POC_CANDIDATE' and view.cve_id==seed.vuln.canonical_id
    assert view.asset_risk_access=='AUTHENTICATED_ONLY' and view.content_trust_level=='UNTRUSTED_EXTERNAL_CONTENT'
    assert all('owner_principal' not in str(x) for x in view.model_dump(mode='json').values())

def test_asset_projection_keeps_original_risk_and_never_returns_another_owners_rows(db,seed):
    from app.assets.risk import RiskService
    from app.monitoring.views import owned_risks
    RiskService.recompute(db,seed.asset.id);db.flush()
    mine=owned_risks(db,str(seed.vuln.id),'test-analyst')
    assert mine.total==1 and mine.items[0]['priority']=='REVIEW'
    assert owned_risks(db,str(seed.vuln.id),'another-actor').items==[]

def test_monitoring_source_failure_cannot_suppress_next_source(db):
    from app.monitoring.service import MonitoringService
    from app.monitoring.catalog import validate_url
    service=MonitoringService(None,session_factory=factory(db),http=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(lambda request:httpx.Response(503) if request.url.host=='blog.trailofbits.com' else httpx.Response(200,content=b'<rss><channel/></rss>')),url_validator=validate_url),embed=Embed())
    try:
        results=service.run_once(['RSS_TRAIL_OF_BITS','RSS_GOOGLE_SECURITY'],limit=2,force=True)
        assert [x['status'] for x in results]==['failed','succeeded']
        assert db.scalar(select(func.count()).select_from(m.SyncRun))==2
    finally:service.close()

def test_collection_enqueues_existing_enrichment_jobs_without_new_agent(db):
    from app.monitoring.collectors import GitHubCollector
    from app.monitoring.service import queue_enrichment
    from app.monitoring.catalog import validate_url
    native=ghsa()
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(lambda request:httpx.Response(200,json=[native] if request.url.path=='/advisories' else native)),url_validator=validate_url)
    try:
        result=SyncService(None,session_factory=factory(db)).sync(GitHubCollector(client,bootstrap_ids=[]),1)
        jobs=queue_enrichment(factory(db),[result])
        assert len(jobs)==6 and {j['kind'] for j in jobs}=={'vendor','epss','kev','poc','patch','version'}
        assert queue_enrichment(factory(db),[result])==[]
        assert db.scalar(select(func.count()).select_from(m.AgentRun))==0
    finally:client.close()

def test_304_reuses_matching_raw_and_does_not_erase_documents(db):
    from app.monitoring.knowledge import FeedSyncService
    from app.monitoring.catalog import validate_url
    body=b'<rss><channel><item><guid>cached-one</guid><title>AI security</title><link>https://blog.trailofbits.com/cache/</link><description>Cached untrusted article.</description></item></channel></rss>'
    responses=iter([httpx.Response(200,content=body,headers={'etag':'"cache-fixture"'}),httpx.Response(304)])
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(lambda request:next(responses)),url_validator=validate_url)
    try:
        service=FeedSyncService(factory(db),http=client,embed=Embed())
        assert service.sync('RSS_TRAIL_OF_BITS')['created']==1
        assert service.sync('RSS_TRAIL_OF_BITS')['skipped']==1
        assert db.scalar(select(func.count()).select_from(m.RawDocument))==1
        assert db.scalar(select(func.count()).select_from(m.KnowledgeDocument))==1
    finally:client.close()

def test_unchanged_source_revision_can_refresh_aged_enrichment_jobs(db):
    from datetime import timedelta
    from app.monitoring.collectors import GitHubCollector
    from app.monitoring.service import queue_enrichment
    from app.monitoring.catalog import validate_url
    from app.utils.time import utcnow
    native=ghsa()
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(lambda r:httpx.Response(200,json=[native] if r.url.path=='/advisories' else native)),url_validator=validate_url)
    try:
        sync=SyncService(None,session_factory=factory(db));collector=GitHubCollector(client,bootstrap_ids=[])
        first=sync.sync(collector,1);assert len(queue_enrichment(factory(db),[first]))==6
        for job in db.scalars(select(m.EnrichmentJob)):
            job.status='no_result';job.scheduled_at=utcnow()-timedelta(days=3);job.started_at=utcnow()-timedelta(days=3);job.finished_at=utcnow()-timedelta(days=2)
        db.flush()
        replay=sync.sync(collector,1);assert replay['skipped']==1
        assert len(queue_enrichment(factory(db),[replay]))==6
    finally:client.close()

def test_explicit_patch_release_survives_inclusive_affected_boundary(db):
    from app.monitoring.collectors import GitHubCollector
    from app.monitoring.views import vulnerability_view
    from app.monitoring.catalog import validate_url
    native=ghsa();native['vulnerabilities'][0]['vulnerable_version_range']='<= 0.6.0'
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(lambda r:httpx.Response(200,json=[native] if r.url.path=='/advisories' else native)),url_validator=validate_url)
    try:
        SyncService(None,session_factory=factory(db)).sync(GitHubCollector(client,bootstrap_ids=[]),1)
        target=db.scalar(select(m.Vulnerability).where(m.Vulnerability.canonical_id==native['cve_id']))
        fixes=vulnerability_view(db,target.id).fixed_versions
        assert any(x['version']=='0.6.1' and x['source']=='GHSA' and x['package']['name']=='vllm' for x in fixes)
        assert all(x['raw_document_id'] and x['locator'] for x in fixes)
    finally:client.close()

@pytest.mark.parametrize('source,ids',[('RSS_TRAIL_OF_BITS',('same-guid','same-guid')),('ARXIV',('http://arxiv.org/abs/2601.12345v2','http://arxiv.org/abs/2601.12345v3'))])
def test_corrected_feed_keeps_history_but_searches_only_current_edition(db,source,ids):
    from app.monitoring.knowledge import FeedSyncService
    from app.monitoring.catalog import validate_url
    from app.monitoring.views import document_view,intelligence_page
    from app.knowledge.retrieval import SemanticSearch
    class SearchEmbed(Embed):
        def query(self,q):return [1.0,0.0]
    def payload(identifier,title):
        if source=='ARXIV':return f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>{identifier}</id><title>{title}</title><summary>Source revision</summary><link rel="alternate" href="{identifier.replace("http:","https:")}"/></entry></feed>'.encode()
        return f'<rss><channel><item><guid>{identifier}</guid><title>{title}</title><link>https://blog.trailofbits.com/revision/</link><description>Source revision</description></item></channel></rss>'.encode()
    responses=iter([httpx.Response(200,content=payload(ids[0],'AI obsolete assertion'),headers={'etag':'"old"'}),httpx.Response(200,content=payload(ids[1],'AI corrected assertion'))])
    requests=[]
    def get(r):requests.append(r);return next(responses)
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(get),url_validator=validate_url)
    try:
        service=FeedSyncService(factory(db),http=client,embed=SearchEmbed())
        assert service.sync(source,1)['created']==1
        assert service.sync(source,2)['created']==1
        docs=list(db.scalars(select(m.KnowledgeDocument).order_by(m.KnowledgeDocument.created_at)))
        assert len(docs)==2
        assert intelligence_page(db,kind='paper' if source=='ARXIV' else 'blog').total==1
        results=SemanticSearch.search(db,'AI',SearchEmbed())
        assert len(results)==1 and results[0]['title']=='AI corrected assertion'
        assert document_view(db,docs[0].id).publication_status=='SUPERSEDED'
        cached=db.scalar(select(m.Source).where(m.Source.source_key==source)).checkpoint
        assert cached['etag'] is None
        if source=='ARXIV':assert requests[1].headers.get('if-none-match') is None
    finally:client.close()

def test_historical_human_exploit_result_is_not_a_current_confirmation(db,seed):
    from app.monitoring.views import has_verified_exploit
    seed.poc.status='confirmed';seed.poc.usability_status='verified_usable'
    seed.claim.range_id=None;seed.claim.poc_candidate_id=seed.poc.id;seed.claim.adopted=True;seed.claim.verification_status='confirmed';seed.claim.revision=2
    result=m.VerificationResult(claim_id=seed.claim.id,claim_revision=1,decision_key='SYNTHETIC-old',status='confirmed',verification_method='human',reason_summary='SYNTHETIC old revision',verified_at=seed.raws[0].retrieved_at,verified_by_type='human',verified_by_id='SYNTHETIC-reviewer')
    db.add(result);db.flush()
    base=seed.evidence[0]
    evidence=m.Evidence(claim_id=seed.claim.id,source_id=base.source_id,raw_document_id=base.raw_document_id,observation_id=base.observation_id,
        scope_key=base.scope_key,evidence_type='SYNTHETIC-validation',stance='support',excerpt=base.excerpt,excerpt_hash=base.excerpt_hash,
        source_url=base.source_url,published_at=base.published_at,retrieved_at=base.retrieved_at,locator=base.locator,locator_key='SYNTHETIC-validated',
        observed_value=base.observed_value,publisher=base.publisher,lineage_key=base.lineage_key,details={'validated_exploit':True})
    db.add(evidence);db.flush()
    db.add(m.VerificationEvidence(verification_result_id=result.id,claim_id=seed.claim.id,evidence_id=evidence.id));db.flush()
    assert has_verified_exploit(db,seed.poc) is False

def test_asset_projection_paginates_beyond_one_hundred_owned_assets(db,seed,monkeypatch):
    from app.assets.risk import RiskService
    from app.monitoring.views import owned_risks
    from app.assets import queries as assets
    RiskService.recompute(db,seed.asset.id);db.flush()
    original=db.scalar(select(m.AssetRiskSnapshot).where(m.AssetRiskSnapshot.asset_id==seed.asset.id))
    for i in range(100):
        asset=m.Asset(name='SYNTHETIC pagination '+str(i),asset_type='service',owner_principal='test-analyst',is_demo=True)
        db.add(asset);db.flush()
        db.add(m.AssetRiskSnapshot(asset_id=asset.id,component_id=original.component_id,vulnerability_id=seed.vuln.id,match_id=original.match_id,
            snapshot_key='SYNTHETIC-page-'+str(i),match_status=original.match_status,priority='REVIEW',inventory_revision=1,intelligence_fingerprint=original.intelligence_fingerprint,payload={}))
    db.flush()
    monkeypatch.setattr(assets,'latest_risks',lambda s,id,actor:[{'vulnerability_id':str(seed.vuln.id),'asset_id':str(id),'component_id':str(original.component_id),'priority':'REVIEW'}])
    page=owned_risks(db,seed.vuln.id,'test-analyst',offset=100,limit=20)
    assert page.total==101 and len(page.items)==1

def test_feed_source_can_return_to_previous_text_without_losing_revision_history(db):
    from app.monitoring.knowledge import FeedSyncService
    from app.monitoring.catalog import validate_url
    from app.monitoring.views import intelligence_page
    def body(title):return f'<rss><channel><item><guid>rollback-guid</guid><title>{title}</title><link>https://blog.trailofbits.com/rollback/</link><description>AI security source</description></item></channel></rss>'.encode()
    responses=iter([httpx.Response(200,content=body(title)) for title in ['AI first edition','AI second edition','AI first edition']])
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(lambda r:next(responses)),url_validator=validate_url)
    try:
        service=FeedSyncService(factory(db),http=client,embed=Embed())
        for i in range(3):assert service.sync('RSS_TRAIL_OF_BITS')['created']==1
        assert db.scalar(select(func.count()).select_from(m.KnowledgeDocument))==3
        view=intelligence_page(db,kind='blog');assert view.total==1 and view.items[0].title=='AI first edition'
    finally:client.close()

def test_same_feed_bytes_at_different_query_urls_keep_a_valid_304_cache(db):
    from app.monitoring.knowledge import FeedSyncService
    from app.monitoring.catalog import validate_url
    body=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2601.11111v1</id><title>AI security</title><summary>TEST ONLY</summary></entry></feed>'
    responses=iter([httpx.Response(200,content=body,headers={'etag':'"same"'}),httpx.Response(200,content=body,headers={'etag':'"same"'}),httpx.Response(304)])
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(lambda r:next(responses)),url_validator=validate_url)
    try:
        service=FeedSyncService(factory(db),http=client,embed=Embed())
        assert service.sync('ARXIV',1)['created']==1
        assert service.sync('ARXIV',2)['skipped']==1
        assert service.sync('ARXIV',2)['status']=='succeeded'
        assert db.scalar(select(func.count()).select_from(m.RawDocument))==2
    finally:client.close()

def test_only_current_human_validated_exploit_projects_verified(db,seed):
    from app.monitoring.views import has_verified_exploit
    from app.utils.time import utcnow
    seed.poc.status='confirmed';seed.poc.usability_status='verified_usable'
    value={'url':seed.poc.url,'usability':'verified_usable'}
    claim=m.Claim(claim_key='SYNTHETIC-validated-poc',vulnerability_id=seed.vuln.id,poc_candidate_id=seed.poc.id,
        claim_type='POC_USABILITY',predicate='POC_USABILITY',value_json=value,scope_key='SYNTHETIC-poc',adopted=True,verification_status='confirmed')
    db.add(claim);db.flush()
    base=seed.evidence[0]
    evidence=m.Evidence(claim_id=claim.id,source_id=base.source_id,raw_document_id=base.raw_document_id,observation_id=base.observation_id,
        scope_key=claim.scope_key,evidence_type='SYNTHETIC-validation',stance='support',excerpt=base.excerpt,excerpt_hash=base.excerpt_hash,
        source_url=base.source_url,published_at=base.published_at,retrieved_at=base.retrieved_at,locator=base.locator,locator_key='SYNTHETIC-validation',
        observed_value=value,publisher=base.publisher,lineage_key=base.lineage_key,details={'validated_exploit':True})
    db.add(evidence);db.flush()
    result=m.VerificationResult(claim_id=claim.id,claim_revision=claim.revision,decision_key='SYNTHETIC-validation',status='confirmed',
        verification_method='human',reason_summary='SYNTHETIC validation',verified_at=utcnow(),verified_by_type='human',verified_by_id='SYNTHETIC-reviewer')
    db.add(result);db.flush()
    db.add(m.VerificationEvidence(verification_result_id=result.id,claim_id=claim.id,evidence_id=evidence.id));db.flush()
    assert has_verified_exploit(db,seed.poc) is True
    claim.verification_status='pending';db.flush()
    assert has_verified_exploit(db,seed.poc) is False

def test_public_intelligence_does_not_disclose_asset_scoped_evidence(db,seed):
    from app.monitoring.views import vulnerability_view
    seed.claim.range_id=None;seed.claim.asset_component_id=seed.component.id;db.flush()
    assert vulnerability_view(db,seed.vuln.id).evidence==[]

def test_native_source_catalog_restores_adapter_metadata_without_touching_legacy_sources(db):
    from app.repositories.sources import source_registry
    source=source_registry(db,'VENDOR_VLLM');source.authority_scope='SYNTHETIC obsolete adapter metadata';db.flush()
    refreshed=source_registry(db,'VENDOR_VLLM')
    assert refreshed.authority_scope=='vllm-project/vllm'
    legacy=source_registry(db,'OSV');original=legacy.authority_scope;source_registry(db,'OSV')
    assert legacy.authority_scope==original

def test_native_monitoring_bridges_explicit_cvss_facts_to_existing_evidence_tools(db):
    from app.monitoring.service import MonitoringService
    from app.monitoring.catalog import validate_url
    def response(request):
        identifier=request.url.params['cveId']
        return httpx.Response(200,json={'vulnerabilities':[{'cve':{'id':identifier,'published':'2026-10-13T00:00:00.000',
            'lastModified':'2026-10-14T00:00:00.000','vulnStatus':'Analyzed','descriptions':[{'lang':'en','value':'TEST ONLY AI component'}],
            'metrics':{'cvssMetricV31':[{'source':'nvd@nist.gov','cvssData':{'version':'3.1','vectorString':'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H','baseScore':9.8,'baseSeverity':'CRITICAL'}}]}}}]})
    service=MonitoringService(None,session_factory=factory(db),http=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(response),url_validator=validate_url))
    try:
        first=service.run_once(['NVD'],limit=1,force=True)[0]
        assert first['source_fact_bridge']['evidence_count']==1
        claim=db.scalar(select(m.Claim).where(m.Claim.claim_type=='CVSS_SCORE'))
        assert claim.value_json['score']==9.8 and claim.adopted is False and claim.verification_status=='pending'
        evidence=db.scalar(select(m.Evidence).where(m.Evidence.claim_id==claim.id))
        assert evidence.locator['json_pointer'].startswith('/vulnerabilities/0/cve/metrics/')
        assert db.get(m.SourceObservation,evidence.observation_id).parse_status=='parsed'
        from app.monitoring.facts import bridge_source_facts
        bridge_source_facts(factory(db),first)
        assert db.scalar(select(func.count()).select_from(m.Evidence))==1
    finally:service.close()

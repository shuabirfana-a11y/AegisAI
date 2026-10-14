"""Synthetic source transports; actual DB/domain pipeline, never business accuracy."""
import importlib
from contextlib import contextmanager
from threading import Event
import httpx
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.db import models as m
from app.core.http import HttpClient
from app.core.config import Settings
from app.monitoring.catalog import validate_url
from app.monitoring.service import MonitoringService
from test_phase14_sources import ghsa
from test_phase14_storage import factory,Embed


def module():
    try:return importlib.import_module('app.monitoring.pipeline')
    except ModuleNotFoundError:pytest.fail('Bounded monitoring pipeline is not implemented')


def clients(db,engine, *,fail_blog=False, empty=False):
    from app.enrichment.service import EnrichmentService
    from app.enrichment.acquisition import validate_enrichment_url
    requests=[]
    native=ghsa()
    def source(req):
        requests.append(str(req.url))
        if req.url.host=='blog.trailofbits.com':
            return httpx.Response(503) if fail_blog else httpx.Response(200,content=b'<rss><channel><item><guid>synthetic-pipeline-blog</guid><title>AI security CVE-2099-9000001</title><link>https://blog.trailofbits.com/test/</link><description>TEST ONLY vllm security.</description></item></channel></rss>')
        return httpx.Response(200,json=[] if empty and req.url.path=='/advisories' else [native] if req.url.path=='/advisories' else native)
    def enrich(req):
        if '/search/' in req.url.path:return httpx.Response(200,json={'items':[],'total_count':0,'incomplete_results':False})
        if req.url.host=='api.first.org':return httpx.Response(200,json={'status':'OK','data':[],'total':0})
        if '/security-advisories/' in req.url.path:return httpx.Response(200,json=native)
        return httpx.Response(503)
    monitor=MonitoringService(engine,session_factory=factory(db),embed=Embed(),
        http=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(source),url_validator=validate_url))
    worker=EnrichmentService(factory(db),http=HttpClient(Settings(retries=0,request_interval=0),
        transport=httpx.MockTransport(enrich),url_validator=validate_enrichment_url))
    return monitor,worker,requests


def pipeline(db,engine,**options):
    cls=module();monitor,worker,requests=clients(db,engine,fail_blog=options.pop('fail_blog',False))
    config=cls.PipelineConfig(execution_mode='MOCK',**options)
    return cls.IntelligencePipeline(engine,config,monitor=monitor,worker=worker),requests


@pytest.mark.parametrize('kwargs',[{'job_budget':21},{'record_limit':0},{'target_budget':0},
    {'cycle_seconds':float('nan')},{'execution_mode':'fake'},{'asset_budget':101}])
def test_configuration_is_bounded_before_network(kwargs):
    with pytest.raises(ValueError):module().PipelineConfig(**kwargs)


def test_registry_covers_existing_categories_without_automatic_mock_fallback():
    from app.monitoring.framework import CollectorRegistry
    reg=CollectorRegistry()
    assert {'NVD','GHSA','VENDOR_VLLM','RSS_TRAIL_OF_BITS','ARXIV'}<=set(reg.keys())
    assert {reg.describe(k).category for k in reg.keys()}>={'vulnerability_database','security_community','vendor_advisory','blog','paper'}
    with pytest.raises(ValueError):reg.describe('UNKNOWN_SOURCE')


@pytest.mark.parametrize('source_key',['NVD','GHSA','VENDOR_VLLM','RSS_TRAIL_OF_BITS','ARXIV'])
def test_existing_adapters_normalize_each_source_category_without_mock_fallback(db,engine,source_key):
    from app.monitoring.framework import CollectorFramework
    native=ghsa()
    def respond(req):
        if req.url.host=='services.nvd.nist.gov':
            cve={'id':req.url.params['cveId'],'published':'2026-10-13T00:00:00.000',
                'lastModified':'2026-10-14T00:00:00.000','vulnStatus':'Analyzed',
                'descriptions':[{'lang':'en','value':'SYNTHETIC vLLM AI security advisory'}],
                'references':[{'url':'https://github.com/vllm-project/vllm/security/advisories/GHSA-abcd-efgh-ijkl'}]}
            return httpx.Response(200,json={'vulnerabilities':[{'cve':cve}],'totalResults':1})
        if req.url.host=='export.arxiv.org':
            return httpx.Response(200,content=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2601.12345v2</id><title>SYNTHETIC AI security</title><summary>Synthetic research abstract</summary><published>2026-01-20T00:00:00Z</published><link rel="alternate" href="https://arxiv.org/abs/2601.12345v2"/></entry></feed>')
        if req.url.host=='blog.trailofbits.com':
            return httpx.Response(200,content=b'<rss><channel><item><guid>synthetic-category</guid><title>SYNTHETIC AI security</title><link>https://blog.trailofbits.com/test/</link><description>vllm security</description></item></channel></rss>')
        return httpx.Response(200,json=[native] if req.url.path.endswith('/advisories') or req.url.path.endswith('/security-advisories') else native)
    monitor=MonitoringService(engine,session_factory=factory(db),embed=Embed(),
        http=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(respond),url_validator=validate_url))
    try:receipt=CollectorFramework(monitor,execution_mode='MOCK').collect(source_key,limit=1,force=True)
    finally:monitor.close()
    assert receipt.status in ('SUCCESS','PARTIAL') and receipt.sync_run_id
    assert receipt.targets or receipt.document_ids
    run=db.get(m.SyncRun,receipt.sync_run_id)
    assert db.scalar(select(func.count()).select_from(m.SourceObservation).where(m.SourceObservation.sync_run_id==run.id))>0


def test_pipeline_collects_normalizes_enriches_and_retains_original_verification(db,engine):
    p,requests=pipeline(db,engine,job_budget=6)
    try:receipt=p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    assert receipt.execution_mode=='MOCK' and receipt.processed_jobs==6
    target=db.scalar(select(m.Vulnerability).where(m.Vulnerability.canonical_id==ghsa()['cve_id']))
    assert target is not None and db.scalar(select(func.count()).select_from(m.Evidence))>0
    assert db.scalar(select(func.count()).select_from(m.VerificationResult))>0
    assert db.scalar(select(func.count()).select_from(m.AgentRun))==0
    run=db.get(m.SyncRun,receipt.sources[0].sync_run_id)
    assert run.details['pipeline_v1']['execution_mode']=='MOCK'
    from app.monitoring.lifecycle import record_view
    record=record_view(db,'vulnerability',target.id)
    assert record.status=='AVAILABLE' and record.query_available
    assert record.verification_status!='CONFIRMED'  # Candidate/insufficient claims remain unconfirmed.
    assert requests


def test_failure_is_durable_and_cannot_suppress_other_sources(db,engine):
    p,_=pipeline(db,engine,job_budget=0,fail_blog=True)
    try:receipt=p.run_cycle(['RSS_TRAIL_OF_BITS','GHSA'],force=True)
    finally:p.close()
    assert receipt.sources[0].status=='FAILED' and receipt.sources[1].status in ('SUCCESS','PARTIAL')
    assert receipt.status=='PARTIAL'
    assert db.scalar(select(func.count()).select_from(m.SyncRun))==2
    assert any(run.details.get('pipeline_v1') for run in db.scalars(select(m.SyncRun)))


def test_batch_does_not_drain_an_unrelated_enrichment_job(db,engine,seed):
    from uuid import uuid4
    from app.utils.time import utcnow
    other=m.EnrichmentJob(vulnerability_id=seed.vuln.id,enrichment_type='poc',status='queued',
        scheduled_at=utcnow(),trace_id=str(uuid4()))
    db.add(other);db.flush()
    p,_=pipeline(db,engine,job_budget=1)
    try:p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    db.refresh(other);assert other.status=='queued'


def test_not_due_cycle_resumes_its_backlog_without_refetching(db,engine):
    p,requests=pipeline(db,engine,job_budget=1)
    try:
        first=p.run_cycle(['GHSA'],force=True);calls=len(requests)
        second=p.run_cycle(['GHSA'])
    finally:p.close()
    assert first.processed_jobs==second.processed_jobs==1
    assert second.sources[0].status=='NOT_DUE' and len(requests)==calls
    assert db.scalar(select(func.count()).select_from(m.SyncRun))==1


def test_disabled_source_is_not_reenabled_by_scheduling(db,engine):
    p,requests=pipeline(db,engine,job_budget=0)
    try:
        p.run_cycle(['GHSA'],force=True)
        source=db.scalar(select(m.Source).where(m.Source.source_key=='GHSA'));source.enabled=False;db.flush()
        calls=len(requests);result=p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    assert result.sources[0].status=='DISABLED' and len(requests)==calls
    assert source.enabled is False


def test_stopped_cycle_does_not_fetch_or_drain_jobs(db,engine):
    p,requests=pipeline(db,engine);stop=Event();stop.set()
    try:receipt=p.run_cycle(['GHSA'],stop=stop)
    finally:p.close()
    assert receipt.status=='CANCELLED' and requests==[]
    assert db.scalar(select(func.count()).select_from(m.SyncRun))==0


def test_mock_is_rejected_for_a_development_database_before_any_work():
    from types import SimpleNamespace
    with pytest.raises(ValueError):
        module().IntelligencePipeline(SimpleNamespace(url=SimpleNamespace(database='aegisai_development')),
            module().PipelineConfig(execution_mode='MOCK'))


def test_scheduler_stop_prevents_extra_cycles_and_does_not_force_every_refresh():
    from app.monitoring.scheduler import MonitoringScheduler
    calls=[];stop=Event()
    class Runner:
        def run_cycle(self,keys,*,force,stop):
            calls.append(force)
            if len(calls)==2:stop.set()
            return 'SYNTHETIC'
    waits=[]
    def wait(seconds):waits.append(seconds);return stop.is_set()
    out=list(MonitoringScheduler(Runner(),interval=3).run(['GHSA'],cycles=10,force_first=True,stop=stop,wait=wait))
    assert calls==[True,False] and len(out)==2 and waits==[3]


def test_record_http_is_read_only_and_contains_actual_progress_without_owner_details(db,engine):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.api.dependencies import get_session
    p,_=pipeline(db,engine,job_budget=1)
    try:p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    app=create_app(engine);app.dependency_overrides[get_session]=lambda:db
    client=TestClient(app)
    page=client.get('/api/v1/intelligence/records')
    assert page.status_code==200 and page.json()['items'][0]['status']=='ENRICHING'
    assert page.json()['items'][0]['execution_mode']=='MOCK'
    runs=client.get('/api/v1/intelligence/monitoring/runs')
    assert runs.status_code==200 and runs.json()['items'][0]['processed_jobs']==1
    assert 'owner_principal' not in runs.text and 'database_url' not in runs.text
    assert client.post('/api/v1/intelligence/monitoring/runs').status_code==405
    assert client.get('/api/v1/intelligence/records?limit=101').status_code==422


def test_pipeline_openapi_is_typed_and_keeps_availability_distinct_from_verification():
    from app.main import create_app
    schema=create_app().openapi()
    assert '/api/v1/intelligence/records' in schema['paths']
    dto=schema['components']['schemas']['IntelligenceRecord']
    assert {'status','verification_status','execution_mode','enrichment_progress','query_available'}<=set(dto['properties'])
    assert {'DISCOVERED','NORMALIZED','ENRICHING','VERIFIED','AVAILABLE'}<=set(dto['properties']['status']['enum'])


def test_pending_jobs_are_partial_progress_instead_of_fake_full_completion(db,engine):
    p,_=pipeline(db,engine,job_budget=1)
    try:receipt=p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    assert receipt.pending_jobs>0 and receipt.status=='PARTIAL'


def test_capture_mode_is_not_relabelled_when_resumed_in_another_mode(db,engine):
    p,_=pipeline(db,engine,job_budget=0)
    try:
        first=p.run_cycle(['GHSA'],force=True)
        p.config=p.config.model_copy(update={'execution_mode':'LIVE'})
        p.framework.execution_mode='LIVE'
        second=p.run_cycle(['GHSA'])
    finally:p.close()
    run=db.get(m.SyncRun,first.sources[0].sync_run_id);db.refresh(run)
    assert run.details['pipeline_v1']['execution_mode']=='MOCK'
    assert second.processed_jobs==0 and second.sources[0].status=='DEFERRED'


def test_failed_capture_remains_failed_and_keeps_error_on_not_due_cycle(db,engine):
    p,_=pipeline(db,engine,job_budget=0,fail_blog=True)
    try:
        first=p.run_cycle(['RSS_TRAIL_OF_BITS'],force=True)
        second=p.run_cycle(['RSS_TRAIL_OF_BITS'])
    finally:p.close()
    run=db.get(m.SyncRun,first.sources[0].sync_run_id);db.refresh(run)
    assert second.status=='FAILED'
    assert run.details['pipeline_v1']['status']=='FAILED'
    assert run.details['pipeline_v1']['errors']


def test_fresh_source_run_does_not_strand_previous_unfinished_scope(db,engine,seed,monkeypatch):
    from uuid import uuid4
    from app.utils.time import utcnow
    from app.monitoring.automation_schemas import SourceReceipt
    p,_=pipeline(db,engine,job_budget=0)
    try:
        first=p.run_cycle(['GHSA'],force=True)
        target=first.sources[0].targets[0]
        source=db.scalar(select(m.Source).where(m.Source.source_key=='GHSA'))
        new=m.SyncRun(source_id=source.id,status='succeeded',started_at=utcnow(),finished_at=utcnow(),details={})
        db.add(new);db.flush()
        monkeypatch.setattr(p.framework,'collect',lambda *a,**k:SourceReceipt(source='GHSA',status='SUCCESS',sync_run_id=new.id,targets=(seed.vuln.id,)))
        p.config=p.config.model_copy(update={'job_budget':20})
        second=p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    assert db.scalar(select(func.count()).select_from(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==target,m.EnrichmentJob.status=='queued'))==0
    assert second.backlog_runs>=1
    db.refresh(new);assert new.details['pipeline_v1']['target_ids']==[str(seed.vuln.id)]


def test_bounded_backlog_cursor_reaches_later_work_past_stalled_duplicate_captures(db,engine,seed):
    from datetime import timedelta
    from app.utils.time import utcnow
    from app.monitoring.automation_schemas import SourceReceipt
    import copy,time
    p,_=pipeline(db,engine,job_budget=0)
    try:
        first=p.run_cycle(['GHSA'],force=True)
        original=db.get(m.SyncRun,first.sources[0].sync_run_id)
        base=utcnow()-timedelta(days=1)
        for index in range(101):
            metadata=copy.deepcopy(original.details)
            if index==100:metadata['pipeline_v1']['target_ids']=[str(seed.vuln.id)]
            db.add(m.SyncRun(source_id=original.source_id,status='succeeded',started_at=base+timedelta(seconds=index),
                finished_at=base+timedelta(seconds=index),details=metadata))
        db.flush();receipts=[SourceReceipt(source='GHSA',status='NOT_DUE')]
        first_scan=p._backlog(receipts,time.monotonic()+60,Event())
        second_scan=p._backlog(receipts,time.monotonic()+60,Event())
    finally:p.close()
    assert first_scan[2] and seed.vuln.id not in {t for r in first_scan[0] for t in r.targets}
    assert seed.vuln.id in {t for r in second_scan[0] for t in r.targets}


def test_running_only_targets_do_not_consume_runnable_backlog_budget(db,engine,seed):
    import time
    from app.utils.time import utcnow
    from app.monitoring.automation_schemas import SourceReceipt
    p,_=pipeline(db,engine,job_budget=0,target_budget=1)
    try:
        first=p.run_cycle(['GHSA'],force=True);target=first.sources[0].targets[0]
        for job in db.scalars(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==target)):
            job.started_at=utcnow();job.status='running' if job.enrichment_type=='vendor' else 'success'
            job.finished_at=None if job.status=='running' else utcnow()
        run=db.get(m.SyncRun,first.sources[0].sync_run_id)
        run.details={**run.details,'pipeline_v1':{**run.details['pipeline_v1'],'target_ids':[str(target),str(seed.vuln.id)]}}
        db.flush()
        rows,_,_=p._backlog([SourceReceipt(source='GHSA',status='NOT_DUE')],time.monotonic()+60,Event())
    finally:p.close()
    assert seed.vuln.id in {t for r in rows for t in r.targets}
    assert target not in {t for r in rows for t in r.targets}


def test_interrupt_retains_terminal_pipeline_receipt_without_rewriting_original_job(db,engine,monkeypatch):
    p,_=pipeline(db,engine,job_budget=1)
    def interrupt(*a,**k):raise KeyboardInterrupt()
    monkeypatch.setattr(p.worker,'run',interrupt)
    try:receipt=p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    assert receipt.status=='CANCELLED'
    run=db.get(m.SyncRun,receipt.sources[0].sync_run_id);db.refresh(run)
    assert run.details['pipeline_v1']['status']=='CANCELLED'
    assert run.status in ('succeeded','partial')  # Original collector outcome is preserved.


def test_failed_dependency_cannot_be_reported_as_pipeline_success(db,engine,monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4
    p,_=pipeline(db,engine,job_budget=6)
    original=p.worker.run
    def dependency(*a,**k):
        return [*original(*a,**k),SimpleNamespace(task_id=uuid4(),status='FAILED')]
    monkeypatch.setattr(p.worker,'run',dependency)
    try:receipt=p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    assert receipt.failed_dependency_jobs>=1 and receipt.status=='PARTIAL'


def test_expired_budget_does_not_start_new_queue_work(db,engine,monkeypatch):
    from app.monitoring.automation_schemas import SourceReceipt
    p,_=pipeline(db,engine,job_budget=0,cycle_seconds=1)
    clock=[0]
    monkeypatch.setattr(module().time,'monotonic',lambda:clock[0])
    def collect(*a,**k):clock[0]=2;return SourceReceipt(source='GHSA',status='SUCCESS')
    monkeypatch.setattr(p.framework,'collect',collect)
    monkeypatch.setattr(p,'_queue',lambda targets:pytest.fail('New work started after deadline'))
    try:receipt=p.run_cycle(['GHSA'])
    finally:p.close()
    assert receipt.status=='PARTIAL' and receipt.queued_jobs==0


def test_backlog_scan_exhausting_budget_cannot_start_queue(db,engine,monkeypatch):
    from app.monitoring.automation_schemas import SourceReceipt
    p,_=pipeline(db,engine,job_budget=0,cycle_seconds=1);clock=[0]
    monkeypatch.setattr(module().time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(p.framework,'collect',lambda *a,**k:SourceReceipt(source='GHSA',status='SUCCESS'))
    def backlog(*a,**k):clock[0]=2;return [],0,False
    monkeypatch.setattr(p,'_backlog',backlog)
    monkeypatch.setattr(p,'_queue',lambda targets:pytest.fail('Queue started after backlog used deadline'))
    try:receipt=p.run_cycle(['GHSA'])
    finally:p.close()
    assert receipt.status=='PARTIAL' and receipt.queued_jobs==0


def test_interrupt_after_collection_retains_real_target_scope(db,engine,monkeypatch):
    p,_=pipeline(db,engine,job_budget=0);original=p.framework.collect
    def interrupted(*a,**k):original(*a,**k);raise KeyboardInterrupt()
    monkeypatch.setattr(p.framework,'collect',interrupted)
    try:receipt=p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    assert receipt.status=='CANCELLED' and receipt.sources[0].targets
    run=db.get(m.SyncRun,receipt.sources[0].sync_run_id);db.refresh(run)
    assert run.details['pipeline_v1']['target_ids'] and run.details['pipeline_v1']['backlog_open']


def test_guard_invalidates_on_uncertain_acquisition_commit():
    from types import SimpleNamespace
    events=[]
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def execute(self,*a,**k):events.append('execute');return SimpleNamespace(scalar=lambda:True)
        def commit(self):raise RuntimeError('SYNTHETIC commit failure')
        def invalidate(self):events.append('invalidate')
    with pytest.raises(RuntimeError):
        with module().cycle_guard(SimpleNamespace(connect=lambda:Connection())):pytest.fail('Acquisition should fail')
    assert 'invalidate' in events


def test_record_observed_at_is_stored_time_instead_of_read_time(db,engine):
    from app.monitoring.lifecycle import record_view
    p,_=pipeline(db,engine,job_budget=0)
    try:receipt=p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    target=receipt.sources[0].targets[0]
    first=record_view(db,'vulnerability',target);second=record_view(db,'vulnerability',target)
    assert first.observed_at==second.observed_at


def test_unchanged_feed_receipt_uses_selected_entry_identity_not_snapshot_raw_id(db,engine):
    from app.monitoring.framework import CollectorFramework
    def body(label):
        return ('<rss><channel><item><guid>A</guid><title>AI security A</title><link>https://blog.trailofbits.com/a/</link><description>same A</description></item>'
            '<item><guid>B</guid><title>AI security B</title><link>https://blog.trailofbits.com/b/</link><description>'+label+'</description></item></channel></rss>').encode()
    current=[body('first B')]
    monitor=MonitoringService(engine,session_factory=factory(db),embed=Embed(),http=HttpClient(Settings(retries=0,request_interval=0),
        transport=httpx.MockTransport(lambda req:httpx.Response(200,content=current[0])),url_validator=validate_url))
    frame=CollectorFramework(monitor,execution_mode='MOCK')
    try:
        frame.collect('RSS_TRAIL_OF_BITS',limit=2,force=True)
        current[0]=body('changed B');frame.collect('RSS_TRAIL_OF_BITS',limit=2,force=True)
        selected=frame.collect('RSS_TRAIL_OF_BITS',limit=1,force=True)
    finally:monitor.close()
    expected=db.scalar(select(m.KnowledgeDocument.id).where(m.KnowledgeDocument.external_id=='A',m.KnowledgeDocument.deleted_at.is_(None)))
    assert selected.document_ids==(expected,)


def test_database_guard_refuses_a_second_process_cycle(db,engine):
    from sqlalchemy import text
    from app.monitoring.pipeline import LOCK_KEY
    p,requests=pipeline(db,engine)
    with engine.connect() as blocker:
        blocker.execute(text('SELECT pg_advisory_lock(hashtextextended(:key,14))'),{'key':LOCK_KEY});blocker.commit()
        try:receipt=p.run_cycle(['GHSA'],force=True)
        finally:
            blocker.execute(text('SELECT pg_advisory_unlock(hashtextextended(:key,14))'),{'key':LOCK_KEY});blocker.commit();p.close()
    assert receipt.status=='BUSY' and requests==[]


def test_optional_inventory_recompute_uses_existing_worker_and_owner_scope(db,engine,seed):
    from app.db.models.application import Asset,AssetComponent
    other=Asset(name='SYNTHETIC other inventory',asset_type='service',owner_principal='another-owner',is_demo=True)
    db.add(other);db.flush()
    db.add(AssetComponent(asset_id=other.id,product_id=seed.products[0].id,package_identifier_id=seed.packages[0].id,
        version='0.6.0',identity_status='confirmed'));db.flush()
    p,_=pipeline(db,engine,job_budget=6);p.asset_owner='test-analyst'
    try:receipt=p.run_cycle(['GHSA'],force=True)
    finally:p.close()
    assert receipt.asset_jobs==1 and receipt.failed_asset_jobs==0
    jobs=list(db.scalars(select(m.AssetRecomputeJob)))
    assert jobs and all(j.asset_id==seed.asset.id for j in jobs)
    assert 'test-analyst' not in str(db.scalar(select(m.SyncRun)).details)


@pytest.mark.parametrize('value',['nan','inf','0','3601'])
def test_invalid_pipeline_deadline_is_rejected_before_db_or_http(value,monkeypatch):
    from app.monitoring.cli import main
    monkeypatch.delenv('AEGIS_DATABASE_URL',raising=False)
    with pytest.raises(SystemExit) as e:main(['--source','NVD','--pipeline','--cycle-seconds',value])
    assert e.value.code==2


@pytest.mark.parametrize('extra,expected',[([],6),(['--process-enrichment','0'],0),(['--process-enrichment','2'],2)])
def test_pipeline_cli_preserves_explicit_zero_budget(extra,expected,monkeypatch):
    from types import SimpleNamespace
    from app.monitoring import cli,automation_cli
    seen=[]
    monkeypatch.setattr(cli,'make_engine',lambda:SimpleNamespace(dispose=lambda:None))
    monkeypatch.setattr(cli,'MonitoringService',lambda e:SimpleNamespace(close=lambda:None))
    monkeypatch.setattr(automation_cli,'run_automation',lambda e,s,a:seen.append(a.process_enrichment) or True)
    cli.main(['--source','NVD','--pipeline',*extra])
    assert seen==[expected]


def test_automation_adapter_does_not_replace_zero_with_six(monkeypatch):
    from types import SimpleNamespace
    from app.monitoring import automation_cli
    seen=[]
    def create(engine,config,**k):
        seen.append(config.job_budget);return SimpleNamespace(worker=SimpleNamespace(http=SimpleNamespace(close=lambda:None)))
    monkeypatch.setattr(automation_cli,'IntelligencePipeline',create)
    monkeypatch.setattr(automation_cli,'MonitoringScheduler',lambda *a,**k:SimpleNamespace(run=lambda *a,**k:[]))
    args=SimpleNamespace(limit=1,process_enrichment=0,cycle_seconds=300,allow_cve_bootstrap=False,interval=3,source=['NVD'],cycles=1,force=False)
    assert automation_cli.run_automation(None,None,args) is True and seen==[0]

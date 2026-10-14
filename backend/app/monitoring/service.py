from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import models as m
from app.core.http import HttpClient
from app.core.config import Settings
from app.collectors.cve import CVECollector
from app.collectors.osv import OSVCollector
from app.collectors.cisa_kev import KEVCollector
from app.services.sync import SyncService
from app.monitoring.collectors import GitHubCollector,NVDCollector
from app.monitoring.catalog import FEEDS,validate_url
from app.monitoring.knowledge import FeedSyncService
from app.enrichment.acquisition import VENDORS
from app.utils.time import utcnow

SOURCES=('CVE_LIST','OSV','CISA_KEV','NVD','GHSA',*VENDORS,*FEEDS)

def queue_enrichment(factory,results):
    """Use the original enrichment scheduler, only for collected target identities."""
    from uuid import UUID
    from app.enrichment.scheduler import schedule_due
    targets=set()
    with factory() as s:
        for result in results:
            if result.get('status') not in ('succeeded','partial') or not result.get('sync_run_id'):continue
            for row in s.scalars(select(m.SourceObservation).where(m.SourceObservation.sync_run_id==UUID(result['sync_run_id']))):
                parsed=row if row.parse_status=='parsed' else None
                if row.record_type=='fetch' and row.details.get('outcome')=='skipped':
                    parsed=s.scalar(select(m.SourceObservation).where(m.SourceObservation.source_id==row.source_id,
                        m.SourceObservation.raw_document_id==row.raw_document_id,m.SourceObservation.external_id==row.external_id,
                        m.SourceObservation.parse_status=='parsed').order_by(m.SourceObservation.created_at.desc()).limit(1))
                if parsed:targets.update(UUID(x) for x in parsed.details.get('vulnerability_ids',[]))
        jobs=schedule_due(s,sorted(targets,key=str),limit=20)
        return [{'job_id':str(j.id),'target_id':str(j.vulnerability_id),'kind':j.enrichment_type,'status':j.status} for j in jobs]

class MonitoringService:
    def __init__(self,engine,*,session_factory=None,http=None,embed=None):
        self.engine=engine
        if session_factory:self.factory=session_factory
        else:
            @contextmanager
            def session():
                with Session(engine) as s:
                    with s.begin():yield s
            self.factory=session
        self.http=http or HttpClient(Settings(http_timeout=15,retries=1,request_interval=6,max_bytes=2_000_000),url_validator=validate_url)
        self.embed=embed
    def close(self):self.http.close()
    def run_once(self,sources=None,*,limit=10,force=False):
        if not 1<=limit<=100:raise ValueError('Monitoring limit must be 1..100')
        sources=list(sources or SOURCES)
        if any(key not in SOURCES for key in sources):raise ValueError('Unregistered monitoring source')
        results=[]
        for key in sources:
            with self.factory() as s:
                source=s.scalar(select(m.Source).where(m.Source.source_key==key))
                if not force and source and source.last_sync_at and (utcnow()-source.last_sync_at).total_seconds()<source.update_interval:
                    results.append({'source':key,'status':'not_due'});continue
            try:
                if key in FEEDS:result=FeedSyncService(self.factory,http=self.http,embed=self.embed).sync(key,limit)
                else:
                    http=self.http
                    if key in ('CVE_LIST','OSV','CISA_KEV'):
                        # Preserve original stricter acquisition scopes.
                        http=HttpClient(Settings(http_timeout=15,retries=1,request_interval=6))
                    try:
                        if key=='CVE_LIST':collector=CVECollector(http=http)
                        elif key=='OSV':collector=OSVCollector(http)
                        elif key=='CISA_KEV':
                            def cache_lookup(identifier):
                                with self.factory() as s:
                                    from uuid import UUID
                                    row=s.get(m.RawDocument,UUID(identifier))
                                    if row:s.expunge(row)
                                    return row
                            collector=KEVCollector(http,cache_lookup)
                        elif key=='NVD':collector=NVDCollector(http)
                        else:collector=GitHubCollector(http,source_key=key)
                        result=SyncService(self.engine,session_factory=self.factory).sync(collector,limit)
                    finally:
                        if http is not self.http:http.close()
                    result={**result,'source':key}
                if key in ('NVD','GHSA',*VENDORS) and result.get('sync_run_id') and result.get('created',0)+result.get('updated',0)+result.get('skipped',0)>0:
                    from app.monitoring.facts import bridge_source_facts
                    try:result['source_fact_bridge']=bridge_source_facts(self.factory,result)
                    except Exception as exc:result['source_fact_bridge']={'status':'FAILED','error_type':type(exc).__name__,'raw_retained':True}
                results.append(result)
            except Exception as e:results.append({'source':key,'status':'failed','errors':[{'error_type':type(e).__name__}],'content_trust_level':'UNTRUSTED_EXTERNAL_CONTENT'})
        return results

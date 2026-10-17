"""Uniform adapter registry over the existing fetch/normalize/save implementations."""
from uuid import UUID
from pathlib import Path
from sqlalchemy import select
from app.db import models as m
from app.monitoring.service import SOURCES
from app.monitoring.catalog import FEEDS
from app.enrichment.acquisition import VENDORS
from app.monitoring.automation_schemas import CollectorSpec,SourceReceipt
from app.utils.time import utcnow


class CollectorRegistry:
    def keys(self):return SOURCES
    def describe(self,key):
        if key not in SOURCES:raise ValueError('Unregistered monitoring source')
        category=('vendor_advisory' if key in VENDORS else FEEDS[key]['type'] if key in FEEDS
            else 'security_community' if key=='GHSA' else 'exploitation_catalog' if key=='CISA_KEV'
            else 'vulnerability_database')
        scope=('Metadata/limited excerpts; bounded RSS/Atom slice' if key in FEEDS
            else 'Existing declared CVE Git namespace; no global corpus coverage' if key=='CVE_LIST'
            else 'Native API records, declared identity/repository window; no independent-publisher guarantee')
        return CollectorSpec(source=key,category=category,
            adapter='FeedSyncService' if key in FEEDS else 'BaseCollector + SyncService',scope=scope)


def run_entities(session,run,*,document_limit=None):
    targets=set();documents=set()
    for obs in session.scalars(select(m.SourceObservation).where(m.SourceObservation.sync_run_id==run.id)):
        parsed=obs if obs.parse_status=='parsed' else None
        if obs.record_type=='fetch' and (obs.details or {}).get('outcome')=='skipped':
            parsed=session.scalar(select(m.SourceObservation).where(m.SourceObservation.source_id==obs.source_id,
                m.SourceObservation.raw_document_id==obs.raw_document_id,m.SourceObservation.external_id==obs.external_id,
                m.SourceObservation.parse_status=='parsed').order_by(m.SourceObservation.created_at.desc()).limit(1))
        if parsed:
            targets.update(UUID(x) for x in parsed.details.get('vulnerability_ids',[]))
            if parsed.details.get('document_id'):documents.add(UUID(parsed.details['document_id']))
    # 304/unchanged feeds may reuse indexed documents without adding another parsed observation.
    raw_id=(run.cursor_after or {}).get('raw_id')
    if raw_id and run.records_skipped:
        source=session.get(m.Source,run.source_id)
        raw=session.get(m.RawDocument,UUID(raw_id))
        if source.source_key in FEEDS and raw and raw.source_id==run.source_id:
            from app.monitoring.feeds import parse_feed
            from app.monitoring.knowledge import fingerprint
            selected=parse_feed(bytes(raw.raw_payload),source.source_key)[:document_limit or (run.cursor_after or {}).get('processed_limit',100)]
            for entry in selected:
                document=session.scalar(select(m.KnowledgeDocument.id).where(
                    m.KnowledgeDocument.source_id==run.source_id,m.KnowledgeDocument.external_id==entry['external_id'],
                    m.KnowledgeDocument.details['content_fingerprint'].astext==fingerprint(entry),
                    m.KnowledgeDocument.deleted_at.is_(None)))
                if document:documents.add(document)
    return tuple(sorted(targets,key=str)),tuple(sorted(documents,key=str))


def controlled_error(value):
    import re
    return value if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_]{1,100}',value) else 'SOURCE_ERROR'


class CollectorFramework:
    def __init__(self,monitor,*,allow_cve_bootstrap=False,execution_mode='LIVE'):
        self.monitor=monitor;self.registry=CollectorRegistry();self.allow_cve_bootstrap=allow_cve_bootstrap
        self.execution_mode=execution_mode
    def collect(self,key,*,limit,force=False):
        self.registry.describe(key)
        with self.monitor.factory() as s:
            source=s.scalar(select(m.Source).where(m.Source.source_key==key))
            if source and not source.enabled and source.last_sync_at:
                return SourceReceipt(source=key,status='DISABLED')
        if key=='CVE_LIST' and not self.allow_cve_bootstrap:
            from app.core.config import Settings
            if not (Settings.from_env().cve_cache.resolve()/'.git').exists():
                return SourceReceipt(source=key,status='DEFERRED',errors=('CVE_CACHE_BOOTSTRAP_REQUIRED',))
        result=self.monitor.run_once([key],limit=limit,force=force)[0]
        status={'succeeded':'SUCCESS','partial':'PARTIAL','failed':'FAILED','not_due':'NOT_DUE','busy':'BUSY'}.get(result['status'],'FAILED')
        errors=[controlled_error(e.get('error_type')) for e in result.get('errors',[])]
        if (result.get('source_fact_bridge') or {}).get('status')=='FAILED':
            status='PARTIAL';errors.append('SOURCE_FACT_BRIDGE_FAILED')
        with self.monitor.factory() as s:
            source=s.scalar(select(m.Source).where(m.Source.source_key==key))
            run=s.get(m.SyncRun,UUID(result['sync_run_id'])) if result.get('sync_run_id') else None
            if status=='NOT_DUE' and source:
                run=s.scalar(select(m.SyncRun).where(m.SyncRun.source_id==source.id).order_by(m.SyncRun.started_at.desc(),m.SyncRun.id.desc()).limit(1))
                prior=(run.details or {}).get('pipeline_v1') if run else None
                if not prior:
                    return SourceReceipt(source=key,status='NOT_DUE',errors=('LEGACY_RUN_NOT_RESUMED',))
                if prior.get('execution_mode')!=self.execution_mode:
                    return SourceReceipt(source=key,status='DEFERRED',errors=('CAPTURE_MODE_MISMATCH',))
                errors.extend(controlled_error(e) for e in prior.get('errors',[]))
                if run.status=='failed':status='FAILED'
                elif run.status=='partial':errors.append('COLLECTION_PARTIAL')
                targets=tuple(UUID(x) for x in prior.get('target_ids',[]))
                documents=tuple(UUID(x) for x in prior.get('document_ids',[]))
            else:targets,documents=run_entities(s,run,document_limit=limit) if run else ((),())
            run_id=run.id if run else None
        return SourceReceipt(source=key,status=status,sync_run_id=run_id,
            targets=targets,document_ids=documents,errors=tuple(errors))

from contextlib import contextmanager
from datetime import date
from pathlib import Path
import json,time
from sqlalchemy.orm import Session
from app.db import models as m
from app.db.persistence import store_raw
from app.repositories.sources import source_registry
from app.repositories.ingestion import persist_record,NORMALIZER_VERSIONS,unique_row
from app.core.logging import event
from app.utils.time import utcnow

class SyncService:
    def __init__(self,engine,*,session_factory=None):
        self.engine=engine
        self.session_factory=session_factory

    @contextmanager
    def session(self):
        if self.session_factory:
            with self.session_factory() as session: yield session
        else:
            with Session(self.engine) as session:
                with session.begin(): yield session

    def sync(self,collector,limit=10,*,recheck=False):
        if not 1<=limit<=1000: raise ValueError('limit must be 1..1000')
        key=collector.source_key; start=time.perf_counter()
        counts={'fetched':0,'created':0,'updated':0,'skipped':0,'failed':0,'vulnerabilities_created':0}
        timings={'normalizer_ms':0,'database_ms':0}; errors=[]; completed=[]; batch=None
        with self.session() as s:
            source=source_registry(s,key)
            if source.status=='running': raise RuntimeError('Source sync already running; recover abandoned run explicitly')
            before=source.checkpoint
            source.enabled=True;source.status='running';source.last_sync_at=utcnow()
            run=m.SyncRun(source_id=source.id,started_at=utcnow(),status='running',cursor_before=before,mode='incremental' if before else 'initial')
            s.add(run);s.flush();run_id=run.id;source_id=source.id
        def save_raw(envelope):
            db_start=time.perf_counter()
            with self.session() as s:
                source=s.get(m.Source,source_id)
                raw=store_raw(s,source_id=source_id,external_id=envelope.external_id,source_url=envelope.source_url,
                    retrieved_at=envelope.retrieved_at,content_type=envelope.content_type.split(';')[0][:100],
                    raw_payload=envelope.raw_payload,publisher=source.name,license_scope=source.license_scope,
                    completeness=envelope.metadata.get('completeness','complete'),details={'untrusted':True,**envelope.metadata})
                s.flush();s.expunge(raw)
            timings['database_ms']+=(time.perf_counter()-db_start)*1000
            return raw
        event('sync.started',source=key,sync_run_id=run_id,status='running')
        try:
            batch=collector.collect({**(before or {}),**({'recheck':True} if recheck else {})},limit,save_raw)
            for envelope in batch.records:
                id=envelope.record_id or envelope.external_id; counts['fetched']+=1
                try:
                    raw=None
                    if envelope.metadata.get('fetch_error'): raise RuntimeError('Fetch:'+envelope.metadata['fetch_error'])
                    if envelope.raw_id:
                        with self.session() as s:
                            raw=s.get(m.RawDocument,envelope.raw_id);s.expunge(raw)
                    else: raw=save_raw(envelope)
                    decode_start=time.perf_counter()
                    payload=envelope.payload if envelope.payload is not None else json.loads(raw.raw_payload)
                    removed=envelope.metadata.get('removed')
                    record=None if removed else collector.normalize(payload,raw.id,envelope.retrieved_at)
                    timings['normalizer_ms']+=(time.perf_counter()-decode_start)*1000
                    db_start=time.perf_counter()
                    with self.session() as s:
                        source=s.get(m.Source,source_id)
                        if removed:
                            vulnerability=s.scalar(__import__('sqlalchemy').select(m.Vulnerability).where(m.Vulnerability.canonical_id==id))
                            if vulnerability:
                                unique_row(s,m.KnownExploitation,{'vulnerability_id':vulnerability.id,'source_id':source_id,'raw_document_id':raw.id},
                                    {'known_exploited':None,'catalog_status':'not_listed_as_of','catalog_complete':True,'catalog_version':payload['catalog']['catalogVersion'],'observed_at':envelope.retrieved_at})
                            result={'outcome':'updated','vulnerabilities_created':0}
                        else:
                            result=persist_record(s,source,raw,record,sync_run_id=run_id,locator=envelope.locator)
                        # A fetch observation is separate from immutable normalized/domain revisions.
                        s.add(m.SourceObservation(source_id=source_id,raw_document_id=raw.id,sync_run_id=run_id,external_id=id,
                            record_type='fetch',retrieved_at=envelope.retrieved_at,http_status=envelope.http_status,raw_locator=envelope.locator,
                            lineage_key=key,publisher=raw.publisher,parse_status='pending',details={'outcome':result['outcome'],'untrusted':True}))
                    timings['database_ms']+=(time.perf_counter()-db_start)*1000
                    counts[result['outcome']]+=1;counts['vulnerabilities_created']+=result['vulnerabilities_created'];completed.append(id)
                    event('record.completed',source=key,sync_run_id=run_id,external_id=id,status=result['outcome'])
                except Exception as exc:
                    counts['failed']+=1;error={'external_id':id,'error_type':type(exc).__name__}
                    # Request failure labels are controlled; arbitrary source/SQL exception messages are not logged.
                    if envelope.metadata.get('fetch_error'): error['error_type']=envelope.metadata['fetch_error']
                    errors.append(error)
                    with self.session() as s:
                        s.add(m.SourceObservation(source_id=source_id,raw_document_id=raw.id if raw is not None else None,
                            sync_run_id=run_id,external_id=id,record_type='failure',retrieved_at=utcnow(),lineage_key=key,publisher=key,
                            parse_status='failed',details=error))
                    event('record.failed',source=key,sync_run_id=run_id,external_id=id,status='failed',error_type=error['error_type'])
        except Exception as exc:
            errors.append({'external_id':None,'error_type':type(exc).__name__})
            event('sync.failed',source=key,sync_run_id=run_id,status='failed',error_type=type(exc).__name__)
        pending=[id for id in (batch.pending if batch else []) if id not in completed]
        if errors and not batch: status='failed'
        elif errors and not completed: status='failed'
        elif errors or pending: status='partial'
        else: status='succeeded'
        checkpoint=None
        if batch:
            candidate={**batch.checkpoint,'pending':pending}
            checkpoint=collector.finalize_checkpoint(before,candidate,pending,bool(errors))
        duration=(time.perf_counter()-start)*1000
        with self.session() as s:
            source=s.get(m.Source,source_id);run=s.get(m.SyncRun,run_id)
            for name in ['fetched','created','updated','skipped','failed']: setattr(run,'records_'+name,counts[name])
            run.status=status;run.finished_at=utcnow();run.cursor_after=checkpoint
            run.error_summary=json.dumps(errors) if errors else None;run.known_gaps={'pending_ids':pending,'errors':errors}
            run.coverage_scope=batch.coverage if batch else {'source_unavailable':True}
            run.details={'duration_ms':duration,'timings':timings,'vulnerabilities_created':counts['vulnerabilities_created'],
                'count_unit':'logical source records; transport/index catalog stored separately','limit':limit,'untrusted':True}
            source.status=status;source.coverage_scope=run.coverage_scope
            if checkpoint is not None: source.checkpoint=checkpoint
            if status=='succeeded': source.last_success_at=run.finished_at
        result={'source':key,'sync_run_id':str(run_id),'status':status,**counts,'duration_ms':duration,'timings':timings,'errors':errors,'pending_count':len(pending)}
        event('sync.finished',source=key,sync_run_id=run_id,duration=round(duration,2),status=status,**counts)
        return result

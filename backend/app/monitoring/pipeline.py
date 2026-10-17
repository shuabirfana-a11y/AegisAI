"""Batch-scoped automation over original services; no models, scans or verdict rewrite."""
from contextlib import contextmanager
from datetime import timedelta
import time
from uuid import uuid4,UUID
from threading import Event
from sqlalchemy import select,text,case,func
from app.db import models as m
from app.monitoring.service import MonitoringService
from app.monitoring.framework import CollectorFramework,controlled_error,run_entities
from app.monitoring.automation_schemas import PipelineConfig,PipelineCycle,SourceReceipt
from app.enrichment.scheduler import KINDS,schedule_due
from app.enrichment.service import EnrichmentService
from app.utils.time import utcnow

ORDER=('vendor','version','epss','kev','patch','poc')
LOCK_KEY='aegisai-monitoring-pipeline-v1'


@contextmanager
def cycle_guard(engine):
    with engine.connect() as connection:
        acquired=None
        try:
            acquired=connection.execute(text('SELECT pg_try_advisory_lock(hashtextextended(:key,14))'),{'key':LOCK_KEY}).scalar()
            connection.commit()
            yield bool(acquired)
        finally:
            if acquired is None:connection.invalidate()
            elif acquired:
                try:
                    connection.execute(text('SELECT pg_advisory_unlock(hashtextextended(:key,14))'),{'key':LOCK_KEY})
                    connection.commit()
                except Exception:connection.invalidate()


class IntelligencePipeline:
    def __init__(self,engine,config=None,*,monitor=None,worker=None,asset_owner=None):
        self.config=PipelineConfig.model_validate(config or {})
        if self.config.execution_mode=='MOCK' and engine.url.database!='aegis_phase5_test':
            raise ValueError('MOCK pipeline requires the dedicated synthetic test database')
        self.engine=engine;self.monitor=monitor or MonitoringService(engine)
        self.factory=self.monitor.factory;self.framework=CollectorFramework(self.monitor,
            allow_cve_bootstrap=self.config.allow_cve_bootstrap,execution_mode=self.config.execution_mode)
        if worker:self.worker=worker
        else:
            from app.core.http import HttpClient
            from app.core.config import Settings
            from app.enrichment.acquisition import validate_enrichment_url
            self.worker=EnrichmentService(self.factory,http=HttpClient(Settings(http_timeout=10,retries=0,request_interval=1),
                url_validator=validate_enrichment_url))
        self.asset_owner=asset_owner
    def close(self):
        self.monitor.close();self.worker.http.close()

    def _remember(self,receipt,cycle_id,*,processed=0,failed=0,status='RUNNING'):
        if receipt.sync_run_id is None:return
        with self.factory() as s:
            run=s.get(m.SyncRun,receipt.sync_run_id)
            prior=(run.details or {}).get('pipeline_v1') or {}
            if prior and prior.get('execution_mode')!=self.config.execution_mode:
                raise ValueError('Capture mode cannot be rewritten')
            if run.status=='failed':status='FAILED' if status!='CANCELLED' else status
            elif run.status=='partial' and status=='SUCCESS':status='PARTIAL'
            history=prior.get('cycle_history',[])
            entry={'cycle_id':str(cycle_id),'status':status,'processed_jobs':processed,'failed_jobs':failed}
            history=[x for x in history if x.get('cycle_id')!=str(cycle_id)]+[entry]
            scope=tuple(UUID(x) for x in prior.get('target_ids',[])) or receipt.targets
            backlog_open=any(self._unfinished(s,target) for target in scope)
            run.details={**run.details,'pipeline_v1':{
                'schema_version':'pipeline-source-run-v1','cycle_id':prior.get('cycle_id') or str(cycle_id),
                'last_cycle_id':str(cycle_id),'execution_mode':prior.get('execution_mode',self.config.execution_mode),'status':status,
                'target_ids':prior.get('target_ids',list(map(str,receipt.targets))),
                'document_ids':prior.get('document_ids',list(map(str,receipt.document_ids))),
                'processed_jobs':prior.get('processed_jobs',0)+processed,'failed_jobs':prior.get('failed_jobs',0)+failed,
                'pending_jobs':s.scalar(select(func.count()).select_from(m.EnrichmentJob).where(
                    m.EnrichmentJob.vulnerability_id.in_([UUID(x) for x in prior.get('target_ids',[])] or receipt.targets),
                    m.EnrichmentJob.status.in_(['queued','running']))),
                'cycle_history':history[-20:],'updated_at':utcnow().isoformat(),
                'backlog_open':backlog_open,
                'errors':list(dict.fromkeys([*prior.get('errors',[]),*receipt.errors]))}}

    @staticmethod
    def _unfinished(session,target):
        jobs=list(session.scalars(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==target)))
        return bool(any(j.status in ('queued','running') for j in jobs) or set(KINDS)-{j.enrichment_type for j in jobs})

    @staticmethod
    def _runnable(session,target):
        jobs=list(session.scalars(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==target)))
        return bool(any(j.status=='queued' for j in jobs) or set(KINDS)-{j.enrichment_type for j in jobs})

    def _backlog(self,receipts,deadline,stop):
        """Bounded rotating scan; historical identities remain on their capture run."""
        from sqlalchemy import tuple_
        from app.utils.time import parse_time
        selected={r.source for r in receipts if r.status not in ('DISABLED','BUSY','DEFERRED')}
        current={r.sync_run_id for r in receipts};backlog=[];seen=set();deferred=0;scan_deferred=False
        with self.factory() as s:
            sources=list(s.scalars(select(m.Source).where(m.Source.source_key.in_(selected))))
            # Fair across sources and across retained runs. Do not let one old
            # RUNNING domain job pin the historical window forever.
            mode=self.config.execution_mode
            state=lambda source:(source.details or {}).get('pipeline_backlog_v1',{}).get(mode,{})
            sources.sort(key=lambda source:(state(source).get('scanned_at',''),source.source_key))
            per_source=max(1,100//max(1,len(sources)))
            for source in sources:
                if stop.is_set() or time.monotonic()>=deadline:scan_deferred=True;break
                cursor=state(source).get('cursor')
                query=select(m.SyncRun).where(m.SyncRun.source_id==source.id,
                    m.SyncRun.details['pipeline_v1']['execution_mode'].astext==mode,
                    m.SyncRun.details['pipeline_v1']['backlog_open'].as_boolean().is_distinct_from(False))
                if cursor:query=query.where(tuple_(m.SyncRun.started_at,m.SyncRun.id)>
                    tuple_(parse_time(cursor['started_at']),UUID(cursor['id'])))
                runs=list(s.scalars(query.order_by(m.SyncRun.started_at,m.SyncRun.id).limit(per_source+1)))
                scanned=None;interrupted=False
                for run in runs[:per_source]:
                    if stop.is_set() or time.monotonic()>=deadline:scan_deferred=True;interrupted=True;break
                    data=run.details['pipeline_v1'];targets=[];unfinished_any=False
                    if run.id not in current:
                        for value in data.get('target_ids',[]):
                            if stop.is_set() or time.monotonic()>=deadline:scan_deferred=True;interrupted=True;break
                            target=UUID(value)
                            if target in seen:unfinished_any=True;continue
                            if not self._unfinished(s,target):continue
                            unfinished_any=True;seen.add(target)
                            if not self._runnable(s,target):scan_deferred=True;continue
                            if sum(len(r.targets) for r in backlog)+len(targets)>=self.config.target_budget:deferred+=1;continue
                            targets.append(target)
                        if targets:backlog.append(SourceReceipt(source=source.source_key,status='NOT_DUE',sync_run_id=run.id,
                            targets=tuple(targets),errors=tuple(controlled_error(e) for e in data.get('errors',[]))))
                        elif not unfinished_any and not interrupted:
                            run.details={**run.details,'pipeline_v1':{**data,'backlog_open':False}}
                    if interrupted:break
                    scanned={'started_at':run.started_at.isoformat(),'id':str(run.id)}
                more=len(runs)>per_source or interrupted
                scan_deferred=scan_deferred or more
                next_cursor=(scanned or cursor) if more else None
                metadata=(source.details or {}).get('pipeline_backlog_v1',{})
                source.details={**(source.details or {}),'pipeline_backlog_v1':{**metadata,
                    mode:{'cursor':next_cursor,'scanned_at':utcnow().isoformat()}}}
        return backlog,deferred,scan_deferred

    def _queue(self,targets):
        now=utcnow()
        with self.factory() as s:
            needed=[]
            for target in sorted(targets,key=str):
                latest={}
                for job in s.scalars(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==target)
                    .order_by(m.EnrichmentJob.created_at.desc(),m.EnrichmentJob.id.desc())):
                    latest.setdefault(job.enrichment_type,job)
                due=any(kind not in latest or latest[kind].status not in ('queued','running') and
                    (latest[kind].finished_at is None or latest[kind].finished_at<now-timedelta(hours=24)) for kind in KINDS)
                if due:needed.append(target)
            jobs=schedule_due(s,needed,limit=self.config.target_budget)
            return len(jobs),max(0,len(needed)-self.config.target_budget)

    def _jobs(self,targets):
        if not targets:return []
        priority=case({key:index for index,key in enumerate(ORDER)},value=m.EnrichmentJob.enrichment_type,else_=99)
        with self.factory() as s:
            return [(j.id,j.vulnerability_id,j.enrichment_type) for j in s.scalars(select(m.EnrichmentJob)
                .where(m.EnrichmentJob.vulnerability_id.in_(targets),m.EnrichmentJob.status=='queued')
                .order_by(m.EnrichmentJob.vulnerability_id,priority,m.EnrichmentJob.scheduled_at,m.EnrichmentJob.id)
                .limit(self.config.job_budget))]

    def _assets(self,targets,cycle_id,stop,deadline):
        if not self.asset_owner or not targets or self.config.asset_budget==0:return 0,0
        from app.enrichment.repository import digest
        from app.assets.events import run_job
        with self.factory() as s:
            packages=select(m.AffectedVersionRange.package_identifier_id).where(m.AffectedVersionRange.vulnerability_id.in_(targets),
                m.AffectedVersionRange.package_identifier_id.is_not(None))
            assets=list(s.scalars(select(m.Asset.id).join(m.AssetComponent,m.AssetComponent.asset_id==m.Asset.id)
                .where(m.Asset.owner_principal==self.asset_owner,m.Asset.deleted_at.is_(None),m.AssetComponent.deleted_at.is_(None),
                    m.AssetComponent.package_identifier_id.in_(packages)).distinct().order_by(m.Asset.id).limit(self.config.asset_budget)))
        done=failed=0
        for asset_id in assets:
            if stop.is_set() or time.monotonic()>=deadline:break
            with self.factory() as s:
                job=m.AssetRecomputeJob(asset_id=asset_id,job_key='monitor:'+digest([str(cycle_id),str(asset_id)]))
                s.add(job);s.flush();run_job(s,job)
                done+=1;failed+=int(job.status=='failed')
        return done,failed

    def run_cycle(self,sources,*,force=False,stop=None):
        sources=list(dict.fromkeys(sources))
        if not sources:raise ValueError('At least one explicitly selected source is required')
        for key in sources:self.framework.registry.describe(key)
        stop=stop or Event();started=utcnow();cycle_id=uuid4();deadline=time.monotonic()+self.config.cycle_seconds
        receipts=[];backlog=[];done=failed=queued=deferred=pending=unresolved=dependencies=dependency_failed=0
        counts={};failed_counts={};by_target=set();warnings=[];asset=asset_failed=0;key=None
        def budget():return not stop.is_set() and time.monotonic()<deadline
        def result(status):
            return PipelineCycle(cycle_id=cycle_id,execution_mode=self.config.execution_mode,status=status,
                started_at=started,finished_at=utcnow(),sources=tuple(receipts),queued_jobs=queued,
                processed_jobs=done,failed_jobs=failed,asset_jobs=asset,failed_asset_jobs=asset_failed,
                deferred_targets=deferred,pending_jobs=pending,unresolved_jobs=unresolved,dependency_jobs=dependencies,
                failed_dependency_jobs=dependency_failed,backlog_runs=len(backlog),resumed_sources=tuple(backlog),warnings=tuple(warnings))
        if stop.is_set():return result('CANCELLED')
        with cycle_guard(self.engine) as acquired:
            if not acquired:return result('BUSY')
            try:
                for key in sources:
                    if not budget():break
                    try:receipt=self.framework.collect(key,limit=self.config.record_limit,force=force)
                    except Exception as exc:
                        receipt=SourceReceipt(source=key,status='FAILED',errors=(controlled_error(type(exc).__name__),))
                    receipts.append(receipt)
                    self._remember(receipt,cycle_id)
                    if receipt.status in ('SUCCESS','PARTIAL','NOT_DUE'):by_target.update(receipt.targets)
                if budget():
                    backlog,deferred,scan_deferred=self._backlog(receipts,deadline,stop)
                    if scan_deferred:warnings.append('BACKLOG_SCAN_DEFERRED; bounded scan or non-runnable pending domain work remains; explicit recovery may be needed.')
                    for receipt in backlog:by_target.update(receipt.targets)
                    if budget():
                        new_queued,new_deferred=self._queue(by_target)
                        queued+=new_queued;deferred+=new_deferred
                for job_id,target,kind in self._jobs(by_target) if budget() else []:
                    if not budget():break
                    try:
                        outputs=self.worker.run(target,kind,job_id=job_id)
                        primary=next(x for x in outputs if x.task_id==job_id)
                        bad=primary.status=='FAILED'
                        extra=[x for x in outputs if x.task_id!=job_id]
                        dependencies+=len(extra);dependency_failed+=sum(x.status=='FAILED' for x in extra)
                        unresolved+=sum(x.status in ('PARTIAL','CONFLICT') for x in outputs)
                    except Exception as exc:
                        bad=True
                        with self.factory() as s:
                            job=s.get(m.EnrichmentJob,job_id)
                            # Never overwrite a running legacy/domain worker. Interrupted
                            # domain work still requires the original explicit recovery.
                            if job.status=='queued':
                                job.started_at=job.started_at or utcnow();job.finished_at=utcnow();job.status='failed'
                                job.error_code=controlled_error(type(exc).__name__);job.retryable=False
                    done+=1;failed+=int(bad)
                    counts[target]=counts.get(target,0)+1;failed_counts[target]=failed_counts.get(target,0)+int(bad)
                if budget():asset,asset_failed=self._assets(by_target,cycle_id,stop,deadline)
            except KeyboardInterrupt:
                stop.set();warnings.append('OPERATOR_INTERRUPTED; interrupted domain work requires explicit recovery.')
                # Collection may have persisted a run before the interrupt reached us.
                if key and not any(r.source==key for r in receipts):
                    with self.factory() as s:
                        run=s.scalar(select(m.SyncRun).join(m.Source,m.Source.id==m.SyncRun.source_id).where(
                            m.Source.source_key==key,m.SyncRun.started_at>=started).order_by(m.SyncRun.started_at.desc()).limit(1))
                        if run:
                            targets,documents=run_entities(s,run,document_limit=self.config.record_limit)
                            receipts.append(SourceReceipt(source=key,status='PARTIAL',sync_run_id=run.id,
                                targets=targets,document_ids=documents,errors=('OPERATOR_INTERRUPTED',)))
            with self.factory() as s:
                pending=s.scalar(select(func.count()).select_from(m.EnrichmentJob).where(
                    m.EnrichmentJob.vulnerability_id.in_(by_target),m.EnrichmentJob.status.in_(['queued','running'])))
            status=('CANCELLED' if stop.is_set() else 'PARTIAL' if time.monotonic()>=deadline or deferred or failed or asset_failed
                or pending or unresolved or dependency_failed or any(x.startswith('BACKLOG_SCAN_DEFERRED') for x in warnings)
                or any(x.errors or x.status in ('PARTIAL','FAILED','BUSY','DEFERRED') for x in [*receipts,*backlog])
                else 'SUCCESS')
            if not stop.is_set() and receipts and all(x.status=='FAILED' for x in receipts):status='FAILED'
            for group in (receipts,backlog):
                for i,receipt in enumerate(group):
                    processed=sum(counts.get(t,0) for t in receipt.targets);bad=sum(failed_counts.get(t,0) for t in receipt.targets)
                    with self.factory() as s:
                        waiting=s.scalar(select(func.count()).select_from(m.EnrichmentJob).where(
                            m.EnrichmentJob.vulnerability_id.in_(receipt.targets),m.EnrichmentJob.status.in_(['queued','running'])))
                    group[i]=receipt.model_copy(update={'processed_jobs':processed,'failed_jobs':bad,'pending_jobs':waiting})
                    self._remember(group[i],cycle_id,processed=processed,failed=bad,status=status)
            if self.asset_owner is None:warnings.append('ASSET_SCOPE_NOT_CONFIGURED; no inventory created or guessed.')
            warnings.append('Verification remains the original scoped rules; pipeline completion is not blanket confirmation.')
            return result(status)

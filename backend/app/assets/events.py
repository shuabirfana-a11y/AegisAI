"""Targeted database queue; poll existing domain events without altering Phase7."""
from datetime import datetime,timedelta
from sqlalchemy import select,exists,or_,and_
from app.db import models as m
from app.enrichment.repository import lock,digest
from app.utils.time import utcnow

EVENT_TYPES=['FIX_VERSION_FOUND','POC_CONFIRMED','POC_STATUS_CHANGED','KEV_ADDED','EPSS_CHANGED','PATCH_FOUND','PATCH_CONFIRMED','VERIFICATION_CHANGED','VERSION_UPDATED','CONFLICT_DETECTED','CONFLICT_RETIRED','CLAIM_ADOPTED']

def dispatch_events(session,limit=50):
    if not 1<=limit<=500:raise ValueError('Event batch limit must be1..500')
    scope=select(m.AffectedVersionRange.vulnerability_id.label('vulnerability_id'),m.AffectedVersionRange.package_identifier_id.label('package_id')).where(m.AffectedVersionRange.package_identifier_id.is_not(None)).union(
        select(m.Claim.vulnerability_id,m.Claim.package_identifier_id).where(m.Claim.package_identifier_id.is_not(None))).subquery()
    # New event/asset pairs, not the oldest N events on every invocation.
    affected=select(m.AssetComponent.asset_id.label('asset_id'),m.IntelligenceEvent.id.label('event_id')).select_from(m.IntelligenceEvent)
    affected=affected.join(scope,scope.c.vulnerability_id==m.IntelligenceEvent.vulnerability_id)
    affected=affected.join(m.AssetComponent,m.AssetComponent.package_identifier_id==scope.c.package_id)
    affected=affected.join(m.Asset,m.Asset.id==m.AssetComponent.asset_id)
    affected=affected.where(m.Asset.deleted_at.is_(None),m.AssetComponent.deleted_at.is_(None),m.IntelligenceEvent.event_type.in_(EVENT_TYPES),
        ~exists(select(m.AssetRecomputeJob.id).where(m.AssetRecomputeJob.asset_id==m.AssetComponent.asset_id,m.AssetRecomputeJob.intelligence_event_id==m.IntelligenceEvent.id)))
    pairs=session.execute(affected.distinct().limit(limit)).all();jobs=[]
    for asset_id,event_id in pairs:
        key='intel:'+digest([str(event_id),str(asset_id)]);lock(session,'asset-job:'+key)
        if session.scalar(select(m.AssetRecomputeJob.id).where(m.AssetRecomputeJob.job_key==key)):continue
        job=m.AssetRecomputeJob(asset_id=asset_id,intelligence_event_id=event_id,job_key=key)
        session.add(job);jobs.append(job)
    session.flush()
    # Phase6 can append a source observation/range before Phase7 emits an event.
    # Inspect dependency metadata; enqueue only changed assets, never recompute here.
    if len(jobs)<limit:jobs.extend(_dispatch_source_changes(session,scope,limit-len(jobs)))
    session.flush();return jobs

def _dispatch_source_changes(session,scope,limit):
    from app.assets.dependencies import dependency_state
    pending=set(session.scalars(select(m.AssetRecomputeJob.asset_id).where(or_(
        m.AssetRecomputeJob.status.in_(['queued','running']),
        and_(m.AssetRecomputeJob.status=='failed',m.AssetRecomputeJob.attempt<3)))))
    candidates=session.execute(select(m.AssetComponent,scope.c.vulnerability_id).join(scope,
        scope.c.package_id==m.AssetComponent.package_identifier_id).join(m.Asset,m.Asset.id==m.AssetComponent.asset_id).where(
        m.Asset.deleted_at.is_(None),m.AssetComponent.deleted_at.is_(None)).order_by(m.AssetComponent.asset_id,m.AssetComponent.id,scope.c.vulnerability_id))
    cache={};changed={};now=utcnow()
    for component,vid in candidates:
        if component.asset_id in pending:continue
        pair=(vid,component.package_identifier_id)
        if pair not in cache:cache[pair]=dependency_state(session,*pair)
        state=cache[pair]
        old=session.scalar(select(m.AssetRiskSnapshot).where(m.AssetRiskSnapshot.component_id==component.id,
            m.AssetRiskSnapshot.vulnerability_id==vid).order_by(m.AssetRiskSnapshot.created_at.desc(),m.AssetRiskSnapshot.id.desc()).limit(1))
        stored=old.payload.get('dependency_state',{}) if old else {}
        expired=bool(state.get('expires_at') and datetime.fromisoformat(state['expires_at'])<now)
        if old is None or old.inventory_revision!=component.inventory_revision or stored.get('signature')!=state['signature'] or expired:
            changed.setdefault(component.asset_id,[]).append([str(component.id),str(vid),component.inventory_revision,state['signature'],state['expires_at'],expired])
    jobs=[]
    for asset_id,changes in changed.items():
        key='source:'+digest([str(asset_id),changes]);lock(session,'asset-job:'+key)
        if session.scalar(select(m.AssetRecomputeJob.id).where(m.AssetRecomputeJob.job_key==key)):continue
        job=m.AssetRecomputeJob(asset_id=asset_id,job_key=key);session.add(job);jobs.append(job)
        if len(jobs)>=limit:break
    return jobs

def run_job(session,job):
    from app.assets.risk import RiskService
    if job.status=='succeeded' or job.attempt>=3:return job
    job.status='running';job.attempt+=1;job.started_at=utcnow();job.finished_at=None;session.flush()
    try:
        with session.begin_nested():RiskService.recompute(session,job.asset_id)
    except Exception as exc:
        job.status='failed';job.error_code=type(exc).__name__[:60]
    else:job.status='succeeded';job.error_code=None
    job.finished_at=utcnow();session.flush();return job

def run_due(engine,limit=20):
    from app.db.session import transaction
    if not 1<=limit<=100:raise ValueError('Job limit must be1..100')
    done=[]
    for _ in range(limit):
        with transaction(engine) as session:
            now=utcnow();due=or_(m.AssetRecomputeJob.status=='queued',
                and_(m.AssetRecomputeJob.status=='failed',m.AssetRecomputeJob.attempt<3,m.AssetRecomputeJob.finished_at<now-timedelta(seconds=30)))
            job=session.scalar(select(m.AssetRecomputeJob).where(due).order_by(m.AssetRecomputeJob.created_at,m.AssetRecomputeJob.id).with_for_update(skip_locked=True).limit(1))
            if job is None:break
            run_job(session,job);done.append({'job_id':str(job.id),'asset_id':str(job.asset_id),'status':job.status,'attempt':job.attempt,'error_code':job.error_code})
    return done

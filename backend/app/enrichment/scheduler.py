from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select
from app.db import models as m
from app.enrichment.repository import lock
from app.utils.time import utcnow
KINDS=('vendor','epss','kev','poc','patch','version')

def schedule_due(session,targets,*,now=None,limit=20):
    now=now or utcnow();result=[]
    for target in targets[:limit]:
        lock(session,'schedule:'+str(target))
        for kind in KINDS:
            latest=session.scalar(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==target,m.EnrichmentJob.enrichment_type==kind)
                .order_by(m.EnrichmentJob.created_at.desc()).limit(1))
            if latest and (latest.status in ('queued','running') or latest.finished_at and latest.finished_at>now-timedelta(hours=24)):continue
            job=m.EnrichmentJob(vulnerability_id=target,enrichment_type=kind,status='queued',scheduled_at=now,trace_id=str(uuid4()),details={'trigger':'new_target_or_daily_refresh'})
            session.add(job);session.flush();result.append(job)
    return result

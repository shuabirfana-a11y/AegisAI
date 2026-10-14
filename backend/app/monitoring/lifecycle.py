"""Read-only lifecycle derived from real normalization, job and evidence records."""
from uuid import UUID
from sqlalchemy import select,func,union_all,literal
from app.db import models as m
from app.assets.remediation import trusted_claim
from app.monitoring.automation_schemas import IntelligenceRecord,RecordPage,EnrichmentProgress,PipelineRun,PipelineRunPage
from app.monitoring.framework import controlled_error
from app.utils.time import utcnow

def record_view(session,kind,identifier):
    uid=UUID(str(identifier));knowledge=kind!='vulnerability'
    entity=session.get(m.KnowledgeDocument if knowledge else m.Vulnerability,uid)
    if entity is None:raise LookupError('Intelligence record not found')
    if knowledge:
        source_ids={entity.source_id}
        jobs=[];claims=list(session.scalars(select(m.Claim).where(m.Claim.knowledge_document_id==uid)))
        chunks=session.scalar(select(func.count()).select_from(m.KnowledgeChunk).where(m.KnowledgeChunk.document_id==uid))
        normalized=True;canonical=None
    else:
        source_ids=set(session.scalars(select(m.SourceObservation.source_id).join(m.AiRelevanceAssessment,
            m.AiRelevanceAssessment.observation_id==m.SourceObservation.id).where(m.AiRelevanceAssessment.vulnerability_id==uid)))
        latest={}
        for j in session.scalars(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==uid)
            .order_by(m.EnrichmentJob.created_at.desc(),m.EnrichmentJob.id.desc())):
            latest.setdefault(j.enrichment_type,j)
        jobs=list(latest.values())
        claims=list(session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==uid,m.Claim.asset_component_id.is_(None))))
        chunks=0;normalized=bool(source_ids);canonical=entity.canonical_id
    active=[c for c in claims if not c.details.get('superseded')]
    verified=sum(trusted_claim(session,c) for c in active)
    conflict=any(c.verification_status=='conflict' for c in active)
    verification=('CONFLICT' if conflict else 'CONFIRMED' if active and verified==len(active)
        else 'PENDING' if active else 'INSUFFICIENT_EVIDENCE')
    pending=any(j.status in ('queued','running') for j in jobs)
    status=('ENRICHING' if pending else 'AVAILABLE' if chunks or jobs and normalized
        else 'VERIFIED' if verification=='CONFIRMED' else 'NORMALIZED' if normalized else 'DISCOVERED')
    stages=['DISCOVERED']
    if normalized:stages.append('NORMALIZED')
    if jobs:stages.append('ENRICHING')
    if verification=='CONFIRMED':stages.append('VERIFIED')
    if status=='AVAILABLE':stages.append('AVAILABLE')
    progress=tuple(EnrichmentProgress(kind=j.enrichment_type,job_id=j.id,status=j.status,error_code=j.error_code,
        retryable=j.retryable,finished_at=j.finished_at) for j in jobs)
    evidence_count=session.scalar(select(func.count()).select_from(m.Evidence).where(m.Evidence.claim_id.in_([c.id for c in active])))
    relevant=[run for run in session.scalars(select(m.SyncRun).where(m.SyncRun.source_id.in_(source_ids))
        .order_by(m.SyncRun.started_at.desc())) if (str(uid) in (run.details.get('pipeline_v1') or {}).get('document_ids',[])
            or str(uid) in (run.details.get('pipeline_v1') or {}).get('target_ids',[]))]
    modes={(run.details.get('pipeline_v1') or {}).get('execution_mode','UNSPECIFIED') for run in relevant}
    mode=next(iter(modes)) if len(modes)==1 else 'UNSPECIFIED'
    observed=(session.scalar(select(func.max(m.SourceObservation.retrieved_at)).join(m.AiRelevanceAssessment,
        m.AiRelevanceAssessment.observation_id==m.SourceObservation.id).where(m.AiRelevanceAssessment.vulnerability_id==uid))
        if not knowledge else session.scalar(select(func.max(m.SourceObservation.retrieved_at)).where(
            m.SourceObservation.raw_document_id==entity.raw_document_id,m.SourceObservation.source_id==entity.source_id)))
    warnings=[]
    if len(modes)>1:warnings.append('MIXED_CAPTURE_MODES; this record cannot be represented as LIVE-only.')
    if verification!='CONFIRMED':warnings.append('Queryability does not establish confirmed claims; original verification remains required.')
    if any(j.status in ('failed','partial','conflict') for j in jobs):warnings.append('Enrichment contains failed/partial/conflicting outcomes; inspect job progress.')
    return IntelligenceRecord(id=uid,type=kind,title=entity.title or canonical or 'Intelligence',
        canonical_id=canonical,sources=tuple(sorted(session.scalars(select(m.Source.source_key).where(m.Source.id.in_(source_ids))))),
        status=status,verification_status=verification,execution_mode=mode,enrichment_progress=progress,
        query_available=normalized,verified_claims=verified,active_claims=len(active),evidence_count=evidence_count,
        knowledge_chunks=chunks,stages=tuple(stages),observed_at=observed or entity.created_at,published_at=entity.published_at,warnings=tuple(warnings))

def record_page(session,*,kind=None,q=None,offset=0,limit=20):
    vuln=select(m.Vulnerability.id.label('id'),literal('vulnerability').label('kind'),
        m.Vulnerability.published_at.label('published'),m.Vulnerability.title.label('title'),
        m.Vulnerability.canonical_id.label('canonical')).where(m.Vulnerability.deleted_at.is_(None))
    doc=select(m.KnowledgeDocument.id.label('id'),m.KnowledgeDocument.document_type.label('kind'),
        m.KnowledgeDocument.published_at.label('published'),m.KnowledgeDocument.title.label('title'),
        m.KnowledgeDocument.external_id.label('canonical')).where(m.KnowledgeDocument.deleted_at.is_(None))
    combined=union_all(vuln,doc).subquery();query=select(combined)
    if kind:query=query.where(combined.c.kind==kind)
    if q:
        term='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        query=query.where(combined.c.title.ilike(term,escape='\\')|combined.c.canonical.ilike(term,escape='\\'))
    total=session.scalar(select(func.count()).select_from(query.subquery()))
    rows=session.execute(query.order_by(combined.c.published.desc().nullslast(),combined.c.id).offset(offset).limit(limit)).mappings()
    return RecordPage(items=tuple(record_view(session,r['kind'],r['id']) for r in rows),total=total,offset=offset,limit=limit)

def pipeline_runs(session,*,source=None,offset=0,limit=20):
    query=select(m.SyncRun,m.Source.source_key).join(m.Source,m.Source.id==m.SyncRun.source_id).where(
        m.SyncRun.details['pipeline_v1']['schema_version'].astext=='pipeline-source-run-v1')
    if source:query=query.where(m.Source.source_key==source)
    total=session.scalar(select(func.count()).select_from(query.subquery()));items=[]
    for run,key in session.execute(query.order_by(m.SyncRun.started_at.desc(),m.SyncRun.id.desc()).offset(offset).limit(limit)):
        data=run.details['pipeline_v1']
        items.append(PipelineRun(sync_run_id=run.id,cycle_id=data['cycle_id'],last_cycle_id=data['last_cycle_id'],
            source=key,execution_mode=data['execution_mode'],status=data['status'],collection_status=run.status.upper(),
            processed_jobs=data['processed_jobs'],failed_jobs=data['failed_jobs'],targets=tuple(data['target_ids']),
            pending_jobs=data.get('pending_jobs',0),
            document_ids=tuple(data['document_ids']),started_at=run.started_at,updated_at=data['updated_at'],
            errors=tuple(controlled_error(x) for x in data.get('errors',[]))))
    return PipelineRunPage(items=tuple(items),total=total,offset=offset,limit=limit)

from time import perf_counter
from uuid import uuid4
from sqlalchemy import select,func
from app.db import models as m
from app.core.config import Settings
from app.core.http import HttpClient
from app.enrichment.acquisition import EnrichmentAcquisition,validate_enrichment_url
from app.enrichment.context import EnrichmentContext
from app.enrichment.contracts import EnrichmentResult
from app.enrichment.enrichers.base import failure
from app.enrichment.enrichers.vendor import VendorEnricher
from app.enrichment.enrichers.epss import EpssEnricher
from app.enrichment.enrichers.kev import KevEnricher
from app.enrichment.enrichers.poc import PocEnricher
from app.enrichment.enrichers.patch import PatchEnricher
from app.enrichment.enrichers.version import VersionEnricher
from app.enrichment.conflict import ConflictDetectionService
from app.enrichment.verification import VerificationService
from app.enrichment.integration import IntelligenceIntegrationService
from app.utils.time import utcnow
from app.core.logging import event

class EnrichmentService:
    def __init__(self,factory,*,http=None,enrichers=None):
        self.factory=factory
        self.http=http or HttpClient(Settings(http_timeout=30,retries=2,request_interval=0.2),url_validator=validate_enrichment_url)
        self.enrichers=enrichers if enrichers is not None else [VendorEnricher(),EpssEnricher(),KevEnricher(),PocEnricher(),PatchEnricher(),VersionEnricher()]

    def run(self,target,kind='all',*,job_id=None):
        with self.factory() as session:ctx=EnrichmentContext.load(session,target)
        selected=[e for e in self.enrichers if kind=='all' or e.name==kind]
        if not selected:raise ValueError('Unsupported enrichment type')
        deps={d for e in selected for d in e.depends_on}
        selected=[e for e in self.enrichers if e in selected or e.name in deps]
        acq=EnrichmentAcquisition(self.factory,self.http);results=[]
        for enricher in selected:
            ctx.task_id=uuid4();started=utcnow();clock=perf_counter();checked_start=len(acq.checked)
            with self.factory() as session:
                job=session.get(m.EnrichmentJob,job_id) if job_id and enricher.name==kind else None
                if job is None:
                    job=m.EnrichmentJob(vulnerability_id=ctx.target_id,enrichment_type=enricher.name,trace_id=str(ctx.trace_id),status='running',scheduled_at=started,started_at=started,attempt=1)
                    session.add(job);session.flush()
                else:
                    if job.status!='queued' or job.vulnerability_id!=ctx.target_id:raise ValueError('Job is not queued for this target')
                    job.status='running';job.started_at=started;job.attempt+=1;job.trace_id=str(ctx.trace_id)
                ctx.task_id=job.id
            try:
                with self.factory() as session:
                    before=self.counts(session,ctx.target_id)
                    out=enricher.investigate(ctx,session,acq)
                    verify_start=perf_counter()
                    conflicts=ConflictDetectionService.detect(session,ctx.target_id)
                    for c in session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==ctx.target_id)):
                        result=VerificationService.verify(session,c)
                        IntelligenceIntegrationService.adopt(session,c,result)
                    session.flush();after=self.counts(session,ctx.target_id)
                    status='CONFLICT' if any(c.status=='open' for c in conflicts) and out.status=='SUCCESS' else out.status
                    counts=[max(0,b-a) for a,b in zip(before,after)]
                    artifacts={**out.artifacts,'claim_ids':list(map(str,out.claims)),'evidence_ids':list(map(str,out.evidence)),
                        'candidate_ids':list(map(str,out.candidates)),'unresolved':out.unresolved,'dependencies':list(enricher.depends_on),
                        'verification_duration_ms':(perf_counter()-verify_start)*1000}
                    if enricher.name=='poc':
                        from app.enrichment.poc_artifacts import poc_page
                        artifacts['poc_snapshot']=poc_page(session,ctx.target_id,limit=100,job_status=status.lower()).model_dump(mode='json')
                    checked=out.checked;errors=out.errors;warnings=out.warnings
            except Exception as exc:
                status='FAILED';counts=[0,0,0];artifacts={'unresolved':['Domain transaction rolled back; acquired raw retained']}
                checked=list(acq.checked[checked_start:]);errors=[failure(exc,enricher.name)];warnings=[]
            finished=utcnow()
            result=EnrichmentResult(task_id=ctx.task_id,enrichment_type=enricher.name,target_id=ctx.target_id,status=status,
                claims_created=counts[0],evidence_created=counts[1],candidates_created=counts[2],sources_checked=checked,
                errors=errors,warnings=warnings,retryable=any(e.get('retryable') for e in errors),started_at=started,finished_at=finished,
                duration_ms=(perf_counter()-clock)*1000,trace_id=ctx.trace_id,artifacts=artifacts)
            with self.factory() as session:
                job=session.get(m.EnrichmentJob,ctx.task_id);job.status=status.lower();job.finished_at=finished
                job.duration_ms=round(result.duration_ms);job.retryable=result.retryable;job.error_code=errors[0]['code'] if errors else None
                job.result=result.model_dump(mode='json')
            results.append(result)
            event('enrichment.finished',source=','.join(enricher.sources),duration=result.duration_ms,status=result.status,
                trace_id=str(result.trace_id),task_id=str(result.task_id),target_id=str(result.target_id),enrichment_type=result.enrichment_type,
                claims_created=result.claims_created,evidence_created=result.evidence_created,candidates_created=result.candidates_created,
                error_code=errors[0]['code'] if errors else None,retryable=result.retryable)
        return results

    @staticmethod
    def counts(session,target):
        return [session.scalar(select(func.count()).select_from(m.Claim).where(m.Claim.vulnerability_id==target)),
            session.scalar(select(func.count()).select_from(m.Evidence).join(m.Claim,m.Evidence.claim_id==m.Claim.id).where(m.Claim.vulnerability_id==target)),
            sum(session.scalar(select(func.count()).select_from(model).where(model.vulnerability_id==target)) for model in (m.PocCandidate,m.PatchCandidate))]

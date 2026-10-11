from datetime import date
from decimal import Decimal
from app.db import models as m
from app.repositories.ingestion import unique_row
from app.enrichment.repository import emit
from app.enrichment.enrichers.base import BaseEnricher,WorkOutcome

class EpssEnricher(BaseEnricher):
    name='epss';sources=('EPSS',)
    def investigate(self,ctx,session,acq):
        start=len(acq.checked);out=WorkOutcome()
        url='https://api.first.org/data/v1/epss?cve='+ctx.canonical_id
        doc=acq.fetch('EPSS',url,'epss:'+ctx.canonical_id,'first:epss')
        payload=doc.payload
        if payload.get('status')!='OK':raise ValueError('EPSS source status not OK')
        for item in payload.get('data') or []:
            if item.get('cve')!=ctx.canonical_id:raise ValueError('EPSS target identity mismatch')
            score=Decimal(item['epss']);percentile=Decimal(item['percentile'])
            if not score.is_finite() or not percentile.is_finite() or not 0<=score<=1 or not 0<=percentile<=1:raise ValueError('EPSS out of range')
            score_date=date.fromisoformat(item['date']);model=payload.get('model_version') or item.get('model_version') or 'unknown_api_not_reported'
            row=unique_row(session,m.EpssSnapshot,{'vulnerability_id':ctx.target_id,'source_id':doc.source_id,'score_date':score_date,
                'model_version':model,'raw_document_id':doc.raw_id},{'score':score,'percentile':percentile,'observed_at':doc.retrieved_at})
            out.status='SUCCESS';out.artifacts['snapshot_id']=str(row.id)
            if model=='unknown_api_not_reported':out.warnings.append('API did not report EPSS model version; API version is not model version')
            emit(session,ctx.target_id,'EPSS_CHANGED',str(row.id),'A dated EPSS snapshot was first observed',source_id=doc.source_id,
                payload={'snapshot_id':str(row.id),'score':str(score),'percentile':str(percentile),'score_date':str(score_date),'model_version':model},occurred_at=doc.retrieved_at)
        return self.finish(out,acq,start)

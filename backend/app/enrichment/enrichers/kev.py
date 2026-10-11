import json
from datetime import date
from sqlalchemy import select
from app.db import models as m
from app.repositories.ingestion import unique_row
from app.enrichment.repository import ClaimStore,emit
from app.enrichment.evidence import EvidenceService
from app.enrichment.enrichers.base import BaseEnricher,WorkOutcome
from app.utils.time import utcnow

class KevEnricher(BaseEnricher):
    name='kev';sources=('CISA_KEV',)
    def investigate(self,ctx,session,acq):
        out=WorkOutcome();source=session.scalar(select(m.Source).where(m.Source.source_key=='CISA_KEV'))
        raw=session.scalar(select(m.RawDocument).where(m.RawDocument.source_id==source.id,m.RawDocument.completeness=='complete')
            .order_by(m.RawDocument.retrieved_at.desc()).limit(1)) if source else None
        if raw is None:out.unresolved.append('No complete Phase6 KEV catalog available');return out
        data=json.loads(raw.raw_payload);items=data['vulnerabilities']
        if len(items)!=data['count'] or len({x['cveID'] for x in items})!=data['count']:raise ValueError('KEV catalog count/identity mismatch')
        match=next(((i,x) for i,x in enumerate(items) if x['cveID']==ctx.canonical_id),None)
        status='listed' if match else 'not_listed_as_of';item=match[1] if match else None
        known=unique_row(session,m.KnownExploitation,{'vulnerability_id':ctx.target_id,'source_id':source.id,'raw_document_id':raw.id},
            {'known_exploited':True if match else None,'catalog_status':status,'catalog_complete':True,'catalog_version':data['catalogVersion'],
                'observed_at':raw.retrieved_at,'date_added':date.fromisoformat(item['dateAdded']) if item and item.get('dateAdded') else None,
                'due_date':date.fromisoformat(item['dueDate']) if item and item.get('dueDate') else None,'required_action':item.get('requiredAction') if item else None})
        obs=session.scalar(select(m.SourceObservation).where(m.SourceObservation.raw_document_id==raw.id,
            m.SourceObservation.external_id==ctx.canonical_id,m.SourceObservation.normalizer_version=='kev-enrichment-v1'))
        locator={'json_pointer':f'/vulnerabilities/{match[0]}' if match else '/vulnerabilities','catalog_complete':True}
        if obs is None:
            obs=m.SourceObservation(source_id=source.id,raw_document_id=raw.id,external_id=ctx.canonical_id,record_type='enrichment',
                retrieved_at=raw.retrieved_at,publisher='CISA',lineage_key='cisa:kev',parse_status='parsed',normalizer_version='kev-enrichment-v1',
                raw_locator=locator,normalized_payload=item or {'catalog_status':status,'catalog_version':data['catalogVersion']})
            session.add(obs);session.flush()
        value={'known_exploited':True if match else None,'catalog_status':status,'catalog_version':data['catalogVersion'],'as_of':data.get('dateReleased')}
        claim=ClaimStore.add(session,ctx.target_id,'KNOWN_EXPLOITED','kev:CISA',value)
        evidence=EvidenceService.add(session,claim,obs,value,locator,evidence_type='kev_record')
        out.claims.append(claim.id);out.evidence.append(evidence.id);out.artifacts['known_exploitation_id']=str(known.id)
        out.checked=[{'source':'CISA_KEV','status':'cached_complete_catalog','checked_at':utcnow().isoformat(),
            'retrieved_at':raw.retrieved_at.isoformat(),'catalog_version':data['catalogVersion'],'catalog_count':data['count'],'raw_document_id':str(raw.id)}]
        if match:
            out.status='SUCCESS';emit(session,ctx.target_id,'KEV_ADDED',str(claim.id),'A complete KEV catalog explicitly lists the target',claim=claim,evidence=evidence,source_id=source.id)
        else:out.unresolved.append('Not listed in this dated complete catalog; exploitation elsewhere remains unknown')
        return out

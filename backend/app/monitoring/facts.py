"""Bridge native source assertions to the existing Claim/Evidence read protocol.

No verification, adoption, inference, model call or exploit execution is done here.
"""
import json
from hashlib import sha256
from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.enrichment.repository import ClaimStore
from app.enrichment.evidence import EvidenceService,pointer

def bridge_source_facts(factory,result):
    seen=set();claims=set();evidence=set()
    with factory() as session:
        run=UUID(result['sync_run_id'])
        for fetch in session.scalars(select(m.SourceObservation).where(m.SourceObservation.sync_run_id==run)):
            observation=fetch if fetch.parse_status=='parsed' else None
            if fetch.record_type=='fetch' and fetch.details.get('outcome')=='skipped':
                observation=session.scalar(select(m.SourceObservation).where(m.SourceObservation.source_id==fetch.source_id,
                    m.SourceObservation.raw_document_id==fetch.raw_document_id,m.SourceObservation.external_id==fetch.external_id,
                    m.SourceObservation.parse_status=='parsed').order_by(m.SourceObservation.created_at.desc()).limit(1))
            if observation is None or observation.id in seen:continue
            seen.add(observation.id)
            raw=session.get(m.RawDocument,observation.raw_document_id)
            for target in observation.details.get('vulnerability_ids',[]):
                for assessment in session.scalars(select(m.CvssAssessment).where(m.CvssAssessment.observation_id==observation.id,m.CvssAssessment.vulnerability_id==UUID(target))):
                    locator={'json_pointer':assessment.details['locator']}
                    # Validate the exact native fragment before storing an assertion.
                    pointer(json.loads(raw.raw_payload),locator['json_pointer'])
                    value={'version':assessment.version,'score':float(assessment.base_score),'vector':assessment.vector,'kind':'base'}
                    scope='CVSS:'+assessment.version+':base:'+sha256(assessment.provider.encode()).hexdigest()[:16]
                    claim=ClaimStore.add(session,UUID(target),'CVSS_SCORE',scope,value,
                        subject={'cvss_assessment_id':assessment.id,'cvss_version':assessment.version,'assessment_kind':'base'},
                        details={'source_asserted':True,'bridge_version':'native-source-facts-v1'})
                    item=EvidenceService.add(session,claim,observation,value,locator,evidence_type='native_cvss',
                        explicit=assessment.details.get('score_method')=='source_explicit',details={'source_asserted':True})
                    claims.add(claim.id);evidence.add(item.id)
    return {'status':'AVAILABLE','claim_count':len(claims),'evidence_count':len(evidence),'verification_performed':False}

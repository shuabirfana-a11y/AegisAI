"""Read-only signatures/expiry for risk dependencies, including un-enriched Phase6 updates."""
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from app.db import models as m
from app.enrichment.repository import digest
from app.enrichment.evidence import current_evidence

def dependency_state(session,vulnerability_id,package_id):
    pkg=session.get(m.PackageIdentifier,package_id)
    ranges=list(session.scalars(select(m.AffectedVersionRange).where(m.AffectedVersionRange.vulnerability_id==vulnerability_id,m.AffectedVersionRange.package_identifier_id==package_id)))
    claims=list(session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==vulnerability_id)))
    # Source observation changes count even before Phase7 regenerates a Claim.
    heads={};range_state=[]
    for r in ranges:
        obs=session.get(m.SourceObservation,r.observation_id)
        head=session.scalar(select(m.SourceObservation.id).where(m.SourceObservation.source_id==r.source_id,m.SourceObservation.external_id==obs.external_id,m.SourceObservation.parse_status=='parsed').order_by(m.SourceObservation.retrieved_at.desc(),m.SourceObservation.created_at.desc(),m.SourceObservation.id.desc()).limit(1))
        heads[str(r.source_id)+':'+obs.external_id]=str(head);range_state.append([str(r.id),str(r.observation_id),r.raw_expression,r.parse_status])
    evidence=[];expires=[]
    for c in claims:
        for e in current_evidence(session,c):
            if e['is_current']:
                evidence.append([str(c.id),e['fingerprint'],e['stance']])
                if e['stance']=='support':expires.append(e['retrieved_at']+timedelta(days=30))
    epss=session.scalar(select(m.EpssSnapshot).where(m.EpssSnapshot.vulnerability_id==vulnerability_id).order_by(m.EpssSnapshot.score_date.desc(),m.EpssSnapshot.observed_at.desc(),m.EpssSnapshot.id).limit(1))
    if epss:expires.append(datetime.combine(epss.score_date+timedelta(days=8),datetime.min.time(),tzinfo=timezone.utc))
    kev=list(session.scalars(select(m.KnownExploitation).where(m.KnownExploitation.vulnerability_id==vulnerability_id)))
    pocs=list(session.scalars(select(m.PocCandidate).where(m.PocCandidate.vulnerability_id==vulnerability_id)))
    patches=list(session.scalars(select(m.PatchCandidate).where(m.PatchCandidate.vulnerability_id==vulnerability_id)))
    conflicts=list(session.scalars(select(m.ConflictRecord).where(m.ConflictRecord.vulnerability_id==vulnerability_id)))
    vuln=session.get(m.Vulnerability,vulnerability_id)
    value={'ranges':sorted(range_state),'heads':heads,'claims':sorted([[str(c.id),c.revision,c.verification_status,c.adopted,c.value_json,c.details.get('superseded')] for c in claims],key=lambda x:x[0]),
        'evidence':sorted(evidence),'epss':str(epss.id) if epss else None,'kev':sorted([[str(k.id),k.catalog_status,k.known_exploited] for k in kev]),
        'pocs':sorted([[str(p.id),p.status] for p in pocs]),'patches':sorted([[str(p.id),p.status,p.details] for p in patches],key=lambda x:x[0]),
        'conflicts':sorted([[str(c.id),c.status] for c in conflicts]),'vulnerability':[vuln.status,vuln.primary_severity,vuln.revision]}
    return {'signature':digest(value),'expires_at':min(expires).isoformat() if expires else None}

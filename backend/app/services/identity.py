from sqlalchemy import select,text
from app.db import models as m
from app.db.persistence import ensure_vulnerability

class VulnerabilityIdentityResolver:
    def resolve(self,session,record):
        cves=sorted({x['value'] for x in record.external_ids if x['type']=='CVE'})
        keys=cves or [record.source+':'+record.external_id]
        locks=set(keys)|{'alias:'+x['namespace']+':'+x['type']+':'+x['value'] for x in record.external_ids}
        for key in sorted(locks):
            session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,1))'),{'key':key})
        owners=set()
        for identity in record.external_ids:
            owners.update(session.scalars(select(m.VulnerabilityIdentifier.vulnerability_id).join(m.ExternalIdentifier,m.ExternalIdentifier.id==m.VulnerabilityIdentifier.identifier_id).where(
                m.ExternalIdentifier.namespace==identity['namespace'],m.ExternalIdentifier.identifier_type==identity['type'],m.ExternalIdentifier.normalized_value==identity['value'])))
        if not cves:
            if len(owners)==1: return [session.get(m.Vulnerability,next(iter(owners)))],0
            # Ambiguous aliases are preserved as a distinct source candidate, never unioned.
        elif len(cves)==1 and len(owners)==1:
            candidate=session.get(m.Vulnerability,next(iter(owners)))
            target=session.scalar(select(m.Vulnerability).where(m.Vulnerability.canonical_id==cves[0]))
            if target is None and not candidate.canonical_id.startswith('CVE-'):
                previous=candidate.canonical_id
                candidate.canonical_id=cves[0]
                candidate.details={**candidate.details,'identity_promotions':[*candidate.details.get('identity_promotions',[]),
                    {'from':previous,'to':cves[0],'source':record.source,'external_id':record.external_id,'rule':'explicit_single_cve_alias'}]}
                session.flush()
                return [candidate],0
        rows=[]; created=0
        for key in keys:
            existing=session.scalar(select(m.Vulnerability).where(m.Vulnerability.canonical_id==key))
            if existing is None: created+=1
            rows.append(existing or ensure_vulnerability(session,key,record.title or key))
        return rows,created

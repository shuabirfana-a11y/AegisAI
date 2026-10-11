"""Thin read-only wrappers around existing identity/range algorithms."""
from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.assets.identity import resolve_component
from app.assets.versions import compare_version
from app.repositories.queries import vulnerability_detail

def inspect_component_version(session, arguments, actor):
    target=arguments['target']; component={k:v for k,v in arguments.items() if k!='target'}
    identity=resolve_component(session,component)
    detail=vulnerability_detail(session,target)
    if detail is None:raise LookupError('Vulnerability not found')
    rows=[]; uncertainties=[]
    if identity['status']=='RESOLVED':
        package=str(identity['package_identifier_id'])
        for r in detail['affected_versions']:
            if str(r['package_identifier_id'])!=package:continue
            current=r['is_current']
            compared=compare_version(arguments['version'],{**r,'ecosystem':identity['ecosystem']})
            value=compared['affected'] if current else None
            rows.append({'range_id':r['id'],'package_identifier_id':package,
                'source_id':r['source_id'],'observation_id':r['observation_id'],
                'is_current':current,'raw_expression':r['raw_expression'],'fixed':r.get('fixed'),
                'range_result':'UNKNOWN' if value is None else 'IN_RANGE' if value else 'OUT_OF_RANGE',
                'comparison':compared,'verified':False,'verification_status':r['verification_status']})
        if not rows:uncertainties.append('No package-specific source range collected')
        elif not any(r['is_current'] for r in rows):uncertainties.append('Only historical ranges available')
    else:uncertainties.append('Component identity '+identity['status']+'; no guessed distribution')
    if any(r['range_result']=='UNKNOWN' for r in rows):uncertainties.append('Some range/version semantics or currentness remain unknown')
    return {'vulnerability_id':detail['id'],'canonical_id':detail['canonical_id'],
        'component':component,'identity_resolution':identity,'source_range_results':rows,
        'coverage':'Observed package-specific local source ranges; not verified asset safety',
        'uncertainties':uncertainties}

def decorate_evidence(session, refs):
    """Source metadata is descriptive; it never changes a verified flag."""
    for ref in refs:
        source=session.get(m.Source,UUID(str(ref['source_id']))) if ref.get('source_id') else None
        ref['authority_level']=source.authority_level if source else None
        ref['authority_scope']=source.authority_scope if source else None
        raw_id=ref.get('raw_document_id'); current=None; lineage=None
        if source and raw_id:
            # An Evidence refers to one immutable observation even if the raw bytes are reused.
            if ref.get('evidence_id'):
                stored=session.get(m.Evidence,UUID(str(ref['evidence_id'])))
                observed=session.get(m.SourceObservation,stored.observation_id) if stored and stored.observation_id else None
                claim=session.get(m.Claim,stored.claim_id) if stored else None
                ref['vulnerability_id']=str(claim.vulnerability_id) if claim and claim.vulnerability_id else None
            elif ref.get('observation_id'):
                observed=session.get(m.SourceObservation,UUID(str(ref['observation_id'])))
            else:
                observed=session.scalar(select(m.SourceObservation).where(
                    m.SourceObservation.raw_document_id==UUID(str(raw_id)),m.SourceObservation.source_id==source.id)
                    .order_by(m.SourceObservation.retrieved_at.desc(),m.SourceObservation.created_at.desc(),m.SourceObservation.id.desc()).limit(1))
            if observed and (observed.source_id!=source.id or str(observed.raw_document_id)!=str(raw_id)):
                observed=None
            if observed:
                latest=session.scalar(select(m.SourceObservation.id).where(m.SourceObservation.source_id==source.id,
                    m.SourceObservation.external_id==observed.external_id,m.SourceObservation.parse_status=='parsed')
                    .order_by(m.SourceObservation.retrieved_at.desc(),m.SourceObservation.created_at.desc(),m.SourceObservation.id.desc()).limit(1))
                current=observed.parse_status=='parsed' and observed.id==latest;lineage=observed.lineage_key
                ref.setdefault('retrieved_at',observed.retrieved_at)
                ref['observation_id']=str(observed.id)
                ref['external_id']=observed.external_id
        ref['is_current']=current
        ref['lineage_key']=lineage
    return refs

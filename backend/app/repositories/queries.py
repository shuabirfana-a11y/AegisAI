from uuid import UUID
from sqlalchemy import select,func,exists,and_,or_
from app.db import models as m

def columns(row,exclude=()):
    return {col.name:getattr(row,'details' if col.name=='metadata' else col.name) for col in row.__table__.columns if col.name not in exclude}

def latest_assessments():
    return select(m.AiRelevanceAssessment.vulnerability_id.label('vulnerability_id'),m.AiRelevanceAssessment.result.label('result'),
        m.AiRelevanceAssessment.id.label('assessment_id'),m.SourceObservation.id.label('observation_id'),m.SourceObservation.source_id.label('source_id'),
        func.row_number().over(partition_by=(m.AiRelevanceAssessment.vulnerability_id,m.SourceObservation.source_id,m.SourceObservation.external_id),
            order_by=(m.RawDocument.retrieved_at.desc(),m.AiRelevanceAssessment.evaluated_at.desc(),m.SourceObservation.id.desc())).label('rn')
    ).join(m.SourceObservation,m.SourceObservation.id==m.AiRelevanceAssessment.observation_id).join(m.RawDocument,m.RawDocument.id==m.SourceObservation.raw_document_id).where(m.SourceObservation.parse_status=='parsed').subquery()

def relevance_filter(ranked,result):
    def has(value): return exists(select(1).where(ranked.c.vulnerability_id==m.Vulnerability.id,ranked.c.rn==1,ranked.c.result==value))
    if result=='relevant': return has('relevant')
    if result=='uncertain': return and_(has('uncertain'),~has('relevant'))
    return and_(has('irrelevant'),~has('relevant'),~has('uncertain'))

def product_filter(product):
    identity=product.casefold().strip()
    return exists(select(1).select_from(m.AffectedVersionRange).join(m.Product,m.Product.id==m.AffectedVersionRange.product_id)
        .outerjoin(m.PackageIdentifier,m.PackageIdentifier.id==m.AffectedVersionRange.package_identifier_id)
        .where(m.AffectedVersionRange.vulnerability_id==m.Vulnerability.id,
            or_(func.lower(m.Product.canonical_name)==identity,func.lower(m.PackageIdentifier.package_name)==identity)))

def list_vulnerabilities(session,*,q=None,source=None,product=None,high_severity=False,ai_relevance=None,offset=0,limit=20,sort='modified_desc'):
    query=select(m.Vulnerability).where(m.Vulnerability.deleted_at.is_(None));ranked=latest_assessments()
    if q:query=query.where(m.Vulnerability.canonical_id.ilike('%'+q.replace('%','\\%').replace('_','\\_')+'%',escape='\\'))
    if product:query=query.where(product_filter(product))
    if high_severity:query=query.where(m.Vulnerability.primary_severity.in_(['high','critical','unknown']))
    if source:
        source_id=select(m.Source.id).where(m.Source.source_key==source).scalar_subquery()
        query=query.where(exists(select(1).where(ranked.c.vulnerability_id==m.Vulnerability.id,ranked.c.source_id==source_id,ranked.c.rn==1)))
    if ai_relevance:query=query.where(relevance_filter(ranked,ai_relevance))
    total=session.scalar(select(func.count()).select_from(query.subquery()))
    sort_column=m.Vulnerability.published_at if sort=='published_desc' else m.Vulnerability.modified_at
    rows=session.scalars(query.order_by(sort_column.desc().nullslast(),m.Vulnerability.id).offset(offset).limit(limit)).all()
    return {'items':[columns(row,('metadata',)) for row in rows],'total':total,'offset':offset,'limit':limit,
        'data_status':'source assertions; not verified intelligence','coverage':'bounded source scopes; see /sources'}

def list_sources(session):
    rows=session.scalars(select(m.Source).order_by(m.Source.source_key)).all();items=[]
    for source in rows:
        run=session.scalar(select(m.SyncRun).where(m.SyncRun.source_id==source.id).order_by(m.SyncRun.started_at.desc(),m.SyncRun.id).limit(1))
        item=columns(source,('metadata',))
        item['last_sync']=str(run.id) if run else None
        item['latest_error']=run.error_summary if run else None
        item['records']={'raw_documents':session.scalar(select(func.count()).select_from(m.RawDocument).where(m.RawDocument.source_id==source.id)),
            'processed_observations':session.scalar(select(func.count()).select_from(m.SourceObservation).where(m.SourceObservation.source_id==source.id,m.SourceObservation.parse_status=='parsed'))}
        items.append(item)
    return {'items':items,'total':len(items),'status_semantics':'Sync status concerns declared scope; last_success_at is never a research-probe date'}

def list_sync_runs(session,source=None,offset=0,limit=20):
    query=select(m.SyncRun)
    if source: query=query.where(m.SyncRun.source_id==select(m.Source.id).where(m.Source.source_key==source).scalar_subquery())
    total=session.scalar(select(func.count()).select_from(query.subquery()))
    items=[columns(row) for row in session.scalars(query.order_by(m.SyncRun.started_at.desc(),m.SyncRun.id).offset(offset).limit(limit))]
    return {'items':items,'total':total,'offset':offset,'limit':limit}

def vulnerability_detail(session,id):
    try:uuid=UUID(id)
    except ValueError:uuid=None
    vulnerability=session.scalar(select(m.Vulnerability).where(or_(m.Vulnerability.id==uuid,m.Vulnerability.canonical_id==id),m.Vulnerability.deleted_at.is_(None)))
    if vulnerability is None:return None
    id=vulnerability.id;result=columns(vulnerability)
    observations=list(session.scalars(select(m.SourceObservation).join(m.AiRelevanceAssessment,m.AiRelevanceAssessment.observation_id==m.SourceObservation.id)
        .where(m.AiRelevanceAssessment.vulnerability_id==id).order_by(m.SourceObservation.retrieved_at.desc(),m.SourceObservation.created_at.desc())))
    ranked=latest_assessments();current_ids=set(session.scalars(select(ranked.c.observation_id).where(ranked.c.vulnerability_id==id,ranked.c.rn==1)))
    sources={row.id:row.source_key for row in session.scalars(select(m.Source))}
    raw_map={r.id:r for r in session.scalars(select(m.RawDocument).where(m.RawDocument.id.in_([o.raw_document_id for o in observations])))}
    result['source_variants']=[];result['source_documents']=[];seen=set()
    for observation in observations:
        payload=observation.normalized_payload
        result['source_variants'].append({'source':sources[observation.source_id],'external_id':observation.external_id,
            'observation_id':str(observation.id),'raw_document_id':str(observation.raw_document_id),'is_current':observation.id in current_ids,
            'title':payload.get('title'),'description':payload.get('description'),'published_at':payload.get('published_at'),'modified_at':payload.get('modified_at'),
            'record_status':payload.get('record_status'),'field_provenance':payload.get('field_provenance'),'lineage':payload.get('upstream_lineage'),
            'verification_status':'pending','normalizer_version':observation.normalizer_version})
        if observation.raw_document_id not in seen:
            raw=raw_map[observation.raw_document_id];seen.add(raw.id)
            result['source_documents'].append({**columns(raw,('raw_payload','parsed_payload','metadata')),
                'raw_document_id':str(raw.id),'source_key':sources[raw.source_id],'source_published_at':payload.get('published_at'),'source_modified_at':payload.get('modified_at'),
                'locator':observation.raw_locator,'untrusted':True})
    result['external_identifiers']=[columns(row) for row in session.scalars(select(m.ExternalIdentifier).join(m.VulnerabilityIdentifier,m.VulnerabilityIdentifier.identifier_id==m.ExternalIdentifier.id).where(m.VulnerabilityIdentifier.vulnerability_id==id))]
    ranges=list(session.scalars(select(m.AffectedVersionRange).where(m.AffectedVersionRange.vulnerability_id==id)))
    result['affected_versions']=[{**columns(row),'source_key':sources[row.source_id],'is_current':row.observation_id in current_ids} for row in ranges]
    result['cvss_assessments']=[{**columns(row),'source_key':sources[row.source_id],'is_current':row.observation_id in current_ids} for row in session.scalars(select(m.CvssAssessment).where(m.CvssAssessment.vulnerability_id==id))]
    product_ids={r.product_id for r in ranges}
    # Products without ranges remain visible through current normalized source assertions.
    for o in observations:
        if o.id not in current_ids:continue
        from app.services.products import canonicalize
        for product in o.normalized_payload.get('products') or []:
            identity=canonicalize(name=product['name'],ecosystem=product.get('ecosystem'),vendor=product.get('vendor'))
            if identity['ecosystem']=='unknown':identity['canonical_key']+=':'+sources[o.source_id]
            product_ids.update(session.scalars(select(m.Product.id).where(m.Product.canonical_key==identity['canonical_key'])))
    result['products']=[columns(row) for row in session.scalars(select(m.Product).where(m.Product.id.in_(product_ids)))]
    result['cwe']=[columns(row) for row in session.scalars(select(m.Weakness).join(m.VulnerabilityWeakness,m.VulnerabilityWeakness.weakness_id==m.Weakness.id).where(m.VulnerabilityWeakness.vulnerability_id==id).distinct())]
    result['references']=[{**columns(reference),'observation_id':str(link.observation_id),'is_current':link.observation_id in current_ids}
        for reference,link in session.execute(select(m.Reference,m.VulnerabilityReference).join(m.VulnerabilityReference,m.VulnerabilityReference.reference_id==m.Reference.id).where(m.VulnerabilityReference.vulnerability_id==id))]
    result['ai_relevance']=[{**columns(row),'is_current':row.observation_id in current_ids} for row in session.scalars(select(m.AiRelevanceAssessment).where(m.AiRelevanceAssessment.vulnerability_id==id))]
    result['known_exploitation']=[columns(row) for row in session.scalars(select(m.KnownExploitation).where(m.KnownExploitation.vulnerability_id==id))]
    result['verification_status']='pending'
    return result

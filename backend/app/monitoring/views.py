from uuid import UUID
from sqlalchemy import select,func,union_all,literal
from app.db import models as m
from app.repositories import queries
from app.enrichment import queries as enriched
from app.monitoring.schemas import SecurityIntelligenceObject,SourceReference,IntelligencePage,SourceStatusPage,AssetRiskPage

def cvss_view(row):
    score=float(row['base_score']);version=row['version'];level=row.get('severity')
    if level in (None,'unknown'):
        level='critical' if version!='2.0' and score>=9 else 'high' if score>=7 else 'medium' if score>=4 else 'low' if score>0 else 'info'
        basis='DERIVED_FROM_SOURCE_SCORE_THRESHOLDS'
    else:basis='SOURCE_ASSERTED'
    return {'version':version,'score':score,'severity':level.upper(),'source':row['source_key'],'provider':row['provider'],
        'observation_id':str(row['observation_id']),'is_current':row['is_current'],'severity_basis':basis,'verification_status':'SOURCE_ASSERTED'}

def has_verified_exploit(session,poc):
    if poc.status!='confirmed' or poc.usability_status!='verified_usable':return False
    from app.assets.remediation import trusted_claim
    claims=list(session.scalars(select(m.Claim).where(m.Claim.poc_candidate_id==poc.id,m.Claim.vulnerability_id==poc.vulnerability_id)))
    trusted=[c.id for c in claims if trusted_claim(session,c)]
    if not trusted:return False
    return session.scalar(select(m.VerificationResult.id).join(m.Claim,m.Claim.id==m.VerificationResult.claim_id)
        .join(m.VerificationEvidence,m.VerificationEvidence.verification_result_id==m.VerificationResult.id)
        .join(m.Evidence,m.Evidence.id==m.VerificationEvidence.evidence_id)
        .where(m.Claim.id.in_(trusted),m.VerificationResult.claim_revision==m.Claim.revision,
            m.VerificationResult.status=='confirmed',m.VerificationResult.verified_by_type=='human',
            m.Evidence.details['validated_exploit'].as_boolean().is_(True)).limit(1)) is not None

def document_links(session,target):
    result=[]
    for relation,doc,claim in session.execute(select(m.KnowledgeVulnerabilityRelation,m.KnowledgeDocument,m.Claim)
        .join(m.KnowledgeDocument,m.KnowledgeDocument.id==m.KnowledgeVulnerabilityRelation.knowledge_document_id)
        .join(m.Claim,m.Claim.id==m.KnowledgeVulnerabilityRelation.claim_id)
        .where(m.KnowledgeVulnerabilityRelation.vulnerability_id==target,m.KnowledgeDocument.deleted_at.is_(None))
        .order_by(m.KnowledgeDocument.published_at.desc().nullslast(),m.KnowledgeDocument.id).limit(50)):
        result.append({'document_id':str(doc.id),'title':doc.title,'type':doc.document_type,'url':doc.url,'relation_status':'CANDIDATE' if not claim.adopted else claim.verification_status.upper(),
            'claim_id':str(claim.id),'basis':claim.value_json,'raw_document_id':str(doc.raw_document_id),'published_time':doc.published_at})
    return result

def explicit_fixes(session,target):
    rows=[];latest={}
    observations=session.scalars(select(m.SourceObservation).where(m.SourceObservation.parse_status=='parsed',
        m.SourceObservation.details['vulnerability_ids'].contains([str(target)])).order_by(m.SourceObservation.created_at.desc(),m.SourceObservation.id.desc()))
    for observation in observations:
        key=(observation.source_id,observation.external_id);current=key not in latest;latest[key]=True
        source=session.get(m.Source,observation.source_id)
        for fix in (observation.normalized_payload or {}).get('fixed_versions') or []:
            rows.append({'version':fix['version'],'package':fix.get('package'),'source':source.source_key,'is_current':current,
                'verification_status':'SOURCE_ASSERTED','observation_id':str(observation.id),'raw_document_id':str(observation.raw_document_id),
                'locator':fix.get('locator')})
    return rows

def vulnerability_view(session,identifier):
    detail=queries.vulnerability_detail(session,str(identifier))
    if detail is None:raise LookupError('Vulnerability not found')
    target=detail['id'];domain=enriched.aggregate(session,target)
    public_claim_ids={str(c.id) for c in session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==target,m.Claim.asset_component_id.is_(None)))}
    pocs=list(session.scalars(select(m.PocCandidate).where(m.PocCandidate.vulnerability_id==target,m.PocCandidate.status!='rejected').limit(100)))
    verified=any(has_verified_exploit(session,p) for p in pocs)
    job=session.scalar(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==target,m.EnrichmentJob.enrichment_type=='poc').order_by(m.EnrichmentJob.created_at.desc()).limit(1))
    searched='NOT_RUN' if job is None else 'FAILED' if job.status=='failed' else 'PARTIAL' if job.status in ('partial','running','queued') else 'COMPLETED'
    refs=[SourceReference(source=x['source_key'],raw_document_id=str(x['raw_document_id']),hash=x['content_hash'],reference=x['source_url'],locator=x['locator'] or {},retrieved_at=x['retrieved_at'],published_at=x['source_published_at']) for x in detail['source_documents']]
    return SecurityIntelligenceObject(id=str(target),type='vulnerability',source=sorted({x.source for x in refs}),title=detail['title'] or detail['canonical_id'],
        cve_id=detail['canonical_id'] if detail['canonical_id'].startswith('CVE-') else None,
        affected_product=[p['canonical_name'] for p in detail['products']],affected_version=detail['affected_versions'],
        fixed_versions=explicit_fixes(session,target),
        cvss=[cvss_view(x) for x in detail['cvss_assessments']],cwe=[x['cwe_id'] for x in detail['cwe']],published_time=detail['published_at'],references=refs,
        status='CONFLICT' if any(str(c['id']) in public_claim_ids and c['verification_status']=='CONFLICT' for c in domain['claims']) else 'SOURCE_ASSERTED',publication_status=detail['status'],
        poc_status='VERIFIED_EXPLOIT' if verified else 'POC_CANDIDATE' if pocs else 'NO_EVIDENCE',poc_search_status=searched,
        pocs=[enriched.serialize(p) for p in pocs],patches=domain['patches'],related_documents=document_links(session,target),evidence=[e for e in domain['evidence'] if str(e['claim_id']) in public_claim_ids],
        limitations=['Source facts are not blanket-confirmed; conflicting versions and CVSS remain separate.',
            'NO_EVIDENCE means no stored qualifying candidate, not proof no exploit exists; check poc_search_status.',
            'Assets require the authenticated assets endpoint. Research links are candidates, not impact evidence.'])

def document_view(session,identifier):
    doc=session.get(m.KnowledgeDocument,UUID(str(identifier)))
    if doc is None or doc.deleted_at and not doc.details.get('superseded_by'):raise LookupError('Knowledge document not found')
    raw=session.get(m.RawDocument,doc.raw_document_id);source=session.get(m.Source,doc.source_id)
    return SecurityIntelligenceObject(id=str(doc.id),type=doc.document_type if doc.document_type in ('paper','blog','advisory','analysis') else 'knowledge',source=[source.source_key],
        title=doc.title,published_time=doc.published_at,modified_time=doc.modified_at,edition=doc.edition,is_current=not bool(doc.deleted_at),
        canonical_publication_id=doc.details.get('canonical_publication_id'),status='CANDIDATE',publication_status='SUPERSEDED' if doc.deleted_at else doc.publication_status or 'source_asserted',
        references=[SourceReference(source=source.source_key,raw_document_id=str(raw.id),hash=raw.content_hash,reference=raw.source_url,
            locator={'xml_paths':doc.details.get('extraction_xml_paths',[]),'json_pointers':doc.details.get('extraction_json_pointers',[])},retrieved_at=raw.retrieved_at,published_at=doc.published_at)],
        limitations=['Metadata/limited excerpt only; publication does not confirm an associated vulnerability.','Canonical publication URL: '+doc.url])

def intelligence_page(session,*,kind=None,q=None,offset=0,limit=20):
    # Pagination happens in SQL over both entity types, not after loading everything.
    vuln=select(m.Vulnerability.id.label('id'),literal('vulnerability').label('kind'),m.Vulnerability.published_at.label('published'),m.Vulnerability.title.label('title'),m.Vulnerability.canonical_id.label('identifier')).where(m.Vulnerability.deleted_at.is_(None))
    doc=select(m.KnowledgeDocument.id.label('id'),m.KnowledgeDocument.document_type.label('kind'),m.KnowledgeDocument.published_at.label('published'),m.KnowledgeDocument.title.label('title'),m.KnowledgeDocument.external_id.label('identifier')).where(m.KnowledgeDocument.deleted_at.is_(None))
    combined=union_all(vuln,doc).subquery();query=select(combined)
    if kind:query=query.where(combined.c.kind==kind)
    if q:
        term='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        query=query.where(combined.c.title.ilike(term,escape='\\')|combined.c.identifier.ilike(term,escape='\\'))
    total=session.scalar(select(func.count()).select_from(query.subquery()))
    rows=session.execute(query.order_by(combined.c.published.desc().nullslast(),combined.c.id).offset(offset).limit(limit)).mappings()
    return IntelligencePage(items=[vulnerability_view(session,x['id']) if x['kind']=='vulnerability' else document_view(session,x['id']) for x in rows],total=total,offset=offset,limit=limit)

def source_status(session):
    data=queries.list_sources(session)
    categories={}
    for item in data['items']:
        key=item['source_key'];category='vulnerability_database' if key in ('CVE_LIST','OSV','NVD') else 'exploitation_catalog' if key=='CISA_KEV' else 'vendor_advisory' if key.startswith('VENDOR_') else 'blog' if key.startswith('RSS_') else 'paper' if key=='ARXIV' else 'security_community' if key=='GHSA' else item['category']
        item['source_category']=category;categories[key]=category
    collected=set(session.scalars(select(m.Source.source_key).join(m.SourceObservation,m.SourceObservation.source_id==m.Source.id)
        .where(m.SourceObservation.parse_status=='parsed').distinct()))
    return SourceStatusPage(items=data['items'],total=data['total'],source_category_count=len(set(categories.values())),
        collected_source_category_count=len({categories[key] for key in collected if key in categories}))

def owned_risks(session,identifier,actor,*,offset=0,limit=20):
    target=enriched.target_id(session,identifier)
    if target is None:raise LookupError('Vulnerability not found')
    from app.assets.queries import latest_risks
    ids=session.scalars(select(m.Asset.id).join(m.AssetRiskSnapshot,m.AssetRiskSnapshot.asset_id==m.Asset.id)
        .where(m.AssetRiskSnapshot.vulnerability_id==target,m.Asset.owner_principal==actor,m.Asset.deleted_at.is_(None)).distinct().order_by(m.Asset.id))
    items=[row for asset_id in ids for row in latest_risks(session,asset_id,actor) if str(row.get('vulnerability_id'))==str(target)]
    return AssetRiskPage(items=items[offset:offset+limit],total=len(items),offset=offset,limit=limit)

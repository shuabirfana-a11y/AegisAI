"""All business logic stays in deterministic Phase6–8 services, outside roles."""
from uuid import UUID
from datetime import timedelta
from sqlalchemy import select,func,or_
from app.db import models as m
from app.repositories import queries as core
from app.enrichment import queries as intel
from app.assets import queries as assets
from app.assets.inventory import owned_asset
from app.assets.remediation import trusted_claim
from app.utils.time import utcnow

def evidence_refs(session,target,claim_id=None):
    from app.tooling.provenance import current_support_ids
    refs=[];current={}
    query=intel.query(session,target,'evidence')
    # Registry context is neutral and append-only. Its obsolete observations
    # must not crowd current security witnesses out of the bounded Tool receipt.
    # Full historical metadata remains available through the evidence API.
    registry_editions=select(m.SourceObservation.id,
        func.row_number().over(partition_by=(m.SourceObservation.source_id,m.SourceObservation.external_id),
            order_by=(m.SourceObservation.retrieved_at.desc(),m.SourceObservation.created_at.desc(),
                      m.SourceObservation.id.desc())).label('edition_rank'))\
        .where(m.SourceObservation.parse_status=='parsed').subquery()
    query=query.where(or_(m.Evidence.evidence_type!='package_registry_metadata',
        m.Evidence.stance!='neutral',m.Evidence.observation_id.in_(
            select(registry_editions.c.id).where(registry_editions.c.edition_rank==1))))
    if claim_id is not None:query=query.where(m.Evidence.claim_id==UUID(str(claim_id)))
    for row in session.scalars(query.limit(100)):
        c=session.get(m.Claim,row.claim_id)
        if c.id not in current:current[c.id]=current_support_ids(session,c)
        refs.append({'evidence_id':str(row.id),'claim_id':str(c.id),'claim_revision':c.revision,
            'source_id':str(row.source_id),'raw_document_id':str(row.raw_document_id),'url':row.source_url,
            'locator':row.locator,'retrieved_at':row.retrieved_at,'stance':row.stance,
            'verified':str(row.id) in current[c.id],'content_trust_level':'UNTRUSTED_EXTERNAL_CONTENT'})
    return refs

def _claim(session,id,actor):
    c=session.get(m.Claim,UUID(str(id)))
    if c is None:raise LookupError('Claim not found')
    if c.asset_component_id:
        component=session.get(m.AssetComponent,c.asset_component_id)
        owned_asset(session,component.asset_id,actor)
    return c

def _intelligence_context(session,target,refs):
    data=intel.aggregate(session,target)
    visible={r['evidence_id'] for r in refs if r.get('evidence_id')}
    rows=data.get('evidence',[])
    data['evidence']=[r for r in rows if not (
        r.get('evidence_type')=='package_registry_metadata' and r.get('stance')=='neutral')
        or str(r['id']) in visible]
    if len(rows)!=len(data['evidence']):
        data['registry_history_omitted_from_tool_context']=len(rows)-len(data['evidence'])
    return data

def execute_local(session,name,args,actor):
    if name in ('analyze_risk_snapshot','analyze_asset_impact_snapshot','prioritize_remediation_snapshot'):
        from app.tooling.analysis import execute_analysis
        return execute_analysis(session,name,args,actor)
    if name in ('evaluate_evidence_snapshot','validate_claim_snapshot','compare_claim_snapshot'):
        from app.tooling.verification import execute_verification
        return execute_verification(session,name,args,actor)
    data={};refs=[];warnings=[]
    target=intel.target_id(session,args['target']) if 'target' in args else None
    if 'target' in args and target is None:raise LookupError('Vulnerability not found')
    if target:refs=evidence_refs(session,target,args.get('claim_id') if name=='get_evidence' else None)
    if name in ('search_vulnerabilities','get_recent_intelligence'):
        data=core.list_vulnerabilities(session,q=args.get('q'),product=args.get('product'),high_severity=args.get('high_severity',False),ai_relevance=args.get('ai_relevance'),limit=args.get('limit',20))
        if args.get('days'):
            cutoff=utcnow()-timedelta(days=args['days'])
            # Time filtering occurs before pagination, not only on the returned page.
            q=select(m.Vulnerability).where(m.Vulnerability.deleted_at.is_(None),m.Vulnerability.published_at>=cutoff)
            if args.get('q'):q=q.where(m.Vulnerability.canonical_id.ilike('%'+args['q'].replace('%','\\%').replace('_','\\_')+'%',escape='\\'))
            if args.get('product'):q=q.where(core.product_filter(args['product']))
            if args.get('high_severity'):q=q.where(m.Vulnerability.primary_severity.in_(['high','critical','unknown']))
            if args.get('ai_relevance'):q=q.where(core.relevance_filter(core.latest_assessments(),args['ai_relevance']))
            from sqlalchemy import func
            data={'items':[core.columns(r) for r in session.scalars(q.order_by(m.Vulnerability.published_at.desc(),m.Vulnerability.id).limit(args.get('limit',20)))],
                'total':session.scalar(select(func.count()).select_from(q.subquery())),'window_days':args['days'],'coverage':'Locally collected records only'}
    elif name=='get_vulnerability':
        data=core.vulnerability_detail(session,str(target));data['intelligence']=_intelligence_context(session,target,refs)
        if args.get('candidate_reference'):
            from app.tooling.candidate_evidence import candidate_evidence
            observed,_=candidate_evidence(session,target,args['candidate_reference'],refs)
            data['candidate_reference']=observed['candidate_reference']
            warnings.append('Specified patch reference is an observation only; commit validation and installation are not inferred.')
        # Sources without extracted claim evidence still retain raw provenance.
        refs.extend({'raw_document_id':str(r['id']),'source_id':str(r['source_id']),'url':r['source_url'],
            'locator':r['locator'],'content_trust_level':'UNTRUSTED_EXTERNAL_CONTENT'} for r in data['source_documents'])
    elif name=='get_product':
        row=session.get(m.Product,UUID(str(args['id'])))
        if row is None or row.deleted_at:raise LookupError('Product not found')
        data=core.columns(row)
    elif name in ('get_claims','get_evidence','get_timeline'):
        if name=='get_evidence' and args.get('candidate_reference'):
            from app.tooling.candidate_evidence import candidate_evidence
            data,refs=candidate_evidence(session,target,args['candidate_reference'],refs,
                claim_id=args.get('claim_id'),limit=args.get('limit',20))
            warnings.append('Candidate reference checked against collected sources only; no remote fetch, commit validation, patch applicability or installation is inferred.')
        elif name=='get_evidence' and args.get('claim_id'):
            claim=session.get(m.Claim,UUID(args['claim_id']))
            if claim is None or claim.vulnerability_id!=target:raise PermissionError('Claim target mismatch')
            from sqlalchemy import func
            q=intel.query(session,target,'evidence').where(m.Evidence.claim_id==claim.id)
            data={'items':[intel.serialize(e,session) for e in session.scalars(q.limit(args.get('limit',20)))],
                  'total':session.scalar(select(func.count()).select_from(q.subquery())),
                  'offset':0,'limit':args.get('limit',20),'claim_id':str(claim.id)}
        else:data=intel.page(session,target,{'get_claims':'claims','get_evidence':'evidence','get_timeline':'timeline'}[name],limit=args.get('limit',20))
        if name=='get_claims':
            for c in data['items']:c['trusted']=trusted_claim(session,session.get(m.Claim,c['id']))
    elif name=='relation_query':
        detail=core.vulnerability_detail(session,str(target))
        data={k:detail[k] for k in ('id','canonical_id','title','published_at','primary_severity','products','affected_versions','references')}
        data.update({k:intel.page(session,target,k,limit=args.get('limit',20)) for k in ('claims','patches','pocs')})
    elif name in ('find_vendor_advisories','find_poc_candidates','find_patch_candidates','get_epss','get_known_exploitation','investigate_vulnerability'):
        if args.get('refresh'):raise ValueError('Refresh runs only in isolated worker service')
        kind={'find_poc_candidates':'pocs','find_patch_candidates':'patches','get_epss':'epss','get_known_exploitation':'known_exploitation'}.get(name)
        data=intel.page(session,target,kind,limit=args.get('limit',20)) if kind else _intelligence_context(session,target,refs)
        if name=='find_vendor_advisories':data={'items':[c for c in data['claims'] if c['claim_type']=='VENDOR_CONFIRMED'],'source_assertions_only':True}
        if kind in ('pocs','patches'):
            warnings.append('Candidates are static associations. PoC usability and patch applicability are not inferred; no code is executed.')
    elif name in ('get_verification_result','get_evidence_for_claim','verify_claim','request_review'):
        c=_claim(session,args['claim_id'],actor);refs=evidence_refs(session,c.vulnerability_id) if c.vulnerability_id else []
        if name=='get_evidence_for_claim':data={'items':[intel.serialize(e,session) for e in session.scalars(select(m.Evidence).where(m.Evidence.claim_id==c.id))]}
        elif name=='get_verification_result':data={'claim':intel.serialize(c),'trusted':trusted_claim(session,c),
            'items':[intel.serialize(r) for r in session.scalars(select(m.VerificationResult).where(m.VerificationResult.claim_id==c.id,m.VerificationResult.claim_revision==c.revision))]}
        elif name=='verify_claim':
            from app.enrichment.verification import VerificationService
            from app.enrichment.integration import IntelligenceIntegrationService
            r=VerificationService.verify(session,c);IntelligenceIntegrationService.adopt(session,c,r)
            data={'claim':intel.serialize(c),'verification':intel.serialize(r),'trusted':trusted_claim(session,c)}
        else:
            from app.enrichment.repository import ensure_review,digest
            r=ensure_review(session,c,'INSUFFICIENT_EVIDENCE',args['reason'],fingerprint=digest([str(c.id),c.revision,args['reason']]),now=utcnow())
            data={'review':intel.serialize(r) if r else None}
    elif name=='verify_poc_candidate':
        p=session.get(m.PocCandidate,UUID(str(args['id'])))
        if p is None:raise LookupError('Candidate not found')
        from app.enrichment.verification import VerificationService
        cs=list(session.scalars(select(m.Claim).where(m.Claim.poc_candidate_id==p.id)))
        data={'candidate':intel.serialize(p),'verification':[intel.serialize(VerificationService.verify(session,c)) for c in cs],
            'usability':'NOT_EXECUTED; existing usability status only'};refs=evidence_refs(session,p.vulnerability_id)
    elif name=='detect_conflicts':
        from app.enrichment.conflict import ConflictDetectionService
        ConflictDetectionService.detect(session,target)
        data=intel.page(session,target,'conflicts',limit=args.get('limit',20))
    elif name=='list_assets':
        data={'items':[intel.serialize(r) for r in session.scalars(select(m.Asset).where(m.Asset.owner_principal==actor,m.Asset.deleted_at.is_(None)).order_by(m.Asset.id).limit(100))]}
    elif name=='get_asset':data=assets.asset_detail(session,UUID(str(args['asset_id'])),actor)
    elif name=='get_asset_risks':
        ids=[UUID(str(args['asset_id']))] if args.get('asset_id') else list(session.scalars(select(m.Asset.id).where(m.Asset.owner_principal==actor,m.Asset.deleted_at.is_(None)).order_by(m.Asset.id).limit(9)))
        if len(ids)>8:raise ValueError('Select an asset; owner inventory exceeds bounded query size')
        items=[]
        for id in ids:
            a=owned_asset(session,id,actor)
            for r in assets.latest_risks(session,id,actor):
                vulnerability=session.get(m.Vulnerability,UUID(r['vulnerability_id']))
                items.append({**r,'asset_id':str(id),'asset_name':a.name,'is_demo':a.is_demo,
                    'published_at':vulnerability.published_at if vulnerability else None})
        data={'items':items[:args.get('limit',100)],'total':len(items),'coverage':'Owner-specific local inventory; unresolved and stale rows retain uncertainty'}
        for r in data['items']:
            if r.get('vulnerability_id'):refs.extend(evidence_refs(session,UUID(r['vulnerability_id'])))
    elif name=='explain_asset_risk':data=assets.explain_asset_risk(session,UUID(str(args['asset_id'])),UUID(str(args['snapshot_id'])),actor)
    elif name=='get_asset_risk_changes':data=assets.get_asset_risk_changes(session,UUID(str(args['asset_id'])),actor)
    elif name=='resolve_component':
        from app.assets.identity import resolve_component
        data=resolve_component(session,args)
    elif name=='inspect_component_version':
        from app.tooling.investigation import inspect_component_version
        data=inspect_component_version(session,args,actor)
    elif name=='match_component_vulnerabilities':
        c=session.get(m.AssetComponent,UUID(str(args['component_id'])))
        if c is None or c.deleted_at:raise LookupError('Component not found')
        owned_asset(session,c.asset_id,actor)
        from app.assets.matching import AssetVulnerabilityMatcher
        data=AssetVulnerabilityMatcher.match(session,c)
    elif name=='get_remediation':
        from app.assets.remediation import get_remediation
        data=get_remediation(session,target,UUID(str(args['package_id'])))
    elif name=='semantic_search':
        from app.knowledge.retrieval import SemanticSearch
        from app.knowledge.embedding import local_embedding,MODEL
        from app.knowledge.index import CHUNKER
        limit=args.get('limit',5)
        if not args['query'].strip() or len(args['query'])>2000 or not 1<=limit<=20:
            raise ValueError('Invalid semantic query')
        # Empty/stale/deleted corpora need no embedding inference. Keep exactly
        # the current-model/revision/chunker constraints used by SemanticSearch.
        searchable=session.scalar(select(m.KnowledgeEmbedding.id)
            .join(m.KnowledgeChunk,m.KnowledgeEmbedding.chunk_id==m.KnowledgeChunk.id)
            .join(m.KnowledgeDocument,m.KnowledgeChunk.document_id==m.KnowledgeDocument.id)
            .join(m.RawDocument,m.KnowledgeChunk.raw_document_id==m.RawDocument.id)
            .where(m.KnowledgeEmbedding.model_version==MODEL,
                m.KnowledgeChunk.document_revision==m.KnowledgeDocument.revision,
                m.KnowledgeChunk.chunker_version==CHUNKER,
                m.KnowledgeDocument.deleted_at.is_(None)).limit(1))
        data={'items':[] if searchable is None else
            SemanticSearch.search(session,args['query'],local_embedding(),limit=limit)}
        refs=[{k:v for k,v in r.items() if k not in ('content','score','title')} for r in data['items']]
    elif name=='get_system_status':data={'sources':core.list_sources(session),'sync_runs':core.list_sync_runs(session,limit=10)}
    else:raise ValueError('Unregistered adapter')
    from app.tooling.investigation import decorate_evidence
    refs=decorate_evidence(session,refs)
    empty=isinstance(data,dict) and 'items' in data and not data['items']
    return {'status':'no_result' if empty else 'success','data':data,'evidence_refs':refs,'warnings':warnings}

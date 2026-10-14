"""SQL entity projection. No collection, matching writes, model calls or risk rules."""
from hashlib import sha256
from datetime import timedelta
import json
from itertools import islice
from uuid import UUID, uuid5, NAMESPACE_URL
from urllib.parse import urlsplit, urlunsplit
from sqlalchemy import select, func, or_
from app.db import models as m
from app.enrichment.queries import target_id
from app.enrichment.contracts import API_VERIFY
from app.enrichment.evidence import current_evidence
from app.assets.remediation import trusted_claim
from app.assets.inventory import owned_asset
from app.enrichment.versions import intervals, canonical_value
from app.utils.time import utcnow
from app.investigation_api.projection import public_copy
from app.knowledge.graph_schemas import KnowledgeNode, KnowledgeEdge, KnowledgeGraph, KnowledgeGraphPage


def identity(kind,record):return kind.lower()+':'+str(uuid5(NAMESPACE_URL,kind+':'+str(record)))


def reference(url):
    try:
        value=urlsplit(url or '')
        if value.scheme not in ('http','https') or not value.hostname or value.username or value.password:return None
        return urlunsplit((value.scheme,value.netloc,value.path,'',''))
    except ValueError:return None


class Builder:
    def __init__(self):self.nodes={};self.edges={};self.warnings=[];self.truncated=False;self.size=0
    def warning(self,value):
        if value not in self.warnings:self.warnings.append(value)
    def take(self,rows,budget):
        rows=list(rows)
        if len(rows)>budget:self.truncated=True;self.warning('GRAPH_TRUNCATED: collection budget reached')
        return rows[:budget]
    def nested(self,value,depth=0,counter=None):
        counter=counter if counter is not None else [0]
        counter[0]+=1
        if depth>5 or counter[0]>128:
            self.truncated=True;self.warning('NESTED_VALUE_TRUNCATED: use source record for complete content');return None
        if isinstance(value,str):
            if len(value)>600:self.truncated=True;self.warning('NESTED_VALUE_TRUNCATED: use source record for complete content')
            return value[:600]
        if isinstance(value,(list,tuple)):
            if len(value)>16:self.truncated=True;self.warning('NESTED_VALUE_TRUNCATED: use source record for complete content')
            return [self.nested(x,depth+1,counter) for x in value[:16]]
        if isinstance(value,dict):
            if len(value)>16:self.truncated=True;self.warning('NESTED_VALUE_TRUNCATED: use source record for complete content')
            return {str(k)[:100]:self.nested(v,depth+1,counter) for k,v in islice(value.items(),16)}
        return value
    def reserve(self,value):
        size=len(json.dumps(value,ensure_ascii=False,default=str).encode('utf-8'))
        if self.size+size>96*1024:
            self.truncated=True;self.warning('GRAPH_TRUNCATED: wire budget reached');return False
        self.size+=size;return True
    def node(self,kind,record,label,**data):
        id=identity(kind,record)
        if id not in self.nodes:
            if len(self.nodes)>=160:self.truncated=True;return id
            node=KnowledgeNode(id=id,type=kind,label=str(label or 'UNKNOWN')[:160],data=public_copy(self.nested(data)))
            if not self.reserve(node.model_dump(mode='json')):return id
            self.nodes[id]=node
        return id
    def edge(self,kind,source,target,status,records,claims=(),evidence=(),historical=False):
        if source not in self.nodes or target not in self.nodes:self.truncated=True;return
        records=tuple(dict.fromkeys(str(x) for x in records))[:32]
        id=identity('edge',(kind,source,target,records))
        if id not in self.edges:
            if len(self.edges)>=320:self.truncated=True;return
            edge=KnowledgeEdge(id=id,type=kind,source=source,target=target,status=status,
                source_records=records,claim_ids=tuple(dict.fromkeys(claims))[:32],evidence_ids=tuple(dict.fromkeys(evidence))[:32],historical_snapshot=historical)
            if self.reserve(edge.model_dump(mode='json')):self.edges[id]=edge


def same_range_assertion(claim,range,ecosystem):
    if claim.claim_type not in ('AFFECTS_VERSION','affected_version'):return False
    expected={'ecosystem':ecosystem,'raw_expression':range.raw_expression,'events':range.events,
        'explicit_versions':range.explicit_versions,'range_type':range.range_type,'parse_status':range.parse_status}
    if len(json.dumps(claim.value_json,default=str))>8192 or len(json.dumps(expected,default=str))>8192:return False
    try:
        left=intervals(claim.value_json);right=intervals(expected)
        return left is not None and left==right
    except (ValueError,TypeError,KeyError,IndexError):return False


def reviewed_support(session,claim,valid,builder):
    """Confirmation uses one intersection of intact/current/fresh/value-matched/attested proofs."""
    now=utcnow()
    review=session.scalar(select(m.VerificationResult).where(m.VerificationResult.claim_id==claim.id,
        m.VerificationResult.claim_revision==claim.revision,m.VerificationResult.status=='confirmed').limit(1))
    if review is None or review.verified_at>now+timedelta(minutes=5):return set()
    declared=review.details.get('observed_evidence_ids',[])
    links=list(session.scalars(select(m.VerificationEvidence.evidence_id).where(
        m.VerificationEvidence.verification_result_id==review.id,m.VerificationEvidence.claim_id==claim.id).limit(33)))
    if not isinstance(declared,list) or len(declared)>32 or len(links)>32:
        builder.truncated=True;builder.warning('REVIEW_BUDGET: confirmation withheld for oversized attestation');return set()
    known={str(x) for x in (*declared,*links)}
    result=set()
    for e,_,current in valid.values():
        if (e.claim_id!=claim.id or str(e.id) not in known or not current or e.stance!='support'
            or not now-timedelta(days=30)<=e.retrieved_at<=min(now,review.verified_at)+timedelta(minutes=5)):
            continue
        if len(json.dumps(e.observed_value,default=str))>8192 or len(json.dumps(claim.value_json,default=str))>8192:
            builder.warning('VALUE_BUDGET: oversized assertion cannot establish confirmation');continue
        try:
            if canonical_value(claim.claim_type,e.observed_value or {})==canonical_value(claim.claim_type,claim.value_json):result.add(e.id)
        except (ValueError,TypeError,KeyError,IndexError,AttributeError):
            builder.warning('INVALID_ASSERTION: malformed evidence cannot establish confirmation')
    return result


def build_security_graph(session,identifier,actor,*,include_assets=False,asset_id=None,linked=None):
    if not actor or not actor.strip():raise PermissionError('Authenticated graph actor required')
    target=target_id(session,identifier)
    if target is None:raise LookupError('Vulnerability not found')
    vuln=session.get(m.Vulnerability,target);b=Builder()
    if linked and (linked.get('vulnerability_id')!=str(target) or linked.get('canonical_id')!=vuln.canonical_id):
        raise ValueError('GRAPH_INVESTIGATION_TARGET_MISMATCH')
    cvss=b.take(session.scalars(select(m.CvssAssessment).where(m.CvssAssessment.vulnerability_id==target).order_by(m.CvssAssessment.id).limit(9)),8)
    root=b.node('VULNERABILITY',target,vuln.canonical_id,vulnerability_id=str(target),cve_id=vuln.canonical_id,
        description=(vuln.description or '')[:2400],severity=vuln.primary_severity.upper(),
        cvss=[{'score':float(x.base_score),'severity':x.severity,'version':x.version,'observation_id':str(x.observation_id),'status':'SOURCE_ASSERTED'} for x in cvss])
    claims=b.take(session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==target,m.Claim.asset_component_id.is_(None)).order_by(m.Claim.id).limit(33)),32)
    evidence_rows=b.take(session.scalars(select(m.Evidence).join(m.Claim,m.Evidence.claim_id==m.Claim.id)
        .where(m.Claim.id.in_([c.id for c in claims])).order_by(m.Evidence.id).limit(97)),96) if claims else []
    valid={};statuses={};current={}
    for c in claims:
        count=session.scalar(select(func.count()).select_from(m.Evidence).where(m.Evidence.claim_id==c.id))
        if count>32:
            current[c.id]={};statuses[c.id]='UNKNOWN';b.truncated=True;b.warning('EVIDENCE_BUDGET: confirmation/currentness withheld for oversized claim');continue
        current[c.id]={x['id']:x['is_current'] for x in current_evidence(session,c)}
        statuses[c.id]='CONFIRMED' if trusted_claim(session,c) else 'CANDIDATE' if c.verification_status=='confirmed' else API_VERIFY[c.verification_status]
        if session.scalar(select(m.ConflictRecord.id).where(m.ConflictRecord.status=='open',
            or_(m.ConflictRecord.claim_a_id==c.id,m.ConflictRecord.claim_b_id==c.id)).limit(1)):
            statuses[c.id]='CONFLICT'
    for e in evidence_rows:
        raw=session.get(m.RawDocument,e.raw_document_id);obs=session.get(m.SourceObservation,e.observation_id);source=session.get(m.Source,e.source_id)
        if (raw is None or obs is None or source is None or raw.source_id!=e.source_id or obs.source_id!=e.source_id
            or obs.raw_document_id!=raw.id or sha256(bytes(raw.raw_payload)).hexdigest()!=raw.content_hash
            or sha256(e.excerpt.encode()).hexdigest()!=e.excerpt_hash):
            b.warning('EVIDENCE_INTEGRITY: invalid source/hash omitted');continue
        valid[e.id]=(e,None,current[e.claim_id].get(str(e.id),False))
    supports={c.id:reviewed_support(session,c,valid,b) if statuses[c.id]=='CONFIRMED' else set() for c in claims}
    for c in claims:
        if statuses[c.id]=='CONFIRMED' and not supports[c.id]:
            statuses[c.id]='CANDIDATE';b.warning('CONFIRMATION_WITHHELD: no intact current reviewed support')
    for e,_,is_current in list(valid.values()):
        raw=session.get(m.RawDocument,e.raw_document_id);obs=session.get(m.SourceObservation,e.observation_id);source=session.get(m.Source,e.source_id)
        status=statuses[e.claim_id]
        if status=='CONFIRMED' and e.id not in supports[e.claim_id]:status='CANDIDATE' if is_current else 'UNKNOWN'
        ev=b.node('EVIDENCE',e.id,source.source_key,evidence_id=str(e.id),claim_id=str(e.claim_id),source=source.source_key,
            reference=reference(e.source_url),type=e.evidence_type,verification_status=status,is_current=is_current,
            stance=e.stance,hash=e.excerpt_hash,raw_document_id=str(raw.id),observation_id=str(obs.id),locator=e.locator,
            retrieved_at=e.retrieved_at.isoformat())
        records=('claim:'+str(e.claim_id),'evidence:'+str(e.id),'raw_document:'+str(raw.id))
        b.edge('HAS_EVIDENCE',root,ev,status,records,claims=(str(e.claim_id),),evidence=(str(e.id),))
        valid[e.id]=(e,ev,is_current)
    ranges=b.take(session.scalars(select(m.AffectedVersionRange).where(m.AffectedVersionRange.vulnerability_id==target).order_by(m.AffectedVersionRange.id).limit(33)),32)
    packages={};package_nodes={}
    for r in ranges:
        pkg=session.get(m.PackageIdentifier,r.package_identifier_id);product=session.get(m.Product,r.product_id)
        obs=session.get(m.SourceObservation,r.observation_id);raw=session.get(m.RawDocument,obs.raw_document_id) if obs else None
        if (pkg is None or product is None or product.deleted_at or pkg.product_id!=product.id or obs is None or raw is None
            or obs.source_id!=r.source_id or raw.source_id!=r.source_id or sha256(bytes(raw.raw_payload)).hexdigest()!=raw.content_hash):
            b.warning('RANGE_PROVENANCE: invalid relation omitted');continue
        packages[pkg.id]=pkg
        component=b.node('COMPONENT',pkg.id,product.canonical_name,package_identifier_id=str(pkg.id),name=pkg.package_name,
            display_name=product.canonical_name,vendor=product.vendor,type=product.product_type,ecosystem=pkg.ecosystem,namespace=pkg.namespace,purl=pkg.purl)
        package_nodes[pkg.id]=component
        related=[c for c in claims if c.range_id==r.id or (c.claim_type in ('AFFECTS_VERSION','affected_version') and c.package_identifier_id==pkg.id and any(
            e.claim_id==c.id and e.observation_id==r.observation_id for e,_,_ in valid.values()))]
        confirmed=[c for c in related if statuses[c.id]=='CONFIRMED' and same_range_assertion(c,r,pkg.ecosystem) and supports[c.id]]
        status='CONFLICT' if any(statuses[c.id]=='CONFLICT' for c in related) else 'CONFIRMED' if related and len(confirmed)==len(related) else 'SOURCE_ASSERTED'
        latest=session.scalar(select(m.SourceObservation.id).where(m.SourceObservation.source_id==r.source_id,
            m.SourceObservation.external_id==obs.external_id,m.SourceObservation.parse_status=='parsed')
            .order_by(m.SourceObservation.retrieved_at.desc(),m.SourceObservation.created_at.desc(),m.SourceObservation.id.desc()).limit(1))
        is_current=latest==obs.id
        if not is_current:
            status='UNKNOWN';b.warning('HISTORICAL_RANGE: superseded source assertion retained')
        if r.parse_status!='parsed':status='INSUFFICIENT_EVIDENCE'
        proofs=tuple(str(e.id) for e,_,_ in valid.values() if e.claim_id in {c.id for c in related})
        claim_ids=tuple(str(c.id) for c in related)
        records=('affected_range:'+str(r.id),'observation:'+str(obs.id),'raw_document:'+str(raw.id))
        version=b.node('VERSION',r.id,r.raw_expression,version_kind='AFFECTED_RANGE',version=r.raw_expression,
            range_id=str(r.id),component_id=str(pkg.id),status=status,parse_status=r.parse_status,introduced=r.introduced,
            fixed=r.fixed,last_affected=r.last_affected,events=r.events,explicit_versions=r.explicit_versions,is_current=is_current)
        b.edge('AFFECTS_COMPONENT',root,component,status,records,claim_ids,proofs)
        b.edge('HAS_AFFECTED_RANGE',component,version,status,records,claim_ids,proofs)
    selected_assets=[]
    if asset_id:selected_assets=[owned_asset(session,UUID(str(asset_id)),actor)]
    elif include_assets:
        selected_assets=b.take(session.scalars(select(m.Asset).join(m.AssetComponent,m.AssetComponent.asset_id==m.Asset.id)
            .where(m.Asset.owner_principal==actor,m.Asset.deleted_at.is_(None),m.AssetComponent.deleted_at.is_(None),
                m.AssetComponent.package_identifier_id.in_(packages)).distinct().order_by(m.Asset.id).limit(17)),16) if packages else []
    elif linked:
        selected_assets=[owned_asset(session,UUID(x),actor) for x in dict.fromkeys(a['asset_id'] for a in linked.get('assets',[]) if a.get('asset_id'))][:16]
    asset_nodes={};deployment={}
    for asset in selected_assets:
        components=b.take(session.scalars(select(m.AssetComponent).where(m.AssetComponent.asset_id==asset.id,m.AssetComponent.deleted_at.is_(None)).order_by(m.AssetComponent.id).limit(17)),16)
        matching=[x for x in components if x.package_identifier_id in packages]
        if not matching:
            b.warning('ASSET_COMPONENT_NOT_LINKED: no exact package relation in local coverage');continue
        asset_node=b.node('ASSET',asset.id,asset.name,name=asset.name,asset_id=str(asset.id),environment=asset.environment,
            exposure=asset.exposure,is_demo=asset.is_demo,provenance='USER_INVENTORY_NOT_SCANNED')
        asset_nodes[str(asset.id)]=asset_node
        for c in matching:
            version=b.node('VERSION','deployment:'+str(c.id)+':'+str(c.inventory_revision),c.version or 'UNKNOWN',
                version_kind='DEPLOYED',version=c.version,component_id=str(c.id),status='KNOWN' if c.version else 'UNKNOWN',inventory_revision=c.inventory_revision)
            records=('asset_component:'+str(c.id),'asset:'+str(asset.id))
            b.edge('HAS_VERSION',package_nodes[c.package_identifier_id],version,'USER_INVENTORY',records)
            b.edge('DEPLOYED_ON',version,asset_node,'USER_INVENTORY',records)
            deployment[str(c.id)]=(c,version)
    limits=['LOCAL_COLLECTED_RELATIONS_ONLY','RELATIONS_DO_NOT_IMPLY_VERIFIED_IMPACT']
    if linked:
        _add_decision(b,linked,asset_nodes,deployment);limits.append('SAVED_DECISION_NOT_CURRENT_SAFETY_ASSESSMENT')
    else:limits.append('NO_RISK_DECISION_SELECTED')
    return KnowledgeGraph(vulnerability_id=str(target),canonical_id=vuln.canonical_id,nodes=tuple(b.nodes.values()),edges=tuple(b.edges.values()),
        truncated=b.truncated,warnings=tuple(b.warnings),limitations=tuple(limits),investigation_id=linked.get('investigation_id') if linked else None,
        agent_references=tuple(linked.get('agent_references',())) if linked else (),gate_status=linked.get('gate_status') if linked else None,
        answer_id=linked.get('answer_id') if linked else None)


def _add_decision(b,linked,asset_nodes,deployment):
    risk=linked.get('risk')
    if not risk:
        b.warning('RISK_UNAVAILABLE: selected investigation has no saved risk view');return
    for item in linked.get('assets',[]):
        asset_node=asset_nodes.get(item.get('asset_id'));dep=deployment.get(item.get('component_id'))
        if not asset_node or not dep:
            b.warning('RISK_SCOPE_UNRESOLVED: saved deployment does not match current owned inventory');continue
        c,version=dep;stale=c.version!=item.get('deployed_version') or (linked.get('inventory_revision') is not None and c.inventory_revision!=linked['inventory_revision'])
        accepted=not stale and risk.get('conclusion_scope')=='ACCEPTED' and linked.get('gate_status') in ('PASS','PASS_WITH_WARNINGS')
        status='CONFIRMED' if accepted and risk.get('verification_status')=='CONFIRMED' else 'UNKNOWN'
        node=b.node('RISK',str(linked['answer_id'])+':'+str(c.id),risk['risk_level'] if accepted else 'UNKNOWN',
            level=risk['risk_level'] if accepted else 'UNKNOWN',priority=risk['priority'] if accepted else 'REVIEW_REQUIRED',
            historical_level=risk['risk_level'],historical_snapshot=True,is_stale=stale,reason=linked.get('summary'),
            evaluation_time=linked.get('evaluation_time'),current_safety_evaluated=False,
            recommendation=linked.get('recommendations',[]),affected=risk.get('affected') if accepted else None,
            version_status=risk.get('version_match_status'),gate_status=linked.get('gate_status'),
            source_artifact=risk['source_artifact'],conclusion_scope=risk.get('conclusion_scope'))
        records=('answer:'+str(linked['answer_id']),'artifact:'+risk['source_artifact']['artifact_id'],'integration:'+str(linked.get('integration_id')))
        b.edge('HAS_RISK',asset_node,node,status,records,historical=True)
        if stale:b.warning('RISK_STALE: inventory version changed; historical decision retained, current risk UNKNOWN')
        for e in b.nodes.values():
            if e.type=='EVIDENCE' and e.data.get('evidence_id') in linked.get('evidence_ids',()):
                b.edge('SUPPORTED_BY',node,e.id,status,records,evidence=(e.data['evidence_id'],),historical=True)


def query_security_graphs(session,actor,*,component=None,ecosystem=None,minimum_severity=None,include_assets=False,offset=0,limit=10):
    if offset<0 or not 1<=limit<=10:raise ValueError('Invalid graph pagination')
    query=select(m.Vulnerability.id).join(m.AffectedVersionRange,m.AffectedVersionRange.vulnerability_id==m.Vulnerability.id)
    query=query.join(m.PackageIdentifier,m.PackageIdentifier.id==m.AffectedVersionRange.package_identifier_id)
    query=query.join(m.Product,m.Product.id==m.PackageIdentifier.product_id).where(m.Vulnerability.deleted_at.is_(None),m.Product.deleted_at.is_(None))
    if component is not None:query=query.where(or_(m.PackageIdentifier.package_name==component,m.Product.canonical_name==component))
    if ecosystem is not None:query=query.where(m.PackageIdentifier.ecosystem==ecosystem)
    if minimum_severity is not None:
        levels={'CRITICAL':['critical'],'HIGH':['critical','high'],'MEDIUM':['critical','high','medium'],'LOW':['critical','high','medium','low']}
        if minimum_severity not in levels:raise ValueError('Unknown source severity')
        threshold={'CRITICAL':9.0,'HIGH':7.0,'MEDIUM':4.0,'LOW':0.1}[minimum_severity]
        source_score=select(m.CvssAssessment.id).where(m.CvssAssessment.vulnerability_id==m.Vulnerability.id,
            m.CvssAssessment.base_score>=threshold).exists()
        query=query.where(or_(m.Vulnerability.primary_severity.in_(levels[minimum_severity]),source_score))
    query=query.distinct();total=session.scalar(select(func.count()).select_from(query.subquery()))
    rows=session.scalars(query.order_by(m.Vulnerability.id).offset(offset).limit(limit))
    return KnowledgeGraphPage(items=tuple(build_security_graph(session,x,actor,include_assets=include_assets) for x in rows),total=total,offset=offset,limit=limit)

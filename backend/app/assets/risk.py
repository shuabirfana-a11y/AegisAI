"""Append-only risk snapshots and structural change events. Read APIs never recompute."""
from datetime import timedelta
from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.enrichment.repository import digest,lock
from app.enrichment.evidence import current_evidence
from app.assets.matching import AssetVulnerabilityMatcher,MATCHER
from app.assets.remediation import trusted_claim,evidence_ids,get_remediation
from app.assets.priority import assess_priority
from app.utils.time import utcnow
from app.assets.dependencies import dependency_state

def risk_context(session,asset,component,match):
    vid=UUID(match['vulnerability_id']);v=session.get(m.Vulnerability,vid)
    claims=list(session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==vid)))
    kev_claims=[c for c in claims if c.claim_type=='KNOWN_EXPLOITED' and c.value_json.get('known_exploited') is True and trusted_claim(session,c)]
    kev_row=session.scalar(select(m.KnownExploitation).where(m.KnownExploitation.vulnerability_id==vid).order_by(m.KnownExploitation.observed_at.desc(),m.KnownExploitation.id).limit(1))
    poc_claims=[c for c in claims if c.claim_type in ('POC_EXISTS','POC_ASSOCIATION') and trusted_claim(session,c)]
    pocs=[session.get(m.PocCandidate,c.poc_candidate_id) for c in poc_claims if c.poc_candidate_id]
    pocs=[p for p in pocs if p is not None and p.status=='confirmed']
    epss_row=session.scalar(select(m.EpssSnapshot).where(m.EpssSnapshot.vulnerability_id==vid).order_by(m.EpssSnapshot.score_date.desc(),m.EpssSnapshot.observed_at.desc(),m.EpssSnapshot.id).limit(1))
    epss={'score':None,'percentile':None,'date':None,'model_version':None,'status':'UNKNOWN'}
    if epss_row:
        stale=epss_row.score_date<utcnow().date()-timedelta(days=7) or epss_row.score_date>utcnow().date()
        epss={'score':None if stale else float(epss_row.score),'observed_score':float(epss_row.score),'percentile':float(epss_row.percentile) if epss_row.percentile is not None else None,
            'date':str(epss_row.score_date),'model_version':epss_row.model_version,'status':'STALE' if stale else 'SOURCE_ASSERTED',
            'raw_document_id':str(epss_row.raw_document_id),'snapshot_id':str(epss_row.id)}
    poc_job=session.scalar(select(m.EnrichmentJob).where(m.EnrichmentJob.vulnerability_id==vid,m.EnrichmentJob.enrichment_type=='poc').order_by(m.EnrichmentJob.created_at.desc()).limit(1))
    return {'asset_id':str(asset.id),'asset_name':asset.name,'is_demo':asset.is_demo,'environment':asset.environment,'exposure':asset.exposure,
        'component_id':str(component.id),'component_name':component.raw_package_name,'installed_version':component.version,'normalized_version':component.normalized_version,
        'vulnerability_id':str(vid),'canonical_id':v.canonical_id,'title':v.title,'severity':v.primary_severity,
        'match_status':match['match_status'],'verification_status':match['verification_status'],
        'kev':{'confirmed':bool(kev_claims),'catalog_status':kev_row.catalog_status if kev_row else 'unknown','known_exploited':kev_row.known_exploited if kev_row else None,
            'as_of':kev_row.observed_at.isoformat() if kev_row else None,'catalog_version':kev_row.catalog_version if kev_row else None,
            'claim_ids':[str(c.id) for c in kev_claims],'evidence_ids':[e for c in kev_claims for e in evidence_ids(session,c)]},
        'poc':{'confirmed':bool(pocs),'confirmed_count':len(pocs),'status':'CONFIRMED' if pocs else poc_job.status.upper() if poc_job else 'UNKNOWN',
            'search_as_of':poc_job.finished_at.isoformat() if poc_job and poc_job.finished_at else None,'usability':'NOT_EVALUATED',
            'claim_ids':[str(c.id) for c in poc_claims],'evidence_ids':[e for c in poc_claims for e in evidence_ids(session,c)]},
        'epss':epss,'remediation':get_remediation(session,vid,component.package_identifier_id),
        'match_explanation':match,'evidence_refs':match['evidence_refs']}

def _changes(before,after):
    if before is None:return ['RISK_DISCOVERED']
    kinds=[]
    if before['installed_version']!=after['installed_version']:kinds.append('ASSET_VERSION_CHANGED')
    if before['match_status']!=after['match_status']:kinds.append('MATCH_CHANGED')
    if before['verification_status']!=after['verification_status']:kinds.append('VERIFICATION_CHANGED')
    if not before['poc']['confirmed'] and after['poc']['confirmed']:kinds.append('POC_CONFIRMED')
    elif before['poc']!=after['poc']:kinds.append('POC_STATUS_CHANGED')
    if not before['kev']['confirmed'] and after['kev']['confirmed']:kinds.append('KEV_ADDED')
    elif before['kev']!=after['kev']:kinds.append('KEV_CHANGED')
    previous=before['epss'].get('score');current=after['epss'].get('score')
    if previous is not None and current is not None and current>previous:kinds.append('EPSS_INCREASED')
    elif before['epss']!=after['epss']:kinds.append('EPSS_CHANGED')
    if before['remediation']!=after['remediation']:kinds.append('PATCH_RELEASED' if not before['remediation']['patches'] and after['remediation']['patches'] else 'REMEDIATION_CHANGED')
    if before['priority']!=after['priority']:kinds.append('PRIORITY_CHANGED')
    if before['match_explanation']['fingerprint']!=after['match_explanation']['fingerprint']:kinds.append('INTELLIGENCE_CHANGED')
    return kinds or ['RISK_CONTEXT_CHANGED']

class RiskService:
    @staticmethod
    def recompute(session,asset_id):
        lock(session,'asset:'+str(asset_id));asset=session.get(m.Asset,asset_id)
        if asset is None or asset.deleted_at:raise LookupError('Asset not found')
        results=[];now=utcnow()
        for component in session.scalars(select(m.AssetComponent).where(m.AssetComponent.asset_id==asset.id)):
            prior_rows=list(session.scalars(select(m.AssetRiskSnapshot).where(m.AssetRiskSnapshot.component_id==component.id).order_by(m.AssetRiskSnapshot.created_at.desc(),m.AssetRiskSnapshot.id.desc())))
            prior={}
            for s in prior_rows:prior.setdefault(s.vulnerability_id,s)
            if component.deleted_at:
                for vid,old in prior.items():
                    if old.match_status=='NOT_EVALUATED' and old.payload.get('component_removed'):continue
                    payload={**old.payload,'component_removed':True,'match_status':'NOT_EVALUATED','priority':'INFO',
                        'why_now':'Component was removed from this inventory; historical vulnerability fact retained','component_revision':component.inventory_revision}
                    _save(session,asset,component,vid,payload,old.match_id,old,'COMPONENT_REMOVED',now);results.append(payload)
                continue
            matches=AssetVulnerabilityMatcher.match(session,component)
            if not matches:
                component.details={**component.details,'match_summary':{'status':'NOT_EVALUATED','reason':'No resolved distribution or no candidate vulnerability in current local coverage'},'last_matched_at':now.isoformat()}
            else:component.details={**component.details,'match_summary':{'status':'EVALUATED','candidate_count':len(matches)},'last_matched_at':now.isoformat()}
            for match in matches:
                vid=UUID(match['vulnerability_id']);payload=risk_context(session,asset,component,match);payload.update(assess_priority(payload))
                payload['component_revision']=component.inventory_revision;payload['content_trust_level']='UNTRUSTED_EXTERNAL_CONTENT'
                payload['dependency_state']=dependency_state(session,vid,component.package_identifier_id)
                signature=digest([match['fingerprint'],payload['kev'],payload['poc'],payload['epss'],payload['remediation'],asset.environment,asset.exposure,payload['rule_version'],payload['severity'],payload['dependency_state']])
                matcher_key=MATCHER+':'+signature[:40]
                first_claim=session.get(m.Claim,UUID(match['claim_ids'][0])) if match['claim_ids'] else None
                row=session.scalar(select(m.AssetVulnerabilityMatch).where(m.AssetVulnerabilityMatch.asset_component_id==component.id,m.AssetVulnerabilityMatch.vulnerability_id==vid,
                    m.AssetVulnerabilityMatch.component_revision==component.inventory_revision,m.AssetVulnerabilityMatch.matcher_version==matcher_key))
                if row is None:
                    row=m.AssetVulnerabilityMatch(asset_component_id=component.id,vulnerability_id=vid,package_identifier_id=component.package_identifier_id,
                        matched_range_id=UUID(match['affected_ranges'][0]['range_id']) if match['affected_ranges'] else None,claim_id=first_claim.id if first_claim else None,
                        match_status={'AFFECTED':'affected','NOT_AFFECTED':'not_affected'}.get(match['match_status'],'unknown'),version_at_evaluation=component.version,
                        component_revision=component.inventory_revision,claim_revision=first_claim.revision if first_claim else 1,matcher_version=matcher_key,
                        reason_summary=match['reason_summary'],detected_at=now,last_evaluated_at=now,details={'explanation':match})
                    session.add(row);session.flush()
                payload['match_id']=str(row.id);payload['intelligence_fingerprint']=signature
                old=prior.get(vid)
                _save(session,asset,component,vid,payload,row.id,old,None,now);results.append(payload)
                # Prioritize existing claim reviews for important inventory, not every unknown component.
                if asset.environment=='production' and match['match_status']=='UNCERTAIN' and first_claim:
                    from app.assets.review import ensure_asset_review
                    ensure_asset_review(session,asset,component,first_claim,match)
        asset.details={**asset.details,'last_risk_recomputed_at':now.isoformat()};session.flush();return results

def _save(session,asset,component,vid,payload,match_id,old,forced_event,now):
    fingerprint=payload.get('intelligence_fingerprint') or digest([payload,component.inventory_revision])
    if old and old.inventory_revision==component.inventory_revision and old.intelligence_fingerprint==fingerprint and old.match_status==payload['match_status'] and old.priority==payload['priority']:return old
    # A->B->A needs a new temporal observation, even though A's semantic value existed earlier.
    key=digest([str(component.id),str(vid),component.inventory_revision,fingerprint,payload['match_status'],payload['priority'],str(old.id) if old else None])
    existing=session.scalar(select(m.AssetRiskSnapshot).where(m.AssetRiskSnapshot.snapshot_key==key))
    if existing:return existing
    row=m.AssetRiskSnapshot(asset_id=asset.id,component_id=component.id,vulnerability_id=vid,match_id=match_id,
        snapshot_key=key,match_status=payload['match_status'],priority=payload['priority'],inventory_revision=component.inventory_revision,
        intelligence_fingerprint=fingerprint,payload=payload)
    session.add(row);session.flush()
    for kind in [forced_event] if forced_event else _changes(old.payload if old else None,payload):
        event=m.AssetRiskChange(asset_id=asset.id,component_id=component.id,vulnerability_id=vid,previous_snapshot_id=old.id if old else None,snapshot_id=row.id,
            event_type=kind,event_key=digest([key,kind]),occurred_at=now,before_state=old.payload if old else None,after_state=payload)
        session.add(event)
    session.flush();return row

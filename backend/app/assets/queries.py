from uuid import UUID
from sqlalchemy import select,func
from app.db import models as m
from app.enrichment.queries import serialize
from app.assets.inventory import owned_asset
from app.assets.dependencies import dependency_state
from app.utils.time import utcnow
from datetime import datetime

ORDER={'P0':0,'P1':1,'P2':2,'P3':3,'REVIEW':4,'INFO':5}

def _stale(session,row,component,dependency_cache):
    if row.inventory_revision!=component.inventory_revision:return True
    stored=row.payload.get('dependency_state')
    if stored is None:return True
    if stored.get('expires_at') and datetime.fromisoformat(stored['expires_at'])<utcnow():return True
    if component.package_identifier_id is None:return True
    pair=(row.vulnerability_id,component.package_identifier_id)
    if pair not in dependency_cache:dependency_cache[pair]=dependency_state(session,*pair)
    if dependency_cache[pair]['signature']!=stored['signature']:return True
    exp=row.payload.get('match_explanation',{})
    for e in exp.get('source_evaluations',[]):
        claim=session.get(m.Claim,UUID(e['claim_id']))
        if claim is None or claim.revision!=e['revision'] or claim.verification_status!=e['status'] or claim.adopted!=e['adopted'] or claim.details.get('superseded'):return True
    newer=session.scalar(select(m.IntelligenceEvent.id).where(m.IntelligenceEvent.vulnerability_id==row.vulnerability_id,m.IntelligenceEvent.detected_at>row.created_at).limit(1))
    queued=session.scalar(select(m.AssetRecomputeJob.id).where(m.AssetRecomputeJob.asset_id==row.asset_id,m.AssetRecomputeJob.status.in_(['queued','running','failed']),m.AssetRecomputeJob.created_at>row.created_at).limit(1))
    return bool(newer or queued)

def latest_risks(session,asset_id,actor):
    asset=owned_asset(session,asset_id,actor);components={c.id:c for c in session.scalars(select(m.AssetComponent).where(m.AssetComponent.asset_id==asset.id,m.AssetComponent.deleted_at.is_(None)))}
    rows=session.scalars(select(m.AssetRiskSnapshot).where(m.AssetRiskSnapshot.asset_id==asset.id).order_by(m.AssetRiskSnapshot.created_at.desc(),m.AssetRiskSnapshot.id.desc()))
    result=[];seen=set();dependency_cache={}
    for row in rows:
        pair=(row.component_id,row.vulnerability_id)
        if pair in seen or row.component_id not in components:continue
        seen.add(pair);stale=_stale(session,row,components[row.component_id],dependency_cache)
        item={**row.payload,'snapshot_id':str(row.id),'evaluated_at':row.created_at.isoformat(),'is_stale':stale}
        if stale:
            item.update({'historical_match_status':item['match_status'],'match_status':'UNCERTAIN','priority':'REVIEW',
                'why_now':'Inventory or intelligence changed after this evaluation; recompute required'})
        result.append(item)
    return sorted(result,key=lambda x:(ORDER[x['priority']],x['canonical_id'],x['component_id']))

def asset_detail(session,asset_id,actor):
    asset=owned_asset(session,asset_id,actor)
    return {**serialize(asset),'components':[serialize(c) for c in session.scalars(select(m.AssetComponent).where(m.AssetComponent.asset_id==asset.id,m.AssetComponent.deleted_at.is_(None)).order_by(m.AssetComponent.created_at,m.AssetComponent.id))]}

def get_asset_risks(session,asset_id,actor,offset=0,limit=20):
    items=latest_risks(session,asset_id,actor)
    return {'items':items[offset:offset+limit],'total':len(items),'offset':offset,'limit':limit,'coverage':'Current locally collected package-specific intelligence; not a claim of complete global coverage'}

def explain_asset_risk(session,asset_id,snapshot_id,actor):
    owned_asset(session,asset_id,actor);row=session.get(m.AssetRiskSnapshot,snapshot_id)
    if row is None or row.asset_id!=asset_id:raise LookupError('Risk not found')
    return {**row.payload,'snapshot_id':str(row.id),'evaluated_at':row.created_at.isoformat(),'historical':True}

def get_asset_risk_changes(session,asset_id,actor,offset=0,limit=20):
    owned_asset(session,asset_id,actor)
    if offset<0 or not 1<=limit<=100:raise ValueError('Invalid pagination')
    q=select(m.AssetRiskChange).where(m.AssetRiskChange.asset_id==asset_id)
    return {'items':[serialize(r) for r in session.scalars(q.order_by(m.AssetRiskChange.occurred_at.desc(),m.AssetRiskChange.id).offset(offset).limit(limit))],
        'total':session.scalar(select(func.count()).select_from(q.subquery())),'offset':offset,'limit':limit}

def overview(session,actor):
    assets=list(session.scalars(select(m.Asset).where(m.Asset.owner_principal==actor,m.Asset.deleted_at.is_(None))))
    components=list(session.scalars(select(m.AssetComponent).where(m.AssetComponent.asset_id.in_([a.id for a in assets]),m.AssetComponent.deleted_at.is_(None)))) if assets else []
    risks=[r for a in assets for r in latest_risks(session,a.id,actor)]
    affected=[r for r in risks if r['match_status']=='AFFECTED']
    return {'assets':len(assets),'components':len(components),'affected_components':len({r['component_id'] for r in affected}),
        'critical_high':sum(r['severity'] in ('critical','high') for r in affected),'confirmed_poc':sum(r['poc']['confirmed'] for r in affected),
        'kev':sum(r['kev']['confirmed'] for r in affected),'patch_available':sum('PATCH_AVAILABLE' in r['remediation']['statuses'] for r in affected),
        'uncertain_matches':sum(r['match_status']=='UNCERTAIN' for r in risks),
        'not_evaluated_components':sum(c.package_identifier_id is None or c.details.get('match_summary',{}).get('status')=='NOT_EVALUATED' for c in components),
        'is_demo_inventory_included':any(a.is_demo for a in assets),'counts_unit':'Components for affected_components; vulnerability-component pairs for risk counts'}

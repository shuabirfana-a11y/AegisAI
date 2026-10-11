from sqlalchemy import select
from app.db import models as m
from app.enrichment.repository import lock

def ensure_asset_review(session,asset,component,claim,match):
    if asset.environment!='production':return None
    lock(session,'asset-review:'+str(component.id)+':'+str(claim.id))
    old=session.scalar(select(m.ReviewTask).where(m.ReviewTask.claim_id==claim.id,m.ReviewTask.review_type=='ASSET_MATCH_REVIEW',m.ReviewTask.status.in_(['open','assigned','deferred']),m.ReviewTask.details['component_id'].astext==str(component.id)))
    if old:return old
    row=m.ReviewTask(claim_id=claim.id,review_type='ASSET_MATCH_REVIEW',priority=1 if match['verification_status']=='CONFLICT' else 2,
        reason='Production asset requires package/version intelligence confirmation',details={'asset_id':str(asset.id),'component_id':str(component.id),
            'owner_principal':asset.owner_principal,'component_revision':component.inventory_revision,'match_status':match['match_status'],'scope':'local private asset review'})
    session.add(row);session.flush();return row

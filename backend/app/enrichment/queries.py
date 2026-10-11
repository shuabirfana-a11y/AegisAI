from uuid import UUID
from sqlalchemy import select,func,or_
from app.db import models as m
from app.repositories.queries import columns
from app.enrichment.contracts import API_VERIFY,CONTENT_TRUST

def target_id(session,id):
    try:uid=UUID(str(id))
    except ValueError:uid=None
    return session.scalar(select(m.Vulnerability.id).where(or_(m.Vulnerability.id==uid,m.Vulnerability.canonical_id==str(id)),m.Vulnerability.deleted_at.is_(None)))

def serialize(row,session=None):
    data=columns(row);data['content_trust_level']=CONTENT_TRUST
    if isinstance(row,m.Claim):data['verification_status']=API_VERIFY[row.verification_status]
    if isinstance(row,m.VerificationResult):data['status']=API_VERIFY[row.status]
    if isinstance(row,m.Evidence) and session is not None:
        data['claim_verification_status']=API_VERIFY[session.get(m.Claim,row.claim_id).verification_status]
        data['source_key']=session.get(m.Source,row.source_id).source_key
    return data

MODELS={'enrichment':m.EnrichmentJob,'claims':m.Claim,'evidence':m.Evidence,'pocs':m.PocCandidate,'patches':m.PatchCandidate,
    'timeline':m.IntelligenceEvent,'epss':m.EpssSnapshot,'known_exploitation':m.KnownExploitation,'conflicts':m.ConflictRecord,
    'verification_results':m.VerificationResult,'reviews':m.ReviewTask}

def query(session,target,kind):
    model=MODELS[kind];q=select(model)
    if kind in ('evidence','verification_results','reviews'):q=q.join(m.Claim,model.claim_id==m.Claim.id).where(m.Claim.vulnerability_id==target)
    else:q=q.where(model.vulnerability_id==target)
    if kind=='reviews':q=q.where(m.ReviewTask.review_type!='ASSET_MATCH_REVIEW')
    return q.order_by(model.created_at.desc(),model.id)

def page(session,target,kind,offset=0,limit=20):
    q=query(session,target,kind)
    return {'items':[serialize(r,session) for r in session.scalars(q.offset(offset).limit(limit))],
        'total':session.scalar(select(func.count()).select_from(q.subquery())),'offset':offset,'limit':limit,'content_trust_level':CONTENT_TRUST}

def aggregate(session,target):
    return {kind:[serialize(r,session) for r in session.scalars(query(session,target,kind))] for kind in MODELS}

def review_detail(session,id):
    row=session.get(m.ReviewTask,id)
    if row is None:return None
    claim=session.get(m.Claim,row.claim_id)
    return {**serialize(row),'claim':serialize(claim),'evidence':[serialize(r,session) for r in session.scalars(select(m.Evidence).where(m.Evidence.claim_id==claim.id))],
        'audit':[serialize(r) for r in session.scalars(select(m.AuditLog).where(m.AuditLog.review_task_id==id))]}

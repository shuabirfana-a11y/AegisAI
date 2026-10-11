from uuid import UUID
from typing import Annotated
from fastapi import APIRouter,Depends,HTTPException,Header,Query,Request
from pydantic import Field,BaseModel,ConfigDict
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.api.dependencies import get_session
from app.db import models as m
from app.db.persistence import RevisionConflict,IdempotencyConflict
from app.enrichment.queries import serialize
from app.assets.auth import asset_principal
from app.assets.contracts import AssetInput,ComponentInput
from app.assets.inventory import AssetService,owned_asset
from app.assets import queries
from app.assets.sbom import MAX_BYTES

router=APIRouter(prefix='/api/v1/assets',tags=['assets'])
SessionDep=Annotated[Session,Depends(get_session)]

def actor(authorization:Annotated[str|None,Header()]=None):
    try:return asset_principal(authorization)
    except RuntimeError as exc:raise HTTPException(503,str(exc)) from exc
    except PermissionError as exc:raise HTTPException(401,str(exc)) from exc

ActorDep=Annotated[str,Depends(actor)]

def mutate(session,fn):
    try:
        with session.begin_nested():result=fn()
        session.commit();return result
    except (RevisionConflict,IdempotencyConflict) as exc:raise HTTPException(409,str(exc)) from exc
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

class NewAsset(AssetInput):request_key:str=Field(min_length=1,max_length=150)
class NewComponent(ComponentInput):request_key:str=Field(min_length=1,max_length=150)
class UpdateVersion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    version:str|None=Field(default=None,max_length=200)
    expected_revision:int=Field(ge=1)
    request_key:str=Field(min_length=1,max_length=150)

@router.get('')
def assets(session:SessionDep,actor:ActorDep,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    q=select(m.Asset).where(m.Asset.owner_principal==actor,m.Asset.deleted_at.is_(None))
    return {'items':[serialize(a) for a in session.scalars(q.order_by(m.Asset.created_at.desc(),m.Asset.id).offset(offset).limit(limit))],
        'total':session.scalar(select(func.count()).select_from(q.subquery())),'offset':offset,'limit':limit}

@router.get('/overview')
def overview(session:SessionDep,actor:ActorDep):return queries.overview(session,actor)

@router.post('',status_code=201)
def create(body:NewAsset,session:SessionDep,actor:ActorDep):
    data=body.model_dump();key=data.pop('request_key')
    return mutate(session,lambda:serialize(AssetService.create(session,data,actor,key)))

@router.get('/{id}')
def detail(id:UUID,session:SessionDep,actor:ActorDep):
    try:return queries.asset_detail(session,id,actor)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc

@router.post('/{id}/components',status_code=201)
def add(id:UUID,body:NewComponent,session:SessionDep,actor:ActorDep):
    data=body.model_dump(mode='json');key=data.pop('request_key')
    return mutate(session,lambda:serialize(AssetService.add_component(session,id,data,actor,key)))

@router.patch('/{id}/components/{component_id}')
def update(id:UUID,component_id:UUID,body:UpdateVersion,session:SessionDep,actor:ActorDep):
    return mutate(session,lambda:serialize(AssetService.update_component(session,id,component_id,body.version,body.expected_revision,actor,body.request_key)))

@router.post('/{id}/sbom')
async def sbom(id:UUID,request:Request,session:SessionDep,actor:ActorDep,x_request_key:Annotated[str,Header(min_length=1,max_length=150)]):
    try:owned_asset(session,id,actor)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    length=request.headers.get('content-length')
    if length:
        try:declared=int(length)
        except ValueError:raise HTTPException(400,'Invalid content length')
        if declared>MAX_BYTES:raise HTTPException(413,'SBOM exceeds2MiB')
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>MAX_BYTES:raise HTTPException(413,'SBOM exceeds2MiB')
    return mutate(session,lambda:AssetService.import_sbom(session,id,bytes(data),actor,x_request_key))

@router.get('/{id}/risks')
def risks(id:UUID,session:SessionDep,actor:ActorDep,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    try:return queries.get_asset_risks(session,id,actor,offset,limit)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc

@router.get('/{id}/risks/{snapshot_id}')
def risk_detail(id:UUID,snapshot_id:UUID,session:SessionDep,actor:ActorDep):
    try:return queries.explain_asset_risk(session,id,snapshot_id,actor)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc

@router.post('/{id}/recompute')
def recompute(id:UUID,session:SessionDep,actor:ActorDep):
    from app.assets.risk import RiskService
    def run():owned_asset(session,id,actor);return {'items':RiskService.recompute(session,id)}
    return mutate(session,run)

@router.get('/{id}/risk-changes')
def changes(id:UUID,session:SessionDep,actor:ActorDep,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    try:return queries.get_asset_risk_changes(session,id,actor,offset,limit)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc

@router.get('/{id}/inventory-history')
def inventory_history(id:UUID,session:SessionDep,actor:ActorDep,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    try:owned_asset(session,id,actor)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    q=select(m.AssetInventoryEvent).where(m.AssetInventoryEvent.asset_id==id)
    return {'items':[{k:v for k,v in serialize(r).items() if k!='payload'}|{'changes':r.payload.get('changes',[]),'summary':{k:v for k,v in r.payload.items() if k!='document'}} for r in session.scalars(q.order_by(m.AssetInventoryEvent.occurred_at.desc()).offset(offset).limit(limit))],
        'total':session.scalar(select(func.count()).select_from(q.subquery())),'offset':offset,'limit':limit}

@router.get('/{id}/reviews')
def asset_reviews(id:UUID,session:SessionDep,actor:ActorDep,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    try:owned_asset(session,id,actor)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    q=select(m.ReviewTask).where(m.ReviewTask.review_type=='ASSET_MATCH_REVIEW',m.ReviewTask.details['asset_id'].astext==str(id),m.ReviewTask.details['owner_principal'].astext==actor)
    from app.enrichment.queries import review_detail
    return {'items':[review_detail(session,row.id) for row in session.scalars(q.order_by(m.ReviewTask.created_at.desc()).offset(offset).limit(limit))],
        'total':session.scalar(select(func.count()).select_from(q.subquery())),'offset':offset,'limit':limit}

import os,secrets
from uuid import UUID
from typing import Annotated,Literal
from fastapi import APIRouter,Depends,HTTPException,Query,Header
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.api.dependencies import get_session
from app.db import models as m
from app.db.persistence import RevisionConflict,IdempotencyConflict
from app.enrichment import queries
from app.enrichment.review import ReviewWorkflow
from app.enrichment.contracts import DB_VERIFY
router=APIRouter(prefix='/api/v1')
SessionDep=Annotated[Session,Depends(get_session)]

def read_handler(kind):
    def handler(id:str,session:SessionDep,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
        target=queries.target_id(session,id)
        if target is None:raise HTTPException(404,'Vulnerability not found')
        return queries.page(session,target,kind,offset,limit)
    return handler

for kind in ('enrichment','claims','evidence','pocs','patches','timeline'):
    router.add_api_route('/vulnerabilities/{id}/'+kind,read_handler(kind),methods=['GET'],name='read_'+kind)

@router.get('/evidence/{id}')
def evidence(id:UUID,session:SessionDep):
    row=session.get(m.Evidence,id)
    if row is None:raise HTTPException(404,'Evidence not found')
    return queries.serialize(row,session)

@router.get('/reviews')
def reviews(session:SessionDep,status:Literal['open','assigned','resolved','deferred','cancelled']|None=None,
    offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    q=select(m.ReviewTask).where(m.ReviewTask.review_type!='ASSET_MATCH_REVIEW')
    if status:q=q.where(m.ReviewTask.status==status)
    return {'items':[queries.serialize(r) for r in session.scalars(q.order_by(m.ReviewTask.created_at.desc(),m.ReviewTask.id).offset(offset).limit(limit))],
        'total':session.scalar(select(func.count()).select_from(q.subquery())),'offset':offset,'limit':limit}

@router.get('/reviews/{id}')
def review(id:UUID,session:SessionDep):
    result=queries.review_detail(session,id)
    if result is None:raise HTTPException(404,'Review not found')
    if result['review_type']=='ASSET_MATCH_REVIEW':raise HTTPException(404,'Review not found')
    return result

class Decision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_revision:int=Field(ge=1)
    expected_claim_revision:int=Field(ge=1)
    request_key:str=Field(min_length=1,max_length=150)
    status:Literal['CONFIRMED','CONFLICT','INSUFFICIENT_EVIDENCE','PENDING','REJECTED','DEFERRED']
    value:dict|None=None
    reason:str=Field(min_length=1,max_length=2000)
    evidence_ids:list[UUID]=Field(max_length=100)

@router.post('/reviews/{id}/resolve')
def resolve(id:UUID,body:Decision,session:SessionDep,authorization:Annotated[str|None,Header()]=None):
    task=session.get(m.ReviewTask,id)
    if task is not None and task.review_type=='ASSET_MATCH_REVIEW':raise HTTPException(404,'Use the protected asset review context')
    token=os.environ.get('AEGIS_REVIEW_TOKEN')
    if not token:raise HTTPException(503,'Local review write access is not configured')
    if not authorization or not secrets.compare_digest(authorization,'Bearer '+token):raise HTTPException(401,'Authentication required')
    actor=os.environ.get('AEGIS_REVIEW_ACTOR','local-analyst')
    values=body.model_dump();values['status']='deferred' if body.status=='DEFERRED' else DB_VERIFY[body.status]
    try:
        audit=ReviewWorkflow.resolve(session,task_id=id,actor=actor,**values)
        result=queries.serialize(audit);session.commit();return result
    except (RevisionConflict,IdempotencyConflict) as exc:session.rollback();raise HTTPException(409,str(exc)) from exc
    except ValueError as exc:session.rollback();raise HTTPException(422,str(exc)) from exc

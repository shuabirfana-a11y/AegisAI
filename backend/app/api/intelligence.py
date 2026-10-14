from typing import Annotated,Literal
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_session
from app.api.assets import ActorDep
from app.monitoring import views
from app.monitoring.schemas import SecurityIntelligenceObject,IntelligencePage,SourceStatusPage,AssetRiskPage
from app.enrichment.poc_schemas import POCPage
from app.enrichment.poc_artifacts import poc_page

router=APIRouter(prefix='/api/v1/intelligence',tags=['intelligence'])
SessionDep=Annotated[Session,Depends(get_session)]

@router.get('',response_model=IntelligencePage)
def listing(session:SessionDep,type:Literal['vulnerability','paper','blog','advisory','analysis','knowledge']|None=None,q:str|None=Query(None,max_length=150),offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    return views.intelligence_page(session,kind=type,q=q,offset=offset,limit=limit)

@router.get('/sources',response_model=SourceStatusPage)
def sources(session:SessionDep):return views.source_status(session)

@router.get('/vulnerabilities/{id}',response_model=SecurityIntelligenceObject)
def vulnerability(id:str,session:SessionDep):
    try:return views.vulnerability_view(session,id)
    except LookupError as e:raise HTTPException(404,str(e)) from e

@router.get('/documents/{id}',response_model=SecurityIntelligenceObject)
def document(id:UUID,session:SessionDep):
    try:return views.document_view(session,id)
    except LookupError as e:raise HTTPException(404,str(e)) from e

@router.get('/vulnerabilities/{id}/poc',response_model=POCPage)
def poc(id:str,session:SessionDep,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    try:return poc_page(session,id,offset=offset,limit=limit)
    except LookupError as e:raise HTTPException(404,str(e)) from e

@router.get('/vulnerabilities/{id}/assets',response_model=AssetRiskPage)
def assets(id:str,session:SessionDep,actor:ActorDep,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    try:return views.owned_risks(session,id,actor,offset=offset,limit=limit)
    except LookupError as e:raise HTTPException(404,str(e)) from e

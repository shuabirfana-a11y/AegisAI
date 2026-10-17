from typing import Annotated,Literal
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_session
from app.api.assets import ActorDep
from app.monitoring import views
from app.monitoring.schemas import SecurityIntelligenceObject,IntelligencePage,SourceStatusPage,AssetRiskPage
from app.enrichment.poc_schemas import POCPage
from app.enrichment.poc_artifacts import poc_page
from app.monitoring.automation_schemas import RecordPage,PipelineRunPage
from app.monitoring.lifecycle import record_page,pipeline_runs
from app.knowledge.graph_schemas import KnowledgeGraph,KnowledgeGraphPage
from app.knowledge.security_graph import build_security_graph,query_security_graphs
from app.knowledge.investigation_graph import load_linked_investigation

router=APIRouter(prefix='/api/v1/intelligence',tags=['intelligence'])
SessionDep=Annotated[Session,Depends(get_session)]

@router.get('',response_model=IntelligencePage)
def listing(session:SessionDep,type:Literal['vulnerability','paper','blog','advisory','analysis','knowledge']|None=None,q:str|None=Query(None,max_length=150),offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    return views.intelligence_page(session,kind=type,q=q,offset=offset,limit=limit)

@router.get('/sources',response_model=SourceStatusPage)
def sources(session:SessionDep):return views.source_status(session)

@router.get('/records',response_model=RecordPage)
def records(session:SessionDep,type:Literal['vulnerability','paper','blog','advisory','analysis','knowledge']|None=None,
    q:str|None=Query(None,max_length=150),offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    return record_page(session,kind=type,q=q,offset=offset,limit=limit)

@router.get('/monitoring/runs',response_model=PipelineRunPage)
def monitoring_runs(session:SessionDep,source:str|None=Query(None,max_length=100),offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    return pipeline_runs(session,source=source,offset=offset,limit=limit)

@router.get('/graph/query',response_model=KnowledgeGraphPage)
def graph_query(session:SessionDep,actor:ActorDep,component:str|None=Query(None,min_length=1,max_length=300),
    ecosystem:str|None=Query(None,min_length=1,max_length=40),minimum_severity:Literal['CRITICAL','HIGH','MEDIUM','LOW']|None=None,
    include_assets:bool=False,offset:int=Query(0,ge=0),limit:int=Query(10,ge=1,le=10)):
    try:return query_security_graphs(session,actor,component=component,ecosystem=ecosystem,
        minimum_severity=minimum_severity,include_assets=include_assets,offset=offset,limit=limit)
    except ValueError as e:raise HTTPException(409,'Knowledge graph binding or projection invalid') from e

@router.get('/vulnerabilities/{id}/graph',response_model=KnowledgeGraph)
def graph(id:str,session:SessionDep,actor:ActorDep,request:Request,asset_id:UUID|None=None,
    include_assets:bool=False,investigation_id:UUID|None=None):
    try:
        linked=load_linked_investigation(request.app.state.engine,investigation_id,actor) if investigation_id else None
        return build_security_graph(session,id,actor,include_assets=include_assets,asset_id=asset_id,linked=linked)
    except LookupError as e:raise HTTPException(404,'Knowledge graph source not found or not accessible') from e
    except ValueError as e:raise HTTPException(409,'Knowledge graph binding or projection invalid') from e

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

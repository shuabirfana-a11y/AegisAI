from typing import Literal,Annotated
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.dependencies import get_session
from app.repositories import queries

router=APIRouter()
SourceKey=Literal['CVE_LIST','OSV','CISA_KEV']
SessionDep=Annotated[Session,Depends(get_session)]

@router.get('/health')
def health(request:Request):
    try:
        with request.app.state.engine.connect() as conn: conn.execute(text('SELECT 1'))
        return {'application':'up','database':'up','sources':'independent; see /api/v1/sources','scope':'local development'}
    except Exception:
        return JSONResponse(status_code=503,content={'application':'up','database':'down','sources':'independent','scope':'local development'})

@router.get('/api/v1/sources')
def sources(session:SessionDep):return queries.list_sources(session)

@router.get('/api/v1/sync-runs')
def sync_runs(session:SessionDep,source:SourceKey|None=None,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    return queries.list_sync_runs(session,source,offset,limit)

@router.get('/api/v1/vulnerabilities')
def vulnerabilities(session:SessionDep,q:str|None=Query(None,max_length=150),source:SourceKey|None=None,
    ai_relevance:Literal['relevant','irrelevant','uncertain']|None=None,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),
    sort:Literal['modified_desc','published_desc']='modified_desc'):
    return queries.list_vulnerabilities(session,q=q,source=source,ai_relevance=ai_relevance,offset=offset,limit=limit,sort=sort)

@router.get('/api/v1/vulnerabilities/{id}')
def vulnerability(id:str,session:SessionDep):
    result=queries.vulnerability_detail(session,id)
    if result is None:raise HTTPException(404,'Vulnerability not found')
    from app.enrichment.queries import aggregate
    enriched=aggregate(session,result['id'])
    # Preserve historical Phase6 fields and expose trusted additions separately.
    result.update(enriched)
    return result

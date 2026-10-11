from uuid import UUID
from fastapi import APIRouter,Request,HTTPException
from app.api.assets import ActorDep
from app.assistant.contracts import QueryRequest
from app.assistant.storage import IdempotencyConflict
from app.assistant.service import AssistantBusy
router=APIRouter(prefix='/api/v1/assistant',tags=['assistant'])

@router.post('/query',status_code=202)
def query(body:QueryRequest,request:Request,actor:ActorDep):
    try:return request.app.state.assistant.start(body,actor)
    except IdempotencyConflict as exc:raise HTTPException(409,str(exc)) from exc
    except PermissionError as exc:raise HTTPException(403,str(exc)) from exc
    except AssistantBusy as exc:raise HTTPException(429,str(exc)) from exc

@router.get('/runs/{id}')
def run(id:UUID,request:Request,actor:ActorDep):
    try:return request.app.state.assistant.read(id,actor)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc

@router.get('/runs/{id}/tasks')
def tasks(id:UUID,request:Request,actor:ActorDep):
    try:return request.app.state.assistant.tasks(id,actor)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc

@router.get('/runs/{id}/trace')
def trace(id:UUID,request:Request,actor:ActorDep):
    try:return request.app.state.assistant.trace(id,actor)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc

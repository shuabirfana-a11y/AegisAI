from uuid import UUID,uuid4
from fastapi import APIRouter,Request,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.api.assets import ActorDep
from app.tooling.contracts import REGISTRY
from app.tooling.gateway import ToolGateway,ToolContext
from app.assistant.contracts import QueryRequest
from app.assistant import storage
from app.db.session import transaction
from app.utils.time import utcnow
router=APIRouter(prefix='/api/v1/tools',tags=['tools'])

@router.get('/contracts')
def contracts(actor:ActorDep):
    return {'version':'ToolContractV3','content_trust_level':'UNTRUSTED_EXTERNAL_CONTENT','tools':[
        {'name':name,'input_schema':spec.input.model_json_schema(),'permission':spec.permission,'category':spec.category,'description':spec.description}
        for name,spec in REGISTRY.items()]}

@router.post('/{name}')
def invoke(name:str,body:dict,request:Request,actor:ActorDep):
    if name not in REGISTRY:raise HTTPException(404,'Tool not found')
    if REGISTRY[name].permission!='READ_ONLY' or body.get('refresh'):raise HTTPException(403,'External tool endpoint is read-only; use approved backend workflow for mutations')
    engine=request.app.state.engine
    with transaction(engine) as session:
        row,_=storage.create_run(session,QueryRequest(question='HTTP Tool '+name,request_key='tool-'+str(uuid4())),actor,agent_type='gateway-http-v1')
        run_id=str(row.id);trace=row.details['trace_id']
    def audit(n,a,r,seq,attempt):
        with transaction(engine) as session:storage.record_tool(session,run_id,1,n,a,r,attempt)
    ctx=ToolContext(actor=actor,max_calls=1,run_id=run_id,trace_id=trace,audit=audit,database_url=engine.url.render_as_string(hide_password=False))
    result=ToolGateway().invoke(name,body,ctx)
    with transaction(engine) as session:
        row=storage.owned_run(session,run_id,actor);row.status='failed' if result.status=='failed' else 'partial' if result.status=='partial' else 'succeeded'
        row.finished_at=utcnow();row.duration_ms=result.duration_ms;row.details={**row.details,'ui_status':'FAILED' if result.status=='failed' else 'COMPLETED','result':result.model_dump(mode='json')}
    return result

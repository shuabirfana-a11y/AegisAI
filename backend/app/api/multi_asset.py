"""Four authenticated batch transport operations; child APIs remain unchanged."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Request, Response
from app.api.investigations import Actor, InvestigationRoute, errors
from app.investigation_api.multi_asset_schemas import BatchRequest, BatchResponse


def service(request:Request):return request.app.state.multi_asset


Service=Annotated[object,Depends(service)]
router=APIRouter(prefix='/api/investigations/batches',tags=['multi-asset-investigations'],
    route_class=InvestigationRoute,responses=errors)


@router.post('',status_code=202,response_model=BatchResponse)
def create(body:BatchRequest,response:Response,actor:Actor,svc:Service,
           idempotency_key:Annotated[str|None,Header(alias='Idempotency-Key')]=None):
    result=svc.create(body,actor=actor,header_key=idempotency_key)
    response.headers['Location']=f'/api/investigations/batches/{result.batch_id}'
    response.headers['Retry-After']='1'
    return result


@router.get('/{id}',response_model=BatchResponse)
def get(id:UUID,actor:Actor,svc:Service):return svc.get(id,actor=actor)


@router.get('/{id}/summary',response_model=BatchResponse)
def summary(id:UUID,actor:Actor,svc:Service):return svc.get(id,actor=actor)


@router.post('/{id}/cancel',response_model=BatchResponse)
def cancel(id:UUID,actor:Actor,svc:Service):return svc.cancel(id,actor=actor)

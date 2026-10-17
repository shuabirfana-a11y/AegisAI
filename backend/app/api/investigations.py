"""Authenticated HTTP entrance; no direct database/tool/model operations."""
import logging
from typing import Annotated, Literal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Header, Query, Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.assets.auth import asset_principal
from app.assistant.storage import IdempotencyConflict
from app.orchestration.service import InvestigationBusy
from app.orchestration.contracts import InvestigationRequest, Overall
from app.investigation_api.errors import ApiFailure
from app.investigation_api.schemas import (
    InvestigationCreateRequest, InvestigationCreateResponse, InvestigationStatusResponse,
    TraceResponse, ArtifactResponse, IntegrationResponse, AnswerResponse, HistoryResponse, ApiError, checked_key,
    ContextRequiredResponse, InvestigationCreateResult,
)

logger = logging.getLogger('aegisai.investigation_api')
bearer = HTTPBearer(auto_error=False)


class InvestigationRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            request_id = uuid4()
            try:
                response = await original(request)
                response.headers['X-Request-ID'] = str(request_id)
                response.headers['Cache-Control'] = 'no-store'
                return response
            except ApiFailure as exc:
                failure = exc
            except RequestValidationError:
                failure = ApiFailure('INVALID_REQUEST', '请求参数不符合接口契约。', status=422)
            except IdempotencyConflict:
                failure = ApiFailure('IDEMPOTENCY_CONFLICT', '该幂等键已用于不同的请求内容。', status=409)
            except InvestigationBusy:
                failure = ApiFailure('INVESTIGATION_BUSY', '调查服务已满，请稍后重试。', status=429, retryable=True)
            except LookupError:
                failure = ApiFailure('INVESTIGATION_NOT_FOUND', '调查或结果不可访问。', status=404)
            except PermissionError:
                failure = ApiFailure('ACCESS_DENIED', '没有访问该调查范围的权限。', status=403)
            except HTTPException as exc:
                failure = ApiFailure('HTTP_ERROR', '请求无法处理。', status=exc.status_code)
            except Exception as exc:
                logger.error('Investigation HTTP failure request_id=%s exception_type=%s', request_id, type(exc).__name__)
                failure = ApiFailure('INTERNAL_ERROR', '调查服务暂时无法处理请求。', status=500)
            headers = {'X-Request-ID': str(request_id), 'Cache-Control': 'no-store'}
            if failure.retryable:
                headers['Retry-After'] = '2'
            if failure.status == 401:
                headers['WWW-Authenticate'] = 'Bearer'
            return JSONResponse(status_code=failure.status, headers=headers,
                content=ApiError(error_code=failure.code, message=failure.message,
                                 request_id=request_id, retryable=failure.retryable).model_dump(mode='json'))
        return handler


def actor(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    authorization = f'{credentials.scheme} {credentials.credentials}' if credentials else None
    try:
        return asset_principal(authorization)
    except PermissionError:
        raise ApiFailure('AUTHENTICATION_REQUIRED', '需要有效的 Bearer 凭据。', status=401) from None
    except RuntimeError:
        raise ApiFailure('AUTHENTICATION_UNAVAILABLE', '服务器尚未配置访问凭据。', status=503) from None


def service(request: Request):
    return request.app.state.investigations


Actor = Annotated[str, Depends(actor)]
Service = Annotated[object, Depends(service)]
errors = {code: {'model': ApiError} for code in (401, 403, 404, 409, 422, 429, 500, 503)}
router = APIRouter(prefix='/api/investigations', tags=['investigations'], route_class=InvestigationRoute, responses=errors)


@router.post('', status_code=202, response_model=InvestigationCreateResult,
             responses={200:{'model':ContextRequiredResponse,'description':'Required context missing; no investigation was created.'}})
def create(body: InvestigationCreateRequest | InvestigationRequest, response: Response, actor: Actor, svc: Service,
           idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None):
    if isinstance(body, InvestigationCreateRequest):
        request = body.to_internal(idempotency_key)
    else:
        checked_key(body.request_key, idempotency_key)
        request = body
    result = svc.create(request, actor=actor)
    if isinstance(result,ContextRequiredResponse):
        response.status_code=200
        return result
    response.headers['Location'] = f'/api/investigations/{result.investigation_id}/status'
    response.headers['Retry-After'] = '1'
    return result


@router.get('/history', response_model=HistoryResponse)
def history(actor: Actor, svc: Service, status: Overall | None = None,
            offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
            sort: Literal['created_desc', 'created_asc'] = 'created_desc'):
    return svc.history(actor=actor, status=status, offset=offset, limit=limit, sort=sort)


@router.get('/{id}/status', response_model=InvestigationStatusResponse)
def status(id: UUID, actor: Actor, svc: Service):
    return svc.status(id, actor=actor)


@router.get('/{id}/trace', response_model=TraceResponse)
def trace(id: UUID, actor: Actor, svc: Service, version: int | None = Query(None,ge=1,le=2)):
    return svc.trace(id, actor=actor, **({'version':version} if version is not None else {}))


@router.get('/{id}/artifacts', response_model=ArtifactResponse)
def artifacts(id: UUID, actor: Actor, svc: Service, version: int | None = Query(None,ge=1,le=2)):
    return svc.artifacts(id, actor=actor, **({'version':version} if version is not None else {}))


@router.get('/{id}/integration', response_model=IntegrationResponse)
def integration(id: UUID, actor: Actor, svc: Service, version: int | None = Query(None,ge=1,le=2)):
    return svc.integration(id, actor=actor, **({'version':version} if version is not None else {}))


@router.get('/{id}/answer', response_model=AnswerResponse)
def answer(id: UUID, actor: Actor, svc: Service, version: int | None = Query(None,ge=1,le=2)):
    return svc.answer(id, actor=actor, **({'version':version} if version is not None else {}))


@router.post('/{id}/cancel', response_model=InvestigationStatusResponse)
def cancel(id: UUID, actor: Actor, svc: Service):
    return svc.cancel(id, actor=actor)

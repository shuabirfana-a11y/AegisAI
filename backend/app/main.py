from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import make_engine
from app.api.routes import router
from app.api.enrichment import router as enrichment_router
from app.api.assets import router as assets_router
from app.api.assistant import router as assistant_router
from app.api.tools import router as tools_router
from app.assistant.service import AssistantService
import os
from urllib.parse import urlsplit
from fastapi.middleware.cors import CORSMiddleware
from app.api.investigations import router as investigations_router
from app.api.intelligence import router as intelligence_router
from app.api.openapi_contracts import install_openapi
from app.investigation_api.service import InvestigationApiService

def cors_allowlist():
    values=os.environ.get('AEGIS_CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173,http://localhost:8769,http://127.0.0.1:8769')
    origins=[value.strip() for value in values.split(',') if value.strip()]
    for origin in origins:
        parsed=urlsplit(origin)
        if (origin=='*' or parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path or '*' in origin):
            raise ValueError('AEGIS_CORS_ORIGINS must contain explicit HTTP origins')
        parsed.port
    return origins


def create_app(engine=None,*,investigation_gateway=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.engine=engine or make_engine()
        assistant=AssistantService(app.state.engine)
        app.state.assistant=assistant
        investigations=None
        try:
            investigations=InvestigationApiService(app.state.engine,investigation_gateway)
            app.state.investigations=investigations
            yield
        finally:
            if investigations is not None:investigations.close()
            assistant.close()
            if engine is None:app.state.engine.dispose()
    application=FastAPI(title='AegisAI ingestion API',version='0.1.0',lifespan=lifespan)
    application.include_router(router)
    application.include_router(enrichment_router)
    application.include_router(assets_router)
    application.include_router(assistant_router)
    application.include_router(tools_router)
    application.include_router(investigations_router)
    application.include_router(intelligence_router)
    application.add_middleware(CORSMiddleware,allow_origins=cors_allowlist(),allow_credentials=False,
        allow_methods=['GET','POST','PATCH','OPTIONS'],allow_headers=['Authorization','Content-Type','Idempotency-Key','X-Request-Key'],
        expose_headers=['Location','Retry-After','X-Request-ID'])
    install_openapi(application)
    return application

app=create_app()

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import make_engine
from app.api.routes import router
from app.api.enrichment import router as enrichment_router
from app.api.assets import router as assets_router
from app.api.assistant import router as assistant_router
from app.api.tools import router as tools_router
from app.assistant.service import AssistantService

def create_app(engine=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.engine=engine or make_engine()
        assistant=AssistantService(app.state.engine)
        app.state.assistant=assistant
        try:yield
        finally:
            assistant.close()
            if engine is None:app.state.engine.dispose()
    application=FastAPI(title='AegisAI ingestion API',version='0.1.0',lifespan=lifespan)
    application.include_router(router)
    application.include_router(enrichment_router)
    application.include_router(assets_router)
    application.include_router(assistant_router)
    application.include_router(tools_router)
    return application

app=create_app()

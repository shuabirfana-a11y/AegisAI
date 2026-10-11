"""Reuse the isolated committed PostgreSQL engine; synthetic data only."""
from tests.runtime.conftest import engine
import pytest


@pytest.fixture(scope='module')
def completed_chain(engine):
    from tests.orchestration.fixtures import scenario
    from app.orchestration.service import InvestigationOrchestrator
    seed,request,gateway,calls,_=scenario(engine)
    service=InvestigationOrchestrator(engine,gateway)
    try:
        result=service.investigate(request,actor=seed.actor)
        yield seed,request,service,result,calls
    finally:gateway.close()

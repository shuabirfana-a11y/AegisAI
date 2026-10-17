"""Synthetic source pipeline -> existing professional Agent and verification.

The original Model Gateway uses a deterministic test provider here. This proves
stored intelligence reuse, not a real-model or accuracy experiment.
"""
from types import SimpleNamespace
from uuid import uuid4
import httpx
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction
from app.core.http import HttpClient
from app.core.config import Settings
from app.monitoring.catalog import validate_url
from app.enrichment.acquisition import validate_enrichment_url
from app.enrichment.service import EnrichmentService
from app.monitoring.service import MonitoringService
from app.monitoring.pipeline import IntelligencePipeline,PipelineConfig
from tests.runtime.conftest import engine
from tests.agents.verification.conftest import verification_seed
from tests.agents.investigation.test_end_to_end import run
from tests.agents.verification.test_snapshot import request
from app.agents.verification.service import EvidenceVerificationService
from test_phase14_sources import ghsa


def test_pipeline_intelligence_is_consumed_through_original_gateway_and_agents(engine):
    seed=verification_seed.__wrapped__(engine)
    native=ghsa();native['cve_id']=seed.cve
    native['vulnerabilities'][0]['package']['name']=seed.component['package_name']
    native['ghsa_id']='GHSA-'+ '-'.join(uuid4().hex[i:i+4] for i in (0,4,8))
    def source(req):return httpx.Response(200,json=[native] if req.url.path=='/advisories' else native)
    monitor=MonitoringService(engine,http=HttpClient(Settings(retries=0,request_interval=0),
        transport=httpx.MockTransport(source),url_validator=validate_url))
    worker=EnrichmentService(lambda:transaction(engine),http=HttpClient(Settings(retries=0,request_interval=0),
        transport=httpx.MockTransport(lambda req:httpx.Response(503)),url_validator=validate_enrichment_url))
    pipeline=IntelligencePipeline(engine,PipelineConfig(execution_mode='MOCK',job_budget=1),monitor=monitor,worker=worker)
    try:cycle=pipeline.run_cycle(['GHSA'],force=True)
    finally:pipeline.close()
    assert cycle.sources[0].targets and cycle.execution_mode=='MOCK'
    service,saved,_,_=run(engine,seed)
    output=service.read_results(saved.runtime_run_id,seed.actor)
    artifact=output.artifacts[0]
    assert artifact.canonical_id==seed.cve and output.traces[0].tools_called
    with transaction(engine) as db:
        assert db.scalar(select(m.PackageIdentifier.id).where(m.PackageIdentifier.purl=='pkg:pypi/vllm')) is None
        observations=set(db.scalars(select(m.SourceObservation.id).where(m.SourceObservation.sync_run_id==cycle.sources[0].sync_run_id)))
        assert db.scalar(select(m.AiRelevanceAssessment.id).where(m.AiRelevanceAssessment.vulnerability_id==seed.vulnerability_id,
            m.AiRelevanceAssessment.observation_id.in_(observations)))
    verifier=EvidenceVerificationService(engine)
    saved_verification=verifier.run(request(SimpleNamespace(artifact=artifact)),actor=seed.actor)
    result=verifier.read_results(saved_verification.run_id,actor=seed.actor)
    assert result.artifacts and result.traces[0].agent_id=='verification_agent'

"""Actual existing Gateway/process/Agent handoff with explicitly synthetic sources."""
import base64
from types import SimpleNamespace
import httpx
from sqlalchemy import select
from tests.runtime.conftest import engine
from app.db import models as m
from app.db.session import transaction
from app.enrichment.enrichers.poc import PocEnricher
from app.enrichment.service import EnrichmentService
from app.enrichment.acquisition import validate_enrichment_url
from app.core.config import Settings
from app.core.http import HttpClient
from tests.agents.verification.conftest import verification_seed
from tests.agents.investigation.test_end_to_end import run
from tests.agents.verification.test_snapshot import request
from app.agents.verification.service import EvidenceVerificationService
from app.enrichment.poc_artifacts import poc_page


def test_existing_professional_verifier_consumes_discovered_poc_and_never_executes_it(engine):
    seed=verification_seed.__wrapped__(engine);urls=[]
    readme=('SYNTHETIC '+seed.cve+' vllm 0.6.0 static demo description.').encode()
    def handler(req):
        urls.append(str(req.url))
        if '/search/' in req.url.path:
            return httpx.Response(200,json={'items':[{'full_name':'synthetic/'+seed.cve,
                'description':'SYNTHETIC static candidate','language':'Python','owner':{'login':'synthetic'}}],
                'total_count':1,'incomplete_results':False})
        return httpx.Response(200,json={'encoding':'base64','content':base64.b64encode(readme).decode(),'size':len(readme)})
    client=HttpClient(Settings(retries=0,request_interval=0),transport=httpx.MockTransport(handler),url_validator=validate_enrichment_url)
    try:
        result=EnrichmentService(lambda:transaction(engine),http=client,enrichers=[PocEnricher()]).run(seed.cve,'poc')[0]
    finally:client.close()
    snapshot=result.artifacts['poc_snapshot']
    assert snapshot['items'] and snapshot['status']=='POC_CANDIDATE'
    assert len(urls)==2 and all('api.github.com' in u for u in urls)
    svc,saved,_,_=run(engine,seed)
    investigation=svc.read_results(saved.runtime_run_id,seed.actor).artifacts[0]
    assert investigation.poc_candidates
    before=investigation.model_dump_json()
    verifier=EvidenceVerificationService(engine)
    source=SimpleNamespace(artifact=investigation,seed=seed)
    verification_run=verifier.run(request(source),actor=seed.actor)
    output=verifier.read_results(verification_run.run_id,actor=seed.actor)
    artifact=output.artifacts[0]
    poc_claims=[c for c in artifact.claims if c.claim.claim_type=='POC_ASSOCIATION']
    assert poc_claims and all(c.status in ('PENDING','INSUFFICIENT_EVIDENCE') for c in poc_claims)
    assert all(c.unresolved_items for c in poc_claims)
    assert output.traces[0].agent_id=='verification_agent' and output.traces[0].tools_called
    assert before==svc.read_results(saved.runtime_run_id,seed.actor).artifacts[0].model_dump_json()
    with transaction(engine) as db:
        projected=poc_page(db,seed.cve)
        assert projected.status=='POC_CANDIDATE'
        assert all(p.usability_status=='not_evaluated' for p in db.scalars(select(m.PocCandidate).where(m.PocCandidate.vulnerability_id==seed.vulnerability_id)))

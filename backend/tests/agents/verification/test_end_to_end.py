"""Full DB/Gateway/process/Runtime handoff, including a controlled real HTTP adapter."""
import copy
import json
import threading
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.db import models as m
from app.db.session import transaction
from app.assistant.storage import IdempotencyConflict
from tests.agents.investigation.test_end_to_end import run
from tests.agents.verification.conftest import verification_seed
from tests.agents.verification.test_snapshot import request
from tests.agents.verification.test_runtime import service


def source_for(engine,seed):
    svc,saved,_,_=run(engine,seed,'version')
    art=svc.read_results(saved.runtime_run_id,seed.actor).artifacts[0]
    return SimpleNamespace(service=svc,run=saved,artifact=art,seed=seed)


def test_waiting_investigation_result_is_read_only_input_not_success_dependency(engine):
    seed=verification_seed.__wrapped__(engine)
    with transaction(engine) as db:db.get(m.Source,seed.source_id).authority_level='community'
    src=source_for(engine,seed)
    assert src.artifact.runtime_status=='WAITING_REVIEW'
    svc=service(engine);saved=svc.run(request(src),actor=seed.actor)
    out=svc.read_results(saved.run_id,actor=seed.actor)
    assert out.artifacts[0].verification_status!='CONFIRMED'
    assert out.traces[0].input_artifact['original_status']=='WAITING_REVIEW'
    assert src.service.read_results(src.artifact.run_id,seed.actor).artifacts[0].runtime_status=='WAITING_REVIEW'
    assert out.artifacts[0].source_run_id!=saved.run_id


def test_no_data_investigation_returns_insufficient_without_fabrication(engine,verification_seed):
    from app.agents.investigation.service import IntelligenceInvestigationService
    from tests.planner.fixtures import valid_plan,gateway_with_responses,cve_input
    value=valid_plan();missing='CVE-2099-'+str(uuid4().int)[:14]
    value['tasks'][0]['input_data']['steps'][0]['arguments']['target']=missing
    gw,_,_=gateway_with_responses([value]);original=IntelligenceInvestigationService(engine,gw)
    try:saved=original.plan_and_run(cve_input(target=missing),verification_seed.actor)
    finally:gw.close()
    art=original.read_results(saved.runtime_run_id,verification_seed.actor).artifacts[0]
    src=SimpleNamespace(artifact=art,seed=verification_seed)
    svc=service(engine);new=svc.run(request(src),actor=verification_seed.actor)
    result=svc.read_results(new.run_id,actor=verification_seed.actor).artifacts[0]
    assert result.verification_status=='INSUFFICIENT_EVIDENCE' and result.confidence==0
    assert result.partial_result and not result.claims
    assert original.read_results(saved.runtime_run_id,verification_seed.actor).artifacts[0].status=='PARTIAL'


def test_claim_selection_and_conflict_only_modes_do_not_override_sealed_request(engine,investigation_source):
    src=investigation_source;svc=service(engine)
    selected=request(src,task_type='claim_validation',claim_ids=(str(src.seed.claim_id),))
    out=svc.read_results(svc.run(selected,actor=src.seed.actor).run_id,actor=src.seed.actor)
    assert out.artifacts[0].verification_status=='CONFIRMED'
    conflicts=request(src,task_type='conflict_detection')
    out=svc.read_results(svc.run(conflicts,actor=src.seed.actor).run_id,actor=src.seed.actor)
    assert out.artifacts[0].verification_status=='PENDING'
    with pytest.raises(IdempotencyConflict):svc.run(selected.model_copy(update={'model_assistance':True}),actor=src.seed.actor)


def test_assisted_process_uses_openai_adapter_once_and_replays_without_network(engine,investigation_source,monkeypatch):
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            calls.append(body)
            output={'id':'SYNTHETIC','model':'synthetic-verification','choices':[{'index':0,
                'message':{'role':'assistant','content':'{"hints":[]}'},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':20,'completion_tokens':5,'total_tokens':25}}
            data=json.dumps(output).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)))
            self.end_headers();self.wfile.write(data)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    env={'MODEL_PROVIDER':'openai_compatible','MODEL_NAME':'synthetic-verification',
         'MODEL_API_BASE':'http://127.0.0.1:'+str(server.server_port)+'/v1','MODEL_API_KEY':'',
         'MODEL_ALLOW_KEYLESS_LOCAL':'true','MODEL_EMBEDDING_PROVIDER':'mock',
         'MODEL_EMBEDDING_NAME':'mock-embedding-v1','MODEL_EMBEDDING_DIMENSION':'384'}
    for key,value in env.items():monkeypatch.setenv(key,value)
    try:
        src=investigation_source;svc=service(engine);req=request(src,model_assistance=True)
        saved=svc.run(req,actor=src.seed.actor)
        result=svc.read_results(saved.run_id,actor=src.seed.actor).artifacts[0]
        assert result.verification_status=='CONFIRMED'
        assert len(calls)==1 and calls[0]['max_tokens']==512
        assert result.model_calls[0]['provider']=='openai_compatible'
        assert result.model_calls[0]['usage']['total_tokens']==25
        assert result.model_calls[0]['status']=='success'
        assert svc.run(req,actor=src.seed.actor)==saved and len(calls)==1
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def test_conflicting_investigation_is_verified_without_rewriting_source(engine):
    from app.utils.time import utcnow
    seed=verification_seed.__wrapped__(engine);now=utcnow();suffix=uuid4().hex
    with transaction(engine) as db:
        base=db.get(m.Claim,seed.claim_id)
        source=m.Source(source_key='VERIFY_CONFLICT_'+suffix,name='SYNTHETIC second vendor',
            source_type='vendor_advisory',category='vulnerability',authority_level='official',
            authority_scope='vulnerability affected versions',acquisition_method='fixture',
            base_url='https://example.invalid/SYNTHETIC/'+suffix,details={'is_test':True})
        db.add(source);db.flush()
        payload=b'SYNTHETIC affected <=0.8.0. Not a real advisory.'
        raw=m.RawDocument(source_id=source.id,external_id=seed.cve,source_url=source.base_url,
            published_at=now,retrieved_at=now,content_type='text/plain',raw_payload=payload,
            content_hash=hashlib.sha256(payload).hexdigest(),publisher=source.name)
        db.add(raw);db.flush()
        obs=m.SourceObservation(source_id=source.id,raw_document_id=raw.id,external_id=seed.cve,
            record_type='vulnerability',retrieved_at=now,parse_status='parsed',lineage_key='SYNTHETIC-second:'+suffix,
            publisher=source.name,normalizer_version='TEST',normalized_payload={'canonical_id':seed.cve})
        db.add(obs);db.flush()
        value={**base.value_json,'raw_expression':'<=0.8.0'}
        claim=m.Claim(claim_key='SYNTHETIC-conflict:'+suffix,vulnerability_id=seed.vulnerability_id,
            package_identifier_id=seed.package_id,claim_type='AFFECTS_VERSION',predicate='AFFECTS_VERSION',
            scope_key=base.scope_key,value_json=value)
        db.add(claim);db.flush();quote='affected <=0.8.0'
        db.add(m.Evidence(claim_id=claim.id,source_id=source.id,raw_document_id=raw.id,observation_id=obs.id,
            scope_key=base.scope_key,evidence_type='official_vendor_advisory',stance='support',excerpt=quote,
            excerpt_hash=hashlib.sha256(quote.encode()).hexdigest(),source_url=raw.source_url,
            published_at=now,retrieved_at=now,locator={'line':1},locator_key='affected',observed_value=value,
            publisher=source.name,lineage_key=obs.lineage_key,details={'is_test':True,'explicit':True}))
    src=source_for(engine,seed)
    assert src.artifact.status=='CONFLICT' and src.artifact.runtime_status=='WAITING_REVIEW'
    before=src.artifact.model_dump(mode='json');svc=service(engine)
    out=svc.read_results(svc.run(request(src),actor=seed.actor).run_id,actor=seed.actor)
    assert out.artifacts[0].verification_status=='CONFLICT'
    assert out.artifacts[0].conflicting_evidence and out.artifacts[0].execution_status=='WAITING_REVIEW'
    assert before==src.service.read_results(src.artifact.run_id,seed.actor).artifacts[0].model_dump(mode='json')


def test_blocked_source_task_without_artifact_cannot_be_verified(engine):
    seed=verification_seed.__wrapped__(engine)
    with transaction(engine) as db:db.get(m.Source,seed.source_id).authority_level='community'
    original,saved,_,_=run(engine,seed,'evidence')
    got=original.read_results(saved.runtime_run_id,seed.actor)
    assert got.blocked_tasks==('evidence',)
    req=request(SimpleNamespace(artifact=got.artifacts[0],seed=seed)).model_copy(
        update={'source_task_id':'evidence','source_artifact_id':uuid4()})
    with pytest.raises(LookupError):service(engine).run(req,actor=seed.actor)

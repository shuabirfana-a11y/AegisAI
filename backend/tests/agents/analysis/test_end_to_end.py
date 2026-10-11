"""Real database/process/tool handoff; controlled local HTTP is a provider fixture."""
import json
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from sqlalchemy import select,func
from app.db import models as m
from app.db.session import transaction
from tests.agents.analysis.helpers import module,request


def counts(engine):
    tables=('Asset','AssetComponent','AssetRiskSnapshot','AssetVulnerabilityMatch','Claim','Evidence',
        'VerificationResult','ConflictRecord','ReviewTask')
    with transaction(engine) as db:
        return {name:db.scalar(select(func.count()).select_from(getattr(m,name))) for name in tables}


@pytest.mark.parametrize('kind',['risk_analysis','asset_impact_analysis','remediation_prioritization'])
def test_real_handoff_without_business_writes(engine,analysis_source,kind):
    src=analysis_source;svc=module('service').SecurityAnalysisService(engine);before=counts(engine)
    original=src.investigation.model_dump_json();verified=src.verification.model_dump_json()
    saved=svc.run(request(src,task_type=kind),actor=src.seed.actor)
    art=svc.read_results(saved.run_id,actor=src.seed.actor).artifacts[0]
    assert art.asset_match_status=='MATCHED' and art.version_match_status=='AFFECTED' and art.affected is True
    assert art.verification_status=='CONFIRMED' and art.confidence<=src.verification.confidence
    assert counts(engine)==before
    assert src.original.read_results(src.investigation.run_id,src.seed.actor).artifacts[0].model_dump_json()==original
    assert src.verifier.read_results(src.verification.run_id,actor=src.seed.actor).artifacts[0].model_dump_json()==verified


@pytest.mark.parametrize('mode',['valid','invalid_json','invented_version'])
def test_real_model_adapter_preserves_decisions_and_records_calls(engine,analysis_source,monkeypatch,mode):
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append(body)
            supplied=json.loads(body['messages'][-1]['content'])
            result={'explanation_sections':['impact','uncertainty'],'factor_ids':supplied['factor_ids'],
                'action_ids':list(reversed(supplied['action_ids']))}
            if mode=='invented_version':result['fixed_version']='9.9.9'
            text='{bad json' if mode=='invalid_json' else json.dumps(result)
            output={'id':'SYNTHETIC','model':'synthetic-analysis','choices':[{'index':0,
                'message':{'role':'assistant','content':text},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':20,'completion_tokens':5,'total_tokens':25}}
            data=json.dumps(output).encode();self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    env={'MODEL_PROVIDER':'openai_compatible','MODEL_NAME':'synthetic-analysis',
        'MODEL_API_BASE':'http://127.0.0.1:'+str(server.server_port)+'/v1','MODEL_API_KEY':'',
        'MODEL_ALLOW_KEYLESS_LOCAL':'true','MODEL_EMBEDDING_PROVIDER':'mock',
        'MODEL_EMBEDDING_NAME':'mock-embedding-v1','MODEL_EMBEDDING_DIMENSION':'384'}
    for key,value in env.items():monkeypatch.setenv(key,value)
    try:
        src=analysis_source;svc=module('service').SecurityAnalysisService(engine);req=request(src,model_assistance=True)
        ctx=svc.contexts.capture(req,actor=src.seed.actor)
        from app.tooling.analysis import base_assessment,protected_decision
        base=base_assessment(ctx);saved=svc.runtime.run_context(ctx,actor=src.seed.actor)
        art=svc.read_results(saved.run_id,actor=src.seed.actor).artifacts[0]
        assessment=module('schemas').RiskAssessment.model_validate(art.model_dump(exclude=set(type(art).model_fields)-set(type(base).model_fields)))
        assert protected_decision(assessment)==protected_decision(base)
        assert art.model_assist_status==('SUCCEEDED' if mode=='valid' else 'FAILED')
        assert len(calls)==1 and calls[0]['max_tokens']==512
        assert art.model_calls[0]['usage']['total_tokens']==25
        assert art.model_calls[0]['provider']=='openai_compatible'
        assert svc.run(req,actor=src.seed.actor)==saved and len(calls)==1
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def test_changed_model_config_skips_call_and_keeps_rules(engine,analysis_source,monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER','mock');monkeypatch.setenv('MODEL_NAME','mock-model-v1')
    src=analysis_source;svc=module('service').SecurityAnalysisService(engine)
    ctx=svc.contexts.capture(request(src,model_assistance=True),actor=src.seed.actor)
    monkeypatch.setenv('MODEL_NAME','changed-model')
    saved=svc.runtime.run_context(ctx,actor=src.seed.actor)
    art=svc.read_results(saved.run_id,actor=src.seed.actor).artifacts[0]
    assert art.affected is True and art.priority=='REVIEW_REQUIRED' and not art.model_calls
    assert art.model_assist_status=='FAILED' and any('configuration' in w for w in art.warnings)

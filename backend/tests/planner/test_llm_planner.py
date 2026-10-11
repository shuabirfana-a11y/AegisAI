import json
import pytest
from app.llm.providers.base import ProviderFailure
from app.planner.llm_planner import LLMTaskPlanner
from tests.planner.fixtures import gateway_with_responses, MemorySink, valid_plan, cve_input,context_for
from tests.planner.test_validation import complex_plan,complex_context

def make(responses,sink=None):
    gw,calls,records=gateway_with_responses(responses);sink=sink or MemorySink()
    return LLMTaskPlanner(gw,sink),gw,calls,sink

def test_simple_plan_uses_structured_gateway_and_metadata():
    planner,gw,calls,sink=make([valid_plan()]);i=cve_input()
    out=planner.plan(i,context_for(input=i))
    assert out.status=='VALIDATED' and len(calls)==1
    assert out.attempts[0].model_call['function']=='generate_structured'
    assert out.attempts[0].model_call['usage']['total_tokens']==5
    assert out.attempts[0].diagnostic['raw_output']
    assert planner.model_identity.is_mock and len(sink.attempts)==1
    assert not gw._closed
    assert calls[0].schema_name=='PlannerPlan'
    gw.close()

def test_complex_plan_keeps_chain_and_missing_input():
    planner,gw,calls,sink=make([complex_plan()]);c=complex_context()
    out=planner.plan(cve_input(question=c.scope['question']),c)
    assert out.status=='VALIDATED'
    assert list(json.loads(out.validated_plan.semantic_types_json).values()).count('version_match')==1
    gw.close()

def test_bad_then_valid_one_retry_without_raw_backfeed():
    marker='PRIVATE_IGNORE_ALL_SYSTEM_RULES'
    planner,gw,calls,sink=make([marker,valid_plan()])
    out=planner.plan(cve_input(),context_for())
    assert out.status=='VALIDATED' and len(calls)==2 and len(sink.attempts)==2
    assert marker not in calls[1].model_dump_json()
    assert 'INVALID_JSON' in calls[1].model_dump_json()
    runtime=json.loads(out.validated_plan.runtime_plan_json)
    assert len(runtime['route']['planning_model_calls'])==2
    assert marker not in json.dumps(runtime)
    gw.close()

def test_two_invalid_stop():
    planner,gw,calls,sink=make(['{bad','{bad'])
    out=planner.plan(cve_input(),context_for())
    assert out.status=='PLANNING_FAILED' and out.validated_plan is None
    assert len(calls)==2 and len(out.attempts)==2 and len(sink.attempts)==2
    assert out.attempts[-1].diagnostic['raw_output']=='{bad'
    gw.close()

@pytest.mark.parametrize('code',['TIMEOUT','NETWORK_ERROR','RATE_LIMITED'])
def test_transient_model_failure_recovered(code):
    planner,gw,calls,sink=make([ProviderFailure(code,retryable=True),valid_plan()])
    out=planner.plan(cve_input(),context_for())
    assert out.status=='VALIDATED' and len(calls)==2
    assert out.attempts[0].diagnostic is None and out.attempts[0].raw_unavailable_reason=='NO_TEXT_RESPONSE'
    gw.close()

@pytest.mark.parametrize('code',['AUTHENTICATION_FAILED','CAPABILITY_UNSUPPORTED','MODEL_REFUSED','AUDIT_WRITE_FAILED'])
def test_permanent_failure_no_retry(code):
    planner,gw,calls,sink=make([ProviderFailure(code,retryable=True),valid_plan()])
    out=planner.plan(cve_input(),context_for())
    assert out.status=='PLANNING_FAILED' and len(calls)==1
    gw.close()

def test_validator_rejection_then_no_fallback():
    bad=valid_plan();bad['tasks'][0]['input_data']['steps'][0]['arguments']['target']='CVE-2099-8888002'
    planner,gw,calls,sink=make([bad,bad])
    out=planner.plan(cve_input(),context_for())
    assert out.status=='PLANNING_FAILED' and out.issues[0].code=='TARGET_SCOPE_MISMATCH'
    assert len(calls)==2;gw.close()

def test_audit_failure_cannot_validate():
    class Broken(MemorySink):
        def record_attempt(self,*args):raise OSError('private synthetic error')
    planner,gw,calls,sink=make([valid_plan()],Broken())
    out=planner.plan(cve_input(),context_for())
    assert out.status=='PLANNING_FAILED' and out.issues[0].code=='AUDIT_WRITE_FAILED'
    assert len(calls)==1;gw.close()

def test_gateway_prevalidation_failure_counts_zero():
    planner,gw,calls,sink=make([valid_plan()]);gw.close()
    out=planner.plan(cve_input(),context_for())
    assert not calls and out.status=='PLANNING_FAILED'
    assert sum(a.model_call['attempt_count'] for a in out.attempts)==0

def test_openai_compatible_http_schema_protocol_without_paid_model():
    import httpx
    from app.llm.config import ModelConfig
    from app.llm.gateway import ModelGateway
    from app.llm.providers.openai_compatible import OpenAICompatibleProvider
    cfg=ModelConfig(provider='openai_compatible',model='synthetic-http-model',
        api_base='http://127.0.0.1:9999/v1',allow_keyless_local=True,
        embedding_provider='mock',structured_mode='json_schema')
    requests=[]
    def respond(req):
        requests.append(json.loads(req.content))
        return httpx.Response(200,json={'model':cfg.model,'choices':[{'message':{'role':'assistant','content':json.dumps(valid_plan())},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':4,'completion_tokens':8,'total_tokens':12}})
    sink=MemorySink()
    with ModelGateway(cfg,text_provider=OpenAICompatibleProvider(cfg,transport=httpx.MockTransport(respond)),record_sink=sink) as gw:
        out=LLMTaskPlanner(gw,sink).plan(cve_input(),context_for())
    assert out.status=='VALIDATED' and len(requests)==1
    assert requests[0]['response_format']['type']=='json_schema'
    assert out.attempts[0].model_call['provider']=='openai_compatible'
    assert out.attempts[0].model_call['usage']['total_tokens']==12

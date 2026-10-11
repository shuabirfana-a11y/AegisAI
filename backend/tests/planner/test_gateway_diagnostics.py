import hashlib
import pytest
from pydantic import SecretStr
from app.llm.config import ModelConfig
from app.llm.providers.base import ProviderFailure
from app.planner.schemas import PlannerPlan
from tests.planner.fixtures import gateway_with_text,structured_request,gateway_with_responses,valid_plan

@pytest.mark.parametrize('output,code',[('{bad','INVALID_JSON'),('{}','SCHEMA_VALIDATION_FAILED'),
    ('{"x":NaN}','INVALID_JSON'),('{"x":1,"x":2}','INVALID_JSON')])
def test_invalid_output_retained_privately(output,code):
    got=[]
    with gateway_with_text(output) as gw:
        r=gw.generate_structured(structured_request(),output_model=PlannerPlan,output_observer=got.append)
    assert r.status=='failed' and r.error.code==code
    assert len(got)==1 and got[0].raw_output==output
    assert got[0].request_id==r.request_id
    assert output not in r.model_dump_json()

def test_truncation_still_has_diagnostic():
    got=[]
    with gateway_with_text('{bad',finish_reason='length') as gw:
        r=gw.generate_structured(structured_request(),output_model=PlannerPlan,output_observer=got.append)
    assert r.error.code=='OUTPUT_TRUNCATED' and got[0].raw_output=='{bad'

def test_oversized_multibyte_key_redaction():
    key='synthetic-secret';output=key+'中'*30000;got=[]
    with gateway_with_text(output,config=ModelConfig(api_key=SecretStr(key))) as gw:
        gw.generate_structured(structured_request(),output_model=PlannerPlan,output_observer=got.append)
    d=got[0];assert key not in d.raw_output and d.redacted and d.truncated
    assert len(d.raw_output.encode('utf-8'))<=65536
    assert d.original_bytes==len(output.encode('utf-8'))
    assert d.sha256==hashlib.sha256(output.encode()).hexdigest()

def test_observer_failure_is_closed():
    def broken(d):raise OSError('synthetic audit failure')
    with gateway_with_text(valid_plan()) as gw:
        r=gw.generate_structured(structured_request(),output_model=PlannerPlan,output_observer=broken)
    assert r.status=='failed' and r.error.code=='AUDIT_WRITE_FAILED'

def test_no_response_and_default_logs():
    got=[];gw,calls,sink=gateway_with_responses([ProviderFailure('TIMEOUT',retryable=True)])
    with gw:r=gw.generate_structured(structured_request(),output_model=PlannerPlan,output_observer=got.append)
    assert r.error.code=='TIMEOUT' and not got
    gw,calls,sink=gateway_with_responses(['PRIVATE_SYNTHETIC_BAD_JSON'])
    with gw:r=gw.generate_structured(structured_request(),output_model=PlannerPlan)
    assert 'PRIVATE_SYNTHETIC_BAD_JSON' not in r.model_dump_json()+sink.records[0].model_dump_json()

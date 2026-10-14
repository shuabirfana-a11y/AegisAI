"""Protocol-only result: a missing-context response earns no fabricated facts."""
import httpx
from evaluation.bench.http_investigation import InvestigationHTTPAdapter
from tests.aegisbench.test_http_investigation import question,binding


def test_need_context_is_not_a_planner_failure_or_successful_risk_answer():
    q=question(version=None);calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'status':'NEED_CONTEXT','missing_fields':['version'],
            'message':'请补充版本。','next_actions':['SUPPLY_CONTEXT','PUBLIC_FACT_LOOKUP'],
            'investigation_created':False,'execution_mode':'NOT_STARTED'})
    with httpx.Client(base_url='http://127.0.0.1:9',transport=httpx.MockTransport(handler)) as client:
        adapter=InvestigationHTTPAdapter(client=client,token='SYNTHETIC-context-token',
            bindings={q.id:binding()},expected_mode='REAL')
        result=adapter.run(q,{})
    assert len(calls)==1
    assert result.status=='NOT_EVALUATED' and result.error_code is None
    assert result.abstained is True
    assert result.answer=={'native_context_status':'NEED_CONTEXT','missing_fields':['version']}
    assert 'risk_level' not in result.answer and 'affected' not in result.answer
    assert result.metadata['execution_mode']=='NOT_STARTED'
    assert adapter.records[q.id]['context_required'] is True

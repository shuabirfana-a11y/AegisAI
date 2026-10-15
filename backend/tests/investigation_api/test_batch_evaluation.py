"""Production HTTP batch/child/Runtime chain on synthetic, non-gold data."""
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from tests.investigation_api.test_multi_asset_database import setup_batch
from tests.investigation_api.test_multi_asset_chain import plans,configure
from tests.planner.fixtures import gateway_with_responses
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from evaluation.bench.schema import Question
from evaluation.bench.http_investigation import InvestigationHTTPAdapter

def test_evaluation_uses_real_batch_and_two_independent_child_answers(engine,monkeypatch):
    seed,old=setup_batch(engine);old.close();gw,calls,_=gateway_with_responses(plans(seed));configure(monkeypatch,seed)
    q=Question(id='SYNTHETIC_BATCH_EVAL_NOT_GOLD',category='multihop',question='Prioritize the supplied assets',
        origin='TEST_FIXTURE',source_ids=['SYNTHETIC_SOURCE'],input_context={'target':seed.cve,
            'component':seed.component['package_name'],'ecosystem':'PyPI','assets':[
                {'id':'input-a','component':seed.component['package_name'],'version':'0.6.0'},
                {'id':'input-b','component':seed.component['package_name'],'version':'0.7.0'}]})
    bindings={q.id:{'assets':[
        {'input_id':'input-a','asset_id':str(seed.asset_id),'component_id':str(seed.component_id)},
        {'input_id':'input-b','asset_id':str(seed.second_asset_id),'component_id':str(seed.second_component_id)}]}}
    try:
        with TestClient(create_app(engine,investigation_gateway=gw)) as client:
            a=InvestigationHTTPAdapter(client=client,token='SYNTHETIC-batch-token',bindings=bindings,
                expected_mode='MOCK',timeout=180,poll_interval=.1)
            p=a.run(q,{})
            assert p.status=='SUCCEEDED',(p.error_code,a.records[q.id].get('adapter_error_code'),a.records[q.id].get('error_class'))
            assert p.answer['priority_asset_ids']==['input-a']
            record=a.records[q.id]
            assert record['batch_response']['execution_status']=='COMPLETED'
            assert len(record['children'])==2 and len(calls)==2
            assert all(c['record']['answer']['result_version']==1 for c in record['children'])
            assert len({c['record']['answer']['answer_id'] for c in record['children']})==2
            assert q.id not in str(record['request'])
    finally:gw.close()

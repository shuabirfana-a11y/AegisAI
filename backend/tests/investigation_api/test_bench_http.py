"""Real HTTP + original services over synthetic inputs; NOT benchmark gold."""
import sys,json
from pathlib import Path
import pytest
from app.main import create_app
from tests.orchestration.fixtures import scenario
from tests.investigation_api.test_tcp_chain import tcp_client,TOKEN

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from evaluation.bench.schema import Question
from evaluation.bench.http_investigation import InvestigationHTTPAdapter


@pytest.mark.parametrize('mode',['complete','unknown_version','conflict'])
def test_evaluation_adapter_reaches_full_original_http_chain(engine,monkeypatch,mode):
    seed,request,gateway,calls,_=scenario(engine,mode)
    monkeypatch.setenv('AEGIS_ASSET_TOKEN',TOKEN)
    monkeypatch.setenv('AEGIS_ASSET_OWNER',seed.actor)
    context={'target':seed.cve}
    if request.planner_input.component is not None:
        context['component']=request.planner_input.component.model_dump(mode='json',exclude_none=True)
    q=Question(id='SYNTHETIC_HTTP_CONTROL_'+mode,question=request.user_query,category='risk',
        origin='TEST_FIXTURE',source_ids=['SYNTHETIC_NOT_BENCHMARK'],
        input_context=context)
    binding={'asset_id':str(seed.asset_id),'component_id':str(seed.component_id)}
    try:
        with tcp_client(create_app(engine,investigation_gateway=gateway)) as client:
            adapter=InvestigationHTTPAdapter(client=client,token=TOKEN,bindings={q.id:binding},
                timeout=90,poll_interval=.05,expected_mode='MOCK')
            prediction=adapter.run(q,{})
            record=adapter.records[q.id]
            if mode=='unknown_version':
                # Phase13-F.4 approved preflight: no Planner/Run/Gate is created.
                assert prediction.status=='NOT_EVALUATED' and prediction.abstained
                assert prediction.answer['native_context_status']=='NEED_CONTEXT'
                assert 'version' in prediction.answer['missing_fields']
                assert record['created']['investigation_created'] is False
                assert record['created']['execution_mode']=='NOT_STARTED'
                assert record['completed'] and not calls
                assert 'investigation_id' not in record and 'trace' not in record
                assert len(record['endpoints'])==1 and record['endpoints'][0]['http_status']==200
                assert 'expected_answer' not in json.dumps(record['request'])
                assert q.id not in json.dumps(record['request'])
                return
            assert prediction.status=='SUCCEEDED',record
            assert calls and record['trace']['planner']['validation_status']=='VALIDATED'
            assert len(record['trace']['agent_runs'])==3
            assert record['artifacts']['verification']['version_observations']
            assert record['artifacts']['verification']['impact_version_evidence']
            assert prediction.metadata['is_mock'] is True
            assert q.id not in json.dumps(record['request'])
            assert 'expected_answer' not in json.dumps(record['request'])
            if mode=='complete':
                assert record['integration']['status']=='PASS'
                assert prediction.answer['affected']=='AFFECTED' and prediction.answer['risk_level']=='HIGH'
            else:
                assert prediction.abstained is True and prediction.answer['risk_level']=='UNKNOWN'
                assert record['integration']['status'] in {'REPLAN_REQUIRED','HUMAN_REVIEW_REQUIRED'}
            if mode=='conflict':assert prediction.answer['verification_status']=='CONFLICT'
            (ROOT/'work/phase13d-e2e').mkdir(parents=True,exist_ok=True)
            (ROOT/'work/phase13d-e2e'/('http-control-'+mode+'.json')).write_text(
                json.dumps({'origin':'SYNTHETIC_HTTP_ENGINEERING_CONTROL_NOT_BENCHMARK',
                    'prediction':prediction.model_dump(mode='json'),'record':record},ensure_ascii=False,indent=2)+'\n',
                encoding='utf-8',newline='\n')
    finally:gateway.close()

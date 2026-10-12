"""Negative controls from a frozen synthetic HTTP run; never benchmark gold."""
import json
from pathlib import Path
from uuid import uuid4
import httpx
import pytest
from evaluation.bench.http_investigation import InvestigationHTTPAdapter, build_request
from evaluation.bench.schema import Question


def fixture():
    return json.loads((Path(__file__).parent / 'fixtures/http-investigation-complete.json').read_text(encoding='utf-8'))


def inputs(data, nested_asset=False):
    observed = data['artifacts']['verification']['version_observations'][0]
    component = {k: observed[k] for k in ('ecosystem','package_name','version','purl')}
    component['name'] = observed['component']
    context = {'component': component, 'environment': observed['environment'], 'exposure': observed['exposure']}
    if nested_asset: context = {'assets': [context]}
    q = Question(id='SYNTHETIC-INTEGRITY-CONTROL', category='risk', origin='TEST_FIXTURE',
                 question=data['answer']['original_question'], input_context=context, source_ids=['SYNTHETIC'])
    return q, {'asset_id': observed['asset_id'], 'component_id': observed['component_id']}


def run(data, q, binding, fail_answer=False):
    def handler(request):
        if request.method == 'POST':
            return httpx.Response(202, json={**data['status'], 'reused':False,'model_provider':'mock','is_mock':True})
        name = request.url.path.rsplit('/',1)[-1]
        if name == 'answer' and fail_answer: return httpx.Response(503, json={'message':'SYNTHETIC failure'})
        return httpx.Response(200, json=data[name])
    with httpx.Client(base_url='http://127.0.0.1:9', transport=httpx.MockTransport(handler)) as client:
        adapter = InvestigationHTTPAdapter(client=client,token='SYNTHETIC-token',bindings={q.id:binding},expected_mode='MOCK')
        prediction = adapter.run(q,{})
    return prediction, adapter.records[q.id]


@pytest.mark.parametrize('version', [None, 'ABSENT'])
def test_binding_cannot_fill_missing_or_null_version(version):
    data=fixture();q,b=inputs(data)
    c=q.input_context['component']
    if version=='ABSENT':c.pop('version')
    else:c['version']=version
    with pytest.raises(ValueError,match='COMPONENT_BINDING_MISMATCH'):
        build_request(q,{**b,'component':{'version':'0.6.0'}})


def test_original_frozen_scope_and_answer_are_accepted():
    data=fixture();q,b=inputs(data)
    assert run(data,q,b)[0].status=='SUCCEEDED'


def test_display_name_can_differ_from_the_explicit_matching_package_identity():
    data=fixture();q,b=inputs(data)
    q.input_context['component']['name']='vllm'
    assert run(data,q,b)[0].status=='SUCCEEDED'


@pytest.mark.parametrize('change', ['question','asset','component','version','package','citation','fact','gate','investigation_trace'])
def test_unrelated_question_asset_and_artifact_references_are_rejected(change):
    data=fixture();q,b=inputs(data,nested_asset=True)
    o=data['artifacts']['verification']['version_observations'][0]
    if change=='question':
        data['trace']['original_question']=data['answer']['original_question']='Unrelated SYNTHETIC question'
    elif change in ('asset','component'):
        o[change+'_id']=str(uuid4())
    elif change=='version':o['version']='9.9.9'
    elif change=='package':o['package_name']='unrelated-component'
    elif change=='citation':
        bad=str(uuid4())
        for c in data['answer']['citations']:c['verification_artifact']['artifact_id']=bad
        for c in data['answer']['evidence_observations']:c['verification_artifact']['artifact_id']=bad
    elif change=='fact':data['answer']['verified_claims'][0]['source_artifact']['artifact_id']=str(uuid4())
    elif change=='gate':data['integration']['artifact_references'][0]['artifact_id']=str(uuid4())
    else:
        ref=data['artifacts']['investigation']['artifact_id']
        for agent in data['trace']['agent_runs']:
            agent['artifact_references']=[x for x in agent['artifact_references'] if x['artifact_id']!=ref]
    assert run(data,q,b)[0].status=='FAILED'


def test_failed_final_read_retains_all_acquired_material_and_model_metadata():
    data=fixture();q,b=inputs(data)
    prediction,record=run(data,q,b,fail_answer=True)
    assert prediction.status=='FAILED' and prediction.error_code=='HTTP_503'
    assert all(key in record for key in ('status','trace','artifacts','integration'))
    assert record['completed'] is False and 'answer' not in record
    assert prediction.metadata['model']==data['trace']['model_execution']['model']

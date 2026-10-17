"""Asset/run-bound persisted risks plus bounded publication permutations.

The HTTP fixture uses real database/tools/verification/risk/Gate and a scripted
planner. Publication permutations use explicit synthetic DTOs, not real-model
security conclusions; the separate local-model runs cover that boundary.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.agents.analysis.reader import AnalysisReader
from app.agents.analysis.context_store import AnalysisContextStore
from app.agents.contracts import AgentFrameworkError
from app.investigation_api.multi_asset_projection import summarize
from app.investigation_api.projection import public_copy
from tests.investigation_api.test_multi_asset_database import setup_batch
from tests.investigation_api.test_multi_asset_chain import plans, wait, HEADERS
from tests.investigation_api.test_multi_asset import item
from tests.planner.fixtures import gateway_with_responses


@pytest.fixture(scope='module')
def sealed_pair(engine):
    seed,old=setup_batch(engine);old.close()
    gw,calls,_=gateway_with_responses(plans(seed)+plans(seed))
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('AEGIS_ASSET_TOKEN','SYNTHETIC-batch-token')
        patch.setenv('AEGIS_ASSET_OWNER',seed.actor)
        try:
            with TestClient(create_app(engine,investigation_gateway=gw)) as client:
                body={'vulnerability_id':seed.cve,'asset_ids':[str(seed.asset_id),str(seed.second_asset_id)]}
                batches=[];keys=[];risks=[]
                for _ in range(2):
                    key=uuid4().hex;keys.append(key)
                    created=client.post('/api/investigations/batches',json=body,headers={**HEADERS,'Idempotency-Key':key})
                    assert created.status_code==202,created.text
                    batch=wait(client,created.json()['batch_id'])
                    assert all(i['execution_status']=='COMPLETED' for i in batch['items']),batch
                    batches.append(batch);by_asset={}
                    for i in batch['items']:
                        art=client.get(f"/api/investigations/{i['investigation_id']}/artifacts",headers=HEADERS).json()['analysis']
                        assert art['asset_id']==i['snapshot']['asset_id']
                        native=AnalysisReader(engine).read(art['run_id'],actor=seed.actor).artifacts[0].model_dump(mode='json')
                        assert public_copy(native)==art
                        by_asset[art['asset_id']]=native
                    risks.append(by_asset)
                yield SimpleNamespace(seed=seed,client=client,body=body,keys=keys,batches=batches,risks=risks,calls=calls,engine=engine)
        finally:gw.close()


def test_a_ten_idempotent_executions_preserve_each_asset_artifact(sealed_pair):
    p=sealed_pair
    for _ in range(10):
        result=p.client.post('/api/investigations/batches',json=p.body,headers={**HEADERS,'Idempotency-Key':p.keys[0]})
        assert result.status_code==202 and result.json()['reused'] is True
        assert result.json()['items']==p.batches[0]['items']
    assert len(p.calls)==4  # Two fresh investigations per batch; retries admit none.


def test_b_input_swap_does_not_reassign_child_or_risk(sealed_pair):
    p=sealed_pair;body={**p.body,'asset_ids':list(reversed(p.body['asset_ids']))}
    result=p.client.post('/api/investigations/batches',json=body,headers={**HEADERS,'Idempotency-Key':p.keys[0]})
    assert result.status_code==202 and result.json()['items']==p.batches[0]['items']


def read_risk(p,art):
    found=AnalysisReader(p.engine).read(art['run_id'],actor=p.seed.actor).artifacts[0].model_dump(mode='json')
    assert found==art
    return found


def test_c_concurrent_asset_reads_do_not_share_mutable_artifacts(sealed_pair):
    p=sealed_pair;arts=list(p.risks[0].values())
    with ThreadPoolExecutor(2) as pool:outputs=list(pool.map(lambda a:read_risk(p,a),arts))
    assert len({a['artifact_id'] for a in outputs})==2
    outputs[0]['evidence_refs'].clear()
    assert read_risk(p,arts[1])['evidence_refs'] and read_risk(p,arts[0])['evidence_refs']


@pytest.mark.parametrize('reverse',[False,True],ids=['D_A_then_B','E_B_then_A'])
def test_ordered_rereads_preserve_first_and_second_artifact(sealed_pair,reverse):
    p=sealed_pair;arts=list(p.risks[0].values())
    if reverse:arts.reverse()
    before=read_risk(p,arts[0]);read_risk(p,arts[1])
    assert read_risk(p,arts[0])==before


def test_f_i_new_investigation_of_same_assets_cannot_replace_old_artifacts(sealed_pair):
    p=sealed_pair
    assert p.batches[0]['batch_id']!=p.batches[1]['batch_id']
    for asset in p.risks[0]:
        old,new=p.risks[0][asset],p.risks[1][asset]
        assert old['artifact_id']!=new['artifact_id'] and old['run_id']!=new['run_id'] and old['context_id']!=new['context_id']
        assert old['input_artifact_ids']!=new['input_artifact_ids']
        assert (old['asset_id'],old['version'],old['risk_level'])==(new['asset_id'],new['version'],new['risk_level'])
        assert read_risk(p,old)==old and read_risk(p,new)==new


def test_h_same_cve_different_assets_keep_individual_verdicts(sealed_pair):
    p=sealed_pair;a=p.risks[0][str(p.seed.asset_id)];b=p.risks[0][str(p.seed.second_asset_id)]
    assert (a['affected'],a['risk_level'],a['version'])==(True,'HIGH','0.6.0')
    assert (b['affected'],b['risk_level'],b['version'])==(False,'LOW','0.7.0')
    assert set(a['input_artifact_ids']).isdisjoint(b['input_artifact_ids'])
    assert p.batches[0]['summary']['actionable_asset_ids']==[a['asset_id']]


def test_g_context_and_risk_cannot_be_rebound_to_other_vulnerability(sealed_pair):
    p=sealed_pair;art=next(iter(p.risks[0].values()))
    context=AnalysisContextStore(p.engine).read(art['context_id'],actor=p.seed.actor)
    original=context.inputs.investigation.canonical_id
    assert original==p.seed.cve
    other=context.inputs.investigation.model_copy(update={'canonical_id':'CVE-2099-99999999'})
    altered=context.inputs.model_copy(update={'investigation':other})
    # Sealed input hash, which includes the source vulnerability and artifacts,
    # distinguishes identical asset/version inventory with different CVEs.
    from app.agents.contracts import fingerprint
    assert fingerprint(altered.model_dump(mode='json'))!=context.input_snapshot_hash
    changed=context.model_dump(mode='json');changed['inputs']=altered.model_dump(mode='json')
    row=SimpleNamespace(id=context.context_id,actor_principal=p.seed.actor,details={'analysis_v1':{'context':changed}})
    with pytest.raises(ValueError,match='Analysis input snapshot hash invalid'):
        AnalysisContextStore(p.engine)._decode(row)
    assert read_risk(p,art)==art


def test_j_reverse_completion_of_reads_keeps_id_binding(sealed_pair):
    from threading import Event
    p=sealed_pair;arts=list(p.risks[0].values());second_done=Event();completion=[]
    def first():
        assert second_done.wait(10);result=read_risk(p,arts[0]);completion.append(result['asset_id']);return result
    def second():
        result=read_risk(p,arts[1]);completion.append(result['asset_id']);second_done.set();return result
    with ThreadPoolExecutor(2) as pool:
        a=pool.submit(first);b=pool.submit(second);results=[a.result(timeout=15),b.result(timeout=15)]
    assert completion==[arts[1]['asset_id'],arts[0]['asset_id']]
    assert [r['artifact_id'] for r in results]==[a['artifact_id'] for a in arts]


@pytest.mark.parametrize('input_reverse',[False,True])
@pytest.mark.parametrize('completion_reverse',[False,True])
def test_actual_child_collector_uses_selected_asset_even_when_publication_order_reverses(sealed_pair,input_reverse,completion_reverse):
    """Real stored children/reader/risk; only the publication repository is local.

    Production executes batch children serially. This deliberately exercises
    the collector out of order without changing that execution policy.
    """
    from app.investigation_api.multi_asset_schemas import BatchResponse
    from app.investigation_api.multi_asset_service import MultiAssetService
    p=sealed_pair;response=BatchResponse.model_validate(deepcopy(p.batches[0]))
    if input_reverse:response.items=tuple(reversed(response.items))
    for it in response.items:
        it.execution_status='RUNNING';it.impact='UNKNOWN';it.risk_level='UNKNOWN';it.priority='REVIEW_REQUIRED'
        it.artifact_references=();it.answer_id=None;it.integration_result_id=None
    record=SimpleNamespace(response=response)
    class PublicationRepository:
        def read(self,*args):return record
        def mutate(self,id,actor,fn):
            fn(record);record.response.summary=summarize(record.response.items);return record
    service=object.__new__(MultiAssetService)
    service.engine=p.engine;service.single=p.client.app.state.investigations;service.repo=PublicationRepository()
    indexes=[0,1]
    if completion_reverse:indexes.reverse()
    first=indexes[0]
    assert service._collect(response.batch_id,first,p.seed.actor) is True
    assert response.items[indexes[1]].execution_status=='RUNNING' and response.items[indexes[1]].risk_level=='UNKNOWN'
    assert service._collect(response.batch_id,indexes[1],p.seed.actor) is True
    expected={str(p.seed.asset_id):('AFFECTED','HIGH','P2'),str(p.seed.second_asset_id):('NOT_AFFECTED','LOW','DEFER')}
    for it in response.items:
        assert (it.impact,it.risk_level,it.priority)==expected[str(it.snapshot.asset_id)]
        native=p.risks[0][str(it.snapshot.asset_id)]
        assert any(str(ref.artifact_id)==native['artifact_id'] for ref in it.artifact_references)
        assert len(it.artifact_references)==3
    assert response.summary.actionable_asset_ids==(p.seed.asset_id,)


def test_two_assets_created_concurrently_receive_separate_risk_artifacts(sealed_pair):
    from app.db import models as m
    from app.db.session import transaction
    p=sealed_pair
    def create(version):
        with transaction(p.engine) as db:
            asset=m.Asset(name='SYNTHETIC simultaneous '+uuid4().hex,asset_type='service',owner_principal=p.seed.actor,is_demo=True)
            db.add(asset);db.flush()
            component=m.AssetComponent(asset_id=asset.id,package_identifier_id=p.seed.package_id,raw_package_name=p.seed.component['package_name'],version=version,ecosystem='PyPI',source='manual',identity_status='resolved')
            db.add(component);db.flush();return asset.id
    with ThreadPoolExecutor(2) as pool:ids=list(pool.map(create,['0.6.0','0.7.0']))
    seed=SimpleNamespace(**vars(p.seed));seed.asset_id,seed.second_asset_id=ids
    gw,_,_=gateway_with_responses(plans(seed))
    try:
        with TestClient(create_app(p.engine,investigation_gateway=gw)) as client:
            response=client.post('/api/investigations/batches',json={'vulnerability_id':p.seed.cve,'asset_ids':list(map(str,ids))},headers={**HEADERS,'Idempotency-Key':uuid4().hex})
            assert response.status_code==202,response.text
            result=wait(client,response.json()['batch_id']);artifacts=[]
            for i in result['items']:
                assert i['execution_status']=='COMPLETED',result
                art=client.get(f"/api/investigations/{i['investigation_id']}/artifacts",headers=HEADERS).json()['analysis'];artifacts.append(art)
                assert art['asset_id']==i['snapshot']['asset_id']
                assert art['affected']==(art['asset_id']==str(ids[0]))
            assert len({a['artifact_id'] for a in artifacts})==len({a['run_id'] for a in artifacts})==2
    finally:gw.close()


def test_second_cve_for_same_asset_has_its_own_source_and_risk_artifact(sealed_pair):
    import time
    from tests.orchestration.fixtures import scenario
    from tests.agents.investigation.test_end_to_end import plan_for
    from tests.planner.fixtures import task
    from app.orchestration.contracts import TERMINAL_STAGES
    p=sealed_pair;other,_,unused,_,_=scenario(p.engine);unused.close()
    original=p.risks[0][str(p.seed.asset_id)]
    seed=SimpleNamespace(**vars(p.seed));seed.cve=other.cve
    seed.component={**seed.component,'name':seed.component['package_name'],'version':'0.6.0'}
    plan=plan_for(seed,'version');plan['tasks'].append(task('asset_lookup','asset','get_asset',{'asset_id':str(seed.asset_id)}))
    gw,_,_=gateway_with_responses([plan])
    try:
        with TestClient(create_app(p.engine,investigation_gateway=gw)) as client:
            created=client.post('/api/investigations',json={'user_query':f'调查 {other.cve} 对当前登记组件 0.6.0 的影响','asset_scope':{'asset_id':str(seed.asset_id),'component_id':str(seed.component_id),'component':seed.component,'target':other.cve},'options':{'objective_profile':'asset_risk_v1'},'idempotency_key':uuid4().hex},headers=HEADERS)
            assert created.status_code==202,created.text
            id=created.json()['investigation_id'];end=time.monotonic()+60
            while time.monotonic()<end:
                status=client.get(f'/api/investigations/{id}/status',headers=HEADERS);assert status.status_code==200,status.text
                if status.json()['status'] in TERMINAL_STAGES:break
                time.sleep(.08)
            else:pytest.fail('Second scoped CVE investigation did not finish')
            artifacts=client.get(f'/api/investigations/{id}/artifacts',headers=HEADERS).json()
            risk=artifacts['analysis'];assert risk is not None
            assert risk['asset_id']==original['asset_id'] and risk['version']==original['version']
            assert risk['artifact_id']!=original['artifact_id'] and risk['run_id']!=original['run_id']
            context=AnalysisContextStore(p.engine).read(AnalysisReader(p.engine).read(risk['run_id'],actor=p.seed.actor).artifacts[0].context_id,actor=p.seed.actor)
            assert context.inputs.investigation.canonical_id==other.cve!=p.seed.cve
            assert set(risk['input_artifact_ids']).isdisjoint(original['input_artifact_ids'])
            assert read_risk(p,original)==original
    finally:gw.close()


@pytest.mark.parametrize('input_reverse',[False,True])
@pytest.mark.parametrize('completion_reverse',[False,True])
@pytest.mark.parametrize('scenario',['both_success','a_success_b_failed','a_failed_b_success','a_need_context_b_pass','a_conflict_b_normal'])
def test_publication_permutations_never_transfer_global_risk(input_reverse,completion_reverse,scenario):
    a=item(execution_status='COMPLETED',investigation_id=uuid4(),impact='AFFECTED',risk_level='HIGH',priority='P1',gate_status='PASS',verification_status='CONFIRMED',evidence_ids=('SYNTHETIC-A',))
    b=item(execution_status='COMPLETED',investigation_id=uuid4(),impact='NOT_AFFECTED',risk_level='LOW',priority='DEFER',gate_status='PASS',verification_status='CONFIRMED',evidence_ids=('SYNTHETIC-B',))
    if scenario=='a_success_b_failed':b=item(execution_status='FAILED',investigation_id=uuid4(),error_code='SYNTHETIC_FAILED')
    if scenario=='a_failed_b_success':a=item(execution_status='FAILED',investigation_id=uuid4(),error_code='SYNTHETIC_FAILED')
    if scenario=='a_need_context_b_pass':a=item(execution_status='NEED_CONTEXT',missing_fields=('version',))
    if scenario=='a_conflict_b_normal':a=item(execution_status='COMPLETED',investigation_id=uuid4(),gate_status='HUMAN_REVIEW_REQUIRED',verification_status='CONFLICT')
    inputs=[a,b];completions=[a,b]
    if input_reverse:inputs.reverse()
    if completion_reverse:completions.reverse()
    before={x.snapshot.asset_id:deepcopy(x.model_dump(mode='json')) for x in inputs}
    published={}
    for result in completions:
        published[result.snapshot.asset_id]=result.model_copy(deep=True)
        partial=summarize(tuple(published.values()))
        assert all(published[id].risk_level=='HIGH' and published[id].gate_status=='PASS' for id in partial.actionable_asset_ids)
    summary=summarize(tuple(published[x.snapshot.asset_id] for x in inputs))
    expected={
        'both_success':((a.snapshot.asset_id,),(),(b.snapshot.asset_id,),1,1,0),
        'a_success_b_failed':((a.snapshot.asset_id,),(b.snapshot.asset_id,),(),1,0,1),
        'a_failed_b_success':((),(a.snapshot.asset_id,),(b.snapshot.asset_id,),0,1,1),
        'a_need_context_b_pass':((),(a.snapshot.asset_id,),(b.snapshot.asset_id,),0,1,1),
        'a_conflict_b_normal':((),(a.snapshot.asset_id,),(b.snapshot.asset_id,),0,1,1),
    }[scenario]
    assert (summary.actionable_asset_ids,summary.unresolved_asset_ids,summary.unaffected_asset_ids,
        summary.counts['AFFECTED'],summary.counts['NOT_AFFECTED'],summary.counts['UNKNOWN'])==expected
    assert {id:x.model_dump(mode='json') for id,x in published.items()}==before
    assert summary.counts['total']==2

"""Deterministic publication interleaving; no synthetic security verdict claims."""
from types import SimpleNamespace as NS
from uuid import uuid4
from app.investigation_api.multi_asset_service import MultiAssetService


def test_batch_collection_pins_published_version_before_reading_child():
    asset=uuid4();component=uuid4();id=uuid4()
    item=NS(execution_status='RUNNING',investigation_id=id,result_version=1,
        snapshot=NS(asset_id=asset,selected_component_id=component,
            components=[NS(component_id=component,version='0.6.0')]))
    record=NS(response=NS(items=[item],vulnerability_id='CVE-2099-9999001'))
    class Repo:
        def read(self,*args):return record
        def mutate(self,id,actor,fn):fn(record);return record
    def result(version):
        return NS(answer=True,context=NS(current_stage='COMPLETED',error_code=None,
            planner_run_id='planner',artifact_references=('art-v'+str(version),),
            integration_result_id='gate-v'+str(version),answer_id='answer-v'+str(version)))
    first,second=result(1),result(2)
    class Single:
        supplements=object()
        published=1
        calls=[]
        def status(self,*args,**kwargs):
            self.published=2  # Publication occurs exactly before status read.
            return NS(processing_complete=True,result_version=2,supplement='summary-v2')
        def result(self,id,*,actor,version=None):
            self.calls.append(('result',version))
            return {1:first,2:second}[version or self.published]
        def artifacts(self,id,*,actor,version=None):
            self.calls.append(('artifacts',version))
            return NS(analysis=NS(asset_id=asset,version='0.6.0',inventory_revision=1,evaluation_time='time-v2'))
        def answer(self,id,*,actor,version=None):
            self.calls.append(('answer',version))
            return NS(unresolved_items=(),warnings=())
    svc=object.__new__(MultiAssetService);svc.single=Single();svc.repo=Repo()
    svc._bound_child=lambda item,actor,target=None,version=None:svc.single.result(id,actor=actor,version=version)
    svc._matches=lambda *args:True
    svc._sealed_snapshot_matches=lambda *args:True
    svc._decision=lambda *args:{'impact':'UNKNOWN','risk_level':'UNKNOWN','priority':'REVIEW_REQUIRED'}
    item.snapshot.components[0].inventory_revision=1
    assert svc._collect(uuid4(),0,'SYNTHETIC-owner') is True
    assert item.result_version==2
    assert item.answer_id=='answer-v2'
    assert item.integration_result_id=='gate-v2'
    assert item.artifact_references==('art-v2',)
    assert all(version==2 for _,version in svc.single.calls)

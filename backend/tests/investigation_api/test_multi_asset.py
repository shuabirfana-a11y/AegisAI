"""Batch adapter regressions; controlled inventory, never Benchmark gold."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.investigation_api.multi_asset_schemas import BatchRequest, BatchItem, BatchSnapshot
from app.investigation_api.multi_asset_projection import summarize


def item(**updates):
    return BatchItem(snapshot=BatchSnapshot(asset_id=uuid4(), asset_name='SYNTHETIC',
        captured_at='2026-10-15T00:00:00Z', inventory_hash='a'*64), **updates)


def test_unknown_and_failure_never_enter_low_risk_or_actionable_list():
    a=item(execution_status='COMPLETED', impact='AFFECTED', risk_level='HIGH', priority='P1',
           gate_status='PASS', verification_status='CONFIRMED', evidence_ids=('E1',))
    b=item(execution_status='NEED_CONTEXT', missing_fields=('version',))
    c=item(execution_status='FAILED', error_code='CHILD_FAILED')
    result=summarize((c,b,a))
    assert result.actionable_asset_ids == (a.snapshot.asset_id,)
    assert set(result.unresolved_asset_ids) == {b.snapshot.asset_id,c.snapshot.asset_id}
    assert result.counts['UNKNOWN']==2 and result.counts['AFFECTED']==1


@pytest.mark.parametrize('gate',['REPLAN_REQUIRED','HUMAN_REVIEW_REQUIRED','FAILED'])
def test_blocked_gate_cannot_be_overridden_by_batch_summary(gate):
    a=item(execution_status='COMPLETED', impact='AFFECTED', risk_level='HIGH', priority='P1',
           gate_status=gate, verification_status='CONFIRMED', evidence_ids=('E1',))
    assert summarize((a,)).actionable_asset_ids == ()
    assert summarize((a,)).unresolved_asset_ids == (a.snapshot.asset_id,)


def test_equal_priorities_sort_by_stable_asset_id():
    assets=[item(execution_status='COMPLETED',impact='AFFECTED',risk_level='HIGH',priority='P1',
        gate_status='PASS',verification_status='CONFIRMED',evidence_ids=('E1',)) for _ in range(3)]
    expected=tuple(sorted((x.snapshot.asset_id for x in assets),key=str))
    assert summarize(tuple(assets)).actionable_asset_ids==expected
    assert summarize(tuple(reversed(assets))).actionable_asset_ids==expected


def test_client_cannot_supply_risk_trust_tools_or_implicit_inventory():
    for extra in ({'risk_level':'LOW'},{'allowed_tools':['scan']},{'trust':'CONFIRMED'}):
        with pytest.raises(ValidationError):
            BatchRequest(vulnerability_id='CVE-2099-9999001',asset_ids=[uuid4()],**extra)
    with pytest.raises(ValidationError):
        BatchRequest(vulnerability_id='CVE-2099-9999001',asset_ids=[])


def test_batch_openapi_exposes_four_typed_authenticated_operations():
    from app.main import create_app
    schema=create_app().openapi()
    paths={k:v for k,v in schema['paths'].items() if '/batches' in k}
    assert len(paths)==4
    ops=[v for p in paths.values() for k,v in p.items() if k in ('get','post')]
    assert len(ops)==4 and all(o.get('security') for o in ops)
    assert all(o['responses'][next(c for c in o['responses'] if c.startswith('2'))]['content']['application/json']['schema'].get('$ref') for o in ops)


def test_projection_exception_cannot_advance_an_unconfirmed_running_child():
    from types import SimpleNamespace
    from app.investigation_api.multi_asset_service import MultiAssetService
    service=object.__new__(MultiAssetService);running=item(execution_status='RUNNING',investigation_id=uuid4())
    saved=SimpleNamespace(response=SimpleNamespace(items=[running]))
    def unavailable(*args):raise RuntimeError('SYNTHETIC temporary read failure')
    service._collect=unavailable
    service.repo=SimpleNamespace(read=lambda *a:saved,mutate=lambda id,actor,fn:fn(saved))
    service._bound_child=lambda *args:SimpleNamespace(context=SimpleNamespace(current_stage='PLANNING'))
    cancelled=[];service._cancel_child=lambda *args:cancelled.append(True)
    assert service._collect_guarded(uuid4(),0,'synthetic') is False
    assert running.execution_status=='RUNNING' and running.impact=='UNKNOWN' and cancelled


def test_rehashed_completed_decision_without_child_is_rejected():
    from datetime import datetime,timezone,timedelta
    from types import SimpleNamespace
    from app.agents.contracts import fingerprint
    from app.investigation_api.multi_asset_repository import BatchRepository,normalized_request,TYPE,NS
    from app.investigation_api.multi_asset_schemas import BatchRecord,BatchResponse
    now=datetime.now(timezone.utc);id=uuid4()
    one=item(execution_status='COMPLETED',impact='NOT_AFFECTED',risk_level='LOW',priority='DEFER')
    one.child_request_key=f'batch:{id}:asset:{one.snapshot.asset_id}'
    request=BatchRequest(vulnerability_id='CVE-2099-9999001',asset_ids=(one.snapshot.asset_id,))
    response=BatchResponse(batch_id=id,vulnerability_id=request.vulnerability_id,items=(one,),summary=summarize((one,)),
        execution_status='COMPLETED',created_at=now,updated_at=now,deadline_at=now+timedelta(seconds=900),
        max_assets=5,model_provider='mock',model_name='test',execution_mode='MOCK')
    record=BatchRecord(owner='synthetic',request_key='synthetic',request_hash=fingerprint(normalized_request(request)),
        request=request,response=response)
    data=record.model_dump(mode='json')
    row=SimpleNamespace(id=id,agent_type=TYPE,actor_principal='synthetic',details={NS:{'payload':data,'hash':fingerprint(data)}})
    with pytest.raises(ValueError,match='BATCH_UNBOUND_DECISION_INVALID'):
        BatchRepository(None)._decode(row,'synthetic')


def test_deadline_under_one_second_before_child_creation_does_not_leave_running_intent(monkeypatch):
    from datetime import datetime,timezone,timedelta
    from types import SimpleNamespace
    import app.investigation_api.multi_asset_service as module
    from app.investigation_api.multi_asset_schemas import InventoryComponent
    now=datetime.now(timezone.utc);clock=[now];component_id=uuid4()
    one=item()
    one.snapshot.selected_component_id=component_id
    one.snapshot.components=(InventoryComponent(component_id=component_id,name='SYNTHETIC',
        package_name='synthetic',version='1.0',inventory_revision=1,source='fixture',identity_status='confirmed'),)
    record=SimpleNamespace(request=SimpleNamespace(child_timeout_seconds=2),
        response=SimpleNamespace(items=[one],cancel_requested_at=None,deadline_at=now+timedelta(seconds=2),
            vulnerability_id='CVE-2099-9999001'))
    def mutate(id,actor,fn):
        fn(record)
        # Admission had >=1s, but lock acquisition left <1s before create.
        clock[0]=now+timedelta(seconds=1.1)
        return record
    calls=[]
    service=object.__new__(module.MultiAssetService)
    service.repo=SimpleNamespace(mutate=mutate)
    service.single=SimpleNamespace(create=lambda *a,**kw:calls.append(True))
    service._matches=lambda *a:True
    monkeypatch.setattr(module,'utcnow',lambda:clock[0])
    service._start(uuid4(),0,'synthetic')
    assert not calls
    assert one.execution_status=='NOT_EXECUTED'
    assert one.error_code=='DEADLINE_BEFORE_CHILD_CREATION'


@pytest.mark.parametrize('mode',['input_incompatible','snapshot_read_failure'])
def test_known_precreation_failure_releases_admission_without_orphan(mode):
    from datetime import datetime,timezone,timedelta
    from types import SimpleNamespace
    from app.investigation_api.multi_asset_service import MultiAssetService
    from app.investigation_api.multi_asset_schemas import InventoryComponent
    component_id=uuid4();one=item();one.snapshot.selected_component_id=component_id
    one.child_request_key='SYNTHETIC-precreation-key'
    one.snapshot.components=(InventoryComponent(component_id=component_id,
        name='x'*201 if mode=='input_incompatible' else 'SYNTHETIC',
        package_name='synthetic',version='1.0',inventory_revision=1,source='fixture',identity_status='confirmed'),)
    record=SimpleNamespace(request=SimpleNamespace(child_timeout_seconds=300),
        response=SimpleNamespace(items=[one],cancel_requested_at=None,
            deadline_at=datetime.now(timezone.utc)+timedelta(seconds=900),vulnerability_id='CVE-2099-9999001'))
    def mutate(id,actor,fn):fn(record);return record
    reads=[];calls=[]
    def matches(*args):
        reads.append(True)
        if mode=='snapshot_read_failure' and len(reads)==2:raise RuntimeError('SYNTHETIC snapshot read unavailable')
        return True
    service=object.__new__(MultiAssetService);service.repo=SimpleNamespace(mutate=mutate)
    service.single=SimpleNamespace(create=lambda *a,**kw:calls.append(True));service._matches=matches
    service._start(uuid4(),0,'synthetic')
    assert not calls and one.investigation_id is None
    if mode=='input_incompatible':
        assert one.execution_status=='NEED_CONTEXT' and one.error_code=='CHILD_INPUT_INCOMPATIBLE'
        assert one.missing_fields==('component_input',)
    else:assert one.execution_status=='FAILED' and one.error_code=='CHILD_PREPARATION_FAILED'

from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select, delete
from .test_contracts_plan import task


def store(engine):
    from app.runtime.store import PostgresRuntimeStore
    return PostgresRuntimeStore(engine)


def create(store_, actor='runtime-unit', key=None):
    from app.runtime.contracts import TaskPlan
    return store_.create_run({'question': 'SYNTHETIC runtime'}, TaskPlan(tasks=[task()]),
                             actor, key or str(uuid4()))


@pytest.fixture
def runtime_store(engine):
    # Construct lazily so missing implementation fails in the test, not setup.
    created_ids = set()
    class Deferred:
        def __getattr__(self, name):
            method = getattr(store(engine), name)
            if name != 'create_run':
                return method
            def tracked(*args, **kwargs):
                result = method(*args, **kwargs)
                created_ids.add(result[0].run_id)
                return result
            return tracked
    instance = Deferred()
    yield instance
    # Committed tool history is intentionally append-only. Keep synthetic audit
    # rows in the guarded dedicated test database; never disable its triggers.


def test_stored_run_reloads_and_owner_cannot_cross_boundary(runtime_store):
    snapshot, fresh = create(runtime_store)
    assert fresh and snapshot.status == 'PLANNING'
    got = runtime_store.read_trace(snapshot.run_id, 'runtime-unit')
    assert got.run_id == snapshot.run_id and got.tasks[0].task_id == 'T1'
    with pytest.raises(LookupError):
        runtime_store.read_trace(snapshot.run_id, 'different-owner')


def test_idempotency_is_plan_body_and_actor_scoped(runtime_store):
    from app.runtime.contracts import TaskPlan
    from app.assistant.storage import IdempotencyConflict
    key = str(uuid4())
    a, fresh = create(runtime_store, key=key)
    b, fresh = create(runtime_store, key=key)
    assert not fresh and a.run_id == b.run_id
    c, _ = create(runtime_store, actor='runtime-unit-other', key=key)
    assert c.run_id != a.run_id
    with pytest.raises(IdempotencyConflict):
        runtime_store.create_run({'question': 'changed'}, TaskPlan(tasks=[task()]), 'runtime-unit', key)


def test_old_and_runtime_same_key_do_not_collide(runtime_store, engine):
    from app.assistant.storage import create_run
    from app.assistant.contracts import QueryRequest
    from app.db.session import transaction
    from app.db import models as m
    key = str(uuid4())
    new, _ = create(runtime_store, key=key)
    with transaction(engine) as session:
        old, fresh = create_run(session, QueryRequest(question='old query',request_key=key), 'runtime-unit')
        assert fresh and old.id != new.run_id
        old_id = old.id
    # Dedicated test cleanup of the legacy row this test created.
    with transaction(engine) as session:
        session.execute(delete(m.AgentRun).where(m.AgentRun.id==old_id))


def completed(snapshot, task_id='T1'):
    from app.runtime.contracts import TaskArtifact, TaskTrace, ToolReceipt
    from app.tooling.contracts import ToolEnvelope
    from app.utils.time import utcnow
    now=utcnow()
    artifact=TaskArtifact(run_id=snapshot.run_id, task_id=task_id, status='SUCCESS',
                          result={'outputs':[{'data':{'synthetic':True}}]},start_time=now,end_time=now)
    trace=TaskTrace(run_id=snapshot.run_id,task_id=task_id,task_type='tool_sequence',
                    status='SUCCESS',start_time=now,end_time=now,artifact_id=artifact.artifact_id)
    receipt=ToolReceipt(call_index=1,name='get_vulnerability',arguments={'target':'CVE-2099-9999001'},
                        started_at=now,finished_at=now,envelope=ToolEnvelope(tool='get_vulnerability',
                        trace_id=str(snapshot.trace_id),status='success',data={'synthetic':True},duration_ms=0))
    return artifact,trace,[receipt]


def test_trace_and_artifact_save_survive_new_session_and_legacy_read(runtime_store, engine):
    from app.assistant.service import AssistantService
    from app.runtime.contracts import RunOutcome
    snapshot,_=create(runtime_store)
    artifact,trace,receipts=completed(snapshot)
    runtime_store.save_task(snapshot.run_id,task(),artifact,trace,receipts)
    runtime_store.finish_run(snapshot.run_id,RunOutcome(run_id=snapshot.run_id,artifacts=[artifact],traces=[trace],status='succeeded'))
    new_store=store(engine)
    got=new_store.read_trace(snapshot.run_id,'runtime-unit')
    assert got.artifacts[0].artifact_id == artifact.artifact_id
    assert got.tasks[0].tools_called[0]['sequence_no'] == 1
    old=AssistantService(engine)
    try:
        assert old.read(snapshot.run_id,'runtime-unit')['status']=='COMPLETED'
        tasks=old.tasks(snapshot.run_id,'runtime-unit')['items']
        assert tasks[0]['goal']=='Lookup' and tasks[0]['status']=='SUCCESS'
        calls=old.trace(snapshot.run_id,'runtime-unit')
        assert calls['items'][0]['tool_name']=='get_vulnerability'
        assert calls['events'][-1]['artifact_id']==str(artifact.artifact_id)
    finally:old.close()


def test_concurrent_task_writes_do_not_lose_json_or_duplicate_sequences(runtime_store):
    from app.runtime.contracts import TaskPlan
    tasks=[task(task_id=f't{i}') for i in range(3)]
    snapshot,_=runtime_store.create_run({'question':'parallel'},TaskPlan(tasks=tasks),'runtime-unit',str(uuid4()))
    def write(item):
        artifact,trace,receipts=completed(snapshot,item.task_id)
        runtime_store.save_task(snapshot.run_id,item,artifact,trace,receipts)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(write,tasks))
    got=runtime_store.read_trace(snapshot.run_id,'runtime-unit')
    assert {a.task_id for a in got.artifacts}=={'t0','t1','t2'}
    assert sorted(t.tools_called[0]['sequence_no'] for t in got.tasks)==[1,2,3]


def test_persistence_failure_raises_instead_of_returning_fake_success(monkeypatch, runtime_store):
    snapshot,_=create(runtime_store)
    from app.runtime import store as module
    from contextlib import contextmanager
    @contextmanager
    def broken(engine):
        raise OSError('private_database_password')
        yield
    monkeypatch.setattr(module,'transaction',broken)
    with pytest.raises(module.StoreFailure,match='STORE_FAILED'):
        runtime_store.read_trace(snapshot.run_id,'runtime-unit')


def test_legacy_tasks_read_live_runtime_states_before_run_completion(runtime_store,engine):
    from app.runtime.contracts import TaskPlan,TaskTrace
    from app.assistant.service import AssistantService
    from app.utils.time import utcnow
    tasks=[task(task_id=key) for key in ('active','done','review','failed','blocked')]
    snapshot,_=runtime_store.create_run({'question':'live states'},TaskPlan(tasks=tasks),
                                      'runtime-unit',str(uuid4()))
    states=['RUNNING','SUCCESS','WAITING_REVIEW','FAILED','BLOCKED']
    for item,state in zip(tasks,states):
        trace=TaskTrace(run_id=snapshot.run_id,task_id=item.task_id,task_type='tool_sequence',
            status=state,transitions=[{'from':'READY','state':state,'at':utcnow().isoformat()}])
        runtime_store.save_task(snapshot.run_id,item,None,trace,[])
    old=AssistantService(engine)
    try:
        got=old.tasks(snapshot.run_id,'runtime-unit')['items']
        assert [t['status'] for t in got]==['running','success','partial','failed','blocked']
        authoritative=runtime_store.read_trace(snapshot.run_id,'runtime-unit')
        assert [t.status for t in authoritative.tasks]==states
    finally:old.close()


def test_oversized_evidence_is_durably_retained_in_tool_record(runtime_store,engine):
    from .test_executor import context,execute
    from app.runtime.contracts import TaskTrace,ToolReceipt,RunOutcome
    from app.assistant.service import AssistantService
    snapshot,_=create(runtime_store)
    ctx=context(run_id=snapshot.run_id,trace_id=snapshot.trace_id)
    ref={'raw_document_id':str(uuid4()),'locator':{'excerpt':'x'*600000},'verified':False}
    artifact,events=execute({'status':'success','data':{'found':True},'evidence_refs':[ref]},context_=ctx)
    receipt=ToolReceipt.model_validate(events[1]['receipt'])
    trace=TaskTrace(run_id=snapshot.run_id,task_id='T1',task_type='tool_sequence',status='FAILED',
        start_time=artifact.start_time,end_time=artifact.end_time,artifact_id=artifact.artifact_id)
    runtime_store.save_task(snapshot.run_id,task(),artifact,trace,[receipt])
    runtime_store.finish_run(snapshot.run_id,RunOutcome(run_id=snapshot.run_id,
        artifacts=[artifact],traces=[trace],status='failed'))
    persisted=runtime_store.read_trace(snapshot.run_id,'runtime-unit').artifacts[0]
    assert persisted.result['evidence_count']==1 and persisted.evidence==[]
    assert persisted.warnings and persisted.confidence is None
    old=AssistantService(engine)
    try:
        calls=old.trace(snapshot.run_id,'runtime-unit')['items']
        assert len(calls)==1 and calls[0]['evidence_refs']==[ref]
    finally:old.close()

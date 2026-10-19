"""Opt-in, content-free lifecycle observation. No application decisions change.

The pytest plugin is inactive unless AEGIS_ARTIFACT_DIAGNOSTIC_LOG is set.
It also supports explicit installation in a diagnostic CLI/process.
"""
from contextlib import contextmanager
from datetime import datetime,timezone
from functools import wraps
import hashlib,inspect,json,os,sys,threading
from pathlib import Path
from uuid import UUID
from pydantic import ValidationError

SAFE_REASONS=frozenset({
    'Cleanup not verified','Finite JSON data required','JSON size limit exceeded',
    'Artifact identity mismatch','Artifact evidence is not receipt-backed',
    'Artifact output was changed after tool execution','Unaccepted success artifact',
    'Receipt call budget exceeded','Receipt does not match authorized execution',
    'Result changed after authorized tool execution','Unexpected original Artifact fields',
    'Artifact binding identity mismatch','Task trace identity mismatch',
    'Task artifact identity mismatch','Run already terminal','Task already terminal',
    'Sealed input changed','Formal Artifact output changed','Rule result changed',
    'Evidence references changed','Unauthorized model call','Artifact/trace mismatch',
})
SAFE_FIELDS=frozenset({'artifact_id','run_id','task_id','asset_id','evidence','result','outputs','confidence','errors','warnings','tool_calls','start_time','end_time','status','input_artifact_ids','context_id','risk_level','assessment'})

def uid(value):
    try:return str(UUID(str(value)))
    except (ValueError,TypeError,AttributeError):return None

def stamp():return datetime.now(timezone.utc).isoformat()

def failure_detail(exc):
    reason=str(exc)
    value={'type':type(exc).__name__,'reason':reason if reason in SAFE_REASONS else 'EXCEPTION_MESSAGE_REDACTED'}
    code=getattr(exc,'code',None)
    if code in ('AGENT_ARTIFACT_INVALID','ARTIFACT_SIZE_LIMIT','AGENT_TRACE_INVALID','AGENT_PLAN_INVALID'):value['code']=code
    if isinstance(exc,ValidationError):
        value['schema_violations']=[{'type':e['type'],'loc':[x if isinstance(x,int) or x in SAFE_FIELDS else '<field>' for x in e['loc']]} for e in exc.errors(include_input=False,include_context=False,include_url=False)[:16]]
    return value

def artifact_hash(artifact):
    try:
        # Persistent receipt IDs replace tool_calls, but cannot change the payload.
        keys=('artifact_id','run_id','task_id','status','result','evidence','confidence','unresolved_questions','warnings','errors')
        value={k:getattr(artifact,k) for k in keys}
        for k in ('artifact_id','run_id'):value[k]=str(value[k])
        raw=json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf8')
        return hashlib.sha256(raw).hexdigest()
    except (ValueError,TypeError,AttributeError,UnicodeError):return None


class Observer:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.sequence=0;self.dropped_events=0
        self.links={};self.hashes={};self.trace_ids={}

    def _write(self,record):
        with self.path.open('a',encoding='utf8') as out:out.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n')

    def link(self,context):
        for run in (context.investigation_run_id,context.verification_run_id,context.analysis_run_id):
            if run:
                with self.lock:self.links[str(run)]=(str(context.logical_investigation_id),uid(context.original_request.planner_input.query.asset_id))

    def emit(self,event,*,artifact=None,context=None,run_id=None,trace_id=None,exception=None,**metadata):
        try:
            run=uid(run_id or getattr(context,'run_id',None) or getattr(artifact,'run_id',None))
            trace=uid(trace_id or getattr(context,'trace_id',None))
            art_id=uid(getattr(artifact,'artifact_id',None));content_hash=artifact_hash(artifact) if artifact else None
            root,asset=self.links.get(run,(None,None))
            claims=set();evidence=set()
            refs=getattr(artifact,'evidence',()) if artifact else ()
            assessments=[]
            if artifact:
                if hasattr(artifact,'evidence_refs'):refs=artifact.evidence_refs
                for out in getattr(artifact,'result',{}).get('outputs',[])[:8]:
                    if isinstance(out,dict) and isinstance(out.get('data'),dict):
                        a=out['data'].get('assessment')
                        if isinstance(a,dict):assessments.append(a)
                for a in assessments:
                    asset=uid(a.get('asset_id')) or asset
                    for c in a.get('claim_dispositions',[])[:32]:
                        if uid(c.get('claim_id')):claims.add(uid(c['claim_id']))
                    refs=(*refs,*a.get('evidence_refs',[])[:128])
                for ref in list(refs)[:256]:
                    if isinstance(ref,dict):
                        if uid(ref.get('claim_id')):claims.add(uid(ref['claim_id']))
                        if uid(ref.get('evidence_id')):evidence.add(uid(ref['evidence_id']))
                asset=uid(getattr(artifact,'asset_id',None)) or asset
            with self.lock:
                if trace:self.trace_ids[run]=trace
                if content_hash and art_id:self.hashes[(run,art_id)]=content_hash
                self.sequence+=1
                now=stamp()
                record={'schema':'artifact-diagnostic-v1','sequence':self.sequence,'event':event,'event_at':now,
                    'trace_id':trace or self.trace_ids.get(run),'investigation_id':root,'runtime_run_id':run,'asset_id':asset,
                    'artifact_id':art_id,'artifact_type':'security_analysis_result' if assessments or hasattr(artifact,'risk_level') or getattr(artifact,'schema_version',None)=='risk-analysis-artifact-v1' else 'runtime_task_artifact',
                    'artifact_schema_version':getattr(artifact,'schema_version',None),
                    'claim_ids':sorted(claims),'evidence_ids':sorted(evidence),
                    'created_at':getattr(artifact,'end_time',None).isoformat() if artifact and getattr(artifact,'end_time',None) else None,
                    'created_at_basis':'DECLARED_WORKER_END_TIME_NOT_CONSTRUCTOR_WALL_TIME',
                    'persisted_at':now if event=='PERSISTED' else None,'read_at':now if event=='READ' else None,
                    'validated_at':now if event in ('VALIDATED','VALIDATION_REJECTED') else None,'publish_at':now if event=='PUBLISHED' else None,
                    'artifact_content_hash':content_hash or self.hashes.get((run,art_id)),
                    'hash_scope':'TaskArtifact_payload_excluding_persistence_receipt_refs',
                    'query_key':None,'transaction_boundary':'NOT_A_DATABASE_EVENT','validation_result':None,
                    'exact_validation_failure':failure_detail(exception) if exception else None,'observer_process_id':os.getpid()}
                allowed=('query_key','transaction_boundary','validation_result','cleanup_verified','rejected_artifact_id','source_file','source_line','instruction_offset','validator','gate_status','reused','observer_process_id')
                record.update({k:v for k,v in metadata.items() if k in allowed})
                self._write(record)
        except Exception:
            with self.lock:self.dropped_events+=1


@contextmanager
def installed(observer):
    import app.agents.executor as executor
    import app.runtime.executor as runtime_executor
    import app.agents.artifacts as artifacts
    from app.runtime.process import ProcessSupervisor
    from app.runtime.store import PostgresRuntimeStore
    from app.agents.analysis.reader import AnalysisReader
    from app.orchestration.store import PostgresInvestigationStore
    patched=[];monitor_id=None
    def patch(owner,name,factory):
        original=getattr(owner,name);wrapped=factory(original);setattr(owner,name,wrapped);patched.append((owner,name,original))
    def observe_call(original):
        @wraps(original)
        def wrapper(self,task,context,dependencies,**kwargs):
            value=original(self,task,context,dependencies,**kwargs)
            observer.emit('WORKER_RECEIVED' if isinstance(self,ProcessSupervisor) else 'VALIDATED' if value.artifact.status!='FAILED' else 'VALIDATION_REJECTED',artifact=value.artifact,context=context,
                cleanup_verified=value.cleanup_verified,validation_result=str(value.artifact.status),
                rejected_artifact_id=observer.__dict__.get('_rejected',{}).get((str(context.run_id),task.task_id)))
            return value
        return wrapper
    patch(ProcessSupervisor,'execute',observe_call);patch(executor.AgentExecutor,'execute',observe_call)
    def monitor(code,offset,exc):
        if code not in watched:return
        try:
            frame=sys._getframe(1);candidate=frame
            for _ in range(10):
                if candidate is None:break
                if candidate.f_code is executor_code:break
                candidate=candidate.f_back
            values=candidate.f_locals if candidate and candidate.f_code is executor_code else frame.f_locals
            outcome=values.get('outcome');art=getattr(outcome,'artifact',None)
            ctx=values.get('context')
            if art and ctx:
                with observer.lock:
                    observer.__dict__.setdefault('_rejected',{})[(str(ctx.run_id),art.task_id)]=str(art.artifact_id)
                observer.emit('EXACT_VALIDATION_EXCEPTION',artifact=art,context=ctx,exception=exc,
                    validator=code.co_name,source_file='/'.join(code.co_filename.replace('\\','/').split('/')[-4:]),
                    source_line=frame.f_lineno,instruction_offset=offset,cleanup_verified=getattr(outcome,'cleanup_verified',None),validation_result='REJECTED')
        except Exception:
            with observer.lock:observer.dropped_events+=1
    executor_code=inspect.unwrap(executor.AgentExecutor.execute).__code__
    watched={executor_code,*[getattr(runtime_executor,name).__code__ for name in ('validate_outcome','validate_receipts')],
        *[inspect.unwrap(getattr(artifacts,name)).__code__ for name in ('validate_artifact_json','validate_persisted_extension')]}
    def create(original):
        @wraps(original)
        def wrapper(self,request_data,plan,actor,request_key):
            result=original(self,request_data,plan,actor,request_key);snapshot,fresh=result
            observer.emit('RUN_COMMITTED',run_id=snapshot.run_id,trace_id=snapshot.trace_id,
                query_key=hashlib.sha256(json.dumps([actor,request_key]).encode()).hexdigest(),transaction_boundary='AFTER_COMMIT',reused=not fresh)
            return result
        return wrapper
    def save(original):
        @wraps(original)
        def wrapper(self,run_id,task,artifact,trace,receipts):
            observer.emit('PERSIST_STARTED',artifact=artifact,run_id=run_id,transaction_boundary='BEFORE_TRANSACTION')
            try:result=original(self,run_id,task,artifact,trace,receipts)
            except Exception as exc:
                observer.emit('PERSIST_FAILED',artifact=artifact,run_id=run_id,exception=exc,transaction_boundary='ROLLED_BACK_OR_OUTCOME_UNKNOWN');raise
            if artifact:observer.emit('PERSISTED',artifact=artifact,run_id=run_id,transaction_boundary='AFTER_COMMIT')
            return result
        return wrapper
    def read_trace(original):
        @wraps(original)
        def wrapper(self,*args,**kwargs):
            result=original(self,*args,**kwargs)
            for artifact in result.artifacts:observer.emit('READ',artifact=artifact,run_id=result.run_id,trace_id=result.trace_id,transaction_boundary='READ_TRANSACTION_CLOSED')
            return result
        return wrapper
    def analysis_read(original):
        @wraps(original)
        def wrapper(self,*args,**kwargs):
            try:result=original(self,*args,**kwargs)
            except Exception as exc:
                observer.emit('READ_REJECTED',run_id=args[0] if args else kwargs.get('run_id'),exception=exc,validation_result='REJECTED');raise
            for artifact in result.artifacts:observer.emit('READ',artifact=artifact,transaction_boundary='READ_TRANSACTION_CLOSED',validation_result='ACCEPTED')
            return result
        return wrapper
    def linked(original,publish=False):
        @wraps(original)
        def wrapper(self,*args,**kwargs):
            value=original(self,*args,**kwargs);context=getattr(value,'context',value)
            if hasattr(context,'logical_investigation_id'):
                observer.link(context)
                if publish:
                    for ref in context.artifact_references:
                        if ref.schema_version=='risk-analysis-artifact-v1':
                            proxy=type('ArtifactIdentity',(),{'run_id':ref.run_id,'artifact_id':ref.artifact_id,'schema_version':ref.schema_version})()
                            observer.emit('PUBLISHED',artifact=proxy,transaction_boundary='AFTER_ANSWER_COMMIT',validation_result=context.overall_status)
            return value
        return wrapper
    try:
        patch(PostgresRuntimeStore,'create_run',create);patch(PostgresRuntimeStore,'save_task',save);patch(PostgresRuntimeStore,'read_trace',read_trace)
        patch(AnalysisReader,'read',analysis_read)
        for name in ('claim','read','advance'):patch(PostgresInvestigationStore,name,linked)
        patch(PostgresInvestigationStore,'seal',lambda original:linked(original,publish=True))
        if not hasattr(sys,'monitoring'):raise RuntimeError('Python 3.12 monitoring required for exact validation capture')
        monitor_id=next((i for i in (3,4,5) if sys.monitoring.get_tool(i) is None),None)
        if monitor_id is None:raise RuntimeError('No free diagnostic monitoring slot')
        sys.monitoring.use_tool_id(monitor_id,'artifact-diagnostics')
        sys.monitoring.register_callback(monitor_id,sys.monitoring.events.RAISE,monitor)
        sys.monitoring.set_events(monitor_id,sys.monitoring.events.RAISE)
        yield observer
    finally:
        if monitor_id is not None:
            sys.monitoring.set_events(monitor_id,0);sys.monitoring.register_callback(monitor_id,sys.monitoring.events.RAISE,None);sys.monitoring.free_tool_id(monitor_id)
        for owner,name,original in reversed(patched):setattr(owner,name,original)


def pytest_configure(config):
    target=os.environ.get('AEGIS_ARTIFACT_DIAGNOSTIC_LOG')
    if target:
        observer=Observer(target);scope=installed(observer);scope.__enter__()
        config._artifact_diagnostic_scope=scope;config._artifact_diagnostic_observer=observer

def pytest_unconfigure(config):
    scope=getattr(config,'_artifact_diagnostic_scope',None)
    if scope:scope.__exit__(None,None,None)

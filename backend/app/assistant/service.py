import os,time,threading
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.db.session import transaction
from app.db import models as m
from app.assistant import storage
from app.assistant.orchestrator import Orchestrator
from app.tooling.gateway import ToolContext
from app.utils.time import utcnow

class AssistantBusy(RuntimeError):pass

class AssistantService:
    def __init__(self,engine):
        self.engine=engine;self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='aegis-assistant');self.capacity=threading.BoundedSemaphore(8)
    def start(self,request,actor):
        if request.realtime and os.environ.get('AEGIS_ALLOW_REALTIME')!='1':raise PermissionError('Realtime network tools are disabled by server policy')
        if not self.capacity.acquire(blocking=False):raise AssistantBusy('Assistant queue is full')
        try:
            with transaction(self.engine) as session:
                row,new=storage.create_run(session,request,actor);value=jsonable_encoder(storage.summary(row));run_id=str(row.id)
            if new:self.pool.submit(self._execute,run_id,request,actor)
            else:self.capacity.release()
            return value
        except Exception:self.capacity.release();raise
    def read(self,id,actor):
        with transaction(self.engine) as session:return jsonable_encoder(storage.summary(storage.owned_run(session,id,actor)))
    def tasks(self,id,actor):
        with transaction(self.engine) as session:
            row=storage.owned_run(session,id,actor);result=row.details.get('result') or {}
            plan={t['task_id']:t for t in row.details.get('plan',[])}
            done={a['task_id']:a for a in result.get('artifacts',[])}
            live={e['task_id']:e['state'] for e in row.details.get('events',[]) if e.get('task_id') in plan and e.get('state') in ('started','success','partial','failed','blocked')}
            return {'items':[{**t,**done.get(key,{}),'status':done.get(key,{}).get('status',
                'running' if live.get(key)=='started' else live.get(key,'pending')),'goal':t['goal']} for key,t in plan.items()]}
    def trace(self,id,actor):
        with transaction(self.engine) as session:
            row=storage.owned_run(session,id,actor)
            calls=session.scalars(select(m.ToolCallRecord).where(m.ToolCallRecord.agent_run_id==row.id).order_by(m.ToolCallRecord.sequence_no,m.ToolCallRecord.attempt))
            return jsonable_encoder({'run_id':str(row.id),'trace_id':row.details['trace_id'],'items':[{'id':r.id,'tool_name':r.tool_name,'status':r.status,'sequence_no':r.sequence_no,'attempt':r.attempt,
                'started_at':r.started_at,'finished_at':r.finished_at,'duration_ms':r.duration_ms,'input_summary':r.input_summary,
                'output_summary':r.output_summary,'errors':r.output_summary.get('errors',[]),'evidence_refs':r.output_summary.get('evidence_refs',[])} for r in calls],
                'events':row.details.get('events',[]),'disclosure':'Execution summaries only; no hidden model reasoning'})
    def _execute(self,run_id,request,actor):
        started=time.monotonic();sequence=0;guard=threading.Lock()
        def update(**changes):
            with transaction(self.engine) as session:
                row=session.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(run_id)).with_for_update())
                if row.finished_at is not None:return
                details=dict(row.details)
                if changes.get('status'):details['ui_status']=changes['status']
                if 'plan' in changes:details['plan']=changes['plan']
                if 'route' in changes:details['route']=changes['route']
                if 'event' in changes:details['events']=[*details.get('events',[]),{**changes['event'],'at':utcnow().isoformat()}][-100:]
                row.details=jsonable_encoder(details);row.status='running'
        def audit(name,args,result,unused,attempt):
            nonlocal sequence
            with guard:sequence+=1;seq=sequence
            with transaction(self.engine) as session:storage.record_tool(session,run_id,seq,name,args,result,attempt)
        with transaction(self.engine) as session:trace=storage.owned_run(session,run_id,actor).details['trace_id']
        permissions={'READ_ONLY','WRITE','REVIEW_ACTION'}
        if request.realtime:permissions.add('EXTERNAL_NETWORK')
        context=ToolContext(actor=actor,permissions=frozenset(permissions),run_id=run_id,trace_id=trace,audit=audit,
            database_url=self.engine.url.render_as_string(hide_password=False))
        try:
            result=Orchestrator(context,on_stage=update).run(request)
            gate=result['gate']['status'];ui='WAITING_REVIEW' if gate=='HUMAN_REVIEW_REQUIRED' else 'COMPLETED' if gate in ('PASS','PASS_WITH_WARNINGS') else 'FAILED'
            with transaction(self.engine) as session:
                result['human_reviews']=storage.review_links(session,result,actor)
                row=storage.owned_run(session,run_id,actor);row.details=jsonable_encoder({**row.details,'ui_status':ui,'result':result,'plan':result['plan'],'route':result['route']})
                row.status='succeeded' if gate=='PASS' else 'partial' if ui in ('COMPLETED','WAITING_REVIEW') else 'failed'
                row.finished_at=utcnow();row.duration_ms=int((time.monotonic()-started)*1000);row.result_summary=result['answer']
                storage.persist_citations(session,run_id,result['evidence_refs'])
        except Exception:
            with transaction(self.engine) as session:
                row=storage.owned_run(session,run_id,actor);row.status='failed';row.finished_at=utcnow();row.duration_ms=int((time.monotonic()-started)*1000)
                row.error_summary='Controlled orchestration failure';row.details={**row.details,'ui_status':'FAILED','result':{'answer':'运行失败，未生成事实结论。','warnings':['Controlled orchestration failure'],'evidence_refs':[]}}
        finally:self.capacity.release()
    def close(self):self.pool.shutdown(wait=True,cancel_futures=False)

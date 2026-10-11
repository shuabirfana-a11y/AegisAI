from uuid import uuid4,UUID
from datetime import timedelta
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.db import models as m
from app.enrichment.repository import lock,digest
from app.utils.time import utcnow

class IdempotencyConflict(ValueError):pass

def create_run(session,request,actor,*,agent_type='deterministic-orchestrator-v1'):
    data=request.model_dump(mode='json');fingerprint=digest(data)
    lock(session,'assistant:'+actor+':'+request.request_key)
    old=session.scalar(select(m.AgentRun).where(m.AgentRun.actor_principal==actor,m.AgentRun.context['request_key'].astext==request.request_key))
    if old:
        if old.context['request_hash']!=fingerprint:raise IdempotencyConflict('Request key was already used with different content')
        return old,False
    run=m.AgentRun(actor_principal=actor,user_request=request.question,agent_type=agent_type,status='queued',started_at=utcnow(),
        context={**data,'request_hash':fingerprint},details={'trace_id':str(uuid4()),'ui_status':'PLANNING','plan':[],'events':[],'result':None})
    session.add(run);session.flush();return run,True

def owned_run(session,id,actor):
    row=session.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(str(id)),m.AgentRun.actor_principal==actor))
    if row is None:raise LookupError('Run not found')
    return row

def summary(row):
    d=row.details
    return {'run_id':str(row.id),'trace_id':d['trace_id'],'status':d['ui_status'],'route':d.get('route'),
        'result':d.get('result'),'warnings':d.get('result',{}).get('warnings',[]) if d.get('result') else [],
        'started_at':row.started_at,'finished_at':row.finished_at,'duration_ms':row.duration_ms}

def record_tool(session,run_id,sequence,name,args,envelope,attempt):
    now=utcnow();status={'success':'succeeded','no_result':'succeeded','partial':'partial','failed':'failed'}[envelope.status]
    if any(e.get('code')=='TOOL_TIMEOUT' for e in envelope.errors):status='timeout'
    row=m.ToolCallRecord(agent_run_id=UUID(str(run_id)),sequence_no=sequence,attempt=attempt,tool_name=name,
        input_summary=jsonable_encoder(args),output_summary=envelope.model_dump(mode='json'),started_at=now-timedelta(milliseconds=envelope.duration_ms),
        finished_at=now,duration_ms=envelope.duration_ms,status=status,error_summary=','.join(e.get('code','UNKNOWN') for e in envelope.errors) or None)
    session.add(row);session.flush();return row

def persist_citations(session,run_id,refs):
    from app.tooling.provenance import current_support_ids
    index=1;seen=set()
    for ref in refs:
        if not ref.get('evidence_id') or not ref.get('claim_id') or not ref.get('verified') or ref['evidence_id'] in seen:continue
        result=session.scalar(select(m.VerificationResult.id).where(m.VerificationResult.claim_id==UUID(ref['claim_id']),m.VerificationResult.claim_revision==ref.get('claim_revision')))
        evidence=session.get(m.Evidence,UUID(ref['evidence_id']))
        claim=session.get(m.Claim,UUID(ref['claim_id']))
        if result is None or evidence is None or claim is None or str(evidence.claim_id)!=ref['claim_id'] or claim.revision!=ref.get('claim_revision'):continue
        if ref['evidence_id'] not in current_support_ids(session,claim):continue
        session.add(m.AgentCitation(agent_run_id=UUID(str(run_id)),evidence_id=evidence.id,claim_id=evidence.claim_id,
            citation_index=index,claim_revision=ref['claim_revision'],assertion_summary='Existing scoped verification; inspect exact evidence and claim revision'))
        seen.add(ref['evidence_id']);index+=1

def review_links(session,result,actor):
    if result.get('gate',{}).get('status')!='HUMAN_REVIEW_REQUIRED':return []
    ids={UUID(c['id']) for a in result.get('artifacts',[]) for c in a.get('claims',[]) if c.get('id')}
    ids.update(UUID(id) for r in result.get('asset_candidates',[]) for id in r.get('claim_ids',[]))
    if not ids:return []
    links=[]
    for row in session.scalars(select(m.ReviewTask).where(m.ReviewTask.claim_id.in_(ids),m.ReviewTask.status.in_(['open','assigned','deferred'])).order_by(m.ReviewTask.created_at,m.ReviewTask.id).limit(100)):
        if row.review_type=='ASSET_MATCH_REVIEW' and row.details.get('owner_principal')!=actor:continue
        links.append({'id':str(row.id),'claim_id':str(row.claim_id),'review_type':row.review_type,'status':row.status,'reason':row.reason})
    return links

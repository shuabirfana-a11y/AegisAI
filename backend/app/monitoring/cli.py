"""Operator CLI; cycles use source due times, optional existing enrichment/HTTP flows."""
import argparse,json,os,time,math
import httpx
from urllib.parse import urlsplit
from app.db.session import make_engine
from app.monitoring.service import MonitoringService,SOURCES,queue_enrichment

def main(argv=None):
    p=argparse.ArgumentParser(description='Bounded AegisAI monitoring; original agents and Gate unchanged')
    p.add_argument('--source',choices=SOURCES,action='append');p.add_argument('--all',action='store_true')
    p.add_argument('--limit',type=int,default=10);p.add_argument('--cycles',type=int,default=1);p.add_argument('--interval',type=float,default=300)
    p.add_argument('--force',action='store_true',help='Ignore source due time for one operator-requested refresh')
    p.add_argument('--pipeline',action='store_true',help='Opt in to batch-scoped automatic enrichment and bounded inventory updates')
    p.add_argument('--cycle-seconds',type=float,default=300,help='Pipeline start-next-work deadline; a current HTTP/domain operation finishes under its original bounds')
    p.add_argument('--allow-cve-bootstrap',action='store_true',help='Explicitly permit the original filtered CVE Git baseline acquisition')
    p.add_argument('--process-enrichment',type=int,default=None,help='Root job budget: legacy default 0, automatic pipeline default 6; explicit 0 queues without executing')
    p.add_argument('--investigate',help='Submit one explicit CVE question to the existing HTTP Orchestrator after collection')
    p.add_argument('--api-base-url',default='http://127.0.0.1:8000')
    a=p.parse_args(argv)
    if a.process_enrichment is None:a.process_enrichment=6 if a.pipeline else 0
    if bool(a.source)==bool(a.all):p.error('Choose --source (repeatable) or --all')
    if not 1<=a.limit<=100 or not 1<=a.cycles<=10000 or not 0<=a.process_enrichment<=20 or not math.isfinite(a.interval) or a.interval<3:p.error('Invalid bounded monitoring budget')
    if a.pipeline and (a.interval>86400 or not math.isfinite(a.cycle_seconds) or not 1<=a.cycle_seconds<=3600):p.error('Invalid automatic pipeline budget')
    if a.investigate:
        import re
        if not re.fullmatch(r'CVE-\d{4}-\d{4,}',a.investigate):p.error('Investigation requires an exact supplied CVE')
        u=urlsplit(a.api_base_url)
        if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.query or u.fragment or u.path.strip('/'):
            p.error('Credential-free HTTP API origin required')
        if u.scheme=='http' and u.hostname not in ('localhost','127.0.0.1','::1'):p.error('Remote API requires HTTPS')
        if not os.environ.get('AEGIS_ASSET_TOKEN'):p.error('Configure local AEGIS_ASSET_TOKEN; do not put it in argv')
    engine=make_engine();service=MonitoringService(engine)
    try:
        if a.pipeline:
            from app.monitoring.automation_cli import run_automation
            if not run_automation(engine,service,a):return
        for i in range(0 if a.pipeline else a.cycles):
            results=service.run_once(a.source if not a.all else None,limit=a.limit,force=a.force)
            jobs=queue_enrichment(service.factory,results)
            processed=[]
            if a.process_enrichment:
                from sqlalchemy import select
                from app.db import models as m
                from app.enrichment.service import EnrichmentService
                with service.factory() as s:
                    selected=[(x.id,x.vulnerability_id,x.enrichment_type) for x in s.scalars(select(m.EnrichmentJob).where(m.EnrichmentJob.status=='queued').order_by(m.EnrichmentJob.scheduled_at,m.EnrichmentJob.id).limit(a.process_enrichment))]
                worker=EnrichmentService(service.factory)
                try:
                    for job,target,kind in selected:
                        processed.extend(x.model_dump(mode='json') for x in worker.run(target,kind,job_id=job))
                finally:worker.http.close()
            print(json.dumps({'execution_mode':'LIVE_PUBLIC_SOURCE_COLLECTION','cycle':i+1,'sources':results,'queued_enrichment':jobs,'processed_enrichment':processed,'global_complete':False},ensure_ascii=False,default=str),flush=True)
            if i+1<a.cycles:time.sleep(a.interval)
        if a.investigate:
            from uuid import uuid4
            with httpx.Client(base_url=a.api_base_url,trust_env=False,follow_redirects=False,timeout=15) as c:
                response=c.post('/api/investigations',headers={'Authorization':'Bearer '+os.environ['AEGIS_ASSET_TOKEN']},
                    json={'user_query':'查询 '+a.investigate+' 的已采集情报和证据来源','asset_scope':{'target':a.investigate},
                        'options':{'objective_profile':'overview_v1'},'idempotency_key':'monitor-'+uuid4().hex})
                response.raise_for_status();print(json.dumps({'existing_orchestrator_http_request':response.json(),'caller':'monitoring-operator','no_model_sdk_call':True},ensure_ascii=False),flush=True)
    finally:service.close();engine.dispose()

if __name__=='__main__':main()

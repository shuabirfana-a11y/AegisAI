"""Opt-in local worker; no service installation or implicit model fan-out."""
import json,os
from threading import Event
from app.monitoring.pipeline import IntelligencePipeline,PipelineConfig
from app.monitoring.scheduler import MonitoringScheduler
from app.monitoring.service import SOURCES

def run_automation(engine,service,args):
    config=PipelineConfig(record_limit=args.limit,job_budget=args.process_enrichment,
        cycle_seconds=args.cycle_seconds,allow_cve_bootstrap=args.allow_cve_bootstrap)
    pipeline=IntelligencePipeline(engine,config,monitor=service,asset_owner=os.environ.get('AEGIS_ASSET_OWNER'))
    stop=Event()
    try:
        for receipt in MonitoringScheduler(pipeline,interval=args.interval).run(args.source or SOURCES,
            cycles=args.cycles,force_first=args.force,stop=stop):
            print(json.dumps(receipt.model_dump(mode='json'),ensure_ascii=False),flush=True)
            if receipt.status=='CANCELLED':return False
        return True
    except KeyboardInterrupt:
        stop.set()
        print(json.dumps({'execution_mode':'LIVE','worker_status':'CANCELLED','reason':'OPERATOR_INTERRUPT'}),flush=True)
        return False
    finally:pipeline.worker.http.close()

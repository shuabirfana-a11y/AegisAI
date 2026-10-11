import json,logging

logger=logging.getLogger('aegis.ingestion')

def event(name,*,source=None,sync_run_id=None,external_id=None,duration=None,status=None,error_type=None,**values):
    # Only caller-selected non-secret fields; never arbitrary exception messages/headers/URLs.
    data={'event':name,'source':source,'sync_run_id':str(sync_run_id) if sync_run_id else None,
          'external_id':external_id,'duration_ms':duration,'status':status,'error_type':error_type,**values}
    logger.info(json.dumps(data,ensure_ascii=True,default=str))

def configure_logging():
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

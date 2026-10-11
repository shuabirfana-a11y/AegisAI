import argparse,json
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.http import HttpClient
from app.core.logging import configure_logging
from app.db.session import make_engine
from app.db import models as m
from app.collectors.cve import CVECollector
from app.collectors.osv import OSVCollector
from app.collectors.cisa_kev import KEVCollector
from app.services.sync import SyncService
from app.repositories.ingestion import persist_record
from app.normalizers import cve,osv,cisa_kev
from app.utils.time import utcnow

def main():
    parser=argparse.ArgumentParser(description='AegisAI bounded real-source ingestion')
    actions=parser.add_subparsers(dest='command',required=True)
    sync=actions.add_parser('sync');sync.add_argument('--source',choices=['CVE_LIST','OSV','CISA_KEV']);sync.add_argument('--all',action='store_true')
    sync.add_argument('--limit',type=int,default=10);sync.add_argument('--recheck',action='store_true',help='Refetch the last bounded records; preserve existing backlog')
    replay=actions.add_parser('replay');replay.add_argument('--raw-id',required=True)
    args=parser.parse_args();configure_logging();settings=Settings.from_env();engine=make_engine(settings.database_url)
    http=HttpClient(settings)
    try:
        if args.command=='replay':
            with Session(engine) as session:
                with session.begin():
                    raw=session.get(m.RawDocument,UUID(args.raw_id))
                    if not raw:raise ValueError('Raw revision not found')
                    source=session.get(m.Source,raw.source_id)
                    if source.source_key=='CISA_KEV' or raw.external_id.startswith('PyPI/modified_id.csv'):raise ValueError('Catalog/index replay requires scoped source sync; single-record replay supports CVE/OSV')
                    normalizer={'CVE_LIST':cve.normalize,'OSV':osv.normalize}[source.source_key]
                    result=persist_record(session,source,raw,normalizer(json.loads(raw.raw_payload),raw.id,raw.retrieved_at))
                    print(json.dumps({'kind':'OFFLINE RAW REPLAY; NO NETWORK','result':result},default=str))
            return
        if bool(args.source)==bool(args.all):parser.error('Specify exactly one of --source or --all')
        def cache_lookup(id):
            with Session(engine) as session:
                raw=session.get(m.RawDocument,UUID(id));
                if raw:session.expunge(raw)
                return raw
        factories={'CVE_LIST':lambda:CVECollector(settings,http),'OSV':lambda:OSVCollector(http),'CISA_KEV':lambda:KEVCollector(http,cache_lookup)}
        results=[]
        for key in factories if args.all else [args.source]:
            results.append(SyncService(engine).sync(factories[key](),args.limit,recheck=args.recheck))
        print(json.dumps({'kind':'REAL PUBLIC SOURCE SYNC','results':results},ensure_ascii=True))
        if any(r['status']=='failed' for r in results):raise SystemExit(1)
    finally:http.close();engine.dispose()

if __name__=='__main__':main()

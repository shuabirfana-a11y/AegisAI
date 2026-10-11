"""Local administrator CLI. It never uploads inventory or contacts model providers."""
import sys,argparse,json
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db.session import make_engine,transaction
from app.assets.events import dispatch_events,run_due
from app.assets.risk import RiskService

parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
dispatch=sub.add_parser('dispatch');dispatch.add_argument('--limit',type=int,default=50)
due=sub.add_parser('due');due.add_argument('--limit',type=int,default=20)
compute=sub.add_parser('recompute');compute.add_argument('--asset',type=UUID,required=True)
args=parser.parse_args();engine=make_engine()
try:
    if args.command=='dispatch':
        with transaction(engine) as session:result=[str(j.id) for j in dispatch_events(session,args.limit)]
    elif args.command=='due':result=run_due(engine,args.limit)
    else:
        with transaction(engine) as session:result=RiskService.recompute(session,args.asset)
    print(json.dumps(result,default=str))
finally:engine.dispose()

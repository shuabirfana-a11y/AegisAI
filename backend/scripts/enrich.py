"""Bounded local CLI. Emits structured job results; never prints credentials."""
import sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.db import models as m
from app.db.session import make_engine,transaction
from app.enrichment.service import EnrichmentService
from app.enrichment.scheduler import schedule_due,KINDS
from app.repositories.queries import latest_assessments

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['investigate','schedule','due']);p.add_argument('--target');p.add_argument('--kind',choices=['all',*KINDS],default='all');p.add_argument('--limit',type=int,default=3)
    args=p.parse_args()
    if not 1<=args.limit<=20:p.error('limit must be 1..20')
    engine=make_engine();factory=lambda:transaction(engine);service=EnrichmentService(factory)
    try:
        if args.command=='investigate':
            if not args.target:p.error('--target required')
            for result in service.run(args.target,args.kind):print(result.model_dump_json())
        elif args.command=='schedule':
            with factory() as s:
                from app.enrichment.queries import target_id
                if args.target:targets=[target_id(s,args.target)]
                else:
                    ranked=latest_assessments();targets=list(s.scalars(select(ranked.c.vulnerability_id).where(ranked.c.rn==1,ranked.c.result=='relevant').distinct().limit(args.limit)))
                if None in targets:raise ValueError('Target not found')
                jobs=schedule_due(s,targets,limit=args.limit)
                print(json.dumps({'scheduled':len(jobs),'job_ids':[str(j.id) for j in jobs]}))
        else:
            with factory() as s:jobs=[(j.id,j.vulnerability_id,j.enrichment_type) for j in s.scalars(select(m.EnrichmentJob).where(m.EnrichmentJob.status=='queued').order_by(m.EnrichmentJob.scheduled_at).limit(args.limit))]
            for id,target,kind in jobs:
                for result in service.run(target,kind,job_id=id):print(result.model_dump_json())
    finally:engine.dispose()

if __name__=='__main__':main()

"""Only the parent gateway starts this fixed worker. External text is never code."""
import json,sys,contextlib
from fastapi.encoders import jsonable_encoder
from app.db.session import make_engine,transaction
from app.tooling.adapters import execute_local

def main():
    request=json.loads(sys.stdin.buffer.read(200_000));name=request['tool'];args=request['args'];engine=make_engine()
    try:
        if args.get('refresh'):
            from app.enrichment.service import EnrichmentService
            kind={'find_vendor_advisories':'vendor','find_poc_candidates':'poc','find_patch_candidates':'patch','get_epss':'epss','get_known_exploitation':'kev','investigate_vulnerability':'all'}[name]
            with contextlib.redirect_stdout(sys.stderr):
                results=EnrichmentService(lambda:transaction(engine)).run(args['target'],kind)
            failures=[r for r in results if r.status.value=='FAILED']
            refresh_warnings=['A bounded live refresh contained failures'] if failures else []
            args={**args,'refresh':False}
        else:failures=[];refresh_warnings=[]
        with transaction(engine) as session:result=execute_local(session,name,args,request['actor'])
        if failures:
            result.update(status='partial',retryable=any(r.retryable for r in failures),errors=[{'code':'REFRESH_FAILED','message':'Existing enrichment reported a refresh failure'}])
        result.setdefault('warnings',[]).extend(refresh_warnings)
    except LookupError:result={'status':'failed','errors':[{'code':'NOT_FOUND','message':'Requested record unavailable'}]}
    except ValueError:result={'status':'failed','errors':[{'code':'INVALID_STATE','message':'Tool could not process supplied state'}]}
    except Exception:result={'status':'failed','errors':[{'code':'TOOL_FAILURE','message':'Tool worker failed; no internal details exposed'}]}
    finally:engine.dispose()
    # Worker stdout is a JSON protocol. ASCII escaping keeps it independent of
    # Windows console code pages while preserving Unicode after JSON decoding.
    sys.stdout.write(json.dumps(jsonable_encoder(result),ensure_ascii=True))

if __name__=='__main__':main()

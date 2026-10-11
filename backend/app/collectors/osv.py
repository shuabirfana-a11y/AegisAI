from datetime import timedelta
from pathlib import Path
import csv,io,json,re
from urllib.parse import quote
from app.collectors.base import BaseCollector,CollectionBatch,RawEnvelope
from app.normalizers import osv
from app.utils.time import parse_time,utcnow

INDEX='https://storage.googleapis.com/osv-vulnerabilities/PyPI/modified_id.csv'

def select_changes(index,checkpoint):
    threshold=parse_time(checkpoint.get('watermark')) if checkpoint else None
    if threshold: threshold-=timedelta(hours=24)
    rows=[]
    for row in csv.reader(io.StringIO(index.decode('utf-8'))):
        if len(row)!=2: raise ValueError('Invalid OSV modified index row')
        modified,id=row
        timestamp=parse_time(modified)
        if not re.fullmatch(r'[A-Za-z0-9_.-]+',id): raise ValueError('Invalid OSV index identity')
        if threshold and timestamp<threshold: break
        rows.append({'id':id,'modified':modified})
    return rows

class OSVCollector(BaseCollector):
    source_key='OSV'
    normalize=staticmethod(osv.normalize)
    def __init__(self,http,bootstrap_ids=None):
        self.http=http
        self.bootstrap=bootstrap_ids if bootstrap_ids is not None else json.loads((Path(__file__).resolve().parents[1]/'resources/bootstrap_ids.json').read_text())['osv']

    def finalize_checkpoint(self,before,candidate,pending,failed):
        result=super().finalize_checkpoint(before,candidate,pending,failed)
        result.update({key:candidate[key] for key in ['baseline_bound','last_processed_ids','index_raw_id']})
        return result

    def collect(self,checkpoint,limit,persist_raw):
        checkpoint=checkpoint or {}; response=self.http.get(INDEX,line_limit=1000)
        prefix=bool(response.extensions.get('aegis_truncated'))
        envelope=RawEnvelope('PyPI/modified_id.csv:prefix1000',INDEX,response.content,content_type='text/csv',metadata={
            'kind':'discovery_index_prefix','etag':response.headers.get('etag'),'completeness':'partial' if prefix else 'complete',
            'prefix_lines':1000,'original_content_length':response.extensions.get('aegis_original_content_length')})
        index_raw=persist_raw(envelope)
        baseline=not checkpoint or limit>checkpoint.get('baseline_bound',0)
        rows=select_changes(response.content,{} if baseline else checkpoint)
        newest=rows[0]['modified'] if rows else checkpoint.get('watermark')
        # A prefix can acknowledge an incremental window only if its tail crosses the old overlap boundary.
        tail=list(csv.reader(io.StringIO(response.content.decode('utf-8'))))
        threshold=parse_time(checkpoint.get('watermark')) if checkpoint.get('watermark') else None
        window_complete=not prefix or bool(threshold and tail and parse_time(tail[-1][0])<threshold-timedelta(hours=24))
        safe_watermark=newest if window_complete else checkpoint.get('watermark')
        discovered=checkpoint.get('candidate_checkpoint') or {}
        resuming_same_index=bool(checkpoint.get('pending') and discovered.get('index_raw_id')==str(index_raw.id))
        if baseline:
            ids=list(dict.fromkeys([*self.bootstrap,*[x['id'] for x in rows]]))[:limit]
            pending=list(dict.fromkeys(checkpoint.get('pending',[])+ids))
        elif resuming_same_index:
            # This exact immutable index was already discovered. Drain its remaining work
            # without adding successful IDs again while the processing watermark is held.
            pending=list(checkpoint['pending'])
        else:
            pending=list(dict.fromkeys(checkpoint.get('pending',[])+[x['id'] for x in rows]))
        if checkpoint.get('recheck'):
            todo=checkpoint.get('last_processed_ids',[])[:limit]
            pending=list(dict.fromkeys(pending+todo))
        else:todo=pending[:limit]
        # A limited initial baseline is explicitly scoped, not claimed to acknowledge the whole index.
        cp={'watermark':checkpoint.get('watermark') if checkpoint.get('recheck') else safe_watermark,'baseline_bound':max(limit,checkpoint.get('baseline_bound',0)),
            'pending':[x for x in pending if x not in todo],'index_raw_id':str(index_raw.id),'ecosystem':'PyPI','initial_baseline_global_complete':False}
        cp['discovery_window_complete']=window_complete
        cp['last_processed_ids']=todo
        def frames():
            for id in todo:
                base='https://storage.googleapis.com/osv-vulnerabilities/PyPI/' if baseline else 'https://api.osv.dev/v1/vulns/'
                url=base+quote(id,safe='')+('.json' if baseline else '')
                try:
                    r=self.http.get(url)
                    yield RawEnvelope(id,url,r.content,content_type=r.headers.get('content-type','application/json'),metadata={'acquisition':'dataset_baseline' if baseline else 'api_incremental'})
                except Exception as exc:
                    # One record request failure must not suppress subsequent IDs.
                    yield RawEnvelope(id,url,b'',metadata={'fetch_error':type(exc).__name__})
        return CollectionBatch(frames(),cp,pending,{'ecosystem':'PyPI','baseline_bound':cp['baseline_bound'],
            'global_complete':False,'index_raw_id':str(index_raw.id),'discovery_index_complete':not prefix,'index_prefix_lines':1000,
            'overlap_hours':24,'known_gaps':['Bounded initial baseline and first1000 discovery rows; older index and EMPTY ecosystem need reconciliation; not global CDC']})

import hashlib,json
from app.collectors.base import BaseCollector,CollectionBatch,RawEnvelope
from app.normalizers import cisa_kev

URL='https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json'

def catalog_delta(catalog,hashes):
    entries=cisa_kev.validate_catalog(catalog)
    current={x['cveID']:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest() for x in entries}
    return {'hashes':current,'changed':[x['cveID'] for x in entries if hashes.get(x['cveID'])!=current[x['cveID']]],'removed':sorted(set(hashes)-set(current))}

class KEVCollector(BaseCollector):
    source_key='CISA_KEV'
    normalize=staticmethod(cisa_kev.normalize)
    def __init__(self,http,cache_lookup=None): self.http=http; self.cache_lookup=cache_lookup

    def finalize_checkpoint(self,before,candidate,pending,failed):
        complete=not pending and not failed
        return {**candidate,'pending':pending,'normalization_complete':complete,
            'normalized_catalog_version':candidate['catalog_version'] if complete else (before or {}).get('normalized_catalog_version')}

    def collect(self,checkpoint,limit,persist_raw):
        checkpoint=checkpoint or {}
        cached=self.cache_lookup(checkpoint.get('raw_id')) if self.cache_lookup and checkpoint.get('raw_id') else None
        headers={'If-None-Match':checkpoint['etag']} if cached and checkpoint.get('etag') else None
        response=self.http.get(URL,headers=headers)
        if response.status_code==304 and not cached: response=self.http.get(URL)
        if response.status_code==304:
            raw=cached; catalog=json.loads(raw.raw_payload); status=304
        else:
            raw=persist_raw(RawEnvelope('catalog',URL,response.content,metadata={'etag':response.headers.get('etag'),'kind':'full_catalog'}))
            catalog=json.loads(response.content); status=200
        delta=catalog_delta(catalog,checkpoint.get('item_hashes',{}))
        entries=catalog['vulnerabilities']; positions={x['cveID']:i for i,x in enumerate(entries)}
        prior_pending=checkpoint.get('pending',[])
        changed=delta['changed']
        # Prioritize a known real AI CVE only if it is actually listed in this fetched catalog.
        changed.sort(key=lambda id:(id!='CVE-2025-32434',-positions[id]))
        work=list(dict.fromkeys(prior_pending+changed+delta['removed']))
        if checkpoint.get('recheck'):
            todo=checkpoint.get('last_processed_ids',[])[:limit]
            work=list(dict.fromkeys(work+todo))
        else: todo=work[:limit]
        cp={'raw_id':str(raw.id),'etag':response.headers.get('etag') or checkpoint.get('etag'),
            'catalog_version':catalog['catalogVersion'],'item_hashes':delta['hashes'],'pending':[x for x in work if x not in todo],'http_status':status,'catalog_count':catalog['count']}
        cp['last_processed_ids']=todo
        def frames():
            for id in todo:
                if id not in positions:
                    yield RawEnvelope('catalog',URL,b'',raw_id=raw.id,record_id=id,payload={'removed':id,'catalog':catalog},metadata={'removed':True},http_status=status)
                else:
                    index=positions[id]
                    yield RawEnvelope('catalog',URL,b'',raw_id=raw.id,record_id=id,payload={'catalog':catalog,'index':index},
                        locator={'json_pointer':'/vulnerabilities/'+str(index)},http_status=status)
        return CollectionBatch(frames(),cp,work,{'transport_complete':True,'catalog_count':catalog['count'],'global_complete':False,
            'domain_processing_limit':limit,'known_gaps':['Whole catalog saved and validated; domain rows populated only for processed IDs'],'http_status':status})

"""Bounded discovery plus exact native records over the existing SyncService."""
import json,os,re
from pathlib import Path
from urllib.parse import urlencode
from app.collectors.base import BaseCollector,CollectionBatch,RawEnvelope
from app.normalizers import ghsa,nvd
from app.monitoring.catalog import validate_url
from app.enrichment.acquisition import VENDORS

def github_headers():
    headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2026-03-10'}
    if os.environ.get('AEGIS_GITHUB_TOKEN'):headers['Authorization']='Bearer '+os.environ['AEGIS_GITHUB_TOKEN']
    return headers

class GitHubCollector(BaseCollector):
    source_key='GHSA'
    def __init__(self,http,*,source_key='GHSA',bootstrap_ids=None):
        if source_key not in {'GHSA',*VENDORS}:raise ValueError('Unregistered GitHub collector')
        self.source_key=source_key;self.http=http
        seeds=json.loads((Path(__file__).resolve().parents[1]/'resources/bootstrap_ids.json').read_text(encoding='utf-8'))['osv']
        self.bootstrap=[x for x in seeds if ghsa.ID.fullmatch(x)] if bootstrap_ids is None and source_key=='GHSA' else bootstrap_ids or []
    def normalize(self,payload,raw_id,retrieved_at):return ghsa.normalize(payload,raw_id,retrieved_at,source=self.source_key)
    def collect(self,checkpoint,limit,persist_raw):
        checkpoint=checkpoint or {};repo=VENDORS.get(self.source_key)
        base='https://api.github.com'+('/repos/'+repo+'/security-advisories' if repo else '/advisories')
        params={'per_page':100}
        if repo:params['state']='published'
        if not repo:params.update(type='reviewed',ecosystem='pip',sort='updated',direction='desc')
        url=base+'?'+urlencode(params);validate_url(url);response=self.http.get(url,headers=github_headers())
        persist_raw(RawEnvelope('discovery:latest100',url,response.content,metadata={'kind':'discovery','global_complete':False}))
        rows=response.json()
        if not isinstance(rows,list) or len(rows)>100:raise ValueError('Unexpected advisory index')
        ids=list(dict.fromkeys([*checkpoint.get('pending',[]),*self.bootstrap,*[x.get('ghsa_id') for x in rows if isinstance(x,dict)]]))
        ids=[x for x in ids if isinstance(x,str) and ghsa.ID.fullmatch(x)]
        selected=ids[:limit]
        def records():
            for identifier in selected:
                url=base+'/'+identifier
                try:
                    response=self.http.get(url,headers=github_headers())
                    yield RawEnvelope(identifier,url,response.content)
                except Exception as e:yield RawEnvelope(identifier,url,b'',metadata={'fetch_error':type(e).__name__})
        return CollectionBatch(records(),{'pending':ids[limit:],'scope':'latest100_pip' if not repo else repo},ids,
            {'kind':'vendor_advisory' if repo else 'security_community','global_complete':False,'index_limit':100,'record_limit':limit,'repository':repo,
             'known_gaps':['Bounded discovery window; not a complete global feed. Same upstream publisher is not independent evidence.']})

class NVDCollector(BaseCollector):
    source_key='NVD'
    def __init__(self,http,ids=None):
        self.http=http;self.ids=ids if ids is not None else json.loads((Path(__file__).resolve().parents[1]/'resources/bootstrap_ids.json').read_text(encoding='utf-8'))['cve']
    def normalize(self,payload,raw_id,retrieved_at):
        rows=payload.get('vulnerabilities')
        if not isinstance(rows,list) or len(rows)!=1:raise ValueError('Exact NVD CVE response required')
        record=nvd.normalize(rows[0]['cve'],raw_id,retrieved_at)
        # Keep all normalized child locations rooted in the original wrapper.
        base='/vulnerabilities/0/cve'
        for name in ('cvss','references'):
            for item in getattr(record,name) or []:item['locator']=base+item['locator']
        record.field_provenance={k:{'json_pointer':base+v['json_pointer']} for k,v in record.field_provenance.items()}
        record.field_provenance['record']={'json_pointer':base}
        return record
    def collect(self,checkpoint,limit,persist_raw):
        ids=list(dict.fromkeys([*(checkpoint or {}).get('pending',[]),*self.ids]))
        if any(not isinstance(x,str) or not re.fullmatch(r'CVE-\d{4}-\d{4,}',x) for x in ids):raise ValueError('Exact CVE IDs required')
        headers={'apiKey':os.environ['AEGIS_NVD_API_KEY']} if os.environ.get('AEGIS_NVD_API_KEY') else None
        def records():
            for identifier in ids[:limit]:
                url='https://services.nvd.nist.gov/rest/json/cves/2.0?'+urlencode({'cveId':identifier})
                try:
                    response=self.http.get(url,headers=headers)
                    yield RawEnvelope(identifier,url,response.content)
                except Exception as e:yield RawEnvelope(identifier,url,b'',metadata={'fetch_error':type(e).__name__})
        return CollectionBatch(records(),{'pending':ids[limit:],'known_ids':ids},ids,
            {'kind':'vulnerability_database','global_complete':False,'known_id_refresh':True,'record_limit':limit,
             'known_gaps':['Only declared known AI CVEs; discovery is provided by existing CVE/OSV and GHSA adapters. CPE predicates not flattened into package fixes.']})

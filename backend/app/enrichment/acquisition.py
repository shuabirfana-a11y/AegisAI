"""Approved read-only API acquisition; original bytes commit before parsing."""
import os,re,json,base64
from dataclasses import dataclass
from urllib.parse import urlsplit
from sqlalchemy import select
from app.db import models as m
from app.db.persistence import store_raw
from app.repositories.ingestion import unique_row
from app.utils.time import utcnow
from app.enrichment.contracts import CONTENT_TRUST

VENDORS={'VENDOR_PYTORCH':'pytorch/pytorch','VENDOR_VLLM':'vllm-project/vllm','VENDOR_MLFLOW':'mlflow/mlflow',
         'VENDOR_LANGGRAPH':'langchain-ai/langgraph','VENDOR_LANGCHAIN':'langchain-ai/langchain'}
REPO=r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+'

def validate_enrichment_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or p.fragment:raise ValueError('Unapproved acquisition address')
    if p.hostname=='pypi.org' and not p.query and re.fullmatch(r'/pypi/[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?/json',p.path):
        # Distribution metadata only. Never follow project links or download wheels.
        if '..' not in p.path:return
    if p.hostname=='api.first.org' and p.path=='/data/v1/epss':return
    if p.hostname=='api.github.com':
        if p.path=='/search/repositories':return
        pattern=r'/repos/('+REPO+r')(?:/(?:readme|security-advisories/GHSA-[A-Za-z0-9-]+|commits/[0-9a-f]{40,64}|pulls/[0-9]+|releases/tags/[A-Za-z0-9_.-]+))?'
        match=re.fullmatch(pattern,p.path)
        if match and all(x not in ('.','..') for x in match.group(1).split('/')):return
    raise ValueError('Unapproved enrichment API path')

def decode_readme(payload):
    if payload.get('encoding')!='base64' or payload.get('size',0)>524288:raise ValueError('Unsupported or oversized README')
    content=''.join((payload.get('content') or '').split())
    if len(content)>699052:raise ValueError('Oversized encoded README')
    data=base64.b64decode(content,validate=True)
    if len(data)>524288:raise ValueError('Oversized decoded README')
    return data.decode('utf-8',errors='replace')

@dataclass
class AcquiredDocument:
    raw_id:object
    observation_id:object
    source_id:object
    source_key:str
    url:str
    payload:object
    retrieved_at:object
    lineage:str

class EnrichmentAcquisition:
    def __init__(self,session_factory,http):self.factory=session_factory;self.http=http;self.checked=[]

    def fetch(self,key,url,external_id,lineage):
        validate_enrichment_url(url)
        if key not in {'EPSS','GITHUB','PYPI_METADATA',*VENDORS}:raise ValueError('Unregistered enrichment source')
        if (key=='PYPI_METADATA') != (urlsplit(url).hostname=='pypi.org'):
            raise ValueError('Registry source scope mismatch')
        if key in VENDORS and not urlsplit(url).path.startswith('/repos/'+VENDORS[key]+'/security-advisories/'):
            raise ValueError('Official vendor scope mismatch')
        now=utcnow();entry={'source':key,'url':url,'checked_at':now.isoformat(),'status':'running'};self.checked.append(entry)
        headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2026-03-10'} if urlsplit(url).hostname=='api.github.com' else None
        token=os.environ.get('AEGIS_GITHUB_TOKEN')
        if token and headers is not None:headers={**headers,'Authorization':'Bearer '+token}
        with self.factory() as s:
            source=unique_row(s,m.Source,{'source_key':key},{'name':key,'source_type':'api','category':'enrichment',
                'authority_level':'community' if key=='GITHUB' else 'official',
                'authority_scope':VENDORS.get(key,'Registry distribution identity and release publication only' if key=='PYPI_METADATA' else 'FIRST EPSS probability only' if key=='EPSS' else 'Public hosting metadata; no exploit authority'),
                'acquisition_method':'https_api','base_url':'https://pypi.org' if key=='PYPI_METADATA' else 'https://api.first.org/data/v1/epss' if key=='EPSS' else 'https://api.github.com',
                'enabled':True,'license_scope':'Upstream terms; metadata/limited evidence only','details':{'content_trust_level':CONTENT_TRUST}})
            source_id=source.id
        try:response=self.http.get(url,headers=headers)
        except Exception as exc:
            entry['status']='failed';entry['error_code']=type(exc).__name__
            with self.factory() as s:
                source=s.get(m.Source,source_id);source.last_sync_at=now;source.status='failed'
            raise
        with self.factory() as s:
            raw=store_raw(s,source_id=source_id,external_id=external_id,source_url=url,retrieved_at=now,
                content_type=response.headers.get('content-type','application/json').split(';')[0],raw_payload=response.content,
                completeness='complete',publisher=VENDORS.get(key,key),
                details={'content_trust_level':CONTENT_TRUST,'http_status':response.status_code})
            raw_id=raw.id
        entry.update({'raw_document_id':str(raw_id),'http_status':response.status_code})
        try:
            payload=json.loads(response.content)
            if not isinstance(payload,(dict,list)):raise ValueError('Structured API response required')
        except (ValueError,TypeError):
            entry['status']='failed';entry['error_code']='PARSER_ERROR'
            with self.factory() as s:
                s.get(m.Source,source_id).status='failed'
            raise ValueError('Unparseable enrichment payload') from None
        with self.factory() as s:
            # Each successful retrieval is a new immutable observation of potentially identical raw bytes.
            observation=m.SourceObservation(source_id=source_id,raw_document_id=raw_id,external_id=external_id,
                record_type='enrichment',retrieved_at=now,http_status=response.status_code,publisher=VENDORS.get(key,key),
                lineage_key=lineage,parse_status='parsed',normalizer_version='enrichment-api-v2',normalized_payload=payload,
                raw_locator={'json_pointer':''},details={'content_trust_level':CONTENT_TRUST})
            s.add(observation);s.flush()
            observation_id=observation.id
            source=s.get(m.Source,source_id);source.last_sync_at=now;source.last_success_at=now;source.status='succeeded'
        entry.update({'status':'checked','observation_id':str(observation_id)})
        return AcquiredDocument(raw_id,observation_id,source_id,key,url,payload,now,lineage)

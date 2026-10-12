"""Controlled real-source snapshot, separate DB; not an enterprise scan or GT."""
import sys,json,os,subprocess
from pathlib import Path
from uuid import uuid4
import psycopg,httpx
from psycopg import sql
sys.path.insert(0,str(Path.cwd()/'backend'))
ROOT=Path(__file__).resolve().parents[2]
os.chdir(ROOT)
(ROOT/'work/phase12d3').mkdir(parents=True,exist_ok=True)
DB='aegis_phase12d3_demo'
URL='postgresql+psycopg://aegis_local@127.0.0.1:55436/'+DB
with psycopg.connect(host='127.0.0.1',port=55436,user='aegis_local',dbname='postgres',autocommit=True) as conn:
 if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DB,)).fetchone():
  conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DB)))
os.environ['AEGIS_DATABASE_URL']=URL
from alembic.config import Config
from alembic import command
cfg=Config('backend/alembic.ini');cfg.set_main_option('script_location','backend/alembic')
command.upgrade(cfg,'head')
from app.db.session import make_engine,transaction
from app.db import models as m
from app.db.persistence import ensure_vulnerability,store_raw
from app.repositories.ingestion import package_row,persist_record,unique_row
from app.enrichment.acquisition import EnrichmentAcquisition
from app.enrichment.parsing import parse_advisory
from app.enrichment.repository import ClaimStore
from app.enrichment.evidence import EvidenceService
from app.normalizers.common import metric
from app.core.http import HttpClient
from app.enrichment.acquisition import validate_enrichment_url
from app.utils.time import utcnow,parse_time
from app.assets.inventory import AssetService
engine=make_engine(URL);http=HttpClient(url_validator=validate_enrichment_url)
# Reuse the already authenticated GitHub account inside this process only;
# never print, serialize, or pass its credential in command-line arguments.
import shutil
if shutil.which('gh'):
 auth=subprocess.run(['gh','auth','token'],capture_output=True,text=True)
 if auth.returncode==0:os.environ['AEGIS_GITHUB_TOKEN']=auth.stdout.strip()
acq=EnrichmentAcquisition(lambda:transaction(engine),http)
url='https://api.github.com/repos/vllm-project/vllm/security-advisories/GHSA-hjq4-87xh-g4fv'
doc=acq.fetch('VENDOR_VLLM',url,'vllm-project/vllm:GHSA-hjq4-87xh-g4fv','github:vllm-project/vllm')
data=doc.payload
assert data['cve_id']=='CVE-2025-47277' and data['state']=='published' and not data.get('withdrawn_at')
parsed=parse_advisory(data,'vllm-project/vllm',data['cve_id'],['GHSA-hjq4-87xh-g4fv'])
# Original OSV bytes go through the existing normalizer and ingestion pipeline.
from app.normalizers import osv
osv_url='https://api.osv.dev/v1/vulns/GHSA-hjq4-87xh-g4fv'
response=httpx.get(osv_url,timeout=20);response.raise_for_status()
with transaction(engine) as db:
 catalog=json.loads(Path('backend/app/resources/sources.json').read_text(encoding='utf-8'))
 entry=next(x for x in catalog if x['source_id']=='OSV')
 source=unique_row(db,m.Source,{'source_key':'OSV'},{'name':'OSV','source_type':'api','category':'vulnerability',
  'authority_level':'authoritative','authority_scope':entry['authority_level'],'acquisition_method':'https_api','base_url':'https://api.osv.dev'})
 raw=store_raw(db,source_id=source.id,external_id='GHSA-hjq4-87xh-g4fv',source_url=osv_url,
  retrieved_at=utcnow(),content_type='application/json',raw_payload=response.content,publisher='OSV')
 record=osv.normalize(response.json(),str(raw.id),raw.retrieved_at)
 persist_record(db,source,raw,record)
with transaction(engine) as db:
 v=ensure_vulnerability(db,data['cve_id'],data['summary'])
 v.description=data['description'];v.published_at=parse_time(data['published_at']);v.status='published'
 source=db.get(m.Source,doc.source_id);obs=db.get(m.SourceObservation,doc.observation_id)
 product,package=package_row(db,{'name':'vllm','ecosystem':'PyPI'},source)
 for item in parsed['claims']:
  subject={'package_identifier_id':package.id} if item['type']!='VENDOR_CONFIRMED' else None
  c=ClaimStore.add(db,v.id,item['type'],item['scope'],item['value'],subject=subject)
  EvidenceService.add(db,c,obs,item['value'],{'json_pointer':item['locator']},evidence_type='official_vendor_advisory')
 cvss=data.get('cvss') or (data.get('cvss_severities') or {}).get('cvss_v3') or {};vector=cvss.get('vector_string')
 cvss_pointer='/cvss' if data.get('cvss') else '/cvss_severities/cvss_v3'
 assert vector,'No official CVSS vector; cannot fabricate severity'
 got=metric(vector,provider='vllm-project/vllm',locator={'json_pointer':cvss_pointer})
 assert cvss.get('score')==got['base_score'] and data['severity']==got['severity'],'Official vector, score and severity must agree'
 value={'version':got['version'],'score':got['base_score'],'severity':got['severity'],'vector':vector}
 c=ClaimStore.add(db,v.id,'CVSS_SCORE',v.canonical_id,value)
 EvidenceService.add(db,c,obs,value,{'json_pointer':cvss_pointer},evidence_type='official_vendor_advisory')
 # The explicit supplied inventory is deliberately a demo, not inferred from a real server.
 actor='phase12d3-demo-operator'
 a=AssetService.create(db,{'name':'Phase12D3 vLLM demo inventory','environment':'production','exposure':'internet','is_demo':True},actor,'phase12d3-demo-asset')
 component=AssetService.add_component(db,a.id,{'name':'vLLM','package_name':'vllm','ecosystem':'PyPI','version':'0.6.5','purl':'pkg:pypi/vllm@0.6.5'},actor,'phase12d3-demo-vllm')
 result={'database_kind':'ISOLATED_REAL_OFFICIAL_SOURCE_SNAPSHOT_WITH_DEMO_INVENTORY',
  'source_url':url,'raw_document_id':str(doc.raw_id),'observation_id':str(doc.observation_id),
  'retrieved_at':doc.retrieved_at.isoformat(),'asset_id':str(a.id),'component_id':str(component.id),
  'is_demo':True,'benchmark':False,'source_scope':'Only the selected official vendor advisory; no exclusion or modification of legacy DB claims',
  'target':v.canonical_id,'affected_range':next(x['value'] for x in parsed['claims'] if x['type']=='AFFECTS_VERSION'),
  'severity':value}
 Path('work/phase12d3/real-demo-inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(result,ensure_ascii=False))
from app.knowledge.index import KnowledgeIndex
from app.knowledge.embedding import local_embedding
with transaction(engine) as db:
 KnowledgeIndex.ingest(db,db.get(m.RawDocument,doc.raw_id),local_embedding())
case={'benchmark':False,'cases':[{'case_id':'real-asset-risk-official-vllm','data_origin':'REAL_SOURCE_WITH_DEMO_INVENTORY','request':{
 'user_query':'对指定资产中的 vLLM 0.6.5 开展 CVE-2025-47277 风险分析和优先级调查，查询漏洞、资产库存、组件版本和证据；未确认项保持未知。',
 'asset_scope':{'asset_id':result['asset_id'],'component_id':result['component_id'],'target':'CVE-2025-47277',
 'component':{'name':'vllm','ecosystem':'PyPI','package_name':'vllm','version':'0.6.5'}},
 'options':{'objective_profile':'asset_risk_v1'}}}]}
Path('work/phase12d3/generated-cases.json').write_text(json.dumps(case,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
http.close();engine.dispose()

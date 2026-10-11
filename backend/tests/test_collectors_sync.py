from contextlib import contextmanager
from pathlib import Path
import json
import httpx
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.collectors.base import BaseCollector,RawEnvelope,CollectionBatch
from app.collectors.osv import select_changes
from app.collectors.cisa_kev import catalog_delta
from app.normalizers import osv
from app.services.sync import SyncService
from app.db import models as m
from app.core.http import HttpClient
from app.core.config import Settings
from app.collectors.osv import OSVCollector
from app.collectors.cisa_kev import KEVCollector
from types import SimpleNamespace
from uuid import uuid4
from app.collectors.cve import CVECollector

F=Path(__file__).parent/'fixtures/source_records'

class RecordsCollector(BaseCollector):
    source_key='OSV'
    def __init__(self,records,fail=None):self.records=records;self.fail=fail
    def collect(self,checkpoint,limit,persist_raw):
        if self.fail: raise self.fail
        def frames():
            for i,payload in enumerate(self.records[:limit]):
                id=payload.get('id','BROKEN-'+str(i))
                yield RawEnvelope(external_id=id,source_url='https://api.osv.dev/v1/vulns/'+id,raw_payload=json.dumps(payload).encode())
        return CollectionBatch(frames(),{'watermark':'2026-10-03T00:00:00Z'},[x.get('id','BROKEN-'+str(i)) for i,x in enumerate(self.records[:limit])],{'scope':'TEST ONLY'})
    normalize=staticmethod(osv.normalize)

def service(db):
    connection=db.connection()
    @contextmanager
    def factory():
        with Session(connection,join_transaction_mode='create_savepoint') as s:
            with s.begin():yield s
    return SyncService(None,session_factory=factory)

def test_phase6_10_sync_same_batch_idempotent(db):
    s=service(db); c=RecordsCollector([json.loads((F/'osv.json').read_bytes())])
    first=s.sync(c,1); second=s.sync(c,1)
    assert first is not None and second is not None
    assert first['created']==1 and second['skipped']==1
    assert db.scalar(select(func.count()).select_from(m.Vulnerability))==1
    assert db.scalar(select(func.count()).select_from(m.RawDocument))==1
    assert db.scalar(select(func.count()).select_from(m.SyncRun))==2

def test_phase6_04_timeout_records_failed_run(db):
    result=service(db).sync(RecordsCollector([],httpx.ReadTimeout('TEST')),10)
    assert result is not None and result['status']=='failed'
    row=db.scalar(select(m.Source)); run=db.scalar(select(m.SyncRun))
    assert row.last_success_at is None and run.finished_at is not None
    assert 'ReadTimeout' in run.error_summary and row.checkpoint is None

def test_bad_record_raw_survives_and_next_item_commits(db):
    good=json.loads((F/'osv.json').read_bytes())
    result=service(db).sync(RecordsCollector([{'id':'BROKEN','modified':'no-date'},good]),10)
    assert result is not None and result['failed']==1 and result['created']==1 and result['status']=='partial'
    assert db.scalar(select(func.count()).select_from(m.RawDocument))==2
    row=db.scalar(select(m.Source))
    assert row.last_success_at is None and 'BROKEN' in row.checkpoint['pending']
    assert row.checkpoint.get('watermark') is None

def test_phase6_03_sync_content_update(db):
    p=json.loads((F/'osv.json').read_bytes()); s=service(db)
    first=s.sync(RecordsCollector([p]),1); p['details']='NEW SOURCE CONTENT'
    second=s.sync(RecordsCollector([p]),1)
    assert first is not None and second is not None and second['updated']==1
    assert db.scalar(select(func.count()).select_from(m.RawDocument))==2

def test_osv_equal_timestamps_all_selected():
    index=b'2026-10-03T00:00:00Z,TEST-A\n2026-10-03T00:00:00Z,TEST-B\n2026-09-01T00:00:00Z,TEST-OLD\n'
    rows=select_changes(index,{'watermark':'2026-10-03T00:00:00Z'})
    assert {x['id'] for x in rows}=={'TEST-A','TEST-B'}

def test_kev_item_deltas_and_removals():
    catalog=json.loads((F/'cisa_kev.json').read_bytes())
    first=catalog_delta(catalog,{})
    assert first is not None and len(first['changed'])==catalog['count']
    second=catalog_delta(catalog,first['hashes'])
    assert not second['changed'] and not second['removed']
    reduced={**catalog,'vulnerabilities':catalog['vulnerabilities'][1:],'count':catalog['count']-1}
    third=catalog_delta(reduced,first['hashes'])
    assert third['removed']==[catalog['vulnerabilities'][0]['cveID']]

def test_osv_recheck_preserves_unprocessed_backlog():
    http=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=b'2026-10-03T00:00:00Z,TEST-A\n')))
    collector=OSVCollector(http,bootstrap_ids=[])
    batch=collector.collect({'baseline_bound':100,'watermark':'2026-10-03T00:00:00Z','pending':['TEST-BACKLOG'],'last_processed_ids':['TEST-A'],'recheck':True},1,lambda e:SimpleNamespace(id=uuid4()))
    assert 'TEST-BACKLOG' in batch.pending
    assert [x.external_id for x in batch.records]==['TEST-A']

def test_kev_304_cache_and_recheck_backlog():
    body=(F/'cisa_kev.json').read_bytes();p=json.loads(body);raw=SimpleNamespace(id=uuid4(),raw_payload=body)
    ids=[x['cveID'] for x in p['vulnerabilities']];seen=[]
    def handler(req):
        seen.append(req);return httpx.Response(304,headers={'etag':'"fixture"'})
    http=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(handler))
    collector=KEVCollector(http,lambda id:raw)
    cp={'raw_id':str(raw.id),'etag':'"fixture"','item_hashes':catalog_delta(p,{})['hashes'],'pending':[ids[0]],'last_processed_ids':[ids[1]],'recheck':True}
    def should_not_fetch_raw(envelope):raise AssertionError('304 must reuse cached immutable raw')
    batch=collector.collect(cp,1,should_not_fetch_raw)
    assert seen[0].headers['if-none-match']=='"fixture"'
    assert set(batch.pending)=={ids[0],ids[1]} and list(batch.records)[0].raw_id==raw.id
    final=collector.finalize_checkpoint(cp,batch.checkpoint,[ids[0]],False)
    assert final['pending']==[ids[0]] and not final['normalization_complete']

def test_cve_git_metadata_with_http_blob_transport(tmp_path):
    body=(F/'cve.json').read_bytes();http=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=body)))
    cache=tmp_path/'official_cache';(cache/'.git').mkdir(parents=True)
    collector=CVECollector(Settings(cve_cache=cache),http)
    sha='a'*40
    def git(*args,check=True):
        if args[0]=='remote':value='https://github.com/CVEProject/cvelistV5.git\n'
        elif args[0]=='ls-remote':value=sha+'\trefs/heads/main\n'
        elif args[0]=='ls-tree':value='cves/2025/32xxx/CVE-2025-32434.json\n'
        elif args[0]=='cat-file':value=''
        else:raise RuntimeError('Git metadata cache contains no record blobs')
        return SimpleNamespace(returncode=0,stdout=value.encode())
    collector.git=git
    batch=collector.collect({},1,lambda frame:None)
    frames=list(batch.records)
    assert len(frames)==1 and frames[0].raw_payload==body and sha in frames[0].source_url

def test_osv_incomplete_discovery_never_advances_global_watermark():
    body=b''.join(b'2026-10-03T00:00:00Z,TEST-'+str(i).encode()+b'\n' for i in range(1001))
    http=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=body)))
    collector=OSVCollector(http,bootstrap_ids=[])
    batch=collector.collect({},1,lambda e:SimpleNamespace(id=uuid4()))
    assert batch.coverage['discovery_index_complete'] is False
    assert batch.checkpoint['watermark'] is None
    assert batch.checkpoint['discovery_window_complete'] is False

@pytest.mark.parametrize('change',['updated','removed'])
def test_kev_recheck_retains_newly_discovered_item_work(change):
    original=json.loads((F/'cisa_kev.json').read_bytes())
    original['vulnerabilities']=original['vulnerabilities'][:2];original['count']=2
    a,b=[x['cveID'] for x in original['vulnerabilities']]
    hashes=catalog_delta(original,{})['hashes'];current=json.loads(json.dumps(original))
    if change=='updated':current['vulnerabilities'][1]['shortDescription']+=' changed'
    else:current['vulnerabilities']=current['vulnerabilities'][:1];current['count']=1
    current['catalogVersion']+='-test-new'
    http=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,json=current)))
    collector=KEVCollector(http)
    batch=collector.collect({'item_hashes':hashes,'last_processed_ids':[a],'pending':[],'recheck':True},1,lambda e:SimpleNamespace(id=uuid4()))
    assert {a,b}<=set(batch.pending)
    checkpoint=collector.finalize_checkpoint({},batch.checkpoint,[b],False)
    ordinary=collector.collect(checkpoint,1,lambda e:SimpleNamespace(id=uuid4()))
    assert b in ordinary.pending and list(ordinary.records)[0].record_id==b

@pytest.mark.parametrize('ancestor',[True,False])
def test_cve_smaller_limit_retains_entire_previously_covered_scope(tmp_path,ancestor):
    cache=tmp_path/'git_metadata';(cache/'.git').mkdir(parents=True)
    http=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=(F/'cve.json').read_bytes())))
    collector=CVECollector(Settings(cve_cache=cache),http);collector.bootstrap=[]
    a='cves/2025/32xxx/CVE-2025-32001.json';b='cves/2025/32xxx/CVE-2025-32002.json';sha='a'*40
    def git(*args,check=True):
        if args[0]=='remote':value='https://github.com/CVEProject/cvelistV5.git\n'
        elif args[0]=='ls-remote':value=sha+'\trefs/heads/main\n'
        elif args[0]=='ls-tree':value=a+'\n'+b+'\n'
        elif args[0]=='cat-file':value=''
        elif args[0]=='merge-base':return SimpleNamespace(returncode=0 if ancestor else 1,stdout=b'')
        elif args[0]=='diff':value=b+'\n'
        else:raise AssertionError(args)
        return SimpleNamespace(returncode=0,stdout=value.encode())
    collector.git=git
    batch=collector.collect({'commit':'b'*40,'covered_paths':[a,b],'pending_paths':[]},1,lambda e:None)
    assert 'CVE-2025-32002' in batch.pending
    if ancestor:assert list(batch.records)[0].external_id=='CVE-2025-32002'

def test_cve_partial_diff_resume_does_not_rediscover_completed_paths(tmp_path):
    cache=tmp_path/'git_metadata';(cache/'.git').mkdir(parents=True)
    http=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=(F/'cve.json').read_bytes())))
    collector=CVECollector(Settings(cve_cache=cache),http);collector.bootstrap=[]
    a='cves/2025/32xxx/CVE-2025-32001.json';b='cves/2025/32xxx/CVE-2025-32002.json';sha='a'*40
    def git(*args,check=True):
        if args[0]=='remote':value='https://github.com/CVEProject/cvelistV5.git\n'
        elif args[0]=='ls-remote':value=sha+'\trefs/heads/main\n'
        elif args[0]=='ls-tree':value=a+'\n'+b+'\n'
        elif args[0] in ('cat-file','merge-base'):value=''
        elif args[0]=='diff':value='' if args[2]==args[3] else a+'\n'+b+'\n'
        else:raise AssertionError(args)
        return SimpleNamespace(returncode=0,stdout=value.encode())
    collector.git=git;before={'commit':'b'*40,'covered_paths':[a,b],'pending_paths':[]}
    first=collector.collect(before,1,lambda e:None)
    checkpoint=collector.finalize_checkpoint(before,first.checkpoint,['CVE-2025-32002'],False)
    second=collector.collect(checkpoint,1,lambda e:None)
    assert second.pending==['CVE-2025-32002']
    finished=collector.finalize_checkpoint(checkpoint,second.checkpoint,[],False)
    assert finished['commit']==sha and not finished['pending_paths']

def test_osv_partial_window_resumes_without_requeueing_completed_ids():
    index=b'2026-10-03T00:00:00Z,TEST-A\n2026-10-03T00:00:00Z,TEST-B\n'
    http=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=index)))
    collector=OSVCollector(http,bootstrap_ids=[]);raw=SimpleNamespace(id=uuid4())
    before={'baseline_bound':2,'watermark':'2026-10-02T00:00:00Z','pending':[]}
    first=collector.collect(before,1,lambda e:raw)
    checkpoint=collector.finalize_checkpoint(before,first.checkpoint,['TEST-B'],False)
    assert checkpoint['watermark']==before['watermark']
    second=collector.collect(checkpoint,1,lambda e:raw)
    assert second.pending==['TEST-B']
    assert [x.external_id for x in second.records]==['TEST-B']
    finished=collector.finalize_checkpoint(checkpoint,second.checkpoint,[],False)
    assert not finished['pending'] and finished['watermark']=='2026-10-03T00:00:00Z'

def test_osv_recheck_preserves_newly_discovered_window_items():
    index=b'2026-10-03T00:00:00Z,TEST-A\n2026-10-03T00:00:00Z,TEST-B\n'
    http=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=index)))
    collector=OSVCollector(http,bootstrap_ids=[]);raw=SimpleNamespace(id=uuid4())
    before={'baseline_bound':2,'watermark':'2026-10-02T00:00:00Z','pending':[],'last_processed_ids':['TEST-A'],'recheck':True}
    batch=collector.collect(before,1,lambda e:raw)
    assert set(batch.pending)=={'TEST-A','TEST-B'}
    checkpoint=collector.finalize_checkpoint({k:v for k,v in before.items() if k!='recheck'},batch.checkpoint,['TEST-B'],False)
    ordinary=collector.collect(checkpoint,1,lambda e:raw)
    assert ordinary.pending==['TEST-B'] and [x.external_id for x in ordinary.records]==['TEST-B']

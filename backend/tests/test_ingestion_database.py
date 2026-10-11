from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import copy,json
from sqlalchemy import select,func
from app.db import models as m
from app.db.persistence import store_raw
from app.normalizers import cve,osv
from app.repositories.ingestion import persist_record

NOW=datetime(2026,10,3,8,0,tzinfo=timezone.utc)
F=Path(__file__).parent/'fixtures/source_records'

def source(db,key):
    row=m.Source(source_key=key,name=key,source_type='test',category='vulnerability',authority_level='official',authority_scope='TEST',acquisition_method='fixture',base_url='https://example.invalid/',details={'is_test':True})
    db.add(row);db.flush();return row

def ingest(db,s,payload,normalizer):
    data=json.dumps(payload).encode(); id=payload.get('id') or payload['cveMetadata']['cveId']
    raw=store_raw(db,source_id=s.id,external_id=id,source_url='https://example.invalid/test',retrieved_at=NOW,content_type='application/json',raw_payload=data,content_hash=sha256(data).hexdigest(),publisher=s.source_key)
    record=normalizer(payload,raw.id,NOW)
    return persist_record(db,s,raw,record)

def count(db,model): return db.scalar(select(func.count()).select_from(model))

def test_phase6_01_two_real_structures_one_cve(db):
    a=source(db,'CVE_LIST'); b=source(db,'OSV')
    ra=ingest(db,a,json.loads((F/'cve.json').read_bytes()),cve.normalize)
    rb=ingest(db,b,json.loads((F/'osv.json').read_bytes()),osv.normalize)
    assert ra is not None and rb is not None
    assert count(db,m.Vulnerability)==1 and count(db,m.RawDocument)==2
    assert count(db,m.CvssAssessment)==2
    assert count(db,m.SourceObservation)==2

def test_phase6_02_repeated_record_no_domain_duplicates(db):
    s=source(db,'OSV'); payload=json.loads((F/'osv.json').read_bytes())
    first=ingest(db,s,payload,osv.normalize)
    assert first is not None
    before={x.__name__:count(db,x) for x in [m.Vulnerability,m.RawDocument,m.Product,m.Reference,m.ExternalIdentifier,m.AffectedVersionRange,m.CvssAssessment,m.AiRelevanceAssessment]}
    second=ingest(db,s,payload,osv.normalize)
    assert second['outcome']=='skipped'
    assert before=={x.__name__:count(db,x) for x in [m.Vulnerability,m.RawDocument,m.Product,m.Reference,m.ExternalIdentifier,m.AffectedVersionRange,m.CvssAssessment,m.AiRelevanceAssessment]}

def test_phase6_03_changed_source_retains_old_raw_and_fields(db):
    s=source(db,'OSV'); payload=json.loads((F/'osv.json').read_bytes())
    first=ingest(db,s,payload,osv.normalize); assert first is not None
    payload['details']='changed source description'; payload['modified']='2026-10-03T07:00:00Z'
    second=ingest(db,s,payload,osv.normalize)
    assert second['outcome']=='updated' and count(db,m.Vulnerability)==1 and count(db,m.RawDocument)==2
    assert count(db,m.SourceObservation)==2 and count(db,m.CvssAssessment)==2

def test_phase6_08_source_scores_and_descriptions_not_overwritten(db):
    a=source(db,'CVE_LIST'); b=source(db,'OSV')
    c=json.loads((F/'cve.json').read_bytes()); o=json.loads((F/'osv.json').read_bytes())
    ingest(db,a,c,cve.normalize); original=db.scalar(select(m.Vulnerability)).description
    o['details']='Different source value'; o['modified']='2026-10-03T07:00:00Z'
    result=ingest(db,b,o,osv.normalize)
    assert result is not None
    assert db.scalar(select(m.Vulnerability)).description==original
    assert {x.source_id for x in db.scalars(select(m.CvssAssessment))}=={a.id,b.id}

def test_phase6_09_irrelevant_raw_retained(db):
    s=source(db,'OSV'); p={'id':'TEST-WEB-001','modified':'2026-10-03T00:00:00Z','summary':'test web library','affected':[{'package':{'ecosystem':'PyPI','name':'unrelated-web-package'},'ranges':[{'type':'ECOSYSTEM','events':[{'introduced':'0'},{'fixed':'2.0'}]}]}]}
    result=ingest(db,s,p,osv.normalize)
    assert result is not None and count(db,m.RawDocument)==1
    assert db.scalar(select(m.AiRelevanceAssessment)).result=='irrelevant'

def test_multi_cve_advisory_links_two_subjects(db):
    s=source(db,'OSV'); p=json.loads((F/'osv.json').read_bytes()); p['aliases']=['CVE-2025-32434','CVE-2022-45907']
    result=ingest(db,s,p,osv.normalize)
    assert result is not None and count(db,m.Vulnerability)==2 and count(db,m.RawDocument)==1
    assert count(db,m.AiRelevanceAssessment)==2
    ghsa=db.scalar(select(m.ExternalIdentifier).where(m.ExternalIdentifier.identifier_type=='GHSA'))
    assert count(db,m.ExternalIdentifier)==3
    assert len(db.scalars(select(m.VulnerabilityIdentifier).where(m.VulnerabilityIdentifier.identifier_id==ghsa.id)).all())==2

def test_unknown_ecosystem_product_stays_separate(db):
    s=source(db,'OSV'); p=json.loads((F/'osv.json').read_bytes())
    result=ingest(db,s,p,osv.normalize); assert result is not None
    p['id']='TEST-NPM-TORCH'; p['aliases']=[]; p['affected'][0]['package']={'ecosystem':'npm','name':'torch'}
    p.pop('severity',None)
    second=ingest(db,s,p,osv.normalize)
    assert second is not None and count(db,m.Product)==2

def test_same_parser_replay_does_not_replace_history(db):
    s=source(db,'OSV'); p=json.loads((F/'osv.json').read_bytes())
    result=ingest(db,s,p,osv.normalize); assert result is not None
    raw=db.scalar(select(m.RawDocument)); old=db.scalar(select(m.SourceObservation))
    record=osv.normalize(p,raw.id,NOW)
    result=persist_record(db,s,raw,record)
    assert result['outcome']=='skipped' and old.normalized_payload['external_id']==p['id']

def test_explicit_single_cve_promotes_source_candidate_preserving_uuid(db):
    s=source(db,'OSV'); p=json.loads((F/'osv.json').read_bytes()); p['aliases']=[]
    first=ingest(db,s,p,osv.normalize); original=db.scalar(select(m.Vulnerability)).id
    p['aliases']=['CVE-2025-32434']; p['modified']='2026-10-03T07:00:00Z'
    second=ingest(db,s,p,osv.normalize)
    assert count(db,m.Vulnerability)==1 and second['vulnerabilities_created']==0
    row=db.scalar(select(m.Vulnerability))
    assert row.id==original and row.canonical_id=='CVE-2025-32434'
    assert count(db,m.RawDocument)==2 and count(db,m.SourceObservation)==2

def test_multi_cve_alias_never_promotes_candidate_into_two_cves(db):
    s=source(db,'OSV'); p=json.loads((F/'osv.json').read_bytes()); p['aliases']=[]
    ingest(db,s,p,osv.normalize); original=db.scalar(select(m.Vulnerability)).id
    p['aliases']=['CVE-2025-32434','CVE-2022-45907']; p['modified']='2026-10-03T07:00:00Z'
    ingest(db,s,p,osv.normalize)
    assert count(db,m.Vulnerability)==3
    assert db.get(m.Vulnerability,original).canonical_id.startswith('OSV:')

def test_unknown_product_vendor_scopes_preserve_package_product_foreign_key(db):
    s=source(db,'CVE_LIST'); p=json.loads((F/'cve.json').read_bytes())
    p['containers']['cna']['affected']=[{'vendor':'Vendor A','product':'libsoup','versions':[{'version':'0','lessThanOrEqual':'3.6.4','status':'affected','versionType':'semver'}]}]
    ingest(db,s,p,cve.normalize)
    p['cveMetadata']['cveId']='CVE-2025-32049'; p['containers']['cna']['affected'][0]['vendor']=None
    result=ingest(db,s,p,cve.normalize)
    assert result['outcome']=='created'
    assert count(db,m.PackageIdentifier)==2 and count(db,m.Product)==2
    for range in db.scalars(select(m.AffectedVersionRange)):
        assert db.get(m.PackageIdentifier,range.package_identifier_id).product_id==range.product_id

def test_explicit_parser_upgrade_appends_revision_to_same_raw(db,monkeypatch):
    from app.repositories.ingestion import NORMALIZER_VERSIONS
    s=source(db,'OSV'); p=json.loads((F/'osv.json').read_bytes())
    ingest(db,s,p,osv.normalize); old=db.scalar(select(m.SourceObservation)); original_version=old.normalizer_version
    monkeypatch.setitem(NORMALIZER_VERSIONS,'OSV',original_version+'-test-upgrade')
    result=ingest(db,s,p,osv.normalize)
    assert result['outcome']=='updated' and count(db,m.RawDocument)==1 and count(db,m.Vulnerability)==1
    assert count(db,m.SourceObservation)==2 and old.normalizer_version==original_version
    assert count(db,m.CvssAssessment)==2

def test_old_raw_parser_replay_cannot_replace_current_source_revision(db,monkeypatch):
    from datetime import timedelta
    from app.repositories.ingestion import NORMALIZER_VERSIONS
    from app.repositories.queries import vulnerability_detail
    s=source(db,'OSV');old=json.loads((F/'osv.json').read_bytes());old['details']='old record'
    def at(payload,when):
        data=json.dumps(payload).encode();raw=store_raw(db,source_id=s.id,external_id=payload['id'],source_url=s.base_url,retrieved_at=when,content_type='application/json',raw_payload=data,publisher='test')
        persist_record(db,s,raw,osv.normalize(payload,raw.id,when));return raw
    raw=at(old,NOW)
    newer=copy.deepcopy(old);newer['details']='new source record';newer['modified']='2026-10-03T09:00:00Z'
    at(newer,NOW+timedelta(hours=1));monkeypatch.setitem(NORMALIZER_VERSIONS,'OSV',osv.VERSION+'-test-upgrade')
    # Even a legacy caller using parse time must not make historical raw the newest source revision.
    persist_record(db,s,raw,osv.normalize(old,raw.id,NOW+timedelta(hours=2)))
    detail=vulnerability_detail(db,'CVE-2025-32434');current=[x for x in detail['source_variants'] if x['is_current']]
    assert len(current)==1 and current[0]['description']=='new source record'

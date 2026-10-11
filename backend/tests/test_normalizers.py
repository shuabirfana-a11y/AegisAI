from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
import copy,json
import pytest
from app.normalizers import cve,osv,cisa_kev

FIXTURES=Path(__file__).parent/'fixtures/source_records'
NOW=datetime(2026,10,3,8,0,tzinfo=timezone.utc)

def fixture(name): return json.loads((FIXTURES/(name+'.json')).read_bytes())

def test_real_cve_fixture_identity_metrics_and_adp():
    p=fixture('cve'); r=cve.normalize(p,uuid4(),NOW)
    assert r is not None
    assert r.source=='CVE_LIST' and r.external_id=='CVE-2025-32434'
    assert r.published_at<r.retrieved_at and r.cvss[0]['version']=='4.0'
    assert float(r.cvss[0]['base_score'])==9.3
    assert r.references and r.products and r.field_provenance
    assert r.extensions['containers']['adp']==p['containers']['adp']

def test_real_osv_fixture_package_events_and_cvss():
    p=fixture('osv'); r=osv.normalize(p,uuid4(),NOW)
    assert r is not None
    assert {'namespace':'global','type':'CVE','value':'CVE-2025-32434'} in r.external_ids
    assert r.packages[0]['name']=='torch' and r.packages[0]['ecosystem']=='PyPI'
    assert r.affected_versions[0]['fixed']=='2.6.0' and r.affected_versions[0]['introduced']=='0'
    assert r.fixed_versions[0]['version']=='2.6.0'
    assert r.cvss[0]['score_method']=='computed_from_source_vector'

def test_real_kev_catalog_has_original_pointer():
    p=fixture('cisa_kev'); r=cisa_kev.normalize({'catalog':p,'index':0},uuid4(),NOW)
    assert r is not None
    assert r.external_id==p['vulnerabilities'][0]['cveID']
    assert r.exploitation['known_exploited'] is True
    assert r.exploitation['catalog_complete'] is True
    assert r.field_provenance['record']['json_pointer']=='/vulnerabilities/0'
    assert r.published_at.date().isoformat()==p['vulnerabilities'][0]['dateAdded']

def test_osv_multiple_cves_are_not_collapsed():
    p=fixture('osv'); p['aliases']=['CVE-2025-32434','CVE-2022-45907']
    r=osv.normalize(p,uuid4(),NOW)
    assert r is not None
    assert len([x for x in r.external_ids if x['type']=='CVE'])==2

def test_osv_last_affected_is_not_fixed():
    p=fixture('osv'); p['affected'][0]['ranges'][0]['events']=[{'introduced':'0'},{'last_affected':'2.5.1'}]
    r=osv.normalize(p,uuid4(),NOW)
    assert r is not None
    assert r.affected_versions[0]['fixed'] is None
    assert r.affected_versions[0]['last_affected']=='2.5.1' and not r.fixed_versions

def test_missing_collections_remain_unknown():
    p={'id':'TEST-UNKNOWN','modified':'2026-10-03T00:00:00Z'}
    r=osv.normalize(p,uuid4(),NOW)
    assert r is not None and r.packages is None and r.cvss is None and r.references is None

def test_rejected_cve_without_cna_description_is_retained():
    p=fixture('cve'); p['cveMetadata']['state']='REJECTED'; p['containers']['cna']={'rejectedReasons':[{'lang':'en','value':'duplicate'}]}
    r=cve.normalize(p,uuid4(),NOW)
    assert r is not None and r.record_status=='rejected' and r.description=='duplicate'

def test_future_schema_is_quarantined():
    p=fixture('cve'); p['dataVersion']='6.0'
    with pytest.raises(ValueError): cve.normalize(p,uuid4(),NOW)

def test_invalid_kev_count_is_not_accepted():
    p=fixture('cisa_kev'); p['count']+=1
    with pytest.raises(ValueError): cisa_kev.normalize({'catalog':p,'index':0},uuid4(),NOW)

def test_input_is_not_mutated():
    p=fixture('osv'); before=copy.deepcopy(p)
    r=osv.normalize(p,uuid4(),NOW)
    assert r is not None and p==before

def test_cve_explicit_semver_never_uses_pep440_build_order():
    p=fixture('cve');p['containers']['cna']['affected']=[{'product':'PyTorch','versions':[{'version':'1.0.0+aaa','lessThan':'1.0.0+zzz','status':'affected','versionType':'semver'}]}]
    record=cve.normalize(p,uuid4(),NOW);range=record.affected_versions[0]
    assert range['parse_status']=='unsupported' and range['source_version_type']=='semver'
    assert range['introduced'] is None and range['limit_version'] is None

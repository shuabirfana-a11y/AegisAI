"""Synthetic API/feed contracts; never a benchmark or a live-source claim."""
from datetime import datetime,timezone
from uuid import uuid4
import copy,json
import pytest

NOW=datetime(2026,10,14,tzinfo=timezone.utc)

def ghsa():
    return {'ghsa_id':'GHSA-abcd-efgh-ijkl','cve_id':'CVE-2099-9000001','summary':'Synthetic vLLM advisory',
        'description':'TEST ONLY','published_at':'2026-10-13T00:00:00Z','updated_at':'2026-10-14T00:00:00Z',
        'type':'reviewed','withdrawn_at':None,'repository_advisory_url':'https://api.github.com/repos/vllm-project/vllm/security-advisories/GHSA-abcd-efgh-ijkl',
        'vulnerabilities':[{'package':{'ecosystem':'pip','name':'vllm'},'vulnerable_version_range':'< 0.6.1','first_patched_version':'0.6.1'}],
        'cvss_severities':{'cvss_v3':{'vector_string':'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H','score':9.8}},
        'cwes':[{'cwe_id':'CWE-502','name':'Synthetic'}],'references':['https://github.com/vllm-project/vllm/security/advisories/GHSA-abcd-efgh-ijkl']}

def test_ghsa_native_fields_keep_source_provenance_and_explicit_fix():
    from app.normalizers.ghsa import normalize
    data=ghsa();before=copy.deepcopy(data);raw=uuid4();result=normalize(data,raw,NOW)
    assert data==before and result.source=='GHSA' and result.raw_document_id==raw
    assert {x['value'] for x in result.external_ids}=={'CVE-2099-9000001','GHSA-abcd-efgh-ijkl'}
    assert result.packages[0]['ecosystem']=='PyPI' and result.fixed_versions[0]['version']=='0.6.1'
    assert result.cvss[0]['base_score']==9.8 and result.cwe==['CWE-502']
    assert result.upstream_lineage==['github:vllm-project/vllm']

def test_ghsa_exclusive_boundary_is_not_invented_fix():
    from app.normalizers.ghsa import normalize
    data=ghsa();data['vulnerabilities'][0]['first_patched_version']=None;data['cve_id']=None
    result=normalize(data,uuid4(),NOW)
    assert result.fixed_versions==[] and result.affected_versions[0]['fixed'] is None
    assert result.affected_versions[0]['limit_version']=='0.6.1'
    assert all(x['type']!='CVE' for x in result.external_ids)

def test_native_upper_only_range_is_consumable_by_existing_version_matcher():
    from app.normalizers.ghsa import normalize
    from app.enrichment.versions import contains
    data=ghsa();data['vulnerabilities'][0]['first_patched_version']=None
    result=normalize(data,uuid4(),NOW)
    value={**result.affected_versions[0],'ecosystem':'PyPI'}
    assert contains(value,'0.6.0') is True
    assert contains(value,'0.6.1') is False
    assert result.fixed_versions==[]

@pytest.mark.parametrize('expression',['< 0.6.1, >= 0.5.0','>= 0.5.0, < 0.6.1'])
def test_native_conjunction_order_does_not_change_version_meaning(expression):
    from app.normalizers.ghsa import normalize
    from app.enrichment.versions import contains
    data=ghsa();data['vulnerabilities'][0]['vulnerable_version_range']=expression
    result=normalize(data,uuid4(),NOW)
    value={**result.affected_versions[0],'ecosystem':'PyPI'}
    assert contains(value,'0.5.1') is True and contains(value,'0.4.9') is False

def test_native_patch_expression_is_retained_without_guessing_a_release():
    from app.normalizers.ghsa import normalize
    data=ghsa();data['vulnerabilities'][0]['first_patched_version']='>=0.6.1'
    result=normalize(data,uuid4(),NOW)
    assert result.fixed_versions==[] and result.extensions['original_vulnerabilities'][0]['first_patched_version']=='>=0.6.1'

def test_unpublished_vendor_advisory_is_not_projected_as_public_fact():
    from app.normalizers.ghsa import normalize
    data=ghsa();data['state']='draft'
    with pytest.raises(ValueError):normalize(data,uuid4(),NOW,source='VENDOR_VLLM')

def test_nvd_preserves_metrics_and_does_not_guess_package_or_fix():
    from app.normalizers.nvd import normalize
    data={'id':'CVE-2099-9000002','sourceIdentifier':'nvd@nist.gov','published':'2026-10-13T00:00:00.000',
        'lastModified':'2026-10-14T00:00:00.000','vulnStatus':'Analyzed','descriptions':[{'lang':'en','value':'Synthetic AI component'}],
        'metrics':{'cvssMetricV31':[{'source':'nvd@nist.gov','cvssData':{'version':'3.1','vectorString':'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H','baseScore':9.8,'baseSeverity':'CRITICAL'}}]},
        'weaknesses':[{'description':[{'lang':'en','value':'CWE-502'}]}],
        'references':[{'url':'https://example.invalid/synthetic'}],
        'configurations':[{'nodes':[{'operator':'AND','cpeMatch':[{'vulnerable':True,'criteria':'cpe:2.3:a:test_vendor:test_product:*:*:*:*:*:*:*:*','versionEndExcluding':'1.0'}]}]}]}
    result=normalize(data,uuid4(),NOW)
    assert result.source=='NVD' and result.published_at.tzinfo is not None and result.cvss[0]['version']=='3.1'
    assert result.cwe==['CWE-502'] and result.fixed_versions is None
    assert result.affected_versions is None and result.extensions['configurations']==data['configurations']

@pytest.mark.parametrize('url',['http://127.0.0.1/feed','https://api.github.com/user','https://api.github.com@127.0.0.1/advisories','https://blog.trailofbits.com/private','https://export.arxiv.org/other','https://api.github.com/advisories#secret'])
def test_monitoring_does_not_fetch_unregistered_paths(url):
    from app.monitoring.catalog import validate_url
    with pytest.raises(ValueError):validate_url(url)

def test_rss_text_and_locator_preserve_exact_item_identity():
    from app.monitoring.feeds import parse_feed
    xml=b'<rss version="2.0"><channel><item><guid>test-entry</guid><title>AI security CVE-2099-9000001</title><link>https://blog.trailofbits.com/test-entry/</link><description>&lt;p&gt;Untrusted source text&lt;/p&gt;</description><pubDate>Tue, 13 Oct 2026 00:00:00 GMT</pubDate></item></channel></rss>'
    entry=parse_feed(xml,'RSS_TRAIL_OF_BITS')[0]
    assert entry['external_id']=='test-entry' and entry['document_type']=='blog'
    assert entry['content']=='Untrusted source text' and entry['locator']=={'xml_path':'/rss/channel/item[1]'}
    assert entry['published_at'].tzinfo is not None

def test_arxiv_atom_keeps_paper_metadata_and_no_fabricated_cve():
    from app.monitoring.feeds import parse_feed
    xml=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2601.12345v2</id><title>AI supply chain security</title><summary>Untrusted research abstract.</summary><author><name>A Researcher</name></author><published>2026-01-20T00:00:00Z</published><updated>2026-01-22T00:00:00Z</updated><link rel="alternate" href="https://arxiv.org/abs/2601.12345v2"/></entry></feed>'
    entry=parse_feed(xml,'ARXIV')[0]
    assert entry['document_type']=='paper' and entry['authors']==['A Researcher']
    assert entry['url']=='https://arxiv.org/abs/2601.12345v2' and entry['locator']=={'xml_path':'/feed/entry[1]'}
    assert 'cve_id' not in entry

@pytest.mark.parametrize('xml',[b'<!DOCTYPE a [<!ENTITY secret SYSTEM "file:///C:/secret">]><rss/>',b'<!DOCTYPE a [<!ENTITY x "expand">]><rss/>',b'<rss>broken',b'\xff\xfe<\x00r\x00s\x00s\x00/\x00>\x00'])
def test_untrusted_feed_rejects_dtd_malformed_and_unsupported_encoding(xml):
    from app.monitoring.feeds import parse_feed
    with pytest.raises(ValueError):parse_feed(xml,'RSS_TRAIL_OF_BITS')

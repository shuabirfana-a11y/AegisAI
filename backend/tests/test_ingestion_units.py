from datetime import timezone
import httpx
import gzip
import pytest
from app.core.config import Settings
from app.core.http import HttpClient
from app.utils.time import parse_time
from app.services.products import canonicalize
from app.services.versions import parse_expression, parse_events

def test_settings_environment_and_secret_repr(monkeypatch):
    monkeypatch.setenv('AEGIS_DATABASE_URL','postgresql+psycopg://x:secret@localhost/db')
    monkeypatch.setenv('AEGIS_HTTP_TIMEOUT','7')
    settings=Settings.from_env()
    assert settings.database_url.endswith('/db') if settings.database_url else False
    assert settings.http_timeout==7
    assert 'secret' not in repr(settings)

def test_http_429_uses_retry_after_and_retains_body():
    seen=[]; waits=[]
    def handler(request):
        seen.append(request)
        return httpx.Response(429,headers={'Retry-After':'2'}) if len(seen)==1 else httpx.Response(200,content=b'{"ok":true}')
    client=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(handler),sleep=waits.append)
    response=client.get('https://api.osv.dev/v1/vulns/TEST')
    assert response is not None
    assert response.content==b'{"ok":true}'
    assert len(seen)==2 and len(waits)==1 and 2<=waits[0]<2.11
    assert seen[0].headers['user-agent'].startswith('AegisAI')

def test_http_400_is_not_retried():
    seen=[]
    def handler(request):
        seen.append(request); return httpx.Response(400)
    with pytest.raises(Exception):
        HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(handler),sleep=lambda x:None).get('https://api.osv.dev/v1/vulns/TEST')
    assert len(seen)==1

def test_http_timeout_has_bounded_retry():
    seen=[]
    def handler(request):
        seen.append(request); raise httpx.ReadTimeout('timeout',request=request)
    with pytest.raises(Exception):
        HttpClient(Settings(retries=2,request_interval=0),transport=httpx.MockTransport(handler),sleep=lambda x:None).get('https://api.osv.dev/v1/vulns/TEST')
    assert len(seen)==3

@pytest.mark.parametrize('url',['http://api.osv.dev/v1/test','https://127.0.0.1/private','https://evil.test/feed','https://api.osv.dev.evil.test/feed','https://user:password@api.osv.dev/test'])
def test_http_blocks_unapproved_addresses(url):
    with pytest.raises(ValueError): HttpClient(Settings()).get(url)

def test_http_preserves_non_json_bytes_before_decode():
    r=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=b'broken-json')),sleep=lambda x:None).get('https://api.osv.dev/v1/vulns/TEST')
    assert r is not None and r.content==b'broken-json'
    with pytest.raises(ValueError): r.json()

def test_http_size_is_bounded():
    with pytest.raises(ValueError):
        HttpClient(Settings(max_bytes=3,request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=b'1234')),sleep=lambda x:None).get('https://api.osv.dev/v1/vulns/TEST')

def test_http_gzip_response_is_decoded_once():
    original=b'{"real_entity":"preserved"}'
    transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-encoding':'gzip'},stream=httpx.ByteStream(gzip.compress(original))))
    response=HttpClient(Settings(request_interval=0),transport=transport).get('https://api.osv.dev/v1/vulns/TEST')
    assert response.content==original and response.json()['real_entity']=='preserved'
    assert response.extensions['aegis_original_content_encoding']=='gzip'

def test_http_discovery_prefix_retains_complete_lines_and_marks_partial():
    body=b'first,row\nsecond,row\nthird,row\n'
    response=HttpClient(Settings(request_interval=0),transport=httpx.MockTransport(lambda req:httpx.Response(200,content=body))).get(
        'https://storage.googleapis.com/osv-vulnerabilities/PyPI/modified_id.csv',line_limit=2)
    assert response.content==b'first,row\nsecond,row\n' and response.extensions['aegis_truncated'] is True

@pytest.mark.parametrize('value',['2025-01-01T00:00:00Z','2025-01-01T08:00:00+08:00','2025-01-01'])
def test_time_is_utc_with_source_precision(value):
    t=parse_time(value)
    assert t is not None and t.tzinfo==timezone.utc
    assert t.hour==0

def test_naive_full_timestamp_is_rejected():
    with pytest.raises(ValueError): parse_time('2025-01-01T08:00:00')

def test_unknown_time_stays_null(): assert parse_time(None) is None

@pytest.mark.parametrize('name',['torch','Torch',' TORCH '])
def test_explicit_pypi_alias_is_canonical(name):
    p=canonicalize(name=name,ecosystem='PyPI')
    assert p is not None and p['canonical_name']=='PyTorch' and p['package_name']=='torch'

def test_same_name_different_ecosystem_is_not_merged():
    a=canonicalize(name='torch',ecosystem='PyPI'); b=canonicalize(name='torch',ecosystem='npm')
    assert a is not None and b is not None and a['canonical_key']!=b['canonical_key']

def test_unqualified_triton_is_ambiguous():
    p=canonicalize(name='Triton')
    assert p is not None and p['ecosystem']=='unknown' and not p['registry_match']

@pytest.mark.parametrize('expression,expected',[
    ('< 0.8.4',{'fixed':'0.8.4'}),('<= 0.8.3',{'last_affected':'0.8.3'}),
    ('>= 1.0, < 1.2',{'introduced':'1.0','fixed':'1.2'}),
    ('>=2.0rc1,<2.0',{'introduced':'2.0rc1','fixed':'2.0'}),
    ('==2.0.post1',{'explicit_versions':['2.0.post1']}),
    ('==2.0.dev2+cpu',{'explicit_versions':['2.0.dev2+cpu']})])
def test_pypi_comparators_preserve_boundary_semantics(expression,expected):
    r=parse_expression(expression)
    assert r is not None and r['parse_status']=='parsed' and r['raw_expression']==expression
    for key,value in expected.items(): assert r[key]==value

@pytest.mark.parametrize('expression',['2.x','all builds before blue','>1.0','>=2,<1','~=1.4'])
def test_unknown_versions_remain_unsupported(expression):
    r=parse_expression(expression)
    assert r is not None and r['parse_status']=='unsupported' and r['raw_expression']==expression

def test_osv_zero_sentinel_and_last_affected():
    r=parse_events([{'introduced':'0'},{'last_affected':'1.2'}])
    assert r is not None and r['parse_status']=='parsed' and r['introduced']=='0' and r['fixed'] is None and r['last_affected']=='1.2'

def test_git_range_is_preserved_unsupported():
    r=parse_events([{'introduced':'0'},{'fixed':'a'*40}],range_type='GIT')
    assert r is not None and r['parse_status']=='unsupported' and r['events'][1]['fixed']=='a'*40

def test_inclusive_single_version_interval_is_valid():
    r=parse_expression('>=1.0,<=1.0')
    assert r['parse_status']=='parsed' and r['introduced']=='1.0' and r['last_affected']=='1.0'

def test_semver_event_is_not_interpreted_as_pep440():
    r=parse_events([{'introduced':'1.0.0-alpha'},{'fixed':'1.0.0+build'}],range_type='SEMVER')
    assert r['parse_status']=='unsupported' and r['events'][1]['fixed']=='1.0.0+build'

def test_strict_fixed_boundary_cannot_equal_introduction():
    r=parse_events([{'introduced':'1.0'},{'fixed':'1.0'}])
    assert r['parse_status']=='unsupported'

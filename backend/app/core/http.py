import random,time
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
import httpx
from app.core.config import Settings
from app.core.logging import event

ALLOWED={'api.osv.dev','storage.googleapis.com','raw.githubusercontent.com','api.github.com'}

def validate_url(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in ALLOWED or parsed.username or parsed.password or parsed.port not in (None,443):
        raise ValueError('Unapproved acquisition address')
    if parsed.hostname=='storage.googleapis.com' and not parsed.path.startswith('/osv-vulnerabilities/'):
        raise ValueError('Unapproved dataset bucket')
    if parsed.hostname=='raw.githubusercontent.com' and not parsed.path.startswith(('/CVEProject/cvelistV5/','/cisagov/kev-data/')):
        raise ValueError('Unapproved repository')
    if parsed.hostname=='api.github.com' and not parsed.path.startswith('/repos/CVEProject/cvelistV5/'):
        raise ValueError('Unapproved repository API')

class HttpClient:
    def __init__(self, settings=None, *, transport=None, sleep=None, url_validator=None):
        self.settings=settings or Settings.from_env()
        self.sleep=sleep or time.sleep
        self.url_validator=url_validator or validate_url
        self.client=httpx.Client(timeout=httpx.Timeout(self.settings.http_timeout,connect=min(10,self.settings.http_timeout)),
            headers={'User-Agent':self.settings.user_agent,'Accept-Encoding':'identity'},transport=transport,follow_redirects=False)
        self.last_request=0
        self.request_count=0
        self.duration_ms=0

    def get(self, url, *, headers=None, line_limit=None):
        self.url_validator(url)
        start=time.perf_counter()
        for attempt in range(self.settings.retries+1):
            delay=self.settings.request_interval-(time.monotonic()-self.last_request)
            if delay>0: self.sleep(delay)
            self.last_request=time.monotonic(); self.request_count+=1
            try:
                with self.client.stream('GET',url,headers=headers) as stream:
                    status=stream.status_code
                    if status in (429,500,502,503,504):
                        if attempt==self.settings.retries: stream.raise_for_status()
                        wait=2**(attempt+1)+random.uniform(0,.1)
                        retry_after=stream.headers.get('retry-after')
                        if retry_after:
                            try: wait=max(wait,float(retry_after))
                            except ValueError:
                                try: wait=max(wait,(parsedate_to_datetime(retry_after)-datetime.now(timezone.utc)).total_seconds())
                                except (TypeError,ValueError): pass
                        if wait>60: raise httpx.HTTPStatusError('Rate limit exceeds task wait budget',request=stream.request,response=stream)
                        event('http.retry',status=status,error_type='retryable_status',attempt=attempt+1,backoff_seconds=wait)
                        self.sleep(wait); continue
                    if status!=304: stream.raise_for_status()
                    chunks=[]; size=0;lines=0;truncated=False
                    for chunk in stream.iter_bytes(chunk_size=4096 if line_limit else None):
                        if line_limit:
                            new_lines=chunk.count(b'\n')
                            if lines+new_lines>=line_limit:
                                offset=-1
                                for _ in range(line_limit-lines): offset=chunk.find(b'\n',offset+1)
                                chunk=chunk[:offset+1];truncated=True
                            lines+=new_lines
                        size+=len(chunk)
                        if size>self.settings.max_bytes: raise ValueError('Acquisition response exceeds inline raw limit')
                        chunks.append(chunk)
                        if truncated:break
                    entity_headers=dict(stream.headers)
                    encoding=entity_headers.pop('content-encoding',None)
                    entity_headers.pop('content-length',None)
                    # iter_bytes already applied transport content decoding; never decode entity bytes twice.
                    response=httpx.Response(status,headers=entity_headers,content=b''.join(chunks),request=stream.request,
                        extensions={'aegis_original_content_encoding':encoding,'aegis_truncated':truncated,
                            'aegis_original_content_length':stream.headers.get('content-length')})
                self.duration_ms+=(time.perf_counter()-start)*1000
                return response
            except (httpx.TimeoutException,httpx.NetworkError) as exc:
                if attempt==self.settings.retries: raise
                wait=2**(attempt+1)+random.uniform(0,.1)
                event('http.retry',error_type=type(exc).__name__,attempt=attempt+1,backoff_seconds=wait)
                self.sleep(wait)
        raise RuntimeError('Unreachable HTTP retry state')

    def close(self):
        self.client.close()

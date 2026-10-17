from urllib.parse import urlsplit
from app.enrichment.acquisition import VENDORS

FEEDS={'RSS_TRAIL_OF_BITS':{'url':'https://blog.trailofbits.com/index.xml','type':'blog','name':'Trail of Bits blog','authority':'authoritative','interval':21600},
    'RSS_GOOGLE_SECURITY':{'url':'https://security.googleblog.com/feeds/posts/default?alt=rss','type':'blog','name':'Google Security Blog','authority':'official','interval':21600},
    'ARXIV':{'url':'https://export.arxiv.org/api/query','type':'paper','name':'arXiv AI security metadata','authority':'community','interval':86400}}

def validate_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or p.fragment:raise ValueError('Unapproved monitoring URL')
    if p.hostname=='services.nvd.nist.gov' and p.path=='/rest/json/cves/2.0':return
    if p.hostname=='api.github.com':
        import re
        if p.path=='/advisories' or re.fullmatch(r'/advisories/GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}',p.path):return
        if any(p.path=='/repos/'+repo+'/security-advisories' or re.fullmatch('/repos/'+re.escape(repo)+r'/security-advisories/GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}',p.path) for repo in VENDORS.values()):return
    if any(p.hostname==urlsplit(spec['url']).hostname and p.path==urlsplit(spec['url']).path for spec in FEEDS.values()):return
    raise ValueError('Unregistered monitoring path')

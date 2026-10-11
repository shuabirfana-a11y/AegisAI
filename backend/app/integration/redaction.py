"""Public pointers omit credentials/query tokens; private source hashes stay intact."""
import hashlib
import re
from urllib.parse import urlsplit,urlunsplit

SENSITIVE=frozenset({'authorization','proxyauthorization','apikey','accesstoken','refreshtoken','token',
    'password','passwd','pwd','secret','cookie','setcookie','signature','credential','privatekey','sessionid'})

def credential_key(key):
    normalized=re.sub(r'[^a-z0-9]','',str(key).casefold())
    return normalized in SENSITIVE or normalized.endswith(('apikey','token','secret','password','credential','privatekey','cookie'))

def public_lineage(value):
    # Stable grouping remains available without exporting arbitrary source text.
    return 'sha256:'+hashlib.sha256(value.encode('utf-8')).hexdigest() if value is not None else None
def public_reference(value):
    if isinstance(value,dict):
        return {key:('[REDACTED]' if credential_key(key) else public_reference(item)) for key,item in value.items()}
    if isinstance(value,(list,tuple)):return [public_reference(item) for item in value]
    if isinstance(value,str) and value.strip().casefold().startswith(('https://','http://')):
        try:
            parsed=urlsplit(value.strip());host=parsed.hostname
            if not host:return '[REDACTED_URL]'
            if ':' in host:host='['+host+']'
            netloc=host+(':'+str(parsed.port) if parsed.port else '')
            return urlunsplit((parsed.scheme.casefold(),netloc,parsed.path,'',''))
        except ValueError:return '[REDACTED_URL]'
    return value

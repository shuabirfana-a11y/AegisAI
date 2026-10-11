from pathlib import Path
from functools import lru_cache
import hashlib,json,re
from packageurl import PackageURL
from packaging.utils import canonicalize_name

@lru_cache
def registry():
    return json.loads((Path(__file__).resolve().parents[1]/'resources/ai_products.json').read_text())

def canonicalize(*, name, ecosystem=None, purl=None, vendor=None):
    name=name.strip()
    if not name: raise ValueError('Product name is empty')
    if purl:
        parsed=PackageURL.from_string(purl)
        if parsed.type=='pypi':
            if ecosystem not in (None,'PyPI') or canonicalize_name(name)!=canonicalize_name(parsed.name):
                raise ValueError('PURL/package identity mismatch')
            ecosystem='PyPI'; name=parsed.name
    matched=None
    if ecosystem=='PyPI':
        name=canonicalize_name(name)
        matched=next((x for x in registry()['products'] if name in x['packages']),None)
    elif ecosystem is None:
        matched=next((x for x in registry()['products'] if name.casefold() in x['aliases']),None)
        if matched: ecosystem='PyPI'; name=matched['packages'][0]
    ecosystem=ecosystem or 'unknown'
    identity='|'.join([ecosystem,name if ecosystem!='unknown' else name.casefold(),vendor or '' if ecosystem=='unknown' else ''])
    key='ai:'+matched['key'] if matched else 'product:'+hashlib.sha256(identity.encode()).hexdigest()
    package_purl=str(PackageURL(type='pypi',name=name)) if ecosystem=='PyPI' else str(PackageURL(type='generic',namespace=ecosystem.lower(),name=name))
    return {'canonical_key':key,'canonical_name':matched['name'] if matched else name,
            'ecosystem':ecosystem,'package_name':name,'purl':package_purl,'vendor':vendor,
            'registry_match':bool(matched),'registry_version':registry()['version']}

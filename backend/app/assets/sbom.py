"""Offline official-schema validation. No user URL or filename is opened or fetched."""
import json,time,hashlib
from pathlib import Path
from functools import lru_cache
from jsonschema import Draft7Validator
from referencing import Registry,Resource
from app.assets.contracts import CONTENT_TRUST
MAX_BYTES=2*1024*1024
MAX_DEPTH=40
MAX_COMPONENTS=1000
MAX_SECONDS=5
SCHEMAS=Path(__file__).resolve().parents[1]/'resources/sbom'

def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('SBOM duplicate JSON key')
        result[key]=value
    return result

def _reject_remote(uri):raise ValueError('Remote schema references are disabled')

@lru_cache
def validator(kind):
    names=['bom-1.6.schema.json','jsf-0.82.schema.json','spdx.schema.cdx.json','spdx.schema.json']
    registry=Registry(retrieve=_reject_remote);documents={}
    for name in names:
        doc=json.loads((SCHEMAS/name).read_text(encoding='utf-8'));documents[name]=doc
        if doc.get('$id'):registry=registry.with_resource(doc['$id'],Resource.from_contents(doc))
        if name=='spdx.schema.cdx.json':registry=registry.with_resource('http://cyclonedx.org/schema/spdx.schema.json',Resource.from_contents(doc))
    return Draft7Validator(documents['bom-1.6.schema.json' if kind=='CycloneDX' else 'spdx.schema.json'],registry=registry)

def parse_sbom(payload):
    started=time.monotonic()
    if not isinstance(payload,bytes) or len(payload)>MAX_BYTES:raise ValueError('SBOM size exceeds 2MiB')
    try:doc=json.loads(payload.decode('utf-8-sig'),object_pairs_hook=_pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('SBOM nonfinite JSON number')))
    except (UnicodeError,json.JSONDecodeError,RecursionError) as exc:raise ValueError('SBOM malformed JSON') from exc
    stack=[(doc,0)];nodes=0
    while stack:
        item,depth=stack.pop();nodes+=1
        if depth>MAX_DEPTH or nodes>100000 or time.monotonic()-started>MAX_SECONDS:raise ValueError('SBOM complexity/time limit exceeded')
        if isinstance(item,dict):stack.extend((v,depth+1) for v in item.values())
        elif isinstance(item,list):stack.extend((v,depth+1) for v in item)
    if not isinstance(doc,dict):raise ValueError('SBOM root must be an object')
    if doc.get('bomFormat')=='CycloneDX' and doc.get('specVersion')=='1.6':kind='CycloneDX'
    elif doc.get('spdxVersion')=='SPDX-2.3':kind='SPDX'
    else:raise ValueError('Supported schemas: CycloneDX1.6 JSON / SPDX2.3 JSON')
    for error in validator(kind).iter_errors(doc):
        raise ValueError('SBOM schema violation at '+('/'.join(map(str,error.path)) or 'root'))
    if time.monotonic()-started>MAX_SECONDS:raise ValueError('SBOM parse time limit exceeded')
    entries=[]
    if kind=='CycloneDX':
        pending=[(x,'/components/'+str(i)) for i,x in enumerate(doc.get('components',[]))]
        # Root metadata component is included only when it is a package, not an environment label.
        root=(doc.get('metadata') or {}).get('component')
        if root and root.get('purl'):pending.append((root,'/metadata/component'))
        elif root:pending.extend((child,'/metadata/component/components/'+str(i)) for i,child in enumerate(root.get('components',[])))
        while pending:
            x,path=pending.pop(0)
            pending.extend((child,path+'/components/'+str(i)) for i,child in enumerate(x.get('components',[])))
            entries.append({'name':x['name'],'version':x.get('version'),'purl':x.get('purl'),'source_ref':x.get('bom-ref'),'locator':path})
            if len(entries)>MAX_COMPONENTS:raise ValueError('SBOM component limit exceeded')
    else:
        for i,x in enumerate(doc.get('packages',[])):
            purls=[r['referenceLocator'] for r in x.get('externalRefs',[]) if r.get('referenceType')=='purl' and r.get('referenceCategory')=='PACKAGE-MANAGER']
            if len(set(purls))>1:raise ValueError('SPDX ambiguous package PURL')
            entries.append({'name':x['name'],'version':x.get('versionInfo'),'purl':purls[0] if purls else None,'source_ref':x['SPDXID'],'locator':'/packages/'+str(i)})
    if len(entries)>MAX_COMPONENTS:raise ValueError('SBOM component limit exceeded')
    seen={};dedup=[]
    for e in entries:
        key=e['source_ref'] or json.dumps([e['purl'],e['name'],e['version']],sort_keys=True)
        signature=(e['name'],e['version'],e['purl'])
        if key in seen:
            if seen[key]!=signature:raise ValueError('SBOM conflicting duplicate component reference')
            continue
        seen[key]=signature;dedup.append(e)
    return {'format':kind,'schema_version':doc.get('specVersion') or doc['spdxVersion'],'sha256':hashlib.sha256(payload).hexdigest(),
        'components':dedup,'document':doc,'duration_ms':(time.monotonic()-started)*1000,'content_trust_level':CONTENT_TRUST}

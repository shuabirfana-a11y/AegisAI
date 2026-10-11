"""Only explicit structured vendor fields and references become assertions."""
import re
from packaging.version import Version,InvalidVersion
from app.services.versions import parse_expression

OFFICIAL_REPOS={'torch':'pytorch/pytorch','vllm':'vllm-project/vllm','mlflow':'mlflow/mlflow'}

def parse_advisory(payload,repo,target,aliases):
    cve=payload.get('cve_id');ghsa=payload.get('ghsa_id')
    matched=(cve==target or ghsa in aliases) and (not cve or cve==target)
    if not matched or payload.get('state','published')!='published' or payload.get('withdrawn_at'):
        return {'association':'UNRESOLVED','claims':[],'references':[],'reason':'Identifier, publication or withdrawal mismatch'}
    claims=[{'type':'VENDOR_CONFIRMED','value':{'repository':repo,'advisory_id':ghsa,'cve':target},'scope':'vendor:'+repo,'locator':'/cve_id'}]
    for index,item in enumerate(payload.get('vulnerabilities') or []):
        package=item.get('package') or {};name=package.get('name');eco={'pip':'PyPI','pypi':'PyPI'}.get(package.get('ecosystem'),package.get('ecosystem'))
        if not name:continue
        scope=str(eco)+':'+name.casefold();base=f'/vulnerabilities/{index}'
        claims.append({'type':'AFFECTS_PRODUCT','value':{'package':name,'ecosystem':eco},'scope':scope,'locator':base+'/package'})
        expression=item.get('vulnerable_version_range')
        if expression:
            parsed=parse_expression(expression,eco)
            claims.append({'type':'AFFECTS_VERSION','value':{'package':name,'ecosystem':eco,'range':expression,'parse_status':parsed['parse_status']},'scope':scope,'locator':base+'/vulnerable_version_range'})
        fixed=item.get('patched_versions') or (item.get('first_patched_version') or {}).get('identifier')
        if fixed:
            try:normalized=str(Version(fixed)) if eco=='PyPI' else None
            except (InvalidVersion,TypeError):normalized=None
            claims.append({'type':'FIXED_VERSION','value':{'package':name,'ecosystem':eco,'version':normalized,'raw_expression':fixed},'scope':scope,
                'locator':base+('/patched_versions' if item.get('patched_versions') else '/first_patched_version/identifier')})
    text=payload.get('description') or ''
    refs=list(dict.fromkeys([x['url'] if isinstance(x,dict) else x for x in payload.get('references') or []]+re.findall(r'https://github\.com/[A-Za-z0-9_.\-/]+',text)))
    return {'association':'MATCHED','claims':claims,'references':refs,'published_at':payload.get('published_at'),'modified_at':payload.get('updated_at')}

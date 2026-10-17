"""Native GitHub assertions; source bounds never invent a fixed release."""
import re
from packaging.version import Version,InvalidVersion
from urllib.parse import urlsplit
from app.schemas.intelligence import NormalizedIntelligenceRecord
from app.normalizers.common import external,metric,CVE_RE
from app.services.versions import parse_expression
from app.utils.time import parse_time

VERSION='ghsa-normalizer-v1'
ID=re.compile(r'GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}')

def normalize(payload,raw_document_id,retrieved_at,*,source='GHSA'):
    if payload.get('state') not in (None,'published','withdrawn'):raise ValueError('Unpublished advisory is not public intelligence')
    identifier=payload.get('ghsa_id')
    if not isinstance(identifier,str) or not ID.fullmatch(identifier):raise ValueError('Invalid advisory identity')
    cve=payload.get('cve_id')
    if cve is not None and (not isinstance(cve,str) or not CVE_RE.fullmatch(cve)):raise ValueError('Invalid CVE alias')
    products=[];packages=[];ranges=[];fixed=[];scores=[]
    for i,item in enumerate(payload.get('vulnerabilities') or []):
        native=item.get('package') or {};name=native.get('name');eco={'pip':'PyPI','pypi':'PyPI'}.get(native.get('ecosystem'),native.get('ecosystem') or 'unknown')
        if not name:continue
        package={'name':name,'ecosystem':eco};base=f'/vulnerabilities/{i}'
        products.append({**package,'locator':base+'/package'});packages.append({**package,'locator':base+'/package'})
        patched=item.get('patched_versions') or item.get('first_patched_version')
        if isinstance(patched,dict):patched=patched.get('identifier')
        if patched and eco=='PyPI':
            try:patched=str(Version(patched))
            except (InvalidVersion,TypeError):patched=None
        if patched:
            fixed.append({'package':package,'version':patched,'locator':base+('/patched_versions' if item.get('patched_versions') else '/first_patched_version')})
        expression=item.get('vulnerable_version_range')
        if expression:
            parsed=parse_expression(expression,eco)
            # '< x' proves exclusion at x, not release/fix existence.
            if parsed.get('fixed') and parsed['fixed']!=patched:
                parsed['limit_version']=parsed['fixed'];parsed['fixed']=None
                parsed['events']=[{'limit':x['fixed']} if 'fixed' in x else x for x in parsed.get('events') or []]
            # Native comma bounds are a conjunction, not ordered OSV events.
            # introduced=0 expresses an unbounded lower end without a release guess.
            if parsed.get('parse_status')=='parsed' and not parsed.get('explicit_versions'):
                events=[{'introduced':parsed.get('introduced') or '0'}]
                for name in ('fixed','last_affected','limit_version'):
                    if parsed.get(name):events.append({'limit' if name=='limit_version' else name:parsed[name]});break
                parsed['events']=events
            parsed.update(package=package,locator=base+'/vulnerable_version_range',source_version_type='github_native_range')
            ranges.append(parsed)
    native_scores=payload.get('cvss_severities') or {}
    for key,version in [('cvss_v3','3.1'),('cvss_v4','4.0')]:
        item=native_scores.get(key)
        if item and item.get('vector_string'):
            if item.get('score') is not None and not 0<=float(item['score'])<=10:raise ValueError('Invalid CVSS score')
            scores.append(metric(item['vector_string'],provider=source,locator='/cvss_severities/'+key,explicit_score=item.get('score'),version=version))
    if not scores and (payload.get('cvss') or {}).get('vector_string'):
        item=payload['cvss']
        if item.get('score') is not None and not 0<=float(item['score'])<=10:raise ValueError('Invalid CVSS score')
        scores.append(metric(item['vector_string'],provider=source,locator='/cvss',explicit_score=item.get('score')))
    refs=[{'url':x.get('url') if isinstance(x,dict) else x,'type':'reference','locator':f'/references/{i}'} for i,x in enumerate(payload.get('references') or [])]
    repo=payload.get('repository_advisory_url') or payload.get('source_code_location') or ''
    parsed=urlsplit(repo);parts=parsed.path.strip('/').split('/')
    if parsed.hostname=='api.github.com' and len(parts)>=3 and parts[0]=='repos':lineage='github:'+('/'.join(parts[1:3])).casefold()
    elif parsed.hostname=='github.com' and len(parts)>=2:lineage='github:'+('/'.join(parts[:2])).casefold()
    else:lineage='github:advisory-database'
    return NormalizedIntelligenceRecord(source=source,external_id=identifier,external_ids=[external(identifier)]+([external(cve)] if cve else []),
        raw_document_id=raw_document_id,retrieved_at=retrieved_at,published_at=parse_time(payload.get('published_at')),modified_at=parse_time(payload.get('updated_at')),
        title=payload.get('summary'),description=payload.get('description'),record_status='withdrawn' if payload.get('withdrawn_at') else 'published',
        products=products,packages=packages,affected_versions=ranges,fixed_versions=fixed,cvss=scores or None,
        cwe=[x['cwe_id'] for x in payload.get('cwes') or [] if re.fullmatch(r'CWE-\d+',x.get('cwe_id',''))],references=refs,
        upstream_lineage=[lineage],field_provenance={k:{'json_pointer':'/'+k} for k in payload},extensions={'original_vulnerabilities':payload.get('vulnerabilities'),'repository_advisory_url':repo,'withdrawn_at':payload.get('withdrawn_at')})

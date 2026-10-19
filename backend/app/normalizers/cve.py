import json,re
from app.schemas.intelligence import NormalizedIntelligenceRecord
from app.utils.time import parse_time
from app.normalizers.common import external,metric,CVE_RE
from app.services.products import canonicalize
from app.services.versions import blank,parse_expression

VERSION='cve-normalizer-v0.3-inline-range'

def normalize(payload, raw_document_id, retrieved_at):
    if not str(payload['dataVersion']).startswith('5.'): raise ValueError('Unsupported CVE schema major')
    metadata=payload['cveMetadata']; id=metadata['cveId']
    if not CVE_RE.fullmatch(id): raise ValueError('Invalid CVE identity')
    cna=payload['containers']['cna']; containers=[('cna',cna)]+[(f'adp/{i}',x) for i,x in enumerate(payload['containers'].get('adp',[]))]
    descriptions=cna.get('descriptions',cna.get('rejectedReasons',[]))
    chosen=next((x for x in descriptions if x.get('lang','').startswith('en')),descriptions[0] if descriptions else {})
    products=[] if 'affected' in cna else None; packages=[] if 'affected' in cna else None
    ranges=[] if 'affected' in cna else None; fixed=[] if 'affected' in cna else None
    metrics=[]; references=[]; cwe=[]; lineage=[]
    for container_key,container in containers:
        provider=container.get('providerMetadata',{}).get('shortName',metadata.get('assignerShortName','CVE CNA'))
        lineage.append('cve-provider:'+provider)
        base='/containers/'+container_key
        for i,reference in enumerate(container.get('references',[])):
            references.append({**reference,'type':'reference','provider':provider,'locator':base+f'/references/{i}'})
        for i,entry in enumerate(container.get('metrics',[])):
            for key,version in [('cvssV2_0','2.0'),('cvssV3_0','3.0'),('cvssV3_1','3.1'),('cvssV4_0','4.0')]:
                if key in entry:
                    value=entry[key]
                    metrics.append(metric(value.get('vectorString',''),provider=provider,locator=base+f'/metrics/{i}/{key}',explicit_score=value.get('baseScore'),version=version,severity=value.get('baseSeverity')))
        for problem in container.get('problemTypes',[]):
            for desc in problem.get('descriptions',[]):
                if re.fullmatch(r'CWE-\d+',desc.get('cweId','')): cwe.append(desc['cweId'])
    for i,affected in enumerate(cna.get('affected',[])):
        name=affected.get('packageName') or affected.get('product')
        if not name: continue
        pointer=f'/containers/cna/affected/{i}'
        product={'name':name,'vendor':affected.get('vendor'),'locator':pointer,'cpes':affected.get('cpes')}
        products.append(product)
        qualified=canonicalize(name=name,purl=affected.get('packageURL'),vendor=affected.get('vendor'))
        package={'name':qualified['package_name'],'ecosystem':qualified['ecosystem'],'purl':qualified['purl'],'vendor':affected.get('vendor')}
        packages.append({**package,'locator':pointer})
        for j,version in enumerate(affected.get('versions',[])):
            if version.get('status')!='affected': continue
            original=json.dumps(version,ensure_ascii=False,separators=(',',':'))
            start=version.get('version'); upper=version.get('lessThan'); inclusive=version.get('lessThanOrEqual')
            expression=(('>='+start+',') if start and start not in ('0','*') and (upper or inclusive) else '')+(('<'+upper) if upper else ('<='+inclusive) if inclusive else '=='+str(start))
            # Some CNA records put an explicit constraint in `version` itself.
            # Preserve it for the existing parser instead of inventing '==<x'.
            inline=bool(not (upper or inclusive) and isinstance(start,str)
                and re.match(r'^\s*(?:>=|<=|==|<)',start))
            if inline:expression=start.strip()
            supported_type=version.get('versionType') in (None,'python','pep440','pep-440')
            parsed=parse_expression(expression,qualified['ecosystem']) if supported_type and not version.get('changes') else blank(original,range_type='ECOSYSTEM')
            if not supported_type:parsed['parse_reason']='Explicit source versionType is unsupported: '+str(version.get('versionType'))
            parsed.update({'raw_expression':original,'package':package,'locator':pointer+f'/versions/{j}','source_version_type':version.get('versionType'),'source_status':version.get('status')})
            if parsed['parse_status']=='parsed' and (upper or inclusive) and start=='0': parsed['introduced']='0'
            if inline and parsed['parse_status']=='parsed' and not parsed.get('explicit_versions'):
                # A conjunction is not an event log: make its lower bound
                # explicit so the unchanged event consumer can read '< x'.
                parsed['events']=[{'introduced':parsed.get('introduced') or '0'}]
                for bound in ('fixed','last_affected'):
                    if parsed.get(bound):parsed['events'].append({bound:parsed[bound]});break
            # A CNA lessThan bound states affected membership; it does not itself prove a fixed release.
            if parsed.get('fixed'):
                parsed['limit_version']=parsed['fixed']; parsed['fixed']=None
                parsed['events']=[{'limit':e['fixed']} if 'fixed' in e else e for e in parsed.get('events') or []]
            ranges.append(parsed)
            if parsed.get('fixed'): fixed.append({'package':package,'version':parsed['fixed'],'locator':parsed['locator'],'basis':'explicit affected boundary; candidate until later verification'})
    status={'PUBLISHED':'published','REJECTED':'rejected'}.get(metadata.get('state'),'unknown')
    return NormalizedIntelligenceRecord(source='CVE_LIST',external_id=id,external_ids=[external(id)],raw_document_id=raw_document_id,
        retrieved_at=retrieved_at,published_at=parse_time(metadata.get('datePublished')),modified_at=parse_time(metadata.get('dateUpdated')),
        title=cna.get('title'),description=chosen.get('value'),language=chosen.get('lang'),record_status=status,
        products=products,packages=packages,affected_versions=ranges,fixed_versions=fixed,cvss=metrics or None,cwe=list(dict.fromkeys(cwe)) or None,
        references=references if any('references' in c for _,c in containers) else None,upstream_lineage=lineage,
        field_provenance={key:{'json_pointer':'/containers/cna/'+key} for key in cna},
        extensions={'cveMetadata':metadata,'containers':payload['containers'],'dataVersion':payload['dataVersion']})

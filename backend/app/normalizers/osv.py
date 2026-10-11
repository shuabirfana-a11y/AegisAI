from app.schemas.intelligence import NormalizedIntelligenceRecord
from app.utils.time import parse_time
from app.normalizers.common import external,metric
from app.services.versions import parse_events

VERSION='osv-normalizer-v0.1'

def normalize(payload, raw_document_id, retrieved_at):
    id=payload['id']; modified=parse_time(payload['modified'])
    if not id or not isinstance(id,str): raise ValueError('Invalid OSV identity')
    if not str(payload.get('schema_version','1.0')).startswith('1.'): raise ValueError('Unsupported OSV schema major')
    products=None if 'affected' not in payload else []; packages=None if 'affected' not in payload else []
    ranges=None if 'affected' not in payload else []; fixed=None if 'affected' not in payload else []
    cvss=None if 'severity' not in payload else []
    upstream=[]; provenance={}
    for i,affected in enumerate(payload.get('affected',[])):
        package=affected['package']; pointer=f'/affected/{i}'
        packages.append({**package,'locator':pointer+'/package'})
        products.append({'name':package['name'],'ecosystem':package['ecosystem'],'locator':pointer+'/package'})
        upstream_source=affected.get('database_specific',{}).get('source')
        if upstream_source: upstream.append(upstream_source)
        native_ranges=affected.get('ranges',[])
        if not native_ranges and affected.get('versions'): native_ranges=[{'type':'ECOSYSTEM','events':[]}]
        for j,native in enumerate(native_ranges):
            item=parse_events(native.get('events',[]),package['ecosystem'],native['type'],affected.get('versions'))
            item.update({'package':package,'locator':pointer+f'/ranges/{j}','repo':native.get('repo')})
            ranges.append(item)
            if item['parse_status']=='parsed':
                for event in native.get('events',[]):
                    if 'fixed' in event: fixed.append({'package':package,'version':event['fixed'],'locator':item['locator']})
        for j,severity in enumerate(affected.get('severity',[])):
            if cvss is None: cvss=[]
            if severity.get('type','').startswith('CVSS_'): cvss.append(metric(severity['score'],provider=upstream_source or 'OSV',locator=pointer+f'/severity/{j}'))
    for i,severity in enumerate(payload.get('severity',[])):
        if severity.get('type','').startswith('CVSS_'): cvss.append(metric(severity['score'],provider=upstream[0] if upstream else 'OSV',locator=f'/severity/{i}'))
    identifiers=list(dict.fromkeys([id,*payload.get('aliases',[])]))
    references=None if 'references' not in payload else [{**x,'locator':f'/references/{i}'} for i,x in enumerate(payload['references'])]
    provenance={key:{'json_pointer':'/'+key} for key in payload}
    return NormalizedIntelligenceRecord(source='OSV',external_id=id,external_ids=[external(x) for x in identifiers],
        raw_document_id=raw_document_id,retrieved_at=retrieved_at,published_at=parse_time(payload.get('published')),modified_at=modified,
        title=payload.get('summary'),description=payload.get('details'),record_status='withdrawn' if payload.get('withdrawn') else 'published',
        products=products,packages=packages,affected_versions=ranges,fixed_versions=fixed,cvss=cvss,
        cwe=payload.get('database_specific',{}).get('cwe_ids'),references=references,upstream_lineage=upstream,
        field_provenance=provenance,extensions={'withdrawn':payload.get('withdrawn'),'database_specific':payload.get('database_specific'),'schema_version':payload.get('schema_version'),'original_affected':payload.get('affected'),'upstream':payload.get('upstream'),'unknown_fields':{k:v for k,v in payload.items() if k not in ('id','modified','published','aliases','summary','details','affected','severity','references','database_specific','withdrawn','schema_version','upstream')}})

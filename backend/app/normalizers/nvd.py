"""NVD metrics and identity, retaining environmental CPE logic without flattening."""
import re
from app.schemas.intelligence import NormalizedIntelligenceRecord
from app.normalizers.common import external,metric,CVE_RE
from app.utils.time import parse_time

VERSION='nvd-normalizer-v1'

def timestamp(value):
    if value and not re.search(r'Z$|[+-]\d\d:\d\d$',value):value+='Z'
    return parse_time(value)

def normalize(payload,raw_document_id,retrieved_at):
    identifier=payload.get('id')
    if not isinstance(identifier,str) or not CVE_RE.fullmatch(identifier):raise ValueError('Invalid NVD CVE identity')
    descriptions=payload.get('descriptions') or [];description=next((x.get('value') for x in descriptions if x.get('lang')=='en'),None)
    scores=[]
    for key in ('cvssMetricV2','cvssMetricV30','cvssMetricV31','cvssMetricV40'):
        for i,item in enumerate((payload.get('metrics') or {}).get(key,[])):
            value=item['cvssData'];score=value.get('baseScore')
            if score is not None and not 0<=float(score)<=10:raise ValueError('Invalid CVSS score')
            scores.append(metric(value.get('vectorString',''),provider=item.get('source','NVD'),locator=f'/metrics/{key}/{i}/cvssData',
                explicit_score=score,version=value.get('version'),severity=value.get('baseSeverity') or item.get('baseSeverity')))
    weaknesses=list(dict.fromkeys(x['value'] for w in payload.get('weaknesses') or [] for x in w.get('description') or [] if re.fullmatch(r'CWE-\d+',x.get('value',''))))
    return NormalizedIntelligenceRecord(source='NVD',external_id=identifier,external_ids=[external(identifier)],raw_document_id=raw_document_id,retrieved_at=retrieved_at,
        published_at=timestamp(payload.get('published')),modified_at=timestamp(payload.get('lastModified')),title=identifier,description=description,
        record_status='rejected' if str(payload.get('vulnStatus','')).casefold()=='rejected' else 'published',
        cvss=scores or None,cwe=weaknesses or None,references=[{**x,'type':'reference','locator':f'/references/{i}'} for i,x in enumerate(payload.get('references') or [])],
        field_provenance={k:{'json_pointer':'/'+k} for k in payload},upstream_lineage=['nvd:'+payload.get('sourceIdentifier','unknown')],
        extensions={'configurations':payload.get('configurations'),'vulnStatus':payload.get('vulnStatus'),'version_scope':'CPE environment predicates retained; package/fixed version not inferred'})

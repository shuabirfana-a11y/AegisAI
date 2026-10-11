from datetime import date
from app.schemas.intelligence import NormalizedIntelligenceRecord
from app.utils.time import parse_time
from app.normalizers.common import external,CVE_RE

VERSION='kev-normalizer-v0.1'

def validate_catalog(catalog):
    entries=catalog['vulnerabilities']
    if catalog['count']!=len(entries): raise ValueError('KEV catalog count mismatch')
    ids=[x['cveID'] for x in entries]
    if len(set(ids))!=len(ids) or any(not CVE_RE.fullmatch(x) for x in ids): raise ValueError('KEV duplicate/invalid identities')
    parse_time(catalog['dateReleased'])
    if not catalog.get('catalogVersion'): raise ValueError('KEV catalog version absent')
    return entries

def normalize(payload, raw_document_id, retrieved_at):
    catalog=payload['catalog']; entries=validate_catalog(catalog); index=payload['index']; item=entries[index]
    pointer='/vulnerabilities/'+str(index)
    return NormalizedIntelligenceRecord(source='CISA_KEV',external_id=item['cveID'],external_ids=[external(item['cveID'])],
        raw_document_id=raw_document_id,retrieved_at=retrieved_at,published_at=parse_time(item.get('dateAdded')),
        modified_at=None,title=item.get('vulnerabilityName'),description=item.get('shortDescription'),record_status='published',
        products=[{'name':item['product'],'vendor':item.get('vendorProject'),'locator':pointer+'/product'}],
        cwe=item.get('cwes'),references=[{'url':x,'type':'reference','locator':pointer+'/notes'} for x in item.get('notes','').split('; ') if x.startswith('https://')],
        exploitation={'known_exploited':True,'catalog_status':'listed','catalog_complete':True,'catalog_version':catalog['catalogVersion'],
                      'date_added':item.get('dateAdded'),'due_date':item.get('dueDate'),'required_action':item.get('requiredAction')},
        upstream_lineage=['CISA KEV'],field_provenance={'record':{'json_pointer':pointer}},
        extensions={'original_item':item,'catalogVersion':catalog['catalogVersion'],'dateReleased':catalog['dateReleased']})

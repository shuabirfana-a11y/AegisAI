from pathlib import Path
import json
from app.db import models as m
from app.repositories.ingestion import unique_row

def source_registry(session,key):
    entries=json.loads((Path(__file__).resolve().parents[1]/'resources/sources.json').read_text(encoding='utf-8'))
    spec=next((x for x in entries if x['source_id']==key),None)
    is_native=spec is None
    if spec is None:
        native=json.loads((Path(__file__).resolve().parents[1]/'monitoring/native_sources.json').read_text(encoding='utf-8'))
        spec=next((x for x in native if x['source_id']==key),None)
    if spec is None: raise ValueError('Source not in frozen first batch')
    values={'name':spec['name'],'source_type':spec['source_type'],
        'category':spec['category'],'authority_level':spec.get('authority_class','official'),'authority_scope':spec['authority_level'],
        'acquisition_method':spec.get('implementation_method') or ('git' if key=='CVE_LIST' else 'api_dataset' if key=='OSV' else 'json_feed'),
        'base_url':spec['base_url'],'license_scope':spec['license'],'update_interval':spec['update_interval']}
    source=unique_row(session,m.Source,{'source_key':key},values)
    if is_native:
        # Adapter-owned metadata only. Preserve original catalogs, sync cursors,
        # captured content, operator enabled state and all verification results.
        for name,value in values.items():setattr(source,name,value)
    return source

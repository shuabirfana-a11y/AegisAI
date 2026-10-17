"""Bounded structured source facts; no inference, trust decision or tool side effect."""
import json
from hashlib import sha256
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from app.db import models as m
from app.enrichment.acquisition import VENDORS
from app.enrichment.repository import ClaimStore
from app.enrichment.evidence import EvidenceService

FACT_TYPES = frozenset({'CWE', 'SOURCE_FACT'})

class CWEValue(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    cwe: str = Field(pattern=r'^CWE-[1-9][0-9]*$', max_length=30)

class SourceFactValue(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    field: Literal['summary']
    text: str = Field(min_length=1, max_length=2000)

def fact_value(kind, value):
    return (CWEValue if kind=='CWE' else SourceFactValue).model_validate(value).model_dump()

def extract_source_facts(payload, target, aliases):
    """OSV/GHSA/vendor structured identifiers only; contradictory CVE rejects all."""
    if not isinstance(payload,dict):return []
    prefix='/record' if isinstance(payload.get('record'),dict) else ''
    record=payload['record'] if prefix else payload
    ids={x for x in (record.get('id'),record.get('cve_id'),record.get('ghsa_id')) if isinstance(x,str)}
    ids.update(x for x in record.get('aliases',[]) if isinstance(x,str))
    ids.update(x['value'] for x in record.get('identifiers',[]) if isinstance(x,dict) and isinstance(x.get('value'),str))
    cves={x for x in ids if x.startswith('CVE-')}
    if (target not in ids and not ids.intersection(aliases)) or (cves and cves!={target}):return []
    if record.get('withdrawn') or record.get('withdrawn_at') or record.get('state','published')!='published':return []
    out=[]
    text=record.get('summary')
    if isinstance(text,str) and text.strip() and len(text)<=2000 and len(json.dumps(text,ensure_ascii=False))<=2400:
        out.append({'type':'SOURCE_FACT','scope':'source-fact:summary',
            'value':{'field':'summary','text':text},'locator':prefix+'/summary'})
    groups=[(record.get('cwes',[]),prefix+'/cwes'),
        ((record.get('database_specific') or {}).get('cwe_ids',[]),prefix+'/database_specific/cwe_ids')]
    for values,base in groups:
        if not isinstance(values,list):continue
        for index,item in enumerate(values[:32]):
            value=item.get('cwe_id') if isinstance(item,dict) else item
            try:data=CWEValue(cwe=value).model_dump()
            except (ValueError,TypeError):continue
            out.append({'type':'CWE','scope':'cwe:'+data['cwe'],'value':data,
                'locator':base+'/'+str(index)+('/cwe_id' if isinstance(item,dict) else '')})
    return out

def persist_source_facts(session,ctx,observation):
    """Create real pending Claims/Evidence in an ingestion transaction. Idempotent."""
    raw=session.get(m.RawDocument,observation.raw_document_id)
    source=session.get(m.Source,observation.source_id)
    if (not raw or not source or raw.source_id!=source.id or observation.parse_status!='parsed' or
        source.source_key not in {'OSV','GITHUB_ADVISORY_SNAPSHOT',*VENDORS} or
        sha256(raw.raw_payload).hexdigest()!=raw.content_hash):return [],[]
    latest=session.scalar(select(m.SourceObservation.id).where(m.SourceObservation.source_id==source.id,
        m.SourceObservation.external_id==observation.external_id,m.SourceObservation.parse_status=='parsed')
        .order_by(m.SourceObservation.retrieved_at.desc(),m.SourceObservation.created_at.desc(),m.SourceObservation.id.desc()).limit(1))
    if latest!=observation.id:return [],[]
    try:items=extract_source_facts(json.loads(raw.raw_payload),ctx.canonical_id,ctx.aliases)
    except (ValueError,TypeError,UnicodeError):return [],[]
    claims=[];evidence=[]
    for item in items:
        value=fact_value(item['type'],item['value'])
        c=ClaimStore.add(session,ctx.target_id,item['type'],item['scope'],value,
            details={'fact_contract':'source-fact-v1','inference':False})
        e=EvidenceService.add(session,c,observation,value,{'json_pointer':item['locator']},
            evidence_type='official_vendor_advisory' if source.source_key in VENDORS else 'structured_source',
            details={'fact_contract':'source-fact-v1','inference':False})
        claims.append(c.id);evidence.append(e.id)
    return claims,evidence

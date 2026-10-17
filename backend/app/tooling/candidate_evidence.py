"""Exact, target-bound references in collected immutable sources. Never fetches a URL."""
import json
from hashlib import sha256
from uuid import UUID
from app.db import models as m
from app.repositories.queries import vulnerability_detail
from app.enrichment import queries as intel
from app.enrichment.rules import classify_patch
from app.enrichment.evidence import pointer
from app.tooling.candidate_reference import validate_candidate_reference

def occurrences(payload,url,path='',depth=0):
    if depth>12:return []
    if isinstance(payload,str):return [path] if payload==url else []
    found=[]
    iterable=payload.items() if isinstance(payload,dict) else enumerate(payload) if isinstance(payload,list) else ()
    for key,value in iterable:
        key=str(key).replace('~','~0').replace('/','~1')
        found.extend(occurrences(value,url,path+'/'+key,depth+1))
        if len(found)>=32:break
    return found[:32]

def candidate_evidence(session,target,url,refs,*,claim_id=None,limit=20):
    validate_candidate_reference(url)
    detail=vulnerability_detail(session,str(target));documents=detail['source_documents']
    aliases={detail['canonical_id']}|{r['normalized_value'] for r in detail['external_identifiers']}
    original=[];raw_ids=set()
    for row in documents:
        raw=session.get(m.RawDocument,UUID(str(row['id'])))
        if raw is None or sha256(raw.raw_payload).hexdigest()!=raw.content_hash:continue
        prefix=(row.get('locator') or {}).get('json_pointer')
        if not isinstance(prefix,str):continue
        try:payload=pointer(json.loads(raw.raw_payload),prefix)
        except (ValueError,UnicodeError,KeyError,IndexError,TypeError):continue
        if not isinstance(payload,dict):continue
        for wrapper in ('record','cve'):
            if isinstance(payload.get(wrapper),dict):payload=payload[wrapper];prefix+='/'+wrapper
        identifiers={payload[k] for k in ('id','cve_id','ghsa_id') if isinstance(payload.get(k),str)}
        cve_id=(payload.get('cveMetadata') or {}).get('cveId')
        if isinstance(cve_id,str):identifiers.add(cve_id)
        identifiers.update(x for x in payload.get('aliases',[]) if isinstance(x,str))
        identifiers.update(x['value'] for x in payload.get('identifiers',[]) if isinstance(x,dict) and isinstance(x.get('value'),str))
        cves={x for x in identifiers if x.startswith('CVE-')}
        if not identifiers.intersection(aliases) or cves and cves!={detail['canonical_id']}:continue
        pointers=occurrences(payload.get('references',[]),url,prefix+'/references')
        containers=payload.get('containers') or {}
        if isinstance(containers,dict):
            cna=containers.get('cna') or {}
            if isinstance(cna,dict):pointers+=occurrences(cna.get('references',[]),url,prefix+'/containers/cna/references')
            adp=containers.get('adp') or []
            if isinstance(adp,list):
                for i,provider in enumerate(adp[:32]):
                    if isinstance(provider,dict):pointers+=occurrences(provider.get('references',[]),url,prefix+'/containers/adp/'+str(i)+'/references')
        if pointers:
            raw_ids.add(str(raw.id))
            original.extend({'source_id':str(raw.source_id),'raw_document_id':str(raw.id),
                'url':raw.source_url,'locator':{'json_pointer':p},'candidate_reference':url,
                'hash':raw.content_hash} for p in pointers)
    selected=[r for r in refs if str(r.get('raw_document_id')) in raw_ids]
    ids={r['evidence_id'] for r in selected if r.get('evidence_id')}
    rows=[]
    for identifier in sorted(ids):
        row=session.get(m.Evidence,UUID(identifier));claim=session.get(m.Claim,row.claim_id) if row else None
        if not claim or claim.vulnerability_id!=target or claim_id and str(claim.id)!=str(claim_id):continue
        rows.append(intel.serialize(row,session))
    found=classify_patch(url,())
    candidate={'reference':url,'status':'CANDIDATE' if original else 'INSUFFICIENT_EVIDENCE',
        'semantic':'PATCH_REFERENCE','patch_type':found['patch_type'],'repository':found['repository'],
        'applicability':'UNKNOWN','patch_applied':None,'vulnerability_id':str(target),
        'reference_evidence':original[:32], 'evidence_ids':sorted(ids),
        'content_checked':False,'execution_performed':False,
        'reason':'Reference listed in collected target source; commit correctness and branch applicability unproven'
            if original else 'No exact candidate reference in collected target sources'}
    return {'items':rows[:limit],'total':len(rows),'offset':0,'limit':limit,
        'candidate_reference':candidate},selected

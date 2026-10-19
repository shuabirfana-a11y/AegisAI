import json
import re
from urllib.parse import urlsplit
from hashlib import sha256
from sqlalchemy import select
from app.db import models as m
from app.repositories.ingestion import unique_row
from app.enrichment.repository import digest
from app.enrichment.contracts import CONTENT_TRUST
from app.enrichment.parsing import OFFICIAL_REPOS
from app.utils.time import parse_time

def pointer(payload,path):
    for token in path.split('/')[1:]:
        token=token.replace('~1','/').replace('~0','~')
        payload=payload[int(token)] if isinstance(payload,list) else payload[token]
    return payload

def origin(observation):
    payload=observation.normalized_payload or {}
    refs=[x.get('url','') for x in payload.get('references') or []]+(payload.get('upstream_lineage') or [])
    for url in refs:
        match=re.match(r'https://github\.com/([^/]+/[^/]+)/security/advisories/GHSA-',url)
        if match:return 'github:'+match.group(1).casefold()
    # A declared copy of this exact advisory takes precedence over a package's
    # repository hint. Otherwise OSV and the original advisory database can be
    # counted as two publishers simply because their normalized shapes differ.
    identifiers={value for value in (payload.get('external_id'),payload.get('ghsa_id'),
        getattr(observation,'external_id',None)) if isinstance(value,str) and
        re.fullmatch(r'GHSA-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}',value)}
    if len(identifiers)==1:
        identifier=next(iter(identifiers))
        for url in refs:
            try:address=urlsplit(url)
            except (ValueError,TypeError):continue
            if (address.scheme!='https' or address.hostname!='github.com' or
                address.username or address.password):continue
            match=re.fullmatch(r'/github/advisory-database/blob/[^/]+/advisories/github-reviewed/\d{4}/\d{2}/'
                r'(GHSA-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4})/\1\.json',address.path)
            if match and match.group(1)==identifier:return 'github:advisory-database'
    if str(payload.get('external_id','')).startswith('GHSA-'):
        repos={OFFICIAL_REPOS[p['name']] for p in payload.get('packages') or [] if p.get('ecosystem')=='PyPI' and p.get('name') in OFFICIAL_REPOS}
        if len(repos)==1:return 'github:'+next(iter(repos)).casefold()
    return observation.lineage_key

def evidence_fingerprint(e):
    return digest([str(e.source_id),str(e.raw_document_id),e.locator_key,e.stance,e.observed_value,e.lineage_key,
        e.details.get('classification'),e.details.get('features')])

class EvidenceService:
    @staticmethod
    def add(session,claim,observation,value,locator,*,stance='support',evidence_type='structured_source',explicit=True,details=None,excerpt=None):
        raw=session.get(m.RawDocument,observation.raw_document_id)
        if raw is None or raw.source_id!=observation.source_id:raise ValueError('Evidence requires consistent immutable raw provenance')
        if excerpt is None:
            try:excerpt=json.dumps(pointer(json.loads(raw.raw_payload),locator.get('json_pointer','')),ensure_ascii=False)
            except (ValueError,KeyError,IndexError,TypeError):excerpt=raw.raw_payload.decode('utf-8',errors='replace')
        excerpt=excerpt[:2400]
        return unique_row(session,m.Evidence,{'claim_id':claim.id,'observation_id':observation.id,'locator_key':digest(locator),'stance':stance},
            {'source_id':raw.source_id,'raw_document_id':raw.id,'scope_key':claim.scope_key,'evidence_type':evidence_type,
             'excerpt':excerpt,'excerpt_hash':sha256(excerpt.encode()).hexdigest(),'source_url':raw.source_url,
             'published_at':raw.published_at or parse_time((observation.normalized_payload or {}).get('published_at')),
             'retrieved_at':observation.retrieved_at,'locator':locator,'observed_value':value,
             'publisher':observation.publisher,'lineage_key':origin(observation),
             'details':{'explicit':explicit,'content_trust_level':CONTENT_TRUST,**(details or {})}})

def current_evidence(session,claim):
    result=[]
    for e in session.scalars(select(m.Evidence).where(m.Evidence.claim_id==claim.id)):
        obs=session.get(m.SourceObservation,e.observation_id);source=session.get(m.Source,e.source_id)
        latest=session.scalar(select(m.SourceObservation.id)
            .where(m.SourceObservation.source_id==e.source_id,m.SourceObservation.external_id==obs.external_id,
                m.SourceObservation.parse_status=='parsed').order_by(m.SourceObservation.retrieved_at.desc(),m.SourceObservation.created_at.desc(),m.SourceObservation.id.desc()).limit(1))
        incident=session.get(m.ConflictRecord,e.details['conflict_id']) if e.details.get('conflict_id') else None
        result.append({'id':str(e.id),'lineage':e.lineage_key,'authority':source.authority_level,'value':e.observed_value,
            'stance':e.stance,'retrieved_at':e.retrieved_at,'explicit':e.details.get('explicit',False),
            'is_current':latest==e.observation_id and not claim.details.get('superseded') and (incident is None or incident.status=='open'),
            'fingerprint':evidence_fingerprint(e),
            'evidence_type':e.evidence_type,'details':e.details,'source':source.source_key})
    return result

"""Immutable feed capture, bounded knowledge indexing and candidate-only links."""
import json,hashlib,re
from urllib.parse import urlencode,quote
from uuid import UUID
from sqlalchemy import select
from app.db import models as m
from app.db.persistence import store_raw
from app.repositories.ingestion import unique_row
from app.enrichment.repository import ClaimStore
from app.enrichment.evidence import EvidenceService
from app.knowledge.index import KnowledgeIndex
from app.monitoring.catalog import FEEDS,validate_url
from app.monitoring.feeds import parse_feed
from app.utils.time import utcnow

TRUST='UNTRUSTED_EXTERNAL_CONTENT'
PARSER='feed-metadata-v1'

def fingerprint(entry):
    return hashlib.sha256(json.dumps({k:v for k,v in entry.items() if k!='locator'},sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def publication_identity(key,entry):
    identity=entry['external_id']
    if key=='ARXIV':identity=re.sub(r'v\d+$','',identity.replace('http://','https://'))
    return identity

def link_candidates(session,document,observation,entry):
    text=entry['title']+'\n'+entry['content'];matches={}
    identifiers=set(re.findall(r'\b(?:CVE-\d{4}-\d{4,}|GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4})\b',text))
    if identifiers:
        for v in session.scalars(select(m.Vulnerability).where(m.Vulnerability.canonical_id.in_(identifiers),m.Vulnerability.deleted_at.is_(None)).limit(20)):
            matches[v.id]={'rule':'EXACT_IDENTIFIER_MENTION','matched':v.canonical_id}
        for v,identifier in session.execute(select(m.Vulnerability,m.ExternalIdentifier.identifier_value)
            .join(m.VulnerabilityIdentifier,m.VulnerabilityIdentifier.vulnerability_id==m.Vulnerability.id)
            .join(m.ExternalIdentifier,m.ExternalIdentifier.id==m.VulnerabilityIdentifier.identifier_id)
            .where(m.ExternalIdentifier.identifier_value.in_(identifiers),m.Vulnerability.deleted_at.is_(None)).limit(20)):
            matches[v.id]={'rule':'EXACT_IDENTIFIER_MENTION','matched':identifier}
    rows=session.execute(select(m.AffectedVersionRange.vulnerability_id,m.PackageIdentifier.package_name)
        .join(m.PackageIdentifier,m.AffectedVersionRange.package_identifier_id==m.PackageIdentifier.id).distinct().limit(200)).all()
    for target,package in rows:
        if len(package)>=4 and re.search(r'(?<![\w-])'+re.escape(package)+r'(?![\w-])',text,re.I):
            matches.setdefault(target,{'rule':'PACKAGE_KEYWORD_CANDIDATE','matched':package})
    for target,basis in list(matches.items())[:20]:
        value={'document_id':str(document.id),'document_type':document.document_type,'basis':basis,'status':'CANDIDATE'}
        claim=ClaimStore.add(session,target,'RELATED_DOCUMENT','document:'+str(document.id),value,details={'association_only':True,'no_version_or_exploit_conclusion':True})
        # XML entry metadata is a lead, not proof of vulnerability impact.
        EvidenceService.add(session,claim,observation,value,entry['locator'],evidence_type='document_association',explicit=False,
            excerpt=text[:2400],details={'extraction':'RSS/Atom metadata text','association_only':True})
        unique_row(session,m.KnowledgeVulnerabilityRelation,{'knowledge_document_id':document.id,'vulnerability_id':target,
            'relation_type':'CANDIDATE','claim_id':claim.id})
    return len(matches)

class FeedSyncService:
    def __init__(self,session_factory,*,http,embed=None):self.factory=session_factory;self.http=http;self.embed=embed
    def sync(self,key,limit=10):
        if key not in FEEDS or not 1<=limit<=100:raise ValueError('Unsupported bounded feed request')
        spec=FEEDS[key];now=utcnow();counts={'fetched':0,'created':0,'updated':0,'skipped':0,'failed':0};errors=[];raw=None;response=None
        with self.factory() as s:
            source=unique_row(s,m.Source,{'source_key':key},{'name':spec['name'],'source_type':'atom' if key=='ARXIV' else 'rss',
                'category':spec['type'],'authority_level':spec['authority'],'authority_scope':'Metadata/analysis assertions; no impact or exploit confirmation',
                'acquisition_method':'https_feed','base_url':spec['url'],'update_interval':spec['interval'],'license_scope':'Upstream metadata/limited excerpts only; original publisher terms',
                'enabled':True,'details':{'content_trust_level':TRUST}})
            source=s.scalar(select(m.Source).where(m.Source.id==source.id).with_for_update())
            if source.status=='running':return {'source':key,'status':'busy','reason':'Existing source run must finish or be explicitly recovered'}
            source_id=source.id;before=source.checkpoint or {};source.status='running';source.last_sync_at=now
            run=m.SyncRun(source_id=source_id,started_at=now,status='running',cursor_before=before,mode='incremental' if before else 'initial')
            s.add(run);s.flush();run_id=run.id
        url=spec['url']
        if key=='ARXIV':url+='?'+urlencode({'search_query':'all:LLM AND all:security','max_results':limit},quote_via=quote,safe=':')
        cache_matches=before.get('request_url')==url
        headers={k:v for k,v in [('If-None-Match',before.get('etag')),('If-Modified-Since',before.get('last_modified'))] if v and cache_matches}
        checkpoint=before
        try:
            validate_url(url);response=self.http.get(url,headers=headers or None)
            with self.factory() as s:
                if response.status_code==304:
                    raw=s.get(m.RawDocument,UUID(before['raw_id'])) if before.get('raw_id') else None
                    if not cache_matches or raw is None or raw.source_id!=source_id or raw.source_url!=url:raise ValueError('304 requires the matching cached immutable body and request URL')
                else:
                    raw=store_raw(s,source_id=source_id,external_id='feed:request:'+hashlib.sha256(url.encode()).hexdigest(),source_url=url,retrieved_at=now,
                        content_type=response.headers.get('content-type','application/xml').split(';')[0],raw_payload=response.content,
                        publisher=spec['name'],license_scope='Upstream metadata/limited excerpts only',completeness='partial',details={'content_trust_level':TRUST,'snapshot_limit':100})
                raw_id=raw.id;payload=bytes(raw.raw_payload);raw_hash=raw.content_hash
            entries=parse_feed(payload,key)[:limit]
            for entry in entries:
                counts['fetched']+=1
                try:
                    with self.factory() as s:
                        edition=fingerprint(entry)
                        doc=s.scalar(select(m.KnowledgeDocument).where(m.KnowledgeDocument.source_id==source_id,m.KnowledgeDocument.external_id==entry['external_id'],
                            m.KnowledgeDocument.deleted_at.is_(None),m.KnowledgeDocument.details['content_fingerprint'].astext==edition))
                        if doc is not None:counts['skipped']+=1;continue
                        old_edition=s.scalar(select(m.KnowledgeDocument.id).where(m.KnowledgeDocument.source_id==source_id,
                            m.KnowledgeDocument.external_id==entry['external_id'],m.KnowledgeDocument.edition==edition))
                        content_fingerprint=edition
                        if old_edition:edition+=':reappearance:'+str(run_id)
                        narrative=(entry['title']+'\n\n'+entry['content'])[:12000]
                        identity=publication_identity(key,entry)
                        prior=list(s.scalars(select(m.KnowledgeDocument).where(m.KnowledgeDocument.source_id==source_id,
                            m.KnowledgeDocument.deleted_at.is_(None),m.KnowledgeDocument.details['canonical_publication_id'].astext==identity)))
                        doc=m.KnowledgeDocument(source_id=source_id,raw_document_id=raw_id,external_id=entry['external_id'],document_type=entry['document_type'],
                            title=entry['title'],content=narrative,url=entry['url'],edition=edition,authors=entry['authors'],publisher=spec['name'],
                            published_at=entry['published_at'],modified_at=entry['modified_at'],license_scope='Metadata/limited excerpts; full text not downloaded',
                            details={'content_trust_level':TRUST,'content_fingerprint':content_fingerprint,'canonical_publication_id':identity,'is_current':True,'raw_hash':raw_hash,'extraction_xml_paths':[entry['locator']['xml_path']],
                                'extractor_version':PARSER,'content_limit':12000,'content_truncated':len(entry['title']+'\n\n'+entry['content'])>12000,
                                'ai_relevance':'relevant' if re.search(r'\b(?:AI|LLM|vllm|torch|langchain|prompt|model)\b',narrative,re.I) else 'uncertain'})
                        s.add(doc);s.flush()
                        observation=m.SourceObservation(source_id=source_id,raw_document_id=raw_id,sync_run_id=run_id,external_id=entry['external_id'],
                            record_type=entry['document_type'],retrieved_at=now,http_status=response.status_code,publisher=spec['name'],lineage_key=key,
                            parse_status='parsed',normalizer_version=PARSER,raw_locator=entry['locator'],
                            normalized_payload={k:(v.isoformat() if hasattr(v,'isoformat') else v) for k,v in entry.items()},details={'document_id':str(doc.id),'content_trust_level':TRUST})
                        s.add(observation);s.flush()
                        if self.embed is None:
                            from app.knowledge.embedding import local_embedding
                            self.embed=local_embedding()
                        KnowledgeIndex.index(s,doc,self.embed)
                        link_candidates(s,doc,observation,entry)
                        # Archive visibility only; immutable raw, content, chunks and
                        # evidence remain available by their original identities.
                        stale=any(old.modified_at and doc.modified_at and doc.modified_at<old.modified_at for old in prior)
                        if key=='ARXIV':
                            version=lambda x:int(re.search(r'v(\d+)$',x).group(1)) if re.search(r'v(\d+)$',x) else 0
                            stale=stale or any(version(doc.external_id)<version(old.external_id) for old in prior)
                        if stale:
                            doc.deleted_at=now;doc.details={**doc.details,'is_current':False,'superseded_by':str(prior[0].id)}
                        else:
                            for old in prior:
                                old.deleted_at=now;old.details={**old.details,'is_current':False,'superseded_by':str(doc.id)}
                        unique_row(s,m.IntelligenceEvent,{'event_key':'monitor:knowledge:'+str(doc.id)},
                            {'knowledge_document_id':doc.id,'source_id':source_id,'event_type':'KNOWLEDGE_DISCOVERED','detected_at':now,
                             'occurred_at':doc.published_at,'summary':doc.title,'payload':{'status':'CANDIDATE','document_type':doc.document_type}})
                        counts['created']+=1
                except Exception as e:
                    counts['failed']+=1;errors.append({'external_id':entry['external_id'],'error_type':type(e).__name__})
            if not errors:checkpoint={'etag':response.headers.get('etag') or (before.get('etag') if response.status_code==304 else None),
                'last_modified':response.headers.get('last-modified') or (before.get('last_modified') if response.status_code==304 else None),
                'raw_id':str(raw_id),'request_url':url,'snapshot_limit':100,'processed_limit':limit}
        except Exception as e:errors.append({'error_type':type(e).__name__});counts['failed']+=1
        status='partial' if errors and counts['created']+counts['skipped'] else 'failed' if errors else 'succeeded'
        with self.factory() as s:
            source=s.get(m.Source,source_id);run=s.get(m.SyncRun,run_id);source.status=status;source.checkpoint=checkpoint
            source.coverage_scope={'global_complete':False,'metadata_only':True,'snapshot_limit':100,'processed_limit':limit,
                'scope':'Bounded relevance-ranked LLM/security query; not latest-paper or exhaustive discovery' if key=='ARXIV' else 'Latest bounded feed slice; older publications not exhaustively reconciled'}
            if status=='succeeded':source.last_success_at=utcnow()
            run.status=status;run.finished_at=utcnow();run.cursor_after=checkpoint;run.coverage_scope=source.coverage_scope
            run.known_gaps={'global_complete':False,'errors':errors};run.error_summary=json.dumps(errors) if errors else None
            for name,count in counts.items():setattr(run,'records_'+name,count)
        return {'source':key,'sync_run_id':str(run_id),'status':status,**counts,'errors':errors,'content_trust_level':TRUST,'global_complete':False}

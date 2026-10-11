import hashlib,math,json
from sqlalchemy import select
from app.db import models as m
CHUNKER='char-span-v1-1000-120'

def split_chunks(text,*,size=1000,overlap=120):
    if not 0<=overlap<size or size>8000:raise ValueError('Invalid chunk size')
    if len(text)>1_000_000:raise ValueError('Document exceeds indexing limit')
    return [{'content':text[start:start+size],'start':start,'end':min(len(text),start+size)}
        for start in range(0,len(text),size-overlap) if text[start:start+size].strip()]

class KnowledgeIndex:
    @staticmethod
    def ingest(session,raw,embed):
        payload=bytes(raw.raw_payload)
        if hashlib.sha256(payload).hexdigest()!=raw.content_hash:raise ValueError('Raw hash mismatch')
        data=json.loads(payload)
        if not isinstance(data,dict):raise ValueError('Unsupported narrative payload')
        parts=[(key,data[key]) for key in ('summary','description','details','body') if isinstance(data.get(key),str) and data[key].strip()]
        if not parts:raise ValueError('No supported narrative fields')
        content='\n\n'.join(value for key,value in parts)
        doc=session.scalar(select(m.KnowledgeDocument).where(m.KnowledgeDocument.source_id==raw.source_id,
            m.KnowledgeDocument.external_id==raw.external_id,m.KnowledgeDocument.edition==raw.content_hash))
        if doc is None:
            doc=m.KnowledgeDocument(source_id=raw.source_id,raw_document_id=raw.id,external_id=raw.external_id,
                document_type='advisory',title=str(data.get('summary') or data.get('title') or raw.external_id)[:2000],content=content,
                url=raw.source_url,edition=raw.content_hash,publisher=raw.publisher,published_at=raw.published_at,license_scope=raw.license_scope,
                details={'extraction_json_pointers':['/'+key for key,value in parts],'raw_hash':raw.content_hash,
                    'extractor_version':'json-narrative-v1','content_trust_level':'UNTRUSTED_EXTERNAL_CONTENT'})
            session.add(doc);session.flush()
        return doc,KnowledgeIndex.index(session,doc,embed)

    @staticmethod
    def index(session,doc,embed):
        parts=split_chunks(doc.content or '')
        vectors=embed.passages([p['content'] for p in parts]) if parts else []
        if len(vectors)!=len(parts):raise ValueError('Embedding count mismatch')
        ids=[]
        for i,(part,vec) in enumerate(zip(parts,vectors)):
            if len(vec)!=embed.dimension or not all(math.isfinite(x) for x in vec):raise ValueError('Invalid embedding')
            chunk=session.scalar(select(m.KnowledgeChunk).where(m.KnowledgeChunk.document_id==doc.id,
                m.KnowledgeChunk.document_revision==doc.revision,m.KnowledgeChunk.chunker_version==CHUNKER,m.KnowledgeChunk.chunk_index==i))
            if chunk is None:
                chunk=m.KnowledgeChunk(document_id=doc.id,raw_document_id=doc.raw_document_id,document_revision=doc.revision,
                    chunk_index=i,chunker_version=CHUNKER,content=part['content'],content_hash=hashlib.sha256(part['content'].encode()).hexdigest(),
                    locator={'text_span':[part['start'],part['end']],'unit':'Unicode code points','source_url':doc.url,
                        'span_scope':'extracted KnowledgeDocument.content','extraction_json_pointers':(doc.details or {}).get('extraction_json_pointers',[]),
                        'raw_hash':(doc.details or {}).get('raw_hash')})
                session.add(chunk);session.flush()
            existing=session.scalar(select(m.KnowledgeEmbedding.id).where(m.KnowledgeEmbedding.chunk_id==chunk.id,m.KnowledgeEmbedding.model_version==embed.model))
            if existing is None:session.add(m.KnowledgeEmbedding(chunk_id=chunk.id,model_version=embed.model,dimensions=embed.dimension,vector=vec))
            ids.append(str(chunk.id))
        session.flush();return ids

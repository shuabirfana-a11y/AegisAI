import math
from sqlalchemy import select
from app.db import models as m
from app.knowledge.index import CHUNKER

def cosine(a,b):
    if not a or len(a)!=len(b) or not all(math.isfinite(x) for x in [*a,*b]):raise ValueError('Invalid vectors')
    na=sum(x*x for x in a);nb=sum(x*x for x in b)
    if not na or not nb:raise ValueError('Zero vector')
    return sum(x*y for x,y in zip(a,b))/math.sqrt(na*nb)

class SemanticSearch:
    @staticmethod
    def search(session,query,embed,*,limit=5):
        if not query.strip() or len(query)>2000 or not 1<=limit<=20:raise ValueError('Invalid semantic query')
        vector=embed.query(query)
        # Explicit bounded exact search; no ANN/pgvector performance claim.
        rows=session.execute(select(m.KnowledgeEmbedding,m.KnowledgeChunk,m.KnowledgeDocument,m.RawDocument)
            .join(m.KnowledgeChunk,m.KnowledgeEmbedding.chunk_id==m.KnowledgeChunk.id)
            .join(m.KnowledgeDocument,m.KnowledgeChunk.document_id==m.KnowledgeDocument.id)
            .join(m.RawDocument,m.KnowledgeChunk.raw_document_id==m.RawDocument.id)
            .where(m.KnowledgeEmbedding.model_version==embed.model,m.KnowledgeChunk.document_revision==m.KnowledgeDocument.revision,
                m.KnowledgeChunk.chunker_version==CHUNKER,m.KnowledgeDocument.deleted_at.is_(None))
            .order_by(m.KnowledgeChunk.id).limit(1001)).all()
        if len(rows)>1000:raise ValueError('Semantic collection exceeds bounded exact search capacity')
        result=[]
        for e,c,d,r in rows:
            result.append({'chunk_id':str(c.id),'document_id':str(d.id),'raw_document_id':str(r.id),'source_id':str(d.source_id),
                'title':d.title,'content':c.content,'url':d.url,'locator':c.locator,'content_hash':c.content_hash,
                'raw_hash':r.content_hash,'published_at':d.published_at,'retrieved_at':r.retrieved_at,'model':e.model_version,
                'score':cosine(vector,e.vector),'document_revision':c.document_revision,
                'content_trust_level':'UNTRUSTED_EXTERNAL_CONTENT','verification_status':'SOURCE_ASSERTED'})
        return sorted(result,key=lambda x:(-x['score'],x['chunk_id']))[:limit]

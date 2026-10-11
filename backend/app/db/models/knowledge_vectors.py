from sqlalchemy import ARRAY, Float, Integer, String, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import mapped_column
from app.db.base import Base
from app.db.types import Record, fk

class KnowledgeEmbedding(Record, Base):
    __tablename__='knowledge_embeddings'
    __table_args__=(UniqueConstraint('chunk_id','model_version'),
        CheckConstraint('dimensions>0 AND cardinality(vector)=dimensions',name='dimensions'),{'schema':'intel'})
    chunk_id=fk('intel.knowledge_chunks.id')
    model_version=mapped_column(String(200),nullable=False)
    dimensions=mapped_column(Integer,nullable=False)
    vector=mapped_column(ARRAY(Float),nullable=False)

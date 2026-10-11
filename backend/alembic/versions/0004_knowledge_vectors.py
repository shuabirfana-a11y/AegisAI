"""Phase9 additive immutable, model-versioned document embeddings."""
from alembic import op
revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('''CREATE TABLE intel.knowledge_embeddings (
      chunk_id UUID NOT NULL REFERENCES intel.knowledge_chunks(id) ON DELETE RESTRICT,
      model_version VARCHAR(200) NOT NULL, dimensions INTEGER NOT NULL, vector FLOAT[] NOT NULL,
      id UUID DEFAULT gen_random_uuid() PRIMARY KEY, created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
      metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
      CONSTRAINT uq_knowledge_embeddings_chunk_id_model_version UNIQUE(chunk_id,model_version),
      CONSTRAINT ck_knowledge_embeddings_dimensions CHECK(dimensions>0 AND cardinality(vector)=dimensions))''')
    op.execute('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON intel.knowledge_embeddings FOR EACH ROW EXECUTE FUNCTION raw.prevent_history_mutation()')

def downgrade():
    op.execute('DROP TABLE intel.knowledge_embeddings')

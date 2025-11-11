"""embeddings: switch to 1536 dims + ANN indexes

Revision ID: 0f6a5c2169b1
Revises: 9c8d6928f5e2
Create Date: 2025-11-11 11:00:54.943360
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0f6a5c2169b1"
down_revision = "9c8d6928f5e2"
branch_labels = None
depends_on = None


def upgrade():
    # Ensure pgvector exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Drop old embedding columns (any dimension) if exist
    op.execute("ALTER TABLE job_embeddings    DROP COLUMN IF EXISTS embedding;")
    op.execute("ALTER TABLE resume_embeddings DROP COLUMN IF EXISTS embedding;")
    op.execute("ALTER TABLE jobs              DROP COLUMN IF EXISTS embedding;")
    op.execute("ALTER TABLE resumes           DROP COLUMN IF EXISTS embedding;")

    # Re-create embedding columns with 1536 dims
    op.execute("ALTER TABLE job_embeddings    ADD COLUMN embedding vector(1536);")
    op.execute("ALTER TABLE resume_embeddings ADD COLUMN embedding vector(1536);")
    op.execute("ALTER TABLE jobs              ADD COLUMN embedding vector(1536);")
    op.execute("ALTER TABLE resumes           ADD COLUMN embedding vector(1536);")

    # IVF indexes for chunk-level tables
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_resume_emb_ivf
        ON resume_embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 200);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_job_emb_ivf
        ON job_embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 200);
    """)

    # Document-level IVF indexes (for coarse retrieval)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_doc_ivf
        ON jobs USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_resumes_doc_ivf
        ON resumes USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    # Helpful btree indexes for filters/joins
    op.execute("CREATE INDEX IF NOT EXISTS idx_resume_chunks_resume_id ON resume_chunks (resume_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_resume_chunks_section   ON resume_chunks (section);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_job_chunks_job_id       ON job_chunks (job_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_job_chunks_section      ON job_chunks (section);")


def downgrade():
    # Drop indexes first (order matters for PG)
    op.execute("DROP INDEX IF EXISTS idx_resumes_doc_ivf;")
    op.execute("DROP INDEX IF EXISTS idx_jobs_doc_ivf;")
    op.execute("DROP INDEX IF EXISTS idx_job_emb_ivf;")
    op.execute("DROP INDEX IF EXISTS idx_resume_emb_ivf;")
    op.execute("DROP INDEX IF EXISTS idx_resume_chunks_section;")
    op.execute("DROP INDEX IF EXISTS idx_resume_chunks_resume_id;")
    op.execute("DROP INDEX IF EXISTS idx_job_chunks_section;")
    op.execute("DROP INDEX IF EXISTS idx_job_chunks_job_id;")

    # Drop 1536-dim columns
    op.execute("ALTER TABLE job_embeddings    DROP COLUMN IF EXISTS embedding;")
    op.execute("ALTER TABLE resume_embeddings DROP COLUMN IF EXISTS embedding;")
    op.execute("ALTER TABLE jobs              DROP COLUMN IF EXISTS embedding;")
    op.execute("ALTER TABLE resumes           DROP COLUMN IF EXISTS embedding;")

    # Restore 3072-dim columns
    op.execute("ALTER TABLE job_embeddings    ADD COLUMN embedding vector(3072);")
    op.execute("ALTER TABLE resume_embeddings ADD COLUMN embedding vector(3072);")
    op.execute("ALTER TABLE jobs              ADD COLUMN embedding vector(3072);")
    op.execute("ALTER TABLE resumes           ADD COLUMN embedding vector(3072);")
